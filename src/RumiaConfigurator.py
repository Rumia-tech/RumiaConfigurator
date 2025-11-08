from PIL import Image, ImageTk
import os
import sys
import customtkinter as ctk
import subprocess
import re
import datetime
import csv
import threading
import queue
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy.signal import butter, lfilter
import pkgutil
import traceback
import platform

# Import python-can if available
try:
    import can
    try:
        interfaces_list = []
        import can.interfaces as ci
        interfaces_list = [m.name for m in pkgutil.iter_modules(ci.__path__)]
    except Exception:
        interfaces_list = []
    can_diagnostics = (
        f"python-can present, version={getattr(can, '__version__', None)}, "
        f"available interfaces={interfaces_list}"
    )
except Exception as e:
    can = None
    can_diagnostics = f"python-can import failed: {e}; traceback: {traceback.format_exc()}"

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

# Filter helper functions
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


class CanInterfaceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RumiaConfigurator")
        self.geometry("1200x800")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        # Column for the main plot area
        self.grid_columnconfigure(3, weight=3)
        self.grid_rowconfigure(1, weight=1)

        self.can_process = None
        self.can_bus = None
        self.data_points = []
        self.acquisition_active = False
        self.data_queue = queue.Queue()
        self.sampling_frequency = 0
        self.update_plot_id = None

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Frame for left-side controls
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=0, column=0, columnspan=3, rowspan=2, padx=10, pady=10, sticky="nsew")

        # Add the logo image to the controls frame (fail silently if missing)
        try:
            logo_path = resource_path("assets/Rumia_logo.png")
            self.logo_image = Image.open(logo_path)
            self.logo_image = self.logo_image.resize((70, 70))
            self.logo_tk = ImageTk.PhotoImage(self.logo_image)
            self.logo_label = ctk.CTkLabel(self.controls_frame, image=self.logo_tk, text="")
            self.logo_label.grid(row=0, column=2, rowspan=4, padx=10, pady=5, sticky="ne")
        except Exception:
            pass

        self.label_sampling = ctk.CTkLabel(self.controls_frame, text="Intervallo di campionamento (1-2000 ms):")
        self.label_sampling.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_sampling = ctk.CTkEntry(self.controls_frame, placeholder_text="Es. 1000")
        self.entry_sampling.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.checkbox_save_csv = ctk.CTkCheckBox(self.controls_frame, text="Salva dati su CSV", command=self.toggle_csv_filename_entry)
        self.checkbox_save_csv.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_csv_filename = ctk.CTkEntry(self.controls_frame, placeholder_text="Nome file CSV (es. dati.csv)")
        self.entry_csv_filename.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.entry_csv_filename.grid_remove()

        # Plot selection checkboxes
        self.label_plot_selection = ctk.CTkLabel(self.controls_frame, text="Seleziona grandezze da plottare:")
        self.label_plot_selection.grid(row=2, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        
        self.checkbox_plot_x_orig = ctk.CTkCheckBox(self.controls_frame, text="Plot X (Originale)")
        self.checkbox_plot_x_orig.grid(row=3, column=0, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_y_orig = ctk.CTkCheckBox(self.controls_frame, text="Plot Y (Originale)")
        self.checkbox_plot_y_orig.grid(row=3, column=1, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_z_orig = ctk.CTkCheckBox(self.controls_frame, text="Plot Z (Originale)")
        self.checkbox_plot_z_orig.grid(row=3, column=2, padx=(10, 5), pady=2, sticky="w")

        self.checkbox_plot_x_incl = ctk.CTkCheckBox(self.controls_frame, text="Plot X_incl (Passa-Basso)", variable=ctk.BooleanVar(value=True))
        self.checkbox_plot_x_incl.grid(row=4, column=0, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_y_incl = ctk.CTkCheckBox(self.controls_frame, text="Plot Y_incl (Passa-Basso)", variable=ctk.BooleanVar(value=True))
        self.checkbox_plot_y_incl.grid(row=4, column=1, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_z_incl = ctk.CTkCheckBox(self.controls_frame, text="Plot Z_incl (Passa-Basso)", variable=ctk.BooleanVar(value=True))
        self.checkbox_plot_z_incl.grid(row=4, column=2, padx=(10, 5), pady=2, sticky="w")

        self.checkbox_plot_x_acc = ctk.CTkCheckBox(self.controls_frame, text="Plot X_acc (Passa-Alto)")
        self.checkbox_plot_x_acc.grid(row=5, column=0, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_y_acc = ctk.CTkCheckBox(self.controls_frame, text="Plot Y_acc (Passa-Alto)")
        self.checkbox_plot_y_acc.grid(row=5, column=1, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_z_acc = ctk.CTkCheckBox(self.controls_frame, text="Plot Z_acc (Passa-Alto)")
        self.checkbox_plot_z_acc.grid(row=5, column=2, padx=(10, 5), pady=2, sticky="w")

        self.checkbox_plot_tetha_xz = ctk.CTkCheckBox(self.controls_frame, text="Plot Tetha_XZ [deg]", variable=ctk.BooleanVar(value=True))
        self.checkbox_plot_tetha_xz.grid(row=6, column=0, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_tetha_yz = ctk.CTkCheckBox(self.controls_frame, text="Plot Tetha_YZ [deg]", variable=ctk.BooleanVar(value=True))
        self.checkbox_plot_tetha_yz.grid(row=6, column=1, padx=(10, 5), pady=2, sticky="w")

        self.button_start = ctk.CTkButton(self.controls_frame, text="Invia e Avvia Acquisizione", command=self.start_acquisition)
        self.button_start.grid(row=7, column=0, padx=10, pady=10, sticky="ew")
        self.button_stop = ctk.CTkButton(self.controls_frame, text="Interrompi Acquisizione", command=self.stop_acquisition, state="disabled")
        self.button_stop.grid(row=7, column=1, padx=10, pady=10, sticky="ew")

        # Log textbox at the bottom
        self.log_textbox = ctk.CTkTextbox(self, height=150)
        self.log_textbox.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")
        self.log_textbox.insert("end", "Ready for configuration and CAN acquisition.\n")
        self.log_textbox.configure(state="disabled")
        self.grid_rowconfigure(2, weight=1)

        # Setup the Matplotlib plotting area
        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.grid(row=0, column=3, rowspan=2, padx=10, pady=10, sticky="nsew")
        self.plot_frame.grid_rowconfigure(0, weight=1)
        self.plot_frame.grid_columnconfigure(0, weight=1)

        self.fig, self.ax = plt.subplots(facecolor='#2B2B2B')
        self.ax.set_facecolor('#2B2B2B')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['top'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.spines['right'].set_color('white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        self.after(100, self.setup_can_interface_gui)
        self.after(100, self.process_data_queue)

    def log_message(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def toggle_csv_filename_entry(self):
        if self.checkbox_save_csv.get() == 1:
            self.entry_csv_filename.grid()
        else:
            self.entry_csv_filename.grid_remove()

    def setup_can_interface_gui(self):
        """
        Cross-platform setup: prefer python-can (slcan) on Windows.
        Fallback: use subprocess commands (slcand/ifconfig/can-utils) when python-can is not available.
        Default backend is slcan and default channel is COM3 (overridable via environment variables).
        """
        tty_device = os.environ.get('CAN_TTY_DEVICE', '/dev/ttyACM0')
        can_interface = os.environ.get('CAN_INTERFACE', 'can0')
        can_backend = os.environ.get('CAN_BACKEND', 'slcan')
        can_channel = os.environ.get('CAN_CHANNEL', 'COM3')

        self.log_message(f"CAN configuration: backend={can_backend} channel={can_channel} tty={tty_device}")

        if can is None:
            self.log_message("python-can not available: using system commands (Linux only).")
            try:
                process_slcand = subprocess.run(['sudo', 'slcand', '-o', '-c', '-s8', tty_device, can_interface], capture_output=True, text=True)
                self.log_message(process_slcand.stdout.strip() or "slcand executed")
                if process_slcand.stderr:
                    self.log_message(f"slcand STDERR: {process_slcand.stderr.strip()}")
                process_slcand.check_returncode()

                process_ifconfig = subprocess.run(['sudo', 'ifconfig', can_interface, 'up'], capture_output=True, text=True)
                self.log_message(process_ifconfig.stdout.strip() or "ifconfig executed")
                if process_ifconfig.stderr:
                    self.log_message(f"ifconfig STDERR: {process_ifconfig.stderr.strip()}")
                process_ifconfig.check_returncode()

                self.log_message("CAN interface configured successfully (subprocess).")
            except subprocess.CalledProcessError as e:
                self.log_message(f"Error configuring CAN interface: {e}")
                try:
                    self.log_message(f"Error details: {e.stderr.strip()}")
                except Exception:
                    pass
                self.button_start.configure(state="disabled")
            except FileNotFoundError:
                self.log_message("Error: slcand or ifconfig not found. Ensure can-utils is installed and commands are in PATH.")
                self.button_start.configure(state="disabled")
            return

        try:
            if can_backend.lower() == 'slcan':
                try:
                    self.can_bus = can.Bus(bustype='slcan', channel=can_channel, bitrate=1000000)
                    self.log_message(f"Bus created: bustype='slcan' channel={can_channel}")
                except Exception as e:
                    self.log_message(f"Failed to create slcan bus: {e}. Trying virtual fallback.")
                    try:
                        self.can_bus = can.Bus(bustype='virtual', channel='vcan0')
                        self.log_message("Virtual bus created as fallback.")
                    except Exception as e2:
                        self.log_message(f"Error creating virtual bus: {e2}")
                        self.button_start.configure(state="disabled")
            elif can_backend.lower() == 'virtual':
                self.can_bus = can.Bus(bustype='virtual', channel='vcan0')
                self.log_message("Using virtual bus.")
            elif can_backend.lower() == 'kvaser':
                try:
                    self.can_bus = can.Bus(bustype='kvaser', channel=int(can_channel))
                    self.log_message("Using kvaser backend.")
                except Exception as e:
                    self.log_message(f"Error creating kvaser bus: {e}")
                    self.button_start.configure(state="disabled")
            elif can_backend.lower() == 'pcan':
                try:
                    self.can_bus = can.Bus(bustype='pcan', channel=int(can_channel))
                    self.log_message("Using pcan backend.")
                except Exception as e:
                    self.log_message(f"Error creating pcan bus: {e}")
                    self.button_start.configure(state="disabled")
            else:
                try:
                    self.can_bus = can.Bus(bustype='slcan', channel=can_channel, bitrate=500000)
                    self.log_message(f"Bus created (fallback slcan): channel={can_channel}")
                except Exception:
                    self.can_bus = can.Bus(bustype='virtual', channel='vcan0')
                    self.log_message("Using virtual bus (fallback).")
        except Exception as e:
            self.log_message(f"Error creating python-can bus: {e}")
            self.button_start.configure(state="disabled")

    def send_can_message_gui(self, can_interface, can_id, data_string):
        """
        Send CAN message: use python-can if available, otherwise fallback to cansend (Linux).
        can_id is expected as a hex string and data_string as a continuous hex bytes string.
        """
        if getattr(self, 'can_bus', None) is not None and can is not None:
            try:
                data_bytes = bytes.fromhex(data_string)
                msg = can.Message(arbitration_id=int(can_id, 16), data=data_bytes, is_extended_id=False)
                self.can_bus.send(msg)
                self.log_message(f"CAN message sent (python-can): {can_id}#{data_string}")
            except Exception as e:
                self.log_message(f"Error sending CAN (python-can): {e}")
        else:
            try:
                process_cansend = subprocess.run(['cansend', can_interface, f'{can_id}#{data_string}'], capture_output=True, text=True)
                self.log_message(process_cansend.stdout.strip() or "cansend executed")
                if process_cansend.stderr:
                    self.log_message(f"cansend STDERR: {process_cansend.stderr.strip()}")
                process_cansend.check_returncode()
                self.log_message(f"CAN message sent: {can_interface} {can_id}#{data_string}")
            except subprocess.CalledProcessError as e:
                self.log_message(f"Error sending CAN message: {e}")
                try:
                    self.log_message(f"Error details: {e.stderr.strip()}")
                except Exception:
                    pass
            except FileNotFoundError:
                self.log_message("Error: cansend not found. Ensure can-utils is installed and cansend is in PATH.")

    def start_acquisition(self):
        if self.acquisition_active:
            self.log_message("Acquisition already in progress.")
            return

        try:
            sampling_interval = int(self.entry_sampling.get())
            if not 1 <= sampling_interval <= 2000:
                self.log_message("Invalid value. Enter a value between 1 and 2000.")
                return
            self.sampling_frequency = 1000 / sampling_interval
            self.log_message(f"Sampling frequency calculated: {self.sampling_frequency:.2f} Hz")
        except (ValueError, ZeroDivisionError):
            self.log_message("Enter a valid integer (non-zero) for the interval.")
            return

        msb, lsb = decimal_to_hex_msb_lsb(sampling_interval)
        can_message = f'2B001805{msb}{lsb}0000'
        self.log_message(f"Sending CAN message: can0 61D#{can_message}")
        self.send_can_message_gui('can0', '61D', can_message)

        if self.checkbox_save_csv.get() == 1 and not self.entry_csv_filename.get():
            self.log_message("Please enter a CSV filename.")
            return

        # Clear previous data and chart
        self.data_points = []
        self.ax.clear()
        self.ax.set_title('Sensor Data in Real Time')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Value')
        self.canvas.draw()

        self.acquisition_active = True
        self.button_start.configure(state="disabled")
        self.button_stop.configure(state="normal")
        self.log_message("Starting acquisition and real-time CAN data processing...")

        self.can_thread = threading.Thread(target=self._run_candump)
        self.can_thread.daemon = True
        self.can_thread.start()

        # Start the periodic plot update cycle
        self.update_plot()

    def _run_candump(self):
        """
        Thread for reading CAN messages.
        Use python-can self.can_bus.recv() when available; otherwise fallback to candump subprocess.
        Puts tuples (timestamp, can_id, x, y, z) into the data queue.
        """
        try:
            if getattr(self, 'can_bus', None) is not None and can is not None:
                self.log_message("Reading CAN via python-can.")
                while self.acquisition_active:
                    try:
                        msg = self.can_bus.recv(timeout=1.0)
                    except Exception as e:
                        self.log_message(f"python-can recv error: {e}")
                        break
                    if msg is None:
                        continue
                    try:
                        hex_bytes = ' '.join(f"{b:02X}" for b in msg.data)
                        line = f"can0 {msg.arbitration_id:X} [{len(msg.data)}] {hex_bytes}"
                        timestamp, can_id, x, y, z = elabora_frame_can(line)
                        if timestamp:
                            self.data_queue.put((timestamp, can_id, x, y, z))
                    except Exception as e:
                        self.log_message(f"Error parsing python-can message: {e}")
                self.log_message("python-can CAN thread terminated.")
            else:
                self.log_message("Reading CAN via candump (subprocess).")
                try:
                    self.can_process = subprocess.Popen(['candump', 'can0'], stdout=subprocess.PIPE, text=True, bufsize=1)
                    for line in iter(self.can_process.stdout.readline, ''):
                        if not self.acquisition_active:
                            break
                        line = line.strip()
                        if line:
                            timestamp, can_id, x, y, z = elabora_frame_can(line)
                            if timestamp:
                                self.data_queue.put((timestamp, can_id, x, y, z))
                    if self.can_process and self.can_process.stdout:
                        self.can_process.stdout.close()
                        self.can_process.wait()
                except FileNotFoundError:
                    self.log_message("Error: candump not found.")
                except Exception as e:
                    self.log_message(f"Error in candump thread: {e}")
        except Exception as e:
            self.log_message(f"Error in CAN thread: {e}")

        self.acquisition_active = False
        self.after(0, self.update_buttons_state)
        self.log_message("candump thread terminated.")
        

    def process_data_queue(self):
        while not self.data_queue.empty():
            data = self.data_queue.get()
            self.data_points.append(data)
        self.after(100, self.process_data_queue)

    def stop_acquisition(self):
        if self.acquisition_active:
            self.log_message("Stopping data acquisition...")
            self.acquisition_active = False
            # Cancel scheduled plot update if present
            if self.update_plot_id:
                self.after_cancel(self.update_plot_id)
                self.update_plot_id = None
            if self.can_process and self.can_process.poll() is None:
                try:
                    self.can_process.terminate()
                    self.can_process.wait()
                    self.log_message("candump process terminated.")
                except Exception as e:
                    self.log_message(f"Error terminating candump process: {e}")
        else:
            self.log_message("No acquisition in progress to stop.")

        self.update_buttons_state()

        # Trigger CSV save if required and data exist
        if self.data_points and self.checkbox_save_csv.get() == 1:
            self.save_data_to_csv()
        elif not self.data_points:
            self.log_message("No data acquired.")


    def update_buttons_state(self):
        if self.acquisition_active:
            self.button_start.configure(state="disabled")
            self.button_stop.configure(state="normal")
        else:
            self.button_start.configure(state="normal")
            self.button_stop.configure(state="disabled")

    def update_plot(self):
        """Update the Matplotlib plot with current data."""
        if not self.acquisition_active or len(self.data_points) < 2:
            if self.acquisition_active:
                self.update_plot_id = self.after(500, self.update_plot)
            return

        self.ax.clear()

        time_data = [dp[0] for dp in self.data_points]
        x_data_orig = np.array([dp[2] for dp in self.data_points])
        y_data_orig = np.array([dp[3] for dp in self.data_points])
        z_data_orig = np.array([dp[4] for dp in self.data_points])

        if self.sampling_frequency > 0:
            cutoff_lowpass = 1.0
            cutoff_highpass = 1.0
            x_incl = butter_lowpass_filter(x_data_orig, cutoff_lowpass, self.sampling_frequency)
            y_incl = butter_lowpass_filter(y_data_orig, cutoff_lowpass, self.sampling_frequency)
            z_incl = butter_lowpass_filter(z_data_orig, cutoff_lowpass, self.sampling_frequency)
            x_acc = butter_highpass_filter(x_data_orig, cutoff_highpass, self.sampling_frequency)
            y_acc = butter_highpass_filter(y_data_orig, cutoff_highpass, self.sampling_frequency)
            z_acc = butter_highpass_filter(z_data_orig, cutoff_highpass, self.sampling_frequency)
            tetha_xz = np.degrees(np.arctan2(x_incl, z_incl))
            tetha_yz = np.degrees(np.arctan2(y_incl, z_incl))
        else:
            x_incl, y_incl, z_incl, x_acc, y_acc, z_acc, tetha_xz, tetha_yz = (np.array([]),) * 8

        if self.checkbox_plot_x_orig.get(): self.ax.plot(time_data, x_data_orig, label='x (Orig)')
        if self.checkbox_plot_y_orig.get(): self.ax.plot(time_data, y_data_orig, label='y (Orig)')
        if self.checkbox_plot_z_orig.get(): self.ax.plot(time_data, z_data_orig, label='z (Orig)')

        if self.checkbox_plot_x_incl.get(): self.ax.plot(time_data, x_incl, label='x_incl', linestyle='--')
        if self.checkbox_plot_y_incl.get(): self.ax.plot(time_data, y_incl, label='y_incl', linestyle='--')
        if self.checkbox_plot_z_incl.get(): self.ax.plot(time_data, z_incl, label='z_incl', linestyle='--')

        if self.checkbox_plot_x_acc.get(): self.ax.plot(time_data, x_acc, label='x_acc', linestyle=':')
        if self.checkbox_plot_y_acc.get(): self.ax.plot(time_data, y_acc, label='y_acc', linestyle=':')
        if self.checkbox_plot_z_acc.get(): self.ax.plot(time_data, z_acc, label='z_acc', linestyle=':')
        
        if self.checkbox_plot_tetha_xz.get(): self.ax.plot(time_data, tetha_xz, label='Tetha_XZ [deg]', linestyle='-.')
        if self.checkbox_plot_tetha_yz.get(): self.ax.plot(time_data, tetha_yz, label='Tetha_YZ [deg]', linestyle='-.')
        
        # Plot styling and formatting
        self.ax.legend(fontsize='small', loc='upper left', bbox_to_anchor=(1, 1), facecolor='#363636', labelcolor='white')
        self.ax.set_title('Sensor Data in Real Time', color='white')
        self.ax.set_xlabel('Time', color='white')
        self.ax.set_ylabel('Value', color='white')
        
        date_format = mdates.DateFormatter('%H:%M:%S')
        self.ax.xaxis.set_major_formatter(date_format)
        self.fig.autofmt_xdate()
        self.fig.tight_layout(rect=[0, 0, 0.8, 1])

        self.canvas.draw()
        
        self.update_plot_id = self.after(500, self.update_plot)

    def save_data_to_csv(self):
        """Save collected data to a CSV file."""
        csv_filename = self.entry_csv_filename.get()
        if not csv_filename:
            self.log_message("CSV save skipped: no filename provided.")
            return

        if not self.data_points:
            self.log_message("No data to save.")
            return

        self.log_message(f"Saving {len(self.data_points)} data points to {csv_filename}...")
        
        x_data_orig = np.array([dp[2] for dp in self.data_points])
        y_data_orig = np.array([dp[3] for dp in self.data_points])
        z_data_orig = np.array([dp[4] for dp in self.data_points])
        
        if self.sampling_frequency > 0:
            cutoff = 1.0
            x_incl = butter_lowpass_filter(x_data_orig, cutoff, self.sampling_frequency)
            y_incl = butter_lowpass_filter(y_data_orig, cutoff, self.sampling_frequency)
            z_incl = butter_lowpass_filter(z_data_orig, cutoff, self.sampling_frequency)
            x_acc = butter_highpass_filter(x_data_orig, cutoff, self.sampling_frequency)
            y_acc = butter_highpass_filter(y_data_orig, cutoff, self.sampling_frequency)
            z_acc = butter_highpass_filter(z_data_orig, cutoff, self.sampling_frequency)
            tetha_xz = np.degrees(np.arctan2(x_incl, z_incl))
            tetha_yz = np.degrees(np.arctan2(y_incl, z_incl))
        else:
            x_incl, y_incl, z_incl, x_acc, y_acc, z_acc, tetha_xz, tetha_yz = ([None] * len(self.data_points),) * 8

        try:
            with open(csv_filename, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Timestamp', 'CAN ID', 'x [g]', 'y [g]', 'z [g]',
                                     'x_incl [g]', 'y_incl [g]', 'z_incl [g]',
                                     'x_acc [g]', 'y_acc [g]', 'z_acc [g]',
                                     'Tetha_XZ [deg]', 'Tetha_YZ [deg]'])
                for i, (ts, cid, xv, yv, zv) in enumerate(self.data_points):
                    csv_writer.writerow([
                        ts.strftime('%Y-%m-%d %H:%M:%S.%f'), cid, xv, yv, zv,
                        x_incl[i], y_incl[i], z_incl[i],
                        x_acc[i], y_acc[i], z_acc[i],
                        tetha_xz[i], tetha_yz[i]
                    ])
            self.log_message(f"Data successfully saved to {csv_filename}")
        except Exception as e:
            self.log_message(f"Error saving CSV: {e}")


if __name__ == "__main__":
    app = CanInterfaceApp()
    app.mainloop()