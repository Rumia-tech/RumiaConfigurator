# RumiaConfigurator - Software Specification

## 1. Project Overview

**Application Name:** RumiaConfigurator  
**Type:** CANopen Bus Data Acquisition and Real-Time Visualization Tool  
**Platform:** Windows/Linux/iOS
**Language:** Python 3.x  
**GUI Framework:** CustomTkinter (tkinter wrapper)  
**Entry Point:** `src/RumiaConfigurator.py`

### Purpose
RumiaConfigurator is an open source desktop application designed to acquire data from CANopen Inertial Measurement Unit (IMU). The application have two main purpose:
- Configuration of CANopen sensors
- Real-time visulation, data signal processing filters, export result to CSV format

---

## 2. Core Architecture

### 2.1 Module Structure

The application is organized into the following modules:

```
src/
├── RumiaConfigurator.py      # Application entry point
├── gui.py                    # Main GUI (CanInterfaceApp class)
├── can_interface.py          # CAN bus communication (CanController class)
├── canopen_config.py         # CANopen classes for sensor configuration
├── plot_manager.py           # Data processing and plotting (PlotManager class)
├── plotting.py               # Matplotlib figure setup
├── utils.py                  # Utility functions (filters, parsing, conversions)
└── assets/                   # UI resources (icons, images)
```

### 2.2 Data Flow

```
CAN Bus → CanController → Queue → GUI → PlotManager → Plot/CSV
```

1. **CAN Bus Reading:** reads CAN messages in a background thread
2. **Queue Processing:** Data is placed in a queue and periodically processed
3. **Data Accumulation:** Raw data points are stored
4. **Plotting:** Data related to sensor measurement can be plotted, other data are used for interface
5. **CSV Export:** It is possible to export configuration data and sensor data in two different csv file.

---

## 3. Dependencies

### Python Packages
```
customtkinter==5.2.2         # Modern GUI framework
matplotlib==3.10.7           # Plotting library
numpy==2.3.4                 # Numerical computations
scipy==1.16.2                # Signal processing (butterworth filters)
python-can==4.6.1            # CAN bus communication
pyserial==3.5                # Serial port enumeration
pillow==12.0.0               # Image handling
pyinstaller==6.16.0          # Executable bundling
```

### External Tools (Optional, for Linux fallback)
- `candump` - CAN message reading (Linux)
- `cansend` - CAN message sending (Linux)
- `slcand` - SLCAN interface setup (Linux)
- `ifconfig` - Network configuration (Linux)

---

## 4. GUI Components (gui.py)

### 4.1 Main Application Class: `RumiaConfiguratorApp`

Inherits from `customtkinter.CTk` and manages the entire GUI.

**Window Configuration:**
- Title: "RumiaConfigurator"
- Size: 1200x800 pixels
- Layout: 3 tabs
- Theme: Dark (System-dependent)

### 4.2 Tab 1: Configuration Tab

**Controls:**

1. **COM Port Selection + CANbus Bitrate**
   - Label: "Porta COM (SLCAN):"
   - Dropdown menu: Lists available COM ports + "Auto" option
   - Refresh button: Scans available COM ports
   - CANbus bitrate control is positioned below COM controls
   - Label includes measurement unit: "CANbus bitrate [kbit/s]"
   - Dropdown list derived from `SmartIMU.eds` (object `0x600A CAN_Baudrate`)
   - "Detect bitrate" button: probes common CAN bitrates and auto-fills the entry
   - If connection fails with selected bitrate, software tries automatic bitrate detection and retries bus initialization

2. **Acquisition Control Buttons**
   - "SmartIMU connection" button: Starts CAN data acquisition
   - "SmartIMU disconnection" button: Stops acquisition (state: disabled initially)

3. **Current configuration acquisition Button**
   - The application sends one CANopen SDO upload request for each supported parameter
   - For each request it waits for SDO response (`0x580 + NodeID`), parses value and updates the corresponding field in "All configuration"
   - If SDO timeout/abort is detected, a popup warning is shown and the next parameter is processed

