from PIL import Image, ImageTk
import customtkinter as ctk
import csv
import queue
import time
import os
from tkinter import messagebox
from serial.tools import list_ports

from utils import (
    resource_path,
    decimal_to_hex_msb_lsb,
    discover_pdo_signals_from_eds,
    discover_can_bitrate_options_from_eds,
)
from plotting import setup_plot_figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from can_interface import CanController
from plot_manager import PlotManager


class CanInterfaceApp(ctk.CTk):
    """Main GUI application for CAN data acquisition and visualization."""
    
    def __init__(self):
        super().__init__()

        self.title("RumiaConfigurator")
        self.geometry("1200x800")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=3)  # Main plot area
        self.grid_rowconfigure(1, weight=1)

        # Initialize controllers and state
        self.can_controller = CanController(log_callback=self.log_message)
        self.can_controller.set_traffic_callback(self.handle_can_traffic)
        self.data_points = []
        self.acquisition_active = False
        self.data_queue = queue.Queue()
        self.sampling_frequency = 1.0
        self.update_plot_id = None
        self.config_entries = {}
        self.supported_config_params = self._build_config_parameter_definitions()
        self.can_traffic_log = []
        self.sdo_rx_queue = queue.Queue()
        self._last_traffic_signature = None
        self._last_traffic_monotonic = 0.0
        self.last_custom_frame_var = ctk.StringVar(value="Last custom frame: -")
        self.can_bitrate_options_kbps = discover_can_bitrate_options_from_eds(self._get_eds_file_path())
        self.can_bitrate_var = ctk.StringVar(value=self.can_bitrate_options_kbps[0])
        self.pdo_signal_vars = {}
        self.pdo_signal_definitions = discover_pdo_signals_from_eds(self._get_eds_file_path())
        self.pdo_decode_map = {}

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Create tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, columnspan=3, rowspan=2, padx=10, pady=10, sticky="nsew")
        
        self.data_tab = self.tabview.add("Data")
        self.config_tab = self.tabview.add("Configuration")
        self.developer_tab = self.tabview.add("Developer")

        self._create_data_controls()
        self._create_config_controls()
        self._create_developer_tab()
        self._create_log_area()
        self._create_plot_area()

        # Setup CAN and start data queue processing
        self.after(100, self.setup_can_interface_gui)
        self.after(100, self.process_data_queue)

    def _create_data_controls(self):
        """Create the Data tab with plot selection and acquisition controls."""
        self.data_tab.grid_columnconfigure(0, weight=1)
        self.data_tab.grid_columnconfigure(1, weight=1)
        self.data_tab.grid_columnconfigure(2, weight=1)
        self.data_tab.grid_rowconfigure(0, weight=0)

        # CSV save options
        self.checkbox_save_csv = ctk.CTkCheckBox(
            self.data_tab, text="Salva dati su CSV", command=self.toggle_csv_filename_entry
        )
        self.checkbox_save_csv.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_csv_filename = ctk.CTkEntry(self.data_tab, placeholder_text="Nome file CSV (es. dati.csv)")
        self.entry_csv_filename.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.entry_csv_filename.grid_remove()

        # Plot selection checkboxes
        self.label_plot_selection = ctk.CTkLabel(
            self.data_tab,
            text="Seleziona grandezze PDO da plottare (rilevate da SmartIMU.eds):",
        )
        self.label_plot_selection.grid(row=1, column=0, padx=10, pady=5, sticky="w", columnspan=3)

        pdo_row = 2
        pdo_col = 0
        if not self.pdo_signal_definitions:
            ctk.CTkLabel(self.data_tab, text="Nessun segnale PDO trovato in SmartIMU.eds").grid(
                row=pdo_row, column=0, padx=10, pady=4, sticky="w", columnspan=3
            )
            pdo_row += 1
        else:
            for i, signal in enumerate(self.pdo_signal_definitions):
                checked = i < 3
                var = ctk.BooleanVar(value=checked)
                checkbox = ctk.CTkCheckBox(self.data_tab, text=signal["label"], variable=var)
                checkbox.grid(row=pdo_row, column=pdo_col, padx=(10, 5), pady=2, sticky="w")
                self.pdo_signal_vars[signal["key"]] = var
                pdo_col += 1
                if pdo_col > 2:
                    pdo_col = 0
                    pdo_row += 1

            if pdo_col != 0:
                pdo_row += 1

