# Simulator and demo mode

The simulator puts CANopen devices on a CAN bus without any hardware: a Smart
IMU and an INCLI Sense that answer SDO requests, follow NMT commands, send
their heartbeat and transmit PDOs with plausible data. It has two uses:

- **tests**: every test of the CANopen features runs against simulated nodes
  on the python-can `virtual` bus;
- **demo mode**: `rumia-configurator --demo` starts the application with the
  simulated nodes and a banner that stays visible for the whole session
  (FR-CON-06).

Source files:

- `src/rumia_configurator/core/simulator/simulator.py`: `Simulator`, the bus
  and the tick thread
- `src/rumia_configurator/core/simulator/node.py`: `SimulatedNode`, what every
  simulated device does
- `src/rumia_configurator/core/simulator/products.py`: `SmartImuNode` and
  `IncliSenseNode`
- `src/rumia_configurator/core/simulator/signals.py`: the generated
  measurements
- `src/rumia_configurator/profiles/eds.py`: tolerant EDS import, also used by
  the simulator
- `src/rumia_configurator/gui/views/demo_banner.py`: the demo mode banner

Like the rest of `core/`, the simulator does not import Qt.

## How it works

```
Application side                     Simulator side
canopen.Network ── virtual bus ──── canopen.Network (its own)
(SDO client, NMT master,  channel   ├─ SmartImuNode   29  (canopen.LocalNode)
 scanner, PDO listener)  "rumia-    └─ IncliSenseNode 10  (canopen.LocalNode)
                          demo"         ↑ tick thread every 10 ms: TPDOs
```

With the `virtual` interface every `can.Bus` opened on the same channel in the
same process receives the frames sent by the others. The simulator opens its
own bus with `receive_own_messages=False`; the application opens another one
on the same channel and sees the simulated nodes exactly as it would see real
devices. Nothing in the application needs to know they are simulated.

