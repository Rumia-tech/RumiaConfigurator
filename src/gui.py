from PIL import Image, ImageTk
import customtkinter as ctk
import csv
import queue
from serial.tools import list_ports

from utils import resource_path, decimal_to_hex_msb_lsb
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
        self.data_points = []
        self.acquisition_active = False
        self.data_queue = queue.Queue()
        self.sampling_frequency = 0
        self.update_plot_id = None

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._create_controls()
        self._create_log_area()
        self._create_plot_area()

        # Setup CAN and start data queue processing
        self.after(100, self.setup_can_interface_gui)
        self.after(100, self.process_data_queue)

    def _create_controls(self):
        """Create the control panel with input fields and buttons."""
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=0, column=0, columnspan=3, rowspan=2, padx=10, pady=10, sticky="nsew")

        # Logo
        try:
            logo_path = resource_path("assets/Rumia_logo.png")
            self.logo_image = Image.open(logo_path)
            self.logo_image = self.logo_image.resize((70, 70))
            self.logo_tk = ImageTk.PhotoImage(self.logo_image)
            self.logo_label = ctk.CTkLabel(self.controls_frame, image=self.logo_tk, text="")
            self.logo_label.grid(row=0, column=2, rowspan=4, padx=10, pady=5, sticky="ne")
        except Exception:
            pass

        # Sampling interval input
        self.label_sampling = ctk.CTkLabel(self.controls_frame, text="Intervallo di campionamento (1-2000 ms):")
        self.label_sampling.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_sampling = ctk.CTkEntry(self.controls_frame, placeholder_text="Es. 1000")
        self.entry_sampling.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        # COM port selection (SLCAN)
        self.label_com = ctk.CTkLabel(self.controls_frame, text="Porta COM (SLCAN):")
        self.label_com.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.com_var = ctk.StringVar(value="Auto")
        self.com_menu = ctk.CTkOptionMenu(self.controls_frame, values=["Auto"], variable=self.com_var)
        self.com_menu.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.button_refresh_com = ctk.CTkButton(self.controls_frame, text="Refresh", command=self.refresh_com_ports, width=80)
        self.button_refresh_com.grid(row=1, column=2, padx=10, pady=5, sticky="e")

        # CSV save options
        self.checkbox_save_csv = ctk.CTkCheckBox(
            self.controls_frame, text="Salva dati su CSV", command=self.toggle_csv_filename_entry
        )
        self.checkbox_save_csv.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_csv_filename = ctk.CTkEntry(self.controls_frame, placeholder_text="Nome file CSV (es. dati.csv)")
        self.entry_csv_filename.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.entry_csv_filename.grid_remove()

        # Plot selection checkboxes
        self.label_plot_selection = ctk.CTkLabel(self.controls_frame, text="Seleziona grandezze da plottare:")
        self.label_plot_selection.grid(row=3, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        
        self.checkbox_plot_x_orig = ctk.CTkCheckBox(self.controls_frame, text="Plot X (Originale)")
        self.checkbox_plot_x_orig.grid(row=4, column=0, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_y_orig = ctk.CTkCheckBox(self.controls_frame, text="Plot Y (Originale)")
        self.checkbox_plot_y_orig.grid(row=4, column=1, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_z_orig = ctk.CTkCheckBox(self.controls_frame, text="Plot Z (Originale)")
        self.checkbox_plot_z_orig.grid(row=4, column=2, padx=(10, 5), pady=2, sticky="w")

        self.checkbox_plot_x_incl = ctk.CTkCheckBox(
            self.controls_frame, text="Plot X_incl (Passa-Basso)", variable=ctk.BooleanVar(value=True)
        )
        self.checkbox_plot_x_incl.grid(row=5, column=0, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_y_incl = ctk.CTkCheckBox(
            self.controls_frame, text="Plot Y_incl (Passa-Basso)", variable=ctk.BooleanVar(value=True)
        )
        self.checkbox_plot_y_incl.grid(row=5, column=1, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_z_incl = ctk.CTkCheckBox(
            self.controls_frame, text="Plot Z_incl (Passa-Basso)", variable=ctk.BooleanVar(value=True)
        )
        self.checkbox_plot_z_incl.grid(row=5, column=2, padx=(10, 5), pady=2, sticky="w")

        self.checkbox_plot_x_acc = ctk.CTkCheckBox(self.controls_frame, text="Plot X_acc (Passa-Alto)")
        self.checkbox_plot_x_acc.grid(row=6, column=0, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_y_acc = ctk.CTkCheckBox(self.controls_frame, text="Plot Y_acc (Passa-Alto)")
        self.checkbox_plot_y_acc.grid(row=6, column=1, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_z_acc = ctk.CTkCheckBox(self.controls_frame, text="Plot Z_acc (Passa-Alto)")
        self.checkbox_plot_z_acc.grid(row=6, column=2, padx=(10, 5), pady=2, sticky="w")

        self.checkbox_plot_tetha_xz = ctk.CTkCheckBox(
            self.controls_frame, text="Plot Tetha_XZ [deg]", variable=ctk.BooleanVar(value=True)
        )
        self.checkbox_plot_tetha_xz.grid(row=7, column=0, padx=(10, 5), pady=2, sticky="w")
        self.checkbox_plot_tetha_yz = ctk.CTkCheckBox(
            self.controls_frame, text="Plot Tetha_YZ [deg]", variable=ctk.BooleanVar(value=True)
        )
        self.checkbox_plot_tetha_yz.grid(row=7, column=1, padx=(10, 5), pady=2, sticky="w")

        # Action buttons
        self.button_start = ctk.CTkButton(
            self.controls_frame, text="Invia e Avvia Acquisizione", command=self.start_acquisition
        )
        self.button_start.grid(row=8, column=0, padx=10, pady=10, sticky="ew")
        self.button_stop = ctk.CTkButton(
            self.controls_frame, text="Interrompi Acquisizione", command=self.stop_acquisition, state="disabled"
        )
        self.button_stop.grid(row=8, column=1, padx=10, pady=10, sticky="ew")

    def _create_log_area(self):
        """Create the log textbox at the bottom."""
        self.log_textbox = ctk.CTkTextbox(self, height=150)
        self.log_textbox.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")
        self.log_textbox.insert("end", "Ready for configuration and CAN acquisition.\n")
        self.log_textbox.configure(state="disabled")
        self.grid_rowconfigure(2, weight=1)

    def _create_plot_area(self):
        """Create the matplotlib plotting area with dark theme."""
        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.grid(row=0, column=3, rowspan=2, padx=10, pady=10, sticky="nsew")
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

    def send_can_message_gui(self, can_interface, can_id, data_string):
        """Send CAN message via CanController."""
        self.can_controller.send_message(can_interface, can_id, data_string)

    def start_acquisition(self):
        """Start CAN data acquisition."""
        if self.acquisition_active:
            self.log_message("Acquisition already in progress.")
            return

        # Validate sampling interval
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

        # Setup CAN bus dynamically based on COM selection
        selected_com = self.com_var.get()
        if selected_com == "Auto":
            ports = self.get_com_ports()
            if ports:
                selected_com = ports[0]
                self.log_message(f"Selezione automatica porta COM: {selected_com}")
            else:
                self.log_message("Nessuna porta COM disponibile per slcan.")
                return
        # Attempt bus setup
        success = self.can_controller.setup_bus(backend='slcan', channel=selected_com, bitrate=1000000)
        if not success:
            self.log_message("Impossibile inizializzare il bus CAN.")
            return

        # Send CAN configuration message
        msb, lsb = decimal_to_hex_msb_lsb(sampling_interval)
        can_message = f'2B001805{msb}{lsb}0000'
        self.log_message(f"Sending CAN message: can0 61D#{can_message}")
        self.send_can_message_gui('can0', '61D', can_message)

        # Validate CSV filename if saving
        if self.checkbox_save_csv.get() == 1 and not self.entry_csv_filename.get():
            self.log_message("Please enter a CSV filename.")
            return

        # Clear previous data and plot
        self.data_points = []
        self.plot_manager.clear_plot()

        # Update UI state
        self.acquisition_active = True
        self.button_start.configure(state="disabled")
        self.button_stop.configure(state="normal")
        self.log_message("Starting acquisition and real-time CAN data processing...")

        # Start CAN reader
        def data_received(timestamp, can_id, x, y, z):
            self.data_queue.put((timestamp, can_id, x, y, z))
        
        def should_stop():
            return not self.acquisition_active
        
        self.can_controller.start_reader(data_received, should_stop)

        # Start plot update cycle
        self.update_plot()

    def process_data_queue(self):
        """Process incoming data from the queue."""
        while not self.data_queue.empty():
            data = self.data_queue.get()
            self.data_points.append(data)
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
        """Update the plot with current data using PlotManager."""
        if not self.acquisition_active or len(self.data_points) < 2:
            if self.acquisition_active:
                self.update_plot_id = self.after(500, self.update_plot)
            return

        # Get plot options from checkboxes
        plot_options = {
            'x_orig': self.checkbox_plot_x_orig.get(),
            'y_orig': self.checkbox_plot_y_orig.get(),
            'z_orig': self.checkbox_plot_z_orig.get(),
            'x_incl': self.checkbox_plot_x_incl.get(),
            'y_incl': self.checkbox_plot_y_incl.get(),
            'z_incl': self.checkbox_plot_z_incl.get(),
            'x_acc': self.checkbox_plot_x_acc.get(),
            'y_acc': self.checkbox_plot_y_acc.get(),
            'z_acc': self.checkbox_plot_z_acc.get(),
            'tetha_xz': self.checkbox_plot_tetha_xz.get(),
            'tetha_yz': self.checkbox_plot_tetha_yz.get(),
        }

        # Delegate to PlotManager
        self.plot_manager.process_and_plot(self.data_points, self.sampling_frequency, plot_options)
        
        self.update_plot_id = self.after(500, self.update_plot)

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
        
        # Compute filtered data using PlotManager
        filtered = self.plot_manager.compute_filtered_data(self.data_points, self.sampling_frequency)

        try:
            with open(csv_filename, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow([
                    'Timestamp', 'CAN ID', 'x [g]', 'y [g]', 'z [g]',
                    'x_incl [g]', 'y_incl [g]', 'z_incl [g]',
                    'x_acc [g]', 'y_acc [g]', 'z_acc [g]',
                    'Tetha_XZ [deg]', 'Tetha_YZ [deg]'
                ])
                for i, (ts, cid, xv, yv, zv) in enumerate(self.data_points):
                    csv_writer.writerow([
                        ts.strftime('%Y-%m-%d %H:%M:%S.%f'), cid, xv, yv, zv,
                        filtered['x_incl'][i], filtered['y_incl'][i], filtered['z_incl'][i],
                        filtered['x_acc'][i], filtered['y_acc'][i], filtered['z_acc'][i],
                        filtered['tetha_xz'][i], filtered['tetha_yz'][i]
                    ])
            self.log_message(f"Data successfully saved to {csv_filename}")
        except Exception as e:
            self.log_message(f"Error saving CSV: {e}")