# Tab with configuration controls
# COM port selection
    def _create_config_controls(self):
        """Create the Configuration tab with COM port settings."""
        self.config_tab.grid_columnconfigure(0, weight=1)
        self.config_tab.grid_columnconfigure(1, weight=1)
        self.config_tab.grid_columnconfigure(2, weight=0)
        self.config_tab.grid_columnconfigure(3, weight=0)
        self.config_tab.grid_columnconfigure(4, weight=0)
        self.config_tab.grid_columnconfigure(5, weight=0)

        # COM port selection (SLCAN)
        self.label_com = ctk.CTkLabel(self.config_tab, text="Porta COM (SLCAN):")
        self.label_com.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.com_var = ctk.StringVar(value="Auto")
        self.com_menu = ctk.CTkOptionMenu(self.config_tab, values=["Auto"], variable=self.com_var)
        self.com_menu.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.button_refresh_com = ctk.CTkButton(self.config_tab, text="Refresh", command=self.refresh_com_ports, width=80)
        self.button_refresh_com.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        self.label_can_bitrate = ctk.CTkLabel(self.config_tab, text="CANbus bitrate [kbit/s]:")
        self.label_can_bitrate.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.menu_can_bitrate = ctk.CTkOptionMenu(
            self.config_tab,
            values=self.can_bitrate_options_kbps,
            variable=self.can_bitrate_var,
            width=120,
        )
        self.menu_can_bitrate.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.button_detect_bitrate = ctk.CTkButton(
            self.config_tab,
            text="Detect bitrate",
            width=120,
            command=self.detect_can_bitrate,
        )
        self.button_detect_bitrate.grid(row=1, column=2, padx=10, pady=5, sticky="e")
        
        # Action buttons
        self.button_start = ctk.CTkButton(
            self.config_tab, text="SmartIMU connection", command=self.start_acquisition
        )
        self.button_start.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.button_stop = ctk.CTkButton(
            self.config_tab, text="SmartIMU disconnection", command=self.stop_acquisition, state="disabled"
        )
        self.button_stop.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.button_read_config = ctk.CTkButton(
            self.config_tab,
            text="Current configuration acquisition",
            command=self.request_current_configuration,
        )
        self.button_read_config.grid(row=2, column=2, padx=10, pady=10, sticky="ew")

        self.label_config_title = ctk.CTkLabel(
            self.config_tab,
            text="All configuration (CANopen SDO)",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.label_config_title.grid(row=3, column=0, padx=10, pady=(8, 4), sticky="w", columnspan=4)

        row = 4
        for param in self.supported_config_params:
            ctk.CTkLabel(self.config_tab, text=f"{param['label']}:").grid(
                row=row, column=0, padx=10, pady=4, sticky="w"
            )
            entry_var = ctk.StringVar(value="")
            entry = ctk.CTkEntry(self.config_tab, textvariable=entry_var)
            entry.grid(row=row, column=1, padx=10, pady=4, sticky="ew")
            self.config_entries[param["key"]] = entry

            send_btn = ctk.CTkButton(
                self.config_tab,
                text="Send",
                width=80,
                command=lambda k=param["key"]: self.send_config_parameter(k),
            )
            send_btn.grid(row=row, column=2, padx=10, pady=4, sticky="ew")
            row += 1

        ctk.CTkLabel(self.config_tab, text="Accelerometer filter: (not available in EDS)").grid(
            row=row, column=0, padx=10, pady=4, sticky="w"
        )
        disabled_acc_filter = ctk.CTkEntry(self.config_tab, placeholder_text="N/A", state="disabled")
        disabled_acc_filter.grid(row=row, column=1, padx=10, pady=4, sticky="ew")
        row += 1

        ctk.CTkLabel(self.config_tab, text="Gyroscope filter: (not available in EDS)").grid(
            row=row, column=0, padx=10, pady=4, sticky="w"
        )
        disabled_gyro_filter = ctk.CTkEntry(self.config_tab, placeholder_text="N/A", state="disabled")
        disabled_gyro_filter.grid(row=row, column=1, padx=10, pady=4, sticky="ew")

    def _create_developer_tab(self):
        """Create Developer tab with full CAN message log and export controls."""
        self.developer_tab.grid_columnconfigure(0, weight=1)
        self.developer_tab.grid_columnconfigure(1, weight=0)
        self.developer_tab.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.developer_tab,
            text="Developer - CAN Traffic",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")

        control_frame = ctk.CTkFrame(self.developer_tab)
        control_frame.grid(row=0, column=1, padx=12, pady=(10, 6), sticky="e")

        self.dev_export_filename_var = ctk.StringVar(value="can_traffic_log.csv")
        self.dev_export_filename_entry = ctk.CTkEntry(
            control_frame,
            textvariable=self.dev_export_filename_var,
            width=220,
            placeholder_text="Nome file log CAN",
        )
        self.dev_export_filename_entry.grid(row=0, column=0, padx=6, pady=6, sticky="ew")

        self.dev_export_button = ctk.CTkButton(
            control_frame,
            text="Export Log",
            command=self.export_can_traffic_log,
            width=120,
        )
        self.dev_export_button.grid(row=0, column=1, padx=6, pady=6)

        self.dev_clear_button = ctk.CTkButton(
            control_frame,
            text="Clear",
            command=self.clear_can_traffic_log,
            width=90,
        )
        self.dev_clear_button.grid(row=0, column=2, padx=6, pady=6)

        self.dev_log_textbox = ctk.CTkTextbox(self.developer_tab, height=320)
        self.dev_log_textbox.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="nsew")
        self.dev_log_textbox.insert("end", "CAN traffic log ready.\n")
        self.dev_log_textbox.configure(state="disabled")

        self._create_custom_can_controls(self.developer_tab, row=2, column=0, columnspan=2)

    def _create_custom_can_controls(self, parent, row, column=0, columnspan=1):
        """Create custom CAN sender controls in the provided tab/frame."""
        self.custom_can_frame = ctk.CTkFrame(parent)
        self.custom_can_frame.grid(row=row, column=column, columnspan=columnspan, padx=12, pady=(0, 12), sticky="ew")
        try:
            self.custom_can_frame.grid_columnconfigure(0, weight=0)
            self.custom_can_frame.grid_columnconfigure(1, weight=0)
            self.custom_can_frame.grid_columnconfigure(2, weight=0)
            self.custom_can_frame.grid_columnconfigure(3, weight=0)
            self.custom_can_frame.grid_columnconfigure(4, weight=1)
        except Exception:
            pass

        ctk.CTkLabel(self.custom_can_frame, text="Custom CAN Message").grid(
            row=0, column=0, padx=(10, 5), pady=(8, 4), sticky="w", columnspan=2
        )
        ctk.CTkLabel(self.custom_can_frame, text="Address").grid(row=1, column=0, padx=(10, 5), pady=(4, 4), sticky="w")
        self.custom_addr_var = ctk.StringVar(value="000")
        self.custom_addr_entry = ctk.CTkEntry(self.custom_can_frame, textvariable=self.custom_addr_var, width=70)
        self.custom_addr_entry.grid(row=1, column=1, padx=(0, 15), pady=(4, 4), sticky="w")

        ctk.CTkLabel(self.custom_can_frame, text="DLC").grid(row=1, column=2, padx=(0, 5), pady=(4, 4), sticky="w")
        self.custom_dlc_var = ctk.StringVar(value="8")
        self.custom_dlc_menu = ctk.CTkOptionMenu(
            self.custom_can_frame,
            values=[str(i) for i in range(0, 9)],
            variable=self.custom_dlc_var,
            width=60,
        )
        self.custom_dlc_menu.grid(row=1, column=3, padx=(0, 10), pady=(4, 4), sticky="w")

        self.custom_data_frame = ctk.CTkFrame(self.custom_can_frame)
        self.custom_data_frame.grid(row=2, column=0, columnspan=5, padx=10, pady=(0, 4), sticky="w")
        for i in range(8):
            ctk.CTkLabel(self.custom_data_frame, text=str(i + 1)).grid(row=0, column=i, padx=5, pady=(0, 2))

        self.custom_data_vars = []
        self.custom_data_entries = []
        for i in range(8):
            var = ctk.StringVar(value="00")
            ent = ctk.CTkEntry(self.custom_data_frame, textvariable=var, width=40)
            ent.grid(row=1, column=i, padx=5)
            self.custom_data_vars.append(var)
            self.custom_data_entries.append(ent)

        self.custom_send_btn = ctk.CTkButton(self.custom_can_frame, text="Send", command=self.send_custom_can)
        self.custom_send_btn.grid(row=3, column=0, padx=10, pady=(4, 8), sticky="w")

        self.custom_last_frame_label = ctk.CTkLabel(
            self.custom_can_frame,
            textvariable=self.last_custom_frame_var,
            anchor="w",
        )
        self.custom_last_frame_label.grid(row=3, column=1, columnspan=4, padx=(10, 10), pady=(4, 8), sticky="w")

        def _custom_update_data_state(*_):
            try:
                n = int(self.custom_dlc_var.get())
            except Exception:
                n = 8
            n = max(0, min(8, n))
            for idx, ent in enumerate(self.custom_data_entries):
                if idx < n:
                    ent.configure(state="normal")
                else:
                    ent.configure(state="disabled")
                    self.custom_data_vars[idx].set("00")

        self.custom_dlc_var.trace_add("write", lambda *_: _custom_update_data_state())
        _custom_update_data_state()

    def _build_config_parameter_definitions(self):
        """Return supported CANopen parameters inferred from SmartIMU EDS."""
        return [
            {
                "key": "heartbeat",
                "label": "Heartbeat [ms]",
                "index": 0x1017,
                "subindex": 0x00,
                "dtype": "u16",
                "min": 0,
                "max": 60000,
                "default": 1000,
            },
            {
                "key": "node_id",
                "label": "Node ID",
                "index": 0x1280,
                "subindex": 0x03,
                "dtype": "u8",
                "min": 1,
                "max": 127,
                "default": 29,
            },
            {
                "key": "tpdo1_period",
                "label": "TPDO1 period [ms]",
                "index": 0x1800,
                "subindex": 0x05,
                "dtype": "u16",
                "min": 0,
                "max": 65535,
                "default": 500,
            },
            {
                "key": "tpdo2_period",
                "label": "TPDO2 period [ms]",
                "index": 0x1801,
                "subindex": 0x05,
                "dtype": "u16",
                "min": 0,
                "max": 65535,
                "default": 500,
            },
            {
                "key": "acc_range",
                "label": "Accelerometer range",
                "index": 0x6007,
                "subindex": 0x00,
                "dtype": "u8",
                "min": 0,
                "max": 3,
                "default": 3,
            },
            {
                "key": "gyro_range",
                "label": "Gyroscope range",
                "index": 0x6008,
                "subindex": 0x00,
                "dtype": "u8",
                "min": 0,
                "max": 4,
                "default": 4,
            },
            {
                "key": "can_term",
                "label": "CAN termination resistor",
                "index": 0x6009,
                "subindex": 0x00,
                "dtype": "u8",
                "min": 0,
                "max": 1,
                "default": 0,
            },
        ]

    def _create_plot_area(self):
        """Create the matplotlib plotting area inside the Data tab with dark theme."""
        # Configure Data tab grid to accommodate plot
        self.data_tab.grid_columnconfigure(3, weight=3)
        
        self.plot_frame = ctk.CTkFrame(self.data_tab)
        self.plot_frame.grid(row=0, column=3, rowspan=9, padx=10, pady=10, sticky="nsew")
        self.plot_frame.grid_rowconfigure(0, weight=1)
        self.plot_frame.grid_columnconfigure(0, weight=1)

        # Setup plot with dark theme
        self.fig, self.ax = setup_plot_figure(figsize=(8, 6))
        try:
            self.fig.set_facecolor('#2B2B2B')
        except Exception:
            pass
        self.ax.set_facecolor('#2B2B2B')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        for spine in ('bottom', 'top', 'left', 'right'):
            self.ax.spines[spine].set_color('white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Initialize PlotManager
        self.plot_manager = PlotManager(self.ax, self.canvas, cutoff_lowpass=1.0, cutoff_highpass=1.0)
    
    def _create_log_area(self):
        """Create the log textbox at the bottom."""
        self.log_textbox = ctk.CTkTextbox(self, height=150)
        self.log_textbox.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")
        self.log_textbox.insert("end", "Ready for configuration and CAN acquisition.\n")
        self.log_textbox.configure(state="disabled")
        self.grid_rowconfigure(2, weight=1)

    def log_message(self, message):
        """Add a message to the log textbox."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def toggle_csv_filename_entry(self):
        """Show/hide CSV filename entry based on checkbox."""
        if self.checkbox_save_csv.get() == 1:
            self.entry_csv_filename.grid()
        else:
            self.entry_csv_filename.grid_remove()

    def get_com_ports(self):
        """Retrieve available COM ports for potential SLCAN devices."""
        return self.can_controller.list_slcan_ports()

    def refresh_com_ports(self):
        """Refresh COM port list and update option menu."""
        ports = self.get_com_ports()
        if ports:
            values = ["Auto"] + ports
            self.com_menu.configure(values=values)
            # Keep current selection if still valid
            if self.com_var.get() not in values:
                self.com_var.set("Auto")
            self.log_message(f"Porte COM trovate: {', '.join(ports)}")
            self.button_start.configure(state="normal")
        else:
            self.com_menu.configure(values=["Auto"])
            self.com_var.set("Auto")
            self.log_message("Nessuna porta COM trovata.")
            # Disable start until a port appears
            self.button_start.configure(state="disabled")

    def setup_can_interface_gui(self):
        """Initial GUI setup: refresh COM ports (delay bus init until start)."""
        self.refresh_com_ports()

    def _get_eds_file_path(self):
        """Return SmartIMU.eds path using workspace-first and bundle fallback."""
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "SmartIMU.eds"),
            resource_path("SmartIMU.eds"),
        ]
        for candidate in candidates:
            normalized = os.path.abspath(candidate)
            if os.path.exists(normalized):
                return normalized
        return os.path.abspath(candidates[0])

    def _build_pdo_runtime_map(self):
        """Build CAN-ID to signal key map using current node ID and EDS PDO definitions."""
        try:
            node_id = self._get_sensor_node_id()
        except Exception:
            node_id = 0x1D

        runtime_map = {}
        for signal in self.pdo_signal_definitions:
            can_id = int(signal["can_base"]) + int(node_id)
            runtime_map.setdefault(can_id, []).append(signal)
        for can_id in runtime_map:
            runtime_map[can_id] = sorted(runtime_map[can_id], key=lambda item: item["position"])
        self.pdo_decode_map = runtime_map

    def _decode_pdo_signals(self, can_id, x_value, y_value, z_value):
        """Decode parsed XYZ tuple into named PDO signals based on current EDS mapping."""
        if not self.pdo_decode_map:
            return {}

        try:
            can_id_int = int(can_id, 16) if isinstance(can_id, str) else int(can_id)
        except Exception:
            return {}

        mapping = self.pdo_decode_map.get(can_id_int)
        if not mapping:
            return {}

        values = [x_value, y_value, z_value]
        decoded = {}
        for signal in mapping:
            position = int(signal["position"])
            if 0 <= position < len(values):
                decoded[signal["key"]] = values[position]
        return decoded

    def send_can_message_gui(self, can_interface, can_id, data_string):
        """Send CAN message via CanController."""
        self._log_tx_frame(can_id=can_id, data_string=data_string, source="gui-send")
        self.can_controller.send_message(can_interface, can_id, data_string)

    def start_acquisition(self):
        """Start CAN data acquisition."""
        if self.acquisition_active:
            self.log_message("Acquisition already in progress.")
            return

        # Ensure CAN bus is ready
        if not self.ensure_can_bus_initialized():
            return

        # Validate CSV filename if saving
        if self.checkbox_save_csv.get() == 1 and not self.entry_csv_filename.get():
            self.log_message("Please enter a CSV filename.")
            return

        # Clear previous data and plot
        self.data_points = []
        self.plot_manager.clear_plot()
        self._build_pdo_runtime_map()
        
        # Initialize sampling frequency (will be calculated from received data)
        self.sampling_frequency = 1.0

        # Update UI state
        self.acquisition_active = True
        self.button_start.configure(state="disabled")
        self.button_stop.configure(state="normal")
        self.log_message("Starting acquisition and real-time CAN data processing...")

        self.log_message("Acquisizione attiva su tutti i CAN ID; decodifica PDO da SmartIMU.eds.")
        
        def data_received(timestamp, can_id, x, y, z):
            decoded_signals = self._decode_pdo_signals(can_id, x, y, z)
            if not decoded_signals:
                return
            self.data_queue.put(
                {
                    "timestamp": timestamp,
                    "can_id": can_id,
                    "signals": decoded_signals,
                }
            )
        
        def should_stop():
            return not self.acquisition_active
        
        self.can_controller.start_reader(data_received, should_stop)

        # Start plot update cycle
        self.update_plot()
        self.log_message("Plot update cycle started.")

    def process_data_queue(self):
        """Process incoming data from the queue."""
        count = 0
        while not self.data_queue.empty():
            data = self.data_queue.get()
            self.data_points.append(data)
            count += 1
        if count > 0 and self.acquisition_active:
            self.log_message(f"Processed {count} data points. Total: {len(self.data_points)}")
        self.after(100, self.process_data_queue)

    def stop_acquisition(self):
        """Stop CAN data acquisition."""
        if self.acquisition_active:
            self.log_message("Stopping data acquisition...")
            self.acquisition_active = False
            
            # Cancel plot update
            if self.update_plot_id:
                self.after_cancel(self.update_plot_id)
                self.update_plot_id = None
            
            # Stop CAN reader
            self.can_controller.stop_reader()
        else:
            self.log_message("No acquisition in progress to stop.")

        self.update_buttons_state()

        # Save CSV if requested
        if self.data_points and self.checkbox_save_csv.get() == 1:
            self.save_data_to_csv()
        elif not self.data_points:
            self.log_message("No data acquired.")

    def update_buttons_state(self):
        """Update button states based on acquisition status."""
        if self.acquisition_active:
            self.button_start.configure(state="disabled")
            self.button_stop.configure(state="normal")
        else:
            self.button_start.configure(state="normal")
            self.button_stop.configure(state="disabled")

    def update_plot(self):
        """Update the plot with current data using PlotManager every 300ms."""
        if not self.acquisition_active:
            return
            
        if len(self.data_points) >= 2:
            selected_signal_keys = self._get_selected_pdo_keys()
            self.plot_manager.process_and_plot_pdo_signals(self.data_points, selected_signal_keys)
        
        # Schedule next update in 300ms
        self.update_plot_id = self.after(300, self.update_plot)

    def _get_selected_pdo_keys(self):
        """Return currently selected PDO signal keys from Data tab checkboxes."""
        return [key for key, var in self.pdo_signal_vars.items() if var.get()]

    def ensure_can_bus_initialized(self) -> bool:
        """Ensure CAN bus is initialized using current COM selection. Returns True on success."""
        if self.can_controller.can_bus is not None:
            return True

        bitrate, err = self._get_selected_bitrate_bps()
        if err:
            self.log_message(err)
            messagebox.showerror("CAN bitrate", err)
            return False

        selected_com = self.com_var.get()
        if selected_com == "Auto":
            ports = self.get_com_ports()
            if ports:
                selected_com = ports[0]
                self.log_message(f"Selezione automatica porta COM: {selected_com}")
            else:
                self.log_message("Nessuna porta COM disponibile per slcan.")
                return False
        success = self.can_controller.setup_bus(backend='slcan', channel=selected_com, bitrate=bitrate)
        if success:
            return True

        self.log_message(f"Init CAN fallita con bitrate {bitrate}. Provo rilevazione automatica...")
        detected = self.can_controller.probe_bitrate(
            backend='slcan',
            channel=selected_com,
            candidates=[1000000, 500000, 250000, 125000, 100000],
            per_bitrate_timeout=0.8,
        )
        if detected is None:
            self.log_message("Impossibile inizializzare il bus CAN: bitrate non rilevato.")
            return False

        self.can_bitrate_var.set(str(detected))
        self.log_message(f"Bitrate rilevato automaticamente: {detected} bps")
        retry_ok = self.can_controller.setup_bus(backend='slcan', channel=selected_com, bitrate=detected)
        if not retry_ok:
            self.log_message("Impossibile inizializzare il bus CAN anche dopo rilevazione bitrate.")
            return False

        return True

    def _get_selected_bitrate_bps(self):
        """Parse selected bitrate option from dropdown (kbit/s -> bps)."""
        raw_text = self.can_bitrate_var.get().strip()
        if not raw_text:
            return None, "CANbus bitrate mancante."

        try:
            value_kbps = int(raw_text, 10)
        except ValueError:
            return None, f"CANbus bitrate non valido: {raw_text}"

        if value_kbps <= 0:
            return None, "CANbus bitrate deve essere maggiore di zero."

        bitrate_bps = value_kbps * 1000

        if not (10000 <= bitrate_bps <= 5000000):
            return None, f"CANbus bitrate fuori range: {bitrate_bps} bps"
        return bitrate_bps, None

    def detect_can_bitrate(self):
        """Probe common CAN bitrates and update bitrate entry with detected value."""
        if self.acquisition_active:
            msg = "Stop acquisition before detecting CAN bitrate."
            self.log_message(msg)
            messagebox.showwarning("CAN bitrate", msg)
            return

        selected_com = self.com_var.get()
        if selected_com == "Auto":
            ports = self.get_com_ports()
            if ports:
                selected_com = ports[0]
                self.log_message(f"Selezione automatica porta COM: {selected_com}")
            else:
                self.log_message("Nessuna porta COM disponibile per bitrate detection.")
                messagebox.showwarning("CAN bitrate", "Nessuna porta COM disponibile.")
                return

        if self.can_controller.can_bus is not None:
            self.can_controller.shutdown()

        self.log_message("Bitrate detection in progress...")
        detected = self.can_controller.probe_bitrate(
            backend='slcan',
            channel=selected_com,
            candidates=[1000000, 500000, 250000, 125000, 100000],
            per_bitrate_timeout=0.8,
        )

        if detected is None:
            self.log_message("No CAN bitrate detected.")
            messagebox.showwarning("CAN bitrate", "Unable to detect CAN bitrate automatically.")
            return

        detected_kbps = detected // 1000 if detected % 1000 == 0 else None
        if detected_kbps is not None:
            detected_kbps_str = str(detected_kbps)
            if detected_kbps_str not in self.can_bitrate_options_kbps:
                self.can_bitrate_options_kbps.append(detected_kbps_str)
                self.can_bitrate_options_kbps = sorted(
                    set(self.can_bitrate_options_kbps), key=lambda item: int(item), reverse=True
                )
                self.menu_can_bitrate.configure(values=self.can_bitrate_options_kbps)
            self.can_bitrate_var.set(detected_kbps_str)
        else:
            self.log_message(f"Detected bitrate {detected} bps non allineato ai kbit/s della lista.")
        self.log_message(f"Detected CAN bitrate: {detected} bps")
        messagebox.showinfo("CAN bitrate", f"Detected CAN bitrate: {detected} bps")

    def send_custom_can(self):
        """Read custom CAN fields from main GUI and send the message."""
        # Validate address
        addr_txt = self.custom_addr_var.get().strip().upper()
        if not addr_txt:
            self.log_message("Address mancante.")
            return
        try:
            addr_val = int(addr_txt, 16)
        except ValueError:
            self.log_message("Address non valido (usa 3 cifre hex 000-7FF).")
            return
        if not (0 <= addr_val <= 0x7FF):
            self.log_message("Address fuori range (0-7FF).")
            return
        addr_txt = f"{addr_val:03X}"

        # DLC and data
        try:
            n = int(self.custom_dlc_var.get())
        except Exception:
            n = 8
        n = max(0, min(8, n))

        bytes_list = []
        for i in range(n):
            b = self.custom_data_vars[i].get().strip().upper()
            if b == "":
                b = "00"
            if len(b) == 1:
                b = "0" + b
            if len(b) != 2:
                self.log_message(f"Byte {i+1} non valido: '{b}'.")
                return
            try:
                int(b, 16)
            except ValueError:
                self.log_message(f"Byte {i+1} non valido: '{b}'.")
                return
            bytes_list.append(b)

        data_string = ''.join(bytes_list)

        # Ensure bus
        if not self.ensure_can_bus_initialized():
            return

        # Send
        self._log_tx_frame(can_id=addr_txt, data_string=data_string, source="gui-custom")
        success = self.can_controller.send_message('can0', addr_txt, data_string)
        if success:
            self.log_message(f"Inviato: can0 {addr_txt}#[{n}] { ' '.join(bytes_list) if n>0 else '' }")
            self.last_custom_frame_var.set(
                f"Last custom frame: {addr_txt}#[{n}] {(' '.join(bytes_list) if n > 0 else '')}"
            )
        else:
            self.log_message("Invio CAN fallito.")

    def _get_sensor_node_id(self):
        """Return SmartIMU node id from Configuration parameters entry."""
        node_entry = self.config_entries.get("node_id")
        node_text = node_entry.get().strip() if node_entry is not None else "29"
        if not node_text:
            node_text = "29"
        try:
            node_id = int(node_text, 0)
        except ValueError:
            raise ValueError("Node ID non valido. Usa valore numerico (es. 29 o 0x1D).")
        if not (0 <= node_id <= 0x7F):
            raise ValueError("Node ID fuori range (0-127).")
        return node_id

    def _send_sdo_request(self, index, subindex, payload, action_label):
        """Send an SDO request to 0x600 + node_id."""
        if not self.ensure_can_bus_initialized():
            return False

        try:
            node_id = self._get_sensor_node_id()
        except ValueError as e:
            self.log_message(str(e))
            messagebox.showerror("Node ID error", str(e))
            return False

        cob_id = f"{0x600 + node_id:03X}"
        self._log_tx_frame(can_id=cob_id, data_string=payload, source="gui-sdo")
        ok = self.can_controller.send_message("can0", cob_id, payload)
        if ok:
            self.log_message(f"{action_label} sent on {cob_id}: {payload}")
            return True

        err = f"Errore invio SDO ({action_label}) su {cob_id}."
        self.log_message(err)
        messagebox.showerror("CANopen SDO error", err)
        return False

    def _build_sdo_write_payload(self, index, subindex, value, dtype):
        """Build expedited SDO download payload (8 bytes) for u8/u16/u32."""
        idx_lo = index & 0xFF
        idx_hi = (index >> 8) & 0xFF

        if dtype == "u8":
            return f"2F{idx_lo:02X}{idx_hi:02X}{subindex:02X}{value & 0xFF:02X}000000"
        if dtype == "u16":
            b0 = value & 0xFF
            b1 = (value >> 8) & 0xFF
            return f"2B{idx_lo:02X}{idx_hi:02X}{subindex:02X}{b0:02X}{b1:02X}0000"
        if dtype == "u32":
            b0 = value & 0xFF
            b1 = (value >> 8) & 0xFF
            b2 = (value >> 16) & 0xFF
            b3 = (value >> 24) & 0xFF
            return f"23{idx_lo:02X}{idx_hi:02X}{subindex:02X}{b0:02X}{b1:02X}{b2:02X}{b3:02X}"
        raise ValueError(f"Unsupported SDO dtype: {dtype}")

    def _build_sdo_read_payload(self, index, subindex):
        """Build expedited SDO upload request payload (8 bytes)."""
        idx_lo = index & 0xFF
        idx_hi = (index >> 8) & 0xFF
        return f"40{idx_lo:02X}{idx_hi:02X}{subindex:02X}00000000"

    def _parse_sdo_upload_response(self, data_bytes, expected_index, expected_subindex):
        """Parse SDO upload response payload and return (value, error_message)."""
        if len(data_bytes) < 8:
            return None, "Risposta SDO troppo corta."

        command = data_bytes[0]
        index = data_bytes[1] | (data_bytes[2] << 8)
        subindex = data_bytes[3]

        if index != expected_index or subindex != expected_subindex:
            return None, "Risposta SDO con index/subindex non atteso."

        if command == 0x80:
            abort_code = int.from_bytes(data_bytes[4:8], byteorder="little", signed=False)
            return None, f"SDO abort 0x{abort_code:08X}"

        command_to_length = {0x4F: 1, 0x4B: 2, 0x47: 3, 0x43: 4}
        value_len = command_to_length.get(command)
        if value_len is None:
            return None, f"Comando SDO upload non supportato: 0x{command:02X}"

        value_bytes = bytes(data_bytes[4:4 + value_len])
        value = int.from_bytes(value_bytes, byteorder="little", signed=False)
        return value, None

    def _parse_sdo_write_response(self, data_bytes, expected_index, expected_subindex):
        """Parse SDO download response and return (ok, error_message)."""
        if len(data_bytes) < 8:
            return False, "Risposta SDO troppo corta."

        command = data_bytes[0]
        index = data_bytes[1] | (data_bytes[2] << 8)
        subindex = data_bytes[3]

        if index != expected_index or subindex != expected_subindex:
            return False, "Risposta SDO con index/subindex non atteso."

        if command == 0x80:
            abort_code = int.from_bytes(data_bytes[4:8], byteorder="little", signed=False)
            return False, f"SDO abort 0x{abort_code:08X}"

        if command != 0x60:
            return False, f"Comando SDO download non supportato: 0x{command:02X}"

        return True, None

    def _drain_sdo_rx_queue(self):
        """Discard pending RX entries before a new SDO request."""
        try:
            while True:
                self.sdo_rx_queue.get_nowait()
        except queue.Empty:
            return

    def _wait_for_sdo_response(self, node_id, expected_index, expected_subindex, timeout_sec=0.6):
        """Wait for expected SDO response using RX queue fed by CAN reader callback."""
        expected_cob_id = f"{0x580 + node_id:03X}"
        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            remaining = max(0.01, deadline - time.monotonic())
            try:
                frame = self.sdo_rx_queue.get(timeout=remaining)
            except queue.Empty:
                continue

            can_id = str(frame.get("can_id", "")).upper()
            if can_id != expected_cob_id:
                continue

            data_str = str(frame.get("data", "")).strip().upper()
            if len(data_str) < 16:
                continue

            try:
                data_bytes = bytes.fromhex(data_str[:16])
            except ValueError:
                continue

            value, err = self._parse_sdo_upload_response(data_bytes, expected_index, expected_subindex)
            if err:
                return None, err
            return value, None

        return None, "Timeout risposta SDO"

    def _wait_for_sdo_write_ack(self, node_id, expected_index, expected_subindex, timeout_sec=0.7):
        """Wait for SDO write acknowledgement frame (0x60) from node response COB-ID."""
        expected_cob_id = f"{0x580 + node_id:03X}"
        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            remaining = max(0.01, deadline - time.monotonic())
            try:
                frame = self.sdo_rx_queue.get(timeout=remaining)
            except queue.Empty:
                continue

            can_id = str(frame.get("can_id", "")).upper()
            if can_id != expected_cob_id:
                continue

            data_str = str(frame.get("data", "")).strip().upper()
            if len(data_str) < 16:
                continue

            try:
                data_bytes = bytes.fromhex(data_str[:16])
            except ValueError:
                continue

            ok, err = self._parse_sdo_write_response(data_bytes, expected_index, expected_subindex)
            if not ok:
                return False, err
            return True, None

        return False, "Timeout risposta SDO"

    def _get_param_definition(self, key):
        for param in self.supported_config_params:
            if param["key"] == key:
                return param
        return None

    def send_config_parameter(self, key):
        """Write one parameter to SmartIMU via CANopen SDO download."""
        param = self._get_param_definition(key)
        if param is None:
            self.log_message(f"Parametro sconosciuto: {key}")
            return

        entry = self.config_entries.get(key)
        if entry is None:
            self.log_message(f"Entry non trovata per {key}")
            return

        raw_value = entry.get().strip()
        try:
            value = int(raw_value, 0)
        except ValueError:
            msg = f"Valore non valido per {param['label']}: {raw_value}"
            self.log_message(msg)
            messagebox.showerror("Validation error", msg)
            entry.delete(0, "end")
            return

        if not (param["min"] <= value <= param["max"]):
            msg = f"Valore fuori range per {param['label']}: {value} (ammesso {param['min']}..{param['max']})"
            self.log_message(msg)
            messagebox.showerror("Validation error", msg)
            entry.delete(0, "end")
            return

        payload = self._build_sdo_write_payload(param["index"], param["subindex"], value, param["dtype"])
        self._drain_sdo_rx_queue()
        sent = self._send_sdo_request(param["index"], param["subindex"], payload, f"Write {param['label']}")
        if not sent:
            entry.delete(0, "end")
            return

        try:
            node_id = self._get_sensor_node_id()
        except ValueError as e:
            self.log_message(str(e))
            entry.delete(0, "end")
            return

        ok, err = self._wait_for_sdo_write_ack(
            node_id=node_id,
            expected_index=param["index"],
            expected_subindex=param["subindex"],
            timeout_sec=0.7,
        )
        if ok:
            self.log_message(f"Write {param['label']} confirmed by SDO response.")
            return

        self.log_message(f"Write {param['label']} failed: {err}")
        messagebox.showwarning("SDO write", f"{param['label']}: {err}")
        entry.delete(0, "end")

    def request_current_configuration(self):
        """Acquire all supported SDO config values and update Configuration fields."""
        if not self.ensure_can_bus_initialized():
            return

        try:
            node_id = self._get_sensor_node_id()
        except ValueError as e:
            self.log_message(str(e))
            messagebox.showerror("Node ID error", str(e))
            return

        self.log_message("Current configuration acquisition avviata...")
        success_count = 0

        for param in self.supported_config_params:
            self._drain_sdo_rx_queue()
            payload = self._build_sdo_read_payload(param["index"], param["subindex"])
            sent_ok = self._send_sdo_request(param["index"], param["subindex"], payload, f"Read {param['label']}")
            if not sent_ok:
                continue

            value, err = self._wait_for_sdo_response(
                node_id=node_id,
                expected_index=param["index"],
                expected_subindex=param["subindex"],
                timeout_sec=0.7,
            )

            if err:
                self.log_message(f"Read {param['label']} fallita: {err}")
                messagebox.showwarning("Current configuration", f"{param['label']}: {err}")
                continue

            entry = self.config_entries.get(param["key"])
            if entry is not None:
                entry.delete(0, "end")
                entry.insert(0, str(value))
            success_count += 1
            self.log_message(f"{param['label']} = {value}")

        self.log_message(
            f"Current configuration acquisition completata: {success_count}/{len(self.supported_config_params)}"
        )

    def handle_can_traffic(self, message):
        """Capture CAN traffic from controller and append to Developer tab safely."""
        direction = str(message.get("direction", "")).upper()
        if direction == "RX":
            self.sdo_rx_queue.put(
                {
                    "timestamp": message.get("timestamp"),
                    "can_id": str(message.get("can_id", "")).upper(),
                    "data": str(message.get("data", "")).upper(),
                    "source": message.get("source", "unknown"),
                }
            )
        self.after(0, lambda m=message: self._append_can_traffic_entry(m))

    def _append_can_traffic_entry(self, message):
        """Append one CAN traffic message to memory and developer textbox."""
        ts = message.get("timestamp")
        if hasattr(ts, "strftime"):
            ts_text = ts.strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            try:
                ts_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts)))
            except Exception:
                ts_text = "N/A"

        direction = str(message.get("direction", "?")).upper()
        can_id = str(message.get("can_id", "???")).upper()
        data = str(message.get("data", "")).upper()
        source = str(message.get("source", "unknown"))

        signature = (direction, can_id, data)
        now_mono = time.monotonic()
        if signature == self._last_traffic_signature and (now_mono - self._last_traffic_monotonic) < 0.15:
            return
        self._last_traffic_signature = signature
        self._last_traffic_monotonic = now_mono

        dlc = len(data) // 2 if data else 0
        row = {
            "timestamp": ts_text,
            "direction": direction,
            "can_id": can_id,
            "dlc": dlc,
            "data": data,
            "source": source,
        }
        self.can_traffic_log.append(row)

        line = f"{ts_text} | {direction} | ID:{can_id} | DLC:{dlc} | DATA:{data} | {source}\n"
        self.dev_log_textbox.configure(state="normal")
        self.dev_log_textbox.insert("end", line)
        self.dev_log_textbox.see("end")
        self.dev_log_textbox.configure(state="disabled")

    def _log_tx_frame(self, can_id, data_string, source):
        """Best-effort TX logging from GUI send paths."""
        try:
            can_id_norm = f"{int(str(can_id).strip(), 16):03X}"
        except Exception:
            can_id_norm = str(can_id).strip().upper()

        self.handle_can_traffic(
            {
                "timestamp": time.time(),
                "direction": "TX",
                "can_id": can_id_norm,
                "data": str(data_string).strip().upper(),
                "source": source,
            }
        )

    def clear_can_traffic_log(self):
        """Clear in-memory and visible CAN traffic log in Developer tab."""
        self.can_traffic_log = []
        self.dev_log_textbox.configure(state="normal")
        self.dev_log_textbox.delete("1.0", "end")
        self.dev_log_textbox.insert("end", "CAN traffic log cleared.\n")
        self.dev_log_textbox.configure(state="disabled")
        self.log_message("Developer CAN traffic log cleared.")

    def export_can_traffic_log(self):
        """Export complete CAN traffic history shown in Developer tab."""
        filename = self.dev_export_filename_var.get().strip()
        if not filename:
            self.log_message("Export CAN log annullato: nome file mancante.")
            messagebox.showerror("Export CAN log", "Inserisci un nome file per il log CAN.")
            return

        if not self.can_traffic_log:
            self.log_message("Export CAN log annullato: nessun messaggio CAN disponibile.")
            messagebox.showwarning("Export CAN log", "Nessun messaggio CAN da esportare.")
            return

        try:
            with open(filename, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Timestamp", "Direction", "CAN ID", "DLC", "Data", "Source"])
                for row in self.can_traffic_log:
                    writer.writerow(
                        [
                            row["timestamp"],
                            row["direction"],
                            row["can_id"],
                            row["dlc"],
                            row["data"],
                            row["source"],
                        ]
                    )
            self.log_message(f"Log CAN esportato in {filename}")
        except Exception as e:
            self.log_message(f"Errore export log CAN: {e}")
            messagebox.showerror("Export CAN log", f"Errore export log CAN: {e}")

    def save_data_to_csv(self):
        """Save collected data to CSV file."""
        csv_filename = self.entry_csv_filename.get()
        if not csv_filename:
            self.log_message("CSV save skipped: no filename provided.")
            return

        if not self.data_points:
            self.log_message("No data to save.")
            return

        self.log_message(f"Saving {len(self.data_points)} data points to {csv_filename}...")
        selected_keys = self._get_selected_pdo_keys()
        if not selected_keys:
            self.log_message("CSV export annullato: nessuna curva selezionata nel grafico.")
            messagebox.showwarning("CSV export", "Seleziona almeno una curva da plottare prima di esportare.")
            return

        key_to_label = {item["key"]: item["label"] for item in self.pdo_signal_definitions}

        try:
            with open(csv_filename, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                headers = ["Timestamp", "CAN ID"] + [key_to_label.get(key, key) for key in selected_keys]
                csv_writer.writerow(headers)

                for record in self.data_points:
                    ts = record.get("timestamp")
                    cid = record.get("can_id")
                    signals = record.get("signals", {})
                    row = [
                        ts.strftime('%Y-%m-%d %H:%M:%S.%f') if hasattr(ts, "strftime") else str(ts),
                        cid,
                    ]
                    row.extend(signals.get(key, "") for key in selected_keys)
                    csv_writer.writerow(row)
            self.log_message(f"Data successfully saved to {csv_filename}")
        except Exception as e:
            self.log_message(f"Error saving CSV: {e}")
