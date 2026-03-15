import os
import sys
import datetime
import re
from scipy.signal import butter, lfilter


def _parse_eds_sections(eds_path):
    """Parse EDS file into section->properties dictionary."""
    sections = {}
    current = None
    with open(eds_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1].strip()
                sections[current] = {}
                continue
            if current and "=" in line:
                key, value = line.split("=", 1)
                sections[current][key.strip()] = value.strip()
    return sections


def _parse_int_default(value_text):
    """Parse integer-like EDS default values, including hex and expressions."""
    if value_text is None:
        return None
    text = value_text.strip()
    if not text:
        return None
    if text.lower().startswith("0x"):
        try:
            return int(text, 16)
        except ValueError:
            return None
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        try:
            return int(text, 10)
        except ValueError:
            return None
    hex_values = re.findall(r"0x[0-9A-Fa-f]+", text)
    if hex_values:
        try:
            return int(hex_values[-1], 16)
        except ValueError:
            return None
    return None


def discover_pdo_signals_from_eds(eds_path):
    """Discover TPDO mapped signals from EDS.

    Returns list of dictionaries:
    {
        'key': 'Acc_x',
        'label': 'Acc_x',
        'pdo_index': '1A00',
        'position': 0,
        'object_index': 0x6001,
        'object_subindex': 0x00,
        'can_base': 0x180,
    }
    """
    if not os.path.exists(eds_path):
        return []

    sections = _parse_eds_sections(eds_path)
    tpdo_mapping_indices = ["1A00", "1A01", "1A02", "1A03"]
    discovered = []
    name_counter = {}

    for idx, pdo_map in enumerate(tpdo_mapping_indices):
        sub0_name = f"{pdo_map}sub0"
        count_val = _parse_int_default(sections.get(sub0_name, {}).get("DefaultValue"))
        if count_val is None or count_val <= 0:
            continue

        comm_idx = f"180{idx}sub1"
        can_default = _parse_int_default(sections.get(comm_idx, {}).get("DefaultValue"))
        if can_default is None:
            can_base = 0x180 + (idx * 0x100)
        else:
            can_base = can_default & 0x7FF

        for pos in range(1, int(count_val) + 1):
            map_section = f"{pdo_map}sub{pos}"
            map_default = _parse_int_default(sections.get(map_section, {}).get("DefaultValue"))
            if map_default is None or map_default == 0:
                continue

            object_index = (map_default >> 16) & 0xFFFF
            object_subindex = (map_default >> 8) & 0xFF
            object_section = f"{object_index:04X}"
            object_name = sections.get(object_section, {}).get("ParameterName", f"0x{object_index:04X}sub{object_subindex}")

            safe_name = object_name.strip().replace(" ", "_")
            count_same = name_counter.get(safe_name, 0)
            name_counter[safe_name] = count_same + 1
            key = safe_name if count_same == 0 else f"{safe_name}_{count_same + 1}"

            discovered.append(
                {
                    "key": key,
                    "label": object_name.strip(),
                    "pdo_index": pdo_map,
                    "position": pos - 1,
                    "object_index": object_index,
                    "object_subindex": object_subindex,
                    "can_base": can_base,
                }
            )

    return discovered


def discover_can_bitrate_options_from_eds(eds_path):
    """Return allowed CAN bitrate options (kbit/s) inferred from EDS CAN_Baudrate object.

    Returns list of strings such as ["1000", "500", "250", "125", "100"].
    """
    standard_kbps = [1000, 800, 500, 250, 125, 100, 50, 20, 10]

    if not os.path.exists(eds_path):
        return [str(value) for value in standard_kbps[:5]]

    sections = _parse_eds_sections(eds_path)
    bitrate_section = sections.get("600A", {})
    high_limit = _parse_int_default(bitrate_section.get("HighLimit"))
    low_limit = _parse_int_default(bitrate_section.get("LowLimit"))
    default_value = _parse_int_default(bitrate_section.get("DefaultValue"))

    if low_limit is None:
        low_limit = 0
    if high_limit is None or high_limit <= 0:
        high_limit = 1000

    options = [value for value in standard_kbps if low_limit <= value <= high_limit]
    if default_value is not None and low_limit <= default_value <= high_limit and default_value not in options:
        options.append(default_value)

    if not options:
        options = [1000]

    options = sorted(set(options), reverse=True)
    return [str(value) for value in options]

def resource_path(relative_path):
    """
    Return path to resource, works for development and PyInstaller bundles.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

def hex_to_signed_decimal(hex_string):
    """Convert a 2-byte hexadecimal string to a signed decimal integer."""
    value = int(hex_string, 16)
    if value & (1 << 15):
        return value - (1 << 16)
    return value

def decimal_to_hex_msb_lsb(decimal_value):
    """Convert a decimal value (1-2000) to MSB and LSB hex string pairs."""
    if not 1 <= decimal_value <= 2000:
        raise ValueError("Decimal value must be between 1 and 2000.")
    hex_value = hex(decimal_value)[2:].zfill(4).upper()
    msb = hex_value[:2]
    lsb = hex_value[2:]
    return msb, lsb

def elabora_frame_can(line):
    """Parse a single candump output line and extract timestamp, CAN ID and x,y,z values."""
    match = re.search(r'can0\s+([0-9A-F]+)\s+\[\d+\]\s+([0-9A-F ]+)', line)
    if match:
        can_id, data_str = match.groups()
        if can_id.upper() not in ("29D", "71D"):
            hex_numbers = data_str.split()
            if len(hex_numbers) >= 6:
                try:
                    hex_ffc3 = hex_numbers[1] + hex_numbers[0].upper()
                    hex_014b = hex_numbers[3] + hex_numbers[2].upper()
                    hex_fc55 = hex_numbers[5] + hex_numbers[4].upper()
                    x = hex_to_signed_decimal(hex_ffc3) / 1000
                    y = hex_to_signed_decimal(hex_014b) / 1000
                    z = hex_to_signed_decimal(hex_fc55) / 1000
                    timestamp = datetime.datetime.now()
                    return timestamp, can_id, x, y, z
                except ValueError:
                    return None, None, None, None, None
    return None, None, None, None, None

def butter_lowpass_filter(data, cutoff, fs, order=5):
    nyquist = 0.5 * fs
    if cutoff >= nyquist or nyquist == 0:
        return data
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = lfilter(b, a, data)
    return y

def butter_highpass_filter(data, cutoff, fs, order=5):
    nyquist = 0.5 * fs
    if cutoff >= nyquist or nyquist == 0:
        return data
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    y = lfilter(b, a, data)
    return y
