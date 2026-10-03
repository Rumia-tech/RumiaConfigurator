# EDS and products

Every node the application talks to needs an object dictionary: which objects
exist, their types, names and defaults. This page explains how the
application loads EDS and DCF files, how it recognises the Rumia products and
picks their EDS automatically, and what happens when it cannot.

Source files:

- `src/rumia_configurator/profiles/eds.py`: tolerant loader of EDS and DCF
  files, warnings, minimal CiA 301 dictionary
- `src/rumia_configurator/profiles/catalog.py`: the Rumia products and the
  recognition rules
- `src/rumia_configurator/profiles/association.py`: `ProfileRegistry`, the
  profile of each node for the session
- `src/rumia_configurator/gui/views/profile_dialog.py`: the *Associate
  profile…* dialog and the list of EDS warnings

## Loading EDS and DCF files (FR-SDO-12)

`load_object_dictionary(path, node_id)` imports a `.eds` or `.dcf` file with
the `canopen` library, after repairing what the library would refuse, and
returns an `EdsLoadResult` with the dictionary and a list of `EdsWarning`.
An incomplete file loads anyway: the warnings are shown to the user, the
application keeps working.

| `EdsWarningCode` | When | What the user reads |
| --- | --- | --- |
| `EMPTY_DEVICE_INFO` | a numeric field of `[DeviceInfo]` is empty, e.g. `VendorNumber=` (canopen refuses the file; it is read as 0) | Field VendorNumber of [DeviceInfo] is empty: read as 0 |
| `MISSING_MANDATORY` | 0x1000, 0x1001 or 0x1018 is not in the file | Mandatory CiA 301 objects missing: 0x1001 |
| `MISSING_DEFAULTS` | readable objects from 0x1000 up without `DefaultValue` | 17 objects without a default value (0x1003:00, …) |
| `EMPTY_PRODUCT_NAME` | `ProductName=` is empty | The product name is empty |
| `LIBRARY` | a warning logged by `canopen` during the import | CANopen library: … |

Each warning has a technical `text` in English for the log and for support,
and the list of `objects` it concerns; the interface translates the code and
shows the first four objects. Defaults written as `$NODEID+0x80` have no value
until a Node-ID is given, and are not counted as missing.

A file that cannot be used raises `EdsLoadError`, never an empty dictionary.
Its `kind` says why, and the interface explains it in three parts:

| `EdsLoadErrorKind` | Cause |
| --- | --- |
| `UNREADABLE` | the file is missing or cannot be read |
| `WRONG_TYPE` | not a `.eds` or `.dcf` file |
| `INVALID` | the library refused the content |
| `EMPTY` | the file defines no objects |

### Nodes without EDS (FR-SDO-01)

`minimal_object_dictionary(node_id)` contains only the objects every CiA 301
node has: 0x1000 Device type, 0x1001 Error register, 0x1017 Producer
heartbeat time and 0x1018 Identity. Any other object will be read raw by
index and sub-index (parameters page, a later task).

## Recognising the Rumia products (FR-NET-03, FR-NET-08)

`recognize(info)` in `src/rumia_configurator/profiles/catalog.py` looks at the
identity read from the node (0x1008, 0x1018) and applies these rules in
order:

1. **Vendor-ID and Product code.** Rumia has no CANopen Vendor-ID yet; when it
   is assigned, `RUMIA_VENDOR_ID` is set and each product gets its
   `product_codes`. Today this rule never applies.
2. **Device name (0x1008)**, compared without case, repeated spaces or NUL
   padding: "Smart IMU", "smart imu" and `"Smart IMU\0\0"` are the same. If
   the product has Product codes and the node reports a different non-zero
   code, name and code disagree and the node is **not** recognised.
3. Otherwise the node is not a known product.

A node is never recognised from its Node-ID, its PDOs or a guess on its
objects: a wrong product would show wrong units and wrong parameters.

Examples:

| 0x1008 | 0x1018:02 | Result |
| --- | --- | --- |
| `Smart IMU` | 0 | Smart IMU, by name (the simulated node of demo mode) |
| `INCLI Sense` | 0 | INCLI Sense, by name |
| missing | 0 | not recognised: the Smart IMU of today (see below) |
| `Smart IMU` | a code of another product | not recognised: name and code disagree |

The Smart IMU firmware of today has no 0x1008 and reports 0 in all of 0x1018,
so it is **not** recognised: the user associates it by hand. It will be
recognised by itself as soon as the firmware answers 0x1008 = "Smart IMU".

## Profile of a node

`ProfileRegistry` keeps one `NodeProfile` per node: the product (if any), the
EDS file, the object dictionary loaded for that Node-ID, the warnings and the
source.

| `ProfileSource` | How | RUMIA badge |
| --- | --- | --- |
| `RECOGNIZED` | after the identity is read, by the rules above; the EDS of the product is loaded | yes |
| `MANUAL_PRODUCT` | the user chose a Rumia product | yes |
| `MANUAL_FILE` | the user chose an EDS or DCF file | no |
| `MANUAL_NONE` | the user chose no profile: minimal dictionary | no |
| `NONE` | not recognised, nothing chosen: minimal dictionary | no |

- A choice of the user always wins: a new identity read (after a boot-up,
  for example) keeps it. *Automatic recognition* in the dialog forgets it.
- Choices last for the **session**: `NetworkController` creates a new
  registry at every connection, so they are forgotten on disconnection.
- Loading a file is blocking, so it runs in the one-thread worker of the
  `NetworkController`, like the SDO reads ([Network](network.md#model-and-view)).
  A file that cannot be loaded leaves the previous profile in place.

In the interface:

- a Rumia product shows the **RUMIA** badge on its row; a profile chosen by
  hand adds "chosen by hand" under the heartbeat;
- a node without profile shows the link **Associate profile…** (ink and
  underlined, as links on the surface panel must be);
- the header of the selected node says "Profile: Smart IMU · smart_imu.eds ·
  recognised by its name", with the links *N EDS warnings* (the list, with
  the technical text in the details) and *Change profile…*.

## Add a recognised product

Example: an "INCLI Sense 2" with its own EDS.

1. Put the EDS in `src/rumia_configurator/profiles/data/incli_sense_2/`.
2. Add the product to `PRODUCTS` in
   `src/rumia_configurator/profiles/catalog.py`, with the exact values its
   firmware answers to 0x1008:

   ```python
   (Product("incli_sense_2", "INCLI Sense 2", ("INCLI Sense 2",)),)
   ```

   When Product codes exist, add them as the fourth argument; a node whose
   name matches but whose code disagrees will not be recognised.
3. Run `uv run pytest tests/test_catalog.py`: the test that loads every EDS of
   the catalog covers the new one. Add a recognition case for its name.
4. To show it in demo mode, add a simulated node
   ([Simulator and demo mode](simulator.md#add-a-simulated-product)).

## Tests

- `tests/test_eds.py`: the Smart IMU EDS loads with its warnings (acceptance
  of T1.6), DCF files, missing mandatory objects, `$NODEID` defaults, every
  `EdsLoadErrorKind`, the minimal dictionary.
- `tests/test_catalog.py`: one case for each recognition rule, conflicts of
  name and code, Vendor-ID rule, every product EDS loads.
- `tests/test_node_profiles.py`: automatic profile, minimal dictionary, choice
  by hand wins, back to automatic, session only, file with warnings, bad file.
- `tests/test_profile_gui.py`: RUMIA badge, *Associate profile…* on a node
  without name, header, cancelled choice, bad file explained, warnings in
  plain words, dialog options, panel width.