Each simulated node wraps a
[`canopen.LocalNode`](https://canopen.readthedocs.io/en/latest/) built from the
product EDS, so its object dictionary is the one of the real device.
`LocalNode` already answers SDO uploads and downloads (with the abort codes of
the library, for example 0x06010002 for a read-only object) and tracks the NMT
state. `SimulatedNode` adds what a real device does on top of that:

| Behaviour | Details |
| --- | --- |
| Start-up | boot-up frame (0x700 + ID, data `00`), heartbeat from 0x1017, then **Operational on its own** as the Rumia sensors do. `auto_start=False` leaves the node in Pre-operational. |
| NMT Start / Stop / Pre-operational | handled by `LocalNode`; the heartbeat carries the new state. |
| NMT Reset node | values back to the stored ones (or to the EDS defaults), new boot-up, Operational. |
| NMT Reset communication | same, but only for the communication area 0x1000–0x1FFF. |
| Stopped | no PDOs and **no SDO answers** (CiA 301): the application sees a timeout. |
| 0x1010 store | accepts only the signature `save` (0x65766173); anything else aborts with 0x08000020. The current values survive the next reset. |
| 0x1011 restore | accepts only `load` (0x64616F6C); the EDS defaults come back at the next reset. Reading 0x1010/0x1011 gives 1 ("saves on command"). |
| Heartbeat stopped on purpose | `stop_heartbeat()` stops it, as a node whose cable was cut; `resume_heartbeat()` starts it again with the period of 0x1017. Used by the heartbeat alarm tests. |
| 0x1008 missing in the EDS | the node answers with the `ProductName` of the EDS, as the improved firmware will. The real Smart IMU of today has no 0x1008: to simulate it, delete the object after creating the node (`del node.local.object_dictionary[0x1008]`, as `tests/test_profile_gui.py` does). |

### TPDOs

TPDOs are not built by `canopen`'s PDO classes. At every tick (10 ms) the
simulator calls `SimulatedNode.poll()`, which, for each TPDO of a node in
Operational state:

1. reads 0x18xx from the object dictionary: COB-ID (sub 1, skipped if bit 31
   says "not valid"), transmission type (sub 2, only event-driven 254/255 are
   simulated) and event timer (sub 5);
2. when the event timer expires, reads the mapping 0x1Axx and concatenates
   the mapped objects, taking their current value;
3. sends the frame.

Everything is read again at every tick, so a PDO reconfigured through SDO (new
event timer, new mapping, disabled COB-ID) is sent as configured straight
away. Not simulated: SYNC-driven transmission types and mappings that are not
whole bytes (a warning is logged and the PDO is skipped).

### Measurements

Measured objects are not stored: a *provider* computes their raw bytes when
they are read, from the simulation time (`SimulatedNode.provide()`). An SDO
read and a TPDO therefore always carry the current sample. While a TPDO is
being built the time is frozen, so all the objects of one frame belong to the
same sample.

| Product | Objects | Signal |
| --- | --- | --- |
| Smart IMU | 0x6001–0x6003, TPDO1 (0x180 + ID), INT16 mg | gravity seen by a sensor that tilts slowly (pitch ±15°, roll ±10°), a 12.5 Hz vibration of 20 mg and a little noise: the magnitude stays near 1000 mg |
| Smart IMU | 0x6004–0x6006, TPDO2 (0x280 + ID), INT16 mdps | the derivative of the same tilt, plus a slow yaw rate and noise |
| INCLI Sense | 0x6010, 0x6020, TPDO1 (0x180 + ID), INT16 in units of 0x6000 | two slow independent swings, ±5° longitudinal and ±3° lateral |

The provisional Smart IMU EDS declares 0x6001–0x6006 as UNSIGNED16, but the
firmware sends INT16: the simulator sends INT16 little-endian bytes, like the
device.

The INCLI Sense follows CiA 410: each axis outputs `sign * slope`, plus the
offset (0x6013) and the differential offset (0x6014) when bit 1 of the
operating parameters (0x6011/0x6021) is set; bit 0 inverts the sign. Writing
the preset (0x6012/0x6022) computes the offset so that the output equals the
preset at that moment. The resolution 0x6000 accepts 1, 10, 100 or 1000
(thousandths of a degree); other values abort with 0x06090030.

### The INCLI Sense EDS is provisional

`src/rumia_configurator/profiles/data/incli_sense/incli_sense.eds` was written
for the simulator from the CiA 410 profile: device type 0x0002019A (profile
410, two axes), the objects above, TPDO1 with both slopes every 100 ms. The
filter object is not there because it is not defined yet. Replace the file
when the firmware EDS is available and check that the tests still pass.

### Threads

| Thread | Does |
| --- | --- |
| `can-simulator` (tick) | `poll()` of every node: builds and sends the due TPDOs |
| python-can receive thread of the simulator's network | SDO requests and NMT commands from the application |
| python-can periodic task | the heartbeat of each node |

Each node has one re-entrant lock around its data store, taken by the tick
thread and by the SDO handler, so a PDO is never built while an SDO write is
half-done. An exception in one node is logged and does not stop the others.

### The EDS loader

The simulator loads EDS files with `load_object_dictionary()` from
`src/rumia_configurator/profiles/eds.py`, which is the first piece of FR-SDO-12
(an incomplete EDS loads anyway, with warnings):

- empty numeric fields of `[DeviceInfo]` (the Smart IMU EDS has
  `VendorNumber=` and `ProductNumber=`), which make `canopen` refuse the file,
  are read as 0 and listed in `EdsLoadResult.warnings`;
- the warnings `canopen` logs during the import are added to the same list;
- a file that cannot be imported even so raises `ValueError` with the file
  name.

`bundled_eds("smart_imu")` returns the EDS shipped in
`src/rumia_configurator/profiles/data/<product>/`.

## Using it in tests

`tests/conftest.py` provides the fixtures; each test gets its own virtual
channel, so tests never see each other's frames.

| Fixture | What it gives |
| --- | --- |
| `sim_channel` | a channel name used only by this test |
| `recorder` | a `FrameRecorder`: every frame the application side received, with `with_id()`, `clear()` and `wait_for(predicate, timeout)` |
| `app_network` | a `canopen.Network` connected to `sim_channel`, feeding `recorder` |
| `simulator` | the demo nodes (Smart IMU 29, INCLI Sense 10) running on `sim_channel`, started after `app_network` so the boot-up frames are recorded |

```python
import canopen

from rumia_configurator.core.simulator import Simulator
from rumia_configurator.profiles.eds import bundled_eds, load_object_dictionary


def test_event_timer_is_readable(simulator: Simulator, app_network: canopen.Network) -> None:
    od = load_object_dictionary(bundled_eds("smart_imu"), 29).od
    node = canopen.RemoteNode(29, od)
    app_network.add_node(node)
    assert node.sdo[0x1800][5].raw == 500
```

For a node with special settings, build the `Simulator` yourself on
`sim_channel`, as `test_incli_inversion_preset_and_offsets` in
`tests/test_simulator.py` does with a fixed slope.

Tips:

- Wait for frames with `recorder.wait_for(...)`, not with a fixed sleep:
  the tests stay fast and do not fail on a slow machine.
- To test heartbeats quickly, write a short producer time (0x1017 = 50 ms)
  first: the default is 1000 ms.
- `canopen`'s SDO client retries forever with `MAX_RETRIES = 0`; use 1 for a
  single attempt when you expect a timeout.
- Both networks use a notifier cycle of 0.1 s (`NOTIFIER_CYCLE`): with the
  library default of 1 s every `disconnect()` waits up to a second.

## Demo mode

`rumia-configurator --demo` makes `run_gui(demo=True)` (in
`src/rumia_configurator/gui/app.py`) call `_start_demo()`, which:

1. creates `Simulator(default_demo_nodes())` on the virtual channel
   `rumia-demo` (`DEMO_CHANNEL`) and starts it;
2. stops it when the application quits (`QApplication.aboutToQuit`);
3. if it cannot start, shows an error with the cause and what to do, and the
   application exits with code 1. It never continues without the simulator.

`MainWindow` then receives the list of simulated nodes and shows `DemoBanner`
between the top bar and the work area. The banner is an `info` callout (see
[Theme](theme.md#brand-components)), names the simulated nodes and cannot be
closed. Its texts are translated like every other text.

After the window is shown, `run_gui()` calls
`MainWindow.start_demo_connection()`, which opens the `rumia-demo` channel with
`ConnectionService.connect_virtual()` ([Connection](connection.md#the-gui-side)).
The adapter button reads "Virtual bus (demo)" and is locked.

## Add a simulated product

1. Put the product EDS in `src/rumia_configurator/profiles/data/<product>/`.
2. If the measurements need a new signal, add a frozen dataclass with a
   `sample(t)` method in `src/rumia_configurator/core/simulator/signals.py`.
   Keep it a pure function of `t`: tests rely on repeatable values.
3. In `src/rumia_configurator/core/simulator/products.py`, subclass
   `SimulatedNode`:

   ```python
   class GatewayNode(SimulatedNode):
       def __init__(self, node_id: int = 5, *, auto_start: bool = True) -> None:
           super().__init__(node_id, bundled_eds("gateway"), auto_start=auto_start)
           self.provide(0x6100, 1, self._input_bytes)

       def _input_bytes(self) -> bytes:
           return struct.pack("<H", round(1000 + 100 * math.sin(self.now())))
   ```

   Register a provider for every measured object; parameters need nothing,
   `LocalNode` stores what the application writes. For a parameter with
   side effects (like the INCLI preset), add a write callback with
   `self.local.add_write_callback()` and raise `SdoAbortedError` to refuse a
   value.
4. Export the class in `src/rumia_configurator/core/simulator/__init__.py` and,
   if it belongs in demo mode, add it to `default_demo_nodes()`. Node-IDs
   must be unique.
5. Add tests in `tests/test_simulator.py`: SDO identity, PDO content and rate,
   and every side effect.

To change the generated data of an existing product, change the defaults of
`ImuMotion` or `InclinationMotion`, or pass another instance:
`SmartImuNode(motion=ImuMotion(vibration_mg=0))`.