4. **All configuration**
   For every configuration there is a small window with data and a button to send. Fields are initially empty. Data can be written by user or by "Current configuration" acquisition Button. User can write a data, click to send button and application send SDO message to overwrite configuration in the sensor.
   - If an SDO write confirmation (`0x60`) is received, value remains in the field.
   - If SDO write fails/aborts/timeouts, popup is shown and the field is cleared.
   - When "Current configuration acquisition" is executed, fields are populated from SDO read responses.
   List of parameters currently available in `SmartIMU.eds` and implemented in software:
   - Heartbeat
   - Node ID
   - TPDO1 period
   - TPDO2 period
   - Accelerometer range
   - Gyroscope range
   - CAN termina resistor
   CANbus bitrate is configured in the top connection area (not in "All configuration").
   Parameters requested in UI but not present in current EDS (shown as N/A):
   - Accelerometer filter
   - Gyroscope filter
   For configuration of parameter application use CANopen rules using SmartIMU.eds
   

### 4.3 Tab 2: Data Tab

**Controls:**

1. **CSV Save Options**
   - Checkbox: "Salva dati su CSV"
   - Entry field: CSV filename (appears when checkbox is enabled)

2. **Plot Selection Checkboxes (PDO from EDS)**
   - The UI discovers mapped TPDO application objects from `SmartIMU.eds`
   - Mapping source: `1A00`, `1A01` (and additional `1A0x` if present)
   - Displayed checkboxes are generated from object names (example: `Acc_x`, `Acc_y`, `Acc_z`, `Vang_x`, `Vang_y`, `Vang_z`)
   - No manual CAN ID filter is present in Data tab; all incoming frames are read and only mapped PDO signals are accumulated

3. **Plot Area**
   - Matplotlib figure embedded in the tab
   - Size: proportional to remaining space (column 3, rows 0-9)
   - Dark theme with white text/axes

### 4.4 Tab 2: Developer Tab

- **Live CAN traffic monitor**: shows all TX/RX CAN frames exchanged by the software
- **Log format**: timestamp, direction, CAN ID, DLC, payload, source backend
- **Export button**: exports the full CAN traffic log to CSV file
- **Clear button**: clears current in-memory CAN traffic history
- **Custom CAN Message Sender**:
   - Address field (hex 000-7FF)
   - DLC selector (0-8)
   - 8 data byte entry fields (disabled beyond DLC)
   - Send button

### 4.5 Log Area

- **Position:** Bottom row (row 2, spans all columns)
- **Type:** Read-only textbox
- **Height:** 150 pixels
- **Content:** Status messages, error logs, data counts
- **Initial Message:** "Ready for configuration and CAN acquisition.\n"

---

## 5. CAN Interface Module (can_interface.py)

### 5.1 CanController Class

Manages all CAN bus communication and background data reading.

**Attributes:**
```python
can_bus                  # python-can Bus object or None
can_process             # subprocess.Popen for candump (Linux fallback)
reader_thread           # Background reading thread
reading_active          # Boolean flag for reader state
selected_channel        # Currently selected COM port or interface name
selected_backend        # CAN backend type (slcan, virtual, kvaser, pcan)
selected_bitrate        # Bitrate (default 1000000)
log_callback            # Function for logging messages
traffic_callback        # Optional callback for each TX/RX CAN frame
```

**Key Methods:**

1. **`list_slcan_ports()`**
   - Returns list of available COM ports on Windows using pyserial
   - Falls back to empty list on error

2. **`setup_bus(backend, channel, bitrate=1000000)`**
   - Initializes CAN bus
   - **Windows:** Uses python-can with 'slcan' backend
   - **Linux:** Tries python-can first, falls back to subprocess (`slcand`, `ifconfig`)
   - Returns: `True` on success, `False` on failure

3. **`send_message(can_interface, can_id, data_string)`**
   - Sends CAN message with given ID and data bytes
   - `can_id`: Hex string (e.g., '61D')
   - `data_string`: Hex bytes string (e.g., '2B00180500010000')
   - Emits TX traffic event to `traffic_callback` on success
   - Returns: `True` on success, `False` on failure

4. **`start_reader(data_callback, stop_flag_fn)`**
   - Starts background thread for continuous CAN message reading
   - `data_callback`: Called with `(timestamp, can_id, x, y, z)` for each parsed message
   - `stop_flag_fn`: Function that returns `True` when reading should stop
   - Thread is daemon thread

