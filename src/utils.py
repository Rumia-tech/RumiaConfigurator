import os
import sys
import datetime
import re
from scipy.signal import butter, lfilter

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
    lsb = hex_value[:2]
    msb = hex_value[2:]
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
