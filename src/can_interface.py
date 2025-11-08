import os
import subprocess
import threading
import traceback

# Import python-can if available
try:
    import can
except ImportError:
    can = None

from utils import elabora_frame_can


class CanController:
    """
    Encapsulates CAN bus setup, message sending, and reading.
    Supports python-can backends (slcan, virtual, kvaser, pcan) and fallback to subprocess (Linux can-utils).
    """
    
    def __init__(self, log_callback=None):
        """
        Args:
            log_callback: optional function(message) to log status messages
        """
        self.log_callback = log_callback or print
        self.can_bus = None
        self.can_process = None
        self.reader_thread = None
        self.reading_active = False
        self.selected_channel = None
        self.selected_backend = None
        self.selected_bitrate = None

    def list_slcan_ports(self):
        """Return list of available COM ports (potential slcan channels) on Windows using pyserial."""
        ports = []
        try:
            import serial.tools.list_ports as lp
            for p in lp.comports():
                # Heuristic: include all COM ports; could refine by p.vid/pid
                ports.append(p.device)
        except Exception as e:
            self.log_callback(f"Unable to list COM ports: {e}")
        return ports
        
    def setup_bus(self, backend: str | None = None, channel: str | None = None, bitrate: int = 1000000):
        """
        Setup CAN bus using provided params or environment defaults.
        Returns: True if setup succeeded, False otherwise
        """
        tty_device = os.environ.get('CAN_TTY_DEVICE', '/dev/ttyACM0')
        can_interface = os.environ.get('CAN_INTERFACE', 'can0')
        can_backend = (backend or os.environ.get('CAN_BACKEND', 'slcan'))
        can_channel = (channel or os.environ.get('CAN_CHANNEL', 'COM3'))

        # Remember selection
        self.selected_backend = can_backend
        self.selected_channel = can_channel
        self.selected_bitrate = bitrate

        self.log_callback(f"CAN configuration: backend={can_backend} channel={can_channel} bitrate={bitrate} tty={tty_device}")

        if can is None:
            self.log_callback("python-can not available: using system commands (Linux only).")
            try:
                process_slcand = subprocess.run(
                    ['sudo', 'slcand', '-o', '-c', '-s8', tty_device, can_interface],
                    capture_output=True, text=True
                )
                self.log_callback(process_slcand.stdout.strip() or "slcand executed")
                if process_slcand.stderr:
                    self.log_callback(f"slcand STDERR: {process_slcand.stderr.strip()}")
                process_slcand.check_returncode()

                process_ifconfig = subprocess.run(
                    ['sudo', 'ifconfig', can_interface, 'up'],
                    capture_output=True, text=True
                )
                self.log_callback(process_ifconfig.stdout.strip() or "ifconfig executed")
                if process_ifconfig.stderr:
                    self.log_callback(f"ifconfig STDERR: {process_ifconfig.stderr.strip()}")
                process_ifconfig.check_returncode()

                self.log_callback("CAN interface configured successfully (subprocess).")
                return True
            except subprocess.CalledProcessError as e:
                self.log_callback(f"Error configuring CAN interface: {e}")
                try:
                    self.log_callback(f"Error details: {e.stderr.strip()}")
                except Exception:
                    pass
                return False
            except FileNotFoundError:
                self.log_callback("Error: slcand or ifconfig not found. Ensure can-utils is installed and commands are in PATH.")
                return False

        try:
            if can_backend.lower() == 'slcan':
                try:
                    self.can_bus = can.Bus(bustype='slcan', channel=can_channel, bitrate=bitrate)
                    self.log_callback(f"Bus created: bustype='slcan' channel={can_channel}")
                except Exception as e:
                    self.log_callback(f"Failed to create slcan bus: {e}. Trying virtual fallback.")
                    try:
                        self.can_bus = can.Bus(bustype='virtual', channel='vcan0')
                        self.log_callback("Virtual bus created as fallback.")
                    except Exception as e2:
                        self.log_callback(f"Error creating virtual bus: {e2}")
                        return False
            elif can_backend.lower() == 'virtual':
                self.can_bus = can.Bus(bustype='virtual', channel='vcan0')
                self.log_callback("Using virtual bus.")
            elif can_backend.lower() == 'kvaser':
                try:
                    self.can_bus = can.Bus(bustype='kvaser', channel=int(can_channel))
                    self.log_callback("Using kvaser backend.")
                except Exception as e:
                    self.log_callback(f"Error creating kvaser bus: {e}")
                    return False
            elif can_backend.lower() == 'pcan':
                try:
                    self.can_bus = can.Bus(bustype='pcan', channel=int(can_channel))
                    self.log_callback("Using pcan backend.")
                except Exception as e:
                    self.log_callback(f"Error creating pcan bus: {e}")
                    return False
            else:
                try:
                    self.can_bus = can.Bus(bustype='slcan', channel=can_channel, bitrate=bitrate)
                    self.log_callback(f"Bus created (fallback slcan): channel={can_channel}")
                except Exception:
                    self.can_bus = can.Bus(bustype='virtual', channel='vcan0')
                    self.log_callback("Using virtual bus (fallback).")
            return True
        except Exception as e:
            self.log_callback(f"Error creating python-can bus: {e}")
            return False

    def send_message(self, can_interface, can_id, data_string):
        """
        Send a CAN message.
        Args:
            can_interface: interface name (e.g. 'can0') used for subprocess fallback
            can_id: hex string CAN ID (e.g. '61D')
            data_string: hex bytes string (e.g. '2B00180500010000')
        Returns: True if sent successfully, False otherwise
        """
        if self.can_bus is not None and can is not None:
            try:
                data_bytes = bytes.fromhex(data_string)
                msg = can.Message(arbitration_id=int(can_id, 16), data=data_bytes, is_extended_id=False)
                self.can_bus.send(msg)
                self.log_callback(f"CAN message sent (python-can): {can_id}#{data_string}")
                return True
            except Exception as e:
                self.log_callback(f"Error sending CAN (python-can): {e}")
                return False
        else:
            try:
                process_cansend = subprocess.run(
                    ['cansend', can_interface, f'{can_id}#{data_string}'],
                    capture_output=True, text=True
                )
                self.log_callback(process_cansend.stdout.strip() or "cansend executed")
                if process_cansend.stderr:
                    self.log_callback(f"cansend STDERR: {process_cansend.stderr.strip()}")
                process_cansend.check_returncode()
                self.log_callback(f"CAN message sent: {can_interface} {can_id}#{data_string}")
                return True
            except subprocess.CalledProcessError as e:
                self.log_callback(f"Error sending CAN message: {e}")
                try:
                    self.log_callback(f"Error details: {e.stderr.strip()}")
                except Exception:
                    pass
                return False
            except FileNotFoundError:
                self.log_callback("Error: cansend not found. Ensure can-utils is installed and cansend is in PATH.")
                return False

    def start_reader(self, data_callback, stop_flag_fn):
        """
        Start a background thread to read CAN messages.
        Args:
            data_callback: function(timestamp, can_id, x, y, z) called when data is parsed
            stop_flag_fn: function() returning True when reading should stop
        """
        self.reading_active = True
        self.reader_thread = threading.Thread(target=self._read_loop, args=(data_callback, stop_flag_fn))
        self.reader_thread.daemon = True
        self.reader_thread.start()

    def _read_loop(self, data_callback, stop_flag_fn):
        """
        Internal loop for reading CAN data. Runs in a background thread.
        """
        try:
            if self.can_bus is not None and can is not None:
                self.log_callback("Reading CAN via python-can.")
                while not stop_flag_fn():
                    try:
                        msg = self.can_bus.recv(timeout=1.0)
                    except Exception as e:
                        self.log_callback(f"python-can recv error: {e}")
                        break
                    if msg is None:
                        continue
                    try:
                        hex_bytes = ' '.join(f"{b:02X}" for b in msg.data)
                        line = f"can0 {msg.arbitration_id:X} [{len(msg.data)}] {hex_bytes}"
                        timestamp, can_id, x, y, z = elabora_frame_can(line)
                        if timestamp:
                            data_callback(timestamp, can_id, x, y, z)
                    except Exception as e:
                        self.log_callback(f"Error parsing python-can message: {e}")
                self.log_callback("python-can CAN thread terminated.")
            else:
                self.log_callback("Reading CAN via candump (subprocess).")
                try:
                    self.can_process = subprocess.Popen(
                        ['candump', 'can0'],
                        stdout=subprocess.PIPE, text=True, bufsize=1
                    )
                    for line in iter(self.can_process.stdout.readline, ''):
                        if stop_flag_fn():
                            break
                        line = line.strip()
                        if line:
                            timestamp, can_id, x, y, z = elabora_frame_can(line)
                            if timestamp:
                                data_callback(timestamp, can_id, x, y, z)
                    if self.can_process and self.can_process.stdout:
                        self.can_process.stdout.close()
                        self.can_process.wait()
                except FileNotFoundError:
                    self.log_callback("Error: candump not found.")
                except Exception as e:
                    self.log_callback(f"Error in candump thread: {e}")
        except Exception as e:
            self.log_callback(f"Error in CAN thread: {e}")
        finally:
            self.reading_active = False
            self.log_callback("CAN reader thread terminated.")

    def stop_reader(self):
        """Stop the background reader and cleanup subprocess if present."""
        self.reading_active = False
        if self.can_process and self.can_process.poll() is None:
            try:
                self.can_process.terminate()
                self.can_process.wait()
                self.log_callback("candump process terminated.")
            except Exception as e:
                self.log_callback(f"Error terminating candump process: {e}")
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2.0)

    def shutdown(self):
        """Cleanup and close CAN bus."""
        self.stop_reader()
        if self.can_bus:
            try:
                self.can_bus.shutdown()
                self.log_callback("CAN bus closed.")
            except Exception as e:
                self.log_callback(f"Error closing CAN bus: {e}")
