import numpy as np
import matplotlib.dates as mdates
from utils import butter_lowpass_filter, butter_highpass_filter


class PlotManager:
    """
    Manages plot data processing, filtering, and rendering.
    Separates plotting logic from GUI code.
    """
    
    def __init__(self, ax, canvas, cutoff_lowpass=1.0, cutoff_highpass=1.0):
        """
        Args:
            ax: matplotlib Axes object
            canvas: FigureCanvasTkAgg object
            cutoff_lowpass: cutoff frequency for lowpass filter
            cutoff_highpass: cutoff frequency for highpass filter
        """
        self.ax = ax
        self.canvas = canvas
        self.cutoff_lowpass = cutoff_lowpass
        self.cutoff_highpass = cutoff_highpass
        
    def clear_plot(self, title='Sensor Data in Real Time', xlabel='Time', ylabel='Value'):
        """Clear the plot and set default labels."""
        self.ax.clear()
        self.ax.set_title(title, color='white')
        self.ax.set_xlabel(xlabel, color='white')
        self.ax.set_ylabel(ylabel, color='white')
        self.canvas.draw()
    
    def process_and_plot(self, data_points, sampling_frequency, plot_options):
        """
        Process data with filters and plot selected signals.
        
        Args:
            data_points: list of tuples (timestamp, can_id, x, y, z)
            sampling_frequency: sampling frequency in Hz
            plot_options: dict with boolean flags for each plot type
                {
                    'x_orig', 'y_orig', 'z_orig',
                    'x_incl', 'y_incl', 'z_incl',
                    'x_acc', 'y_acc', 'z_acc',
                    'tetha_xz', 'tetha_yz'
                }
        """
        if len(data_points) < 2:
            return
        
        self.ax.clear()
        
        # Extract raw data
        time_data = [dp[0] for dp in data_points]
        x_data_orig = np.array([dp[2] for dp in data_points])
        y_data_orig = np.array([dp[3] for dp in data_points])
        z_data_orig = np.array([dp[4] for dp in data_points])
        
        # Apply filters and calculate derived signals
        if sampling_frequency > 0:
            x_incl = butter_lowpass_filter(x_data_orig, self.cutoff_lowpass, sampling_frequency)
            y_incl = butter_lowpass_filter(y_data_orig, self.cutoff_lowpass, sampling_frequency)
            z_incl = butter_lowpass_filter(z_data_orig, self.cutoff_lowpass, sampling_frequency)
            x_acc = butter_highpass_filter(x_data_orig, self.cutoff_highpass, sampling_frequency)
            y_acc = butter_highpass_filter(y_data_orig, self.cutoff_highpass, sampling_frequency)
            z_acc = butter_highpass_filter(z_data_orig, self.cutoff_highpass, sampling_frequency)
            tetha_xz = np.degrees(np.arctan2(x_incl, z_incl))
            tetha_yz = np.degrees(np.arctan2(y_incl, z_incl))
        else:
            x_incl, y_incl, z_incl, x_acc, y_acc, z_acc, tetha_xz, tetha_yz = (np.array([]),) * 8
        
        # Plot selected signals
        if plot_options.get('x_orig'):
            self.ax.plot(time_data, x_data_orig, label='x (Orig)')
        if plot_options.get('y_orig'):
            self.ax.plot(time_data, y_data_orig, label='y (Orig)')
        if plot_options.get('z_orig'):
            self.ax.plot(time_data, z_data_orig, label='z (Orig)')
        
        if plot_options.get('x_incl'):
            self.ax.plot(time_data, x_incl, label='x_incl', linestyle='--')
        if plot_options.get('y_incl'):
            self.ax.plot(time_data, y_incl, label='y_incl', linestyle='--')
        if plot_options.get('z_incl'):
            self.ax.plot(time_data, z_incl, label='z_incl', linestyle='--')
        
        if plot_options.get('x_acc'):
            self.ax.plot(time_data, x_acc, label='x_acc', linestyle=':')
        if plot_options.get('y_acc'):
            self.ax.plot(time_data, y_acc, label='y_acc', linestyle=':')
        if plot_options.get('z_acc'):
            self.ax.plot(time_data, z_acc, label='z_acc', linestyle=':')
        
        if plot_options.get('tetha_xz'):
            self.ax.plot(time_data, tetha_xz, label='Tetha_XZ [deg]', linestyle='-.')
        if plot_options.get('tetha_yz'):
            self.ax.plot(time_data, tetha_yz, label='Tetha_YZ [deg]', linestyle='-.')
        
        # Apply styling
        self._apply_plot_styling()
        
        # Draw the updated plot
        self.canvas.draw()
    
    def _apply_plot_styling(self):
        """Apply consistent styling to the plot (dark theme)."""
        self.ax.legend(
            fontsize='small',
            loc='upper left',
            bbox_to_anchor=(1, 1),
            facecolor='#363636',
            labelcolor='white'
        )
        self.ax.set_title('Sensor Data in Real Time', color='white')
        self.ax.set_xlabel('Time', color='white')
        self.ax.set_ylabel('Value', color='white')
        
        date_format = mdates.DateFormatter('%H:%M:%S')
        self.ax.xaxis.set_major_formatter(date_format)
        self.ax.figure.autofmt_xdate()
        self.ax.figure.tight_layout(rect=[0, 0, 0.8, 1])
    
    def compute_filtered_data(self, data_points, sampling_frequency):
        """
        Compute all filtered signals for CSV export.
        
        Returns:
            dict with keys: x_incl, y_incl, z_incl, x_acc, y_acc, z_acc, tetha_xz, tetha_yz
        """
        if not data_points:
            return {}
        
        x_data_orig = np.array([dp[2] for dp in data_points])
        y_data_orig = np.array([dp[3] for dp in data_points])
        z_data_orig = np.array([dp[4] for dp in data_points])
        
        if sampling_frequency > 0:
            x_incl = butter_lowpass_filter(x_data_orig, self.cutoff_lowpass, sampling_frequency)
            y_incl = butter_lowpass_filter(y_data_orig, self.cutoff_lowpass, sampling_frequency)
            z_incl = butter_lowpass_filter(z_data_orig, self.cutoff_lowpass, sampling_frequency)
            x_acc = butter_highpass_filter(x_data_orig, self.cutoff_highpass, sampling_frequency)
            y_acc = butter_highpass_filter(y_data_orig, self.cutoff_highpass, sampling_frequency)
            z_acc = butter_highpass_filter(z_data_orig, self.cutoff_highpass, sampling_frequency)
            tetha_xz = np.degrees(np.arctan2(x_incl, z_incl))
            tetha_yz = np.degrees(np.arctan2(y_incl, z_incl))
        else:
            n = len(data_points)
            x_incl, y_incl, z_incl = [None] * n, [None] * n, [None] * n
            x_acc, y_acc, z_acc = [None] * n, [None] * n, [None] * n
            tetha_xz, tetha_yz = [None] * n, [None] * n
        
        return {
            'x_incl': x_incl,
            'y_incl': y_incl,
            'z_incl': z_incl,
            'x_acc': x_acc,
            'y_acc': y_acc,
            'z_acc': z_acc,
            'tetha_xz': tetha_xz,
            'tetha_yz': tetha_yz,
        }