5. **`_read_loop(data_callback, stop_flag_fn)`**
   - Internal loop running in background thread
   - **Windows/python-can:** Reads via `self.can_bus.recv(timeout=1.0)`
   - **Linux fallback:** Reads from `candump` subprocess output
   - Emits RX traffic event to `traffic_callback` for each received frame
   - Parses each message via `elabora_frame_can()` in utils
   - Calls `data_callback()` for each successfully parsed message

6. **`set_traffic_callback(callback)`**
   - Registers callback used by GUI Developer tab to collect CAN TX/RX history

6. **`stop_reader()`**
   - Stops background reading thread
   - Terminates `candump` subprocess if present
   - Waits for thread termination (timeout: 2.0 seconds)

7. **`shutdown()`**
   - Calls `stop_reader()`
   - Closes CAN bus

---

## 6. Data Processing Module (plot_manager.py)

### 6.1 PlotManager Class

Handles all signal processing, filtering, and plotting.

**Attributes:**
```python
ax                      # matplotlib Axes object
canvas                  # FigureCanvasTkAgg object
cutoff_lowpass          # Low-pass filter cutoff frequency (Hz)
cutoff_highpass         # High-pass filter cutoff frequency (Hz)
```

**Key Methods:**

1. **`clear_plot(title, xlabel, ylabel)`**
   - Clears the matplotlib axes
   - Sets default labels and styling
   - Draws blank canvas

2. **`process_and_plot(data_points, sampling_frequency, plot_options)`**
   
   **Input:**
   - `data_points`: List of tuples `(timestamp, can_id, x, y, z)`
   - `sampling_frequency`: Frequency in Hz (used for filter design)
   - `plot_options`: Dictionary with boolean flags:
     ```python
     {
         'x_orig', 'y_orig', 'z_orig',          # Raw signals
         'x_incl', 'y_incl', 'z_incl',          # Low-pass filtered
         'x_acc', 'y_acc', 'z_acc',             # High-pass filtered
         'tetha_xz', 'tetha_yz'                 # Angle calculations
     }
     ```
   
   **Process:**
   1. Extract raw x, y, z data from data_points
   2. Apply low-pass filter → x_incl, y_incl, z_incl
   3. Apply high-pass filter → x_acc, y_acc, z_acc
   4. Calculate angles: 
      - `tetha_xz = arctan2(x_incl, z_incl)` in degrees
      - `tetha_yz = arctan2(y_incl, z_incl)` in degrees
   5. Plot selected signals with appropriate line styles:
      - Raw: solid line
      - Low-pass (incl): dashed line
      - High-pass (acc): dotted line
      - Angles: dash-dot line
   6. Apply dark theme styling
   7. Redraw canvas

3. **`_apply_plot_styling()`**
   - Applies consistent dark theme styling
   - Configures legend (upper left corner, floating outside plot)
   - Sets axis labels, title, date format
   - Applies tight layout

4. **`compute_filtered_data(data_points, sampling_frequency)`**
   
   **Output:** Dictionary with filtered arrays:
   ```python
   {
       'x_incl': np.array,
       'y_incl': np.array,
       'z_incl': np.array,
       'x_acc': np.array,
       'y_acc': np.array,
       'z_acc': np.array,
       'tetha_xz': np.array,
       'tetha_yz': np.array
   }
   ```
   - Used by CSV export function

---

## 7. Utility Functions (utils.py)

### 7.1 Signal Processing Functions

1. **`butter_lowpass_filter(data, cutoff, fs, order=5)`**
   - Applies Butterworth low-pass filter
   - Parameters:
     - `data`: Input signal (numpy array)
     - `cutoff`: Cutoff frequency (Hz)
     - `fs`: Sampling frequency (Hz)
     - `order`: Filter order (default: 5)
   - Returns: Filtered signal (numpy array)

2. **`butter_highpass_filter(data, cutoff, fs, order=5)`**
   - Applies Butterworth high-pass filter
   - Same parameters as low-pass
   - Returns: Filtered signal (numpy array)

