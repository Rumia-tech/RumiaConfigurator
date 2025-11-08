from PIL import Image, ImageTk
import os
import sys
import customtkinter as ctk
import csv
import queue
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

from utils import (
    resource_path,
    decimal_to_hex_msb_lsb,
    butter_lowpass_filter,
    butter_highpass_filter,
)
from plotting import setup_plot_figure, finalize_layout
from can_interface import CanController


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

        self.can_controller = CanController(log_callback=self.log_message)
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

        # Use plotting helpers; adjust colors for dark theme
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
        """Setup CAN interface using CanController."""
        success = self.can_controller.setup_bus()
        if not success:
            self.button_start.configure(state="disabled")

    def send_can_message_gui(self, can_interface, can_id, data_string):
        """Send CAN message via CanController."""
        self.can_controller.send_message(can_interface, can_id, data_string)

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

        # Start CAN reader using CanController
        def data_received(timestamp, can_id, x, y, z):
            self.data_queue.put((timestamp, can_id, x, y, z))
        
        def should_stop():
            return not self.acquisition_active
        
        self.can_controller.start_reader(data_received, should_stop)

        # Start the periodic plot update cycle
        self.update_plot()

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
            # Stop CAN reader
            self.can_controller.stop_reader()
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