### 7.2 Data Parsing Functions

1. **`elabora_frame_can(line)`**
   
   Parses a candump output line:
   ```
   can0 61D [6] FF C3 01 4B FC 55
   ```
   
   **Extraction Logic:**
   - Regex: `r'can0\s+([0-9A-F]+)\s+\[\d+\]\s+([0-9A-F ]+)'`
   - Skips CAN IDs: 29D, 71D (control messages)
   - Byte mapping:
     - `hex_ffc3 = byte[1] + byte[0]` → x value
     - `hex_014b = byte[3] + byte[2]` → y value
     - `hex_fc55 = byte[5] + byte[4]` → z value
   - Conversion: `value / 1000` (units: g)
   - Returns: `(timestamp, can_id, x, y, z)`
   - Returns: `(None, None, None, None, None)` on parse error

2. **`hex_to_signed_decimal(hex_string)`**
   - Converts 2-byte hex string to signed decimal
   - Handles two's complement for negative values
   - Example: 'FFC3' → -61 (as decimal)

3. **`decimal_to_hex_msb_lsb(decimal_value)`**
   - Converts decimal value (1-2000) to MSB/LSB hex pair
   - Example: 1234 → ('04', 'D2')
   - Raises ValueError if out of range

### 7.3 Resource Path Function

1. **`resource_path(relative_path)`**
   - Returns correct path for resources (images, assets)
   - Works with both development and PyInstaller bundled executables
   - Uses `sys._MEIPASS` for bundled apps

---

## 8. Plotting Setup (plotting.py)

### 8.1 Function: `setup_plot_figure(figsize)`

- Creates matplotlib Figure and Axes
- Figsize: Tuple (width, height) in inches
- Returns: `(fig, ax)`

---

## 9. Acquisition Workflow

### 9.1 Start Acquisition Flow

1. User clicks "Avvia Acquisizione" button
2. `start_acquisition()` method:
   - Validates CAN bus initialization
   - Validates CSV filename if enabled
   - Clears previous data and plot
   - Sets `acquisition_active = True`
   - Disables Start button, enables Stop button
   - Starts `CanController.start_reader()` with filter callback
   - Initiates `update_plot()` cycle (300ms interval)

### 9.2 Data Reception

- Background reader thread continuously reads CAN messages
- For each message:
  - Parses via `elabora_frame_can()`
  - Applies CAN ID filter if specified
  - Calls data_callback → queues data to `self.data_queue`

### 9.3 Data Processing

- `process_data_queue()` runs every 100ms
- Retrieves queued data points
- Appends to `self.data_points` list
- Logs count of processed points

### 9.4 Plot Update

- `update_plot()` runs every 300ms (while acquisition active)
- Reads dynamically generated PDO checkboxes
- Calls `PlotManager.process_and_plot_pdo_signals()` with selected PDO keys
- Matplotlib canvas automatically redraws

### 9.5 Stop Acquisition Flow

1. User clicks "Interrompi Acquisizione" button
2. `stop_acquisition()` method:
   - Sets `acquisition_active = False`
   - Cancels plot update callback
   - Calls `CanController.stop_reader()`
   - Updates button states
   - If CSV save enabled: Calls `save_data_to_csv()`

### 9.6 CSV Export

CSV file structure is dynamic and includes only curves currently selected in Data tab plot options.

Base columns always present:
```csv
Timestamp,CAN ID
```

Optional columns (added only if corresponding PDO checkbox is selected):
- Signal names discovered from EDS PDO mapping (example: `Acc_x`, `Acc_y`, `Acc_z`, `Vang_x`, `Vang_y`, `Vang_z`)

Example (Acc_x + Acc_y selected):
```csv
Timestamp,CAN ID,Acc_x,Acc_y
2026-02-22 10:30:45.123456,61D,-0.012,0.034
...
```

---

## 10. Constants and Defaults

### 10.1 Default Configuration
- **CAN Bitrate:** 1000000 bps (1 Mbps)
- **COM Port (Windows):** COM3 (if no specific port selected)
- **CAN Interface (Linux):** can0
- **TTY Device (Linux):** /dev/ttyACM0
- **Sampling Frequency:** 1.0 Hz (used for filter design)
- **Low-pass Cutoff:** 1.0 Hz
- **High-pass Cutoff:** 1.0 Hz
- **Butterworth Filter Order:** 5
- **Update Interval:** 300 ms (plot), 100 ms (queue processing)
- **Reader Timeout:** 1.0 second

### 10.2 CAN Message Format
- **Standard CAN IDs:** 0x000 - 0x7FF (11-bit identifiers)
- **Data Length Code (DLC):** 0-8 bytes
- **Acceleration Unit:** Grams (g)
- **Angles Unit:** Degrees (deg)

---

## 11. Error Handling

### 11.1 CAN Bus Errors
- **Setup Failure:** Logs error, returns False, prevents acquisition start
- **Reader Error:** Logs error, thread terminates gracefully
- **Message Parse Error:** Logs error, skips message

### 11.2 CSV Export Errors
- **File I/O Error:** Logs error message to GUI
- **Missing Filename:** Displays error, skips save

### 11.3 Filter Errors
- **Invalid Cutoff:** Returns raw data if cutoff >= Nyquist frequency
- **Invalid Sampling Freq:** Handles gracefully (0 Hz case)

---

## 12. Build and Deployment

### 12.1 PyInstaller Specs

**Files:** `RumiaConfigurator.spec`, `RumiaConfigurator_debug.spec`

**Build Process:**
```bash
pyinstaller RumiaConfigurator.spec
```

**Output Directory:** `build/RumiaConfigurator/`

**Executable:** `build/RumiaConfigurator/RumiaConfigurator.exe`

---

## 13. Features Summary

✅ Real-time CAN bus data acquisition  
✅ Dual filtering: Low-pass (inclination) + High-pass (acceleration)  
✅ Angle calculation from accelerometer data  
✅ Selective signal visualization via checkboxes  
✅ CSV data export with all processed signals  
✅ CAN message sender (custom frames)  
✅ COM port auto-detection  
✅ CAN ID filtering  
✅ Dark theme GUI  
✅ Multi-threaded background processing  
✅ Windows and Linux CAN support  
✅ Logging console  

---

## 14. Known Limitations

- Sampling frequency fixed at 1.0 Hz for filter design (not user-configurable)
- Cutoff frequencies fixed at 1.0 Hz (not user-configurable)
- Angle calculations use only x/y and z channels (arctan2)
- CAN ID filter is hexadecimal text input (no validation UI feedback)
- No data visualization export (only CSV)
- No real-time data buffering limit (may consume memory for long acquisitions)

---

## 15. Development Notes

### 15.1 Threading Model
- GUI runs on main thread (Tkinter requirement)
- CAN reader runs in background daemon thread
- Queue for thread-safe data passing
- All GUI updates via `self.after()` callbacks

### 15.2 Color Theme
- Background: #2B2B2B (dark gray)
- Text: white
- Legend background: #363636

### 15.3 Platform-Specific Code
- **Windows:** Uses python-can library exclusively
- **Linux:** Tries python-can first, falls back to system commands (candump, cansend)
- Environment variables for configuration: `CAN_BACKEND`, `CAN_CHANNEL`, `CAN_TTY_DEVICE`, `CAN_INTERFACE`

---

## 16. File Structure

```
Software_interfaccia/
├── src/
│   ├── RumiaConfigurator.py
│   ├── gui.py
│   ├── can_interface.py
│   ├── plot_manager.py
│   ├── plotting.py
│   ├── utils.py
│   ├── __pycache__/
│   └── assets/
├── scripts/
│   └── build_exe.bat
├── build/
│   ├── RumiaConfigurator/
│   └── RumiaConfigurator_debug/
├── requirements.txt
├── RumiaConfigurator.spec
├── RumiaConfigurator_debug.spec
├── dati.csv
└── Software_specification.md
```

---

## 17. Entry Point Code

File: `src/RumiaConfigurator.py`

```python
from gui import CanInterfaceApp

def main():
    """Launch the RumiaConfigurator GUI application."""
    app = CanInterfaceApp()
    app.mainloop()

if __name__ == "__main__":
    main()
```

---

**End of Specification Document**
