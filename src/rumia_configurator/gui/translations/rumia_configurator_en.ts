<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="en_US">
<context>
    <name>AdapterDialog</name>
    <message>
        <source>Other adapter</source>
        <translation>Other adapter</translation>
    </message>
    <message>
        <source>Adapter type</source>
        <translation>Adapter type</translation>
    </message>
    <message>
        <source>Channel</source>
        <translation>Channel</translation>
    </message>
    <message>
        <source>Example: %1</source>
        <translation>Example: %1</translation>
    </message>
    <message>
        <source>The bitrate of this adapter is set in the operating system, not here.</source>
        <translation>The bitrate of this adapter is set in the operating system, not here.</translation>
    </message>
</context>
<context>
    <name>ConnectionMessages</name>
    <message>
        <source>Connection lost</source>
        <translation>Connection lost</translation>
    </message>
    <message>
        <source>The connection to %1 was lost.</source>
        <translation>The connection to %1 was lost.</translation>
    </message>
    <message>
        <source>Connection failed</source>
        <translation>Connection failed</translation>
    </message>
    <message>
        <source>Could not connect to %1.</source>
        <translation>Could not connect to %1.</translation>
    </message>
    <message>
        <source>Cause: the port does not exist. The adapter is unplugged or has another name.</source>
        <translation>Cause: the port does not exist. The adapter is unplugged or has another name.</translation>
    </message>
    <message>
        <source>Plug the adapter in, choose Refresh list in the adapter menu and select it again.</source>
        <translation>Plug the adapter in, choose Refresh list in the adapter menu and select it again.</translation>
    </message>
    <message>
        <source>Cause: another program is using the port, for example another configurator, a serial terminal or a second copy of this application.</source>
        <translation>Cause: another program is using the port, for example another configurator, a serial terminal or a second copy of this application.</translation>
    </message>
    <message>
        <source>Close the other program, or disconnect it from the port, then try again.</source>
        <translation>Close the other program, or disconnect it from the port, then try again.</translation>
    </message>
    <message>
        <source>Cause: your user is not allowed to use serial ports on this computer.</source>
        <translation>Cause: your user is not allowed to use serial ports on this computer.</translation>
    </message>
    <message>
        <source>Ask the administrator to run once: sudo usermod -aG dialout $USER (uucp on Arch Linux and macOS), then log out and in again. This application never asks for administrator rights.</source>
        <translation>Ask the administrator to run once: sudo usermod -aG dialout $USER (uucp on Arch Linux and macOS), then log out and in again. This application never asks for administrator rights.</translation>
    </message>
    <message>
        <source>Cause: the driver or library of %2 is not installed.</source>
        <translation>Cause: the driver or library of %2 is not installed.</translation>
    </message>
    <message>
        <source>Cause: the SocketCAN interface %1 is down.</source>
        <translation>Cause: the SocketCAN interface %1 is down.</translation>
    </message>
    <message>
        <source>Ask the administrator to bring it up with the network bitrate, for example: sudo ip link set %1 up type can bitrate 500000. For SocketCAN the bitrate is set there, not in this application.</source>
        <translation>Ask the administrator to bring it up with the network bitrate, for example: sudo ip link set %1 up type can bitrate 500000. For SocketCAN the bitrate is set there, not in this application.</translation>
    </message>
    <message>
        <source>Cause: the port opened, but nothing answered like an SLCAN adapter. It may be another device, or an adapter with a different firmware.</source>
        <translation>Cause: the port opened, but nothing answered like an SLCAN adapter. It may be another device, or an adapter with a different firmware.</translation>
    </message>
    <message>
        <source>Choose the port of the Rumia USB-CAN interface (it is first in the list, marked RUMIA). If it is already selected, unplug it, plug it in again and retry.</source>
        <translation>Choose the port of the Rumia USB-CAN interface (it is first in the list, marked RUMIA). If it is already selected, unplug it, plug it in again and retry.</translation>
    </message>
    <message>
        <source>Cause: %2 adapters cannot be used on this operating system.</source>
        <translation>Cause: %2 adapters cannot be used on this operating system.</translation>
    </message>
    <message>
        <source>Choose another adapter type in Other adapter…</source>
        <translation>Choose another adapter type in Other adapter…</translation>
    </message>
    <message>
        <source>Cause: the connection settings are not valid (%3).</source>
        <translation>Cause: the connection settings are not valid (%3).</translation>
    </message>
    <message>
        <source>Check the adapter type, the channel and the bitrate in Other adapter…</source>
        <translation>Check the adapter type, the channel and the bitrate in Other adapter…</translation>
    </message>
    <message>
        <source>Cause: only one bus can be open at a time.</source>
        <translation>Cause: only one bus can be open at a time.</translation>
    </message>
    <message>
        <source>Disconnect first, then connect to the other adapter.</source>
        <translation>Disconnect first, then connect to the other adapter.</translation>
    </message>
    <message>
        <source>Cause: the adapter stopped answering. It was unplugged, or its driver reported an error.</source>
        <translation>Cause: the adapter stopped answering. It was unplugged, or its driver reported an error.</translation>
    </message>
    <message>
        <source>Plug the adapter in again and press Connect.</source>
        <translation>Plug the adapter in again and press Connect.</translation>
    </message>
    <message>
        <source>Cause: the CAN library reported an error that the application does not know: %3</source>
        <translation>Cause: the CAN library reported an error that the application does not know: %3</translation>
    </message>
    <message>
        <source>Try again. If it happens again, export the logs (menu, Export logs…) and send them to Rumia support.</source>
        <translation>Try again. If it happens again, export the logs (menu, Export logs…) and send them to Rumia support.</translation>
    </message>
    <message>
        <source>Install the PEAK driver with the PCAN-Basic library from the manufacturer&apos;s website, then restart the application.</source>
        <translation>Install the PEAK driver with the PCAN-Basic library from the manufacturer&apos;s website, then restart the application.</translation>
    </message>
    <message>
        <source>Install the Kvaser drivers with the CANlib library from the manufacturer&apos;s website, then restart the application.</source>
        <translation>Install the Kvaser drivers with the CANlib library from the manufacturer&apos;s website, then restart the application.</translation>
    </message>
    <message>
        <source>Install the IXXAT VCI driver from the manufacturer&apos;s website, then restart the application.</source>
        <translation>Install the IXXAT VCI driver from the manufacturer&apos;s website, then restart the application.</translation>
    </message>
    <message>
        <source>This version of the application does not include support for candleLight (gs_usb) adapters. Use an SLCAN adapter such as the Rumia USB-CAN interface.</source>
        <translation>This version of the application does not include support for candleLight (gs_usb) adapters. Use an SLCAN adapter such as the Rumia USB-CAN interface.</translation>
    </message>
    <message>
        <source>Install the driver of the adapter, then restart the application.</source>
        <translation>Install the driver of the adapter, then restart the application.</translation>
    </message>
</context>
<context>
    <name>DemoBanner</name>
    <message>
        <source>Demo mode</source>
        <translation>Demo mode</translation>
    </message>
    <message>
        <source>Virtual bus with simulated nodes (%1). No real device is connected: to use a sensor, restart the application without --demo.</source>
        <translation>Virtual bus with simulated nodes (%1). No real device is connected: to use a sensor, restart the application without --demo.</translation>
    </message>
</context>
<context>
    <name>EdsWarnings</name>
    <message>
        <source>Field %1 of [DeviceInfo] is empty: read as 0</source>
        <translation>Field %1 of [DeviceInfo] is empty: read as 0</translation>
    </message>
    <message>
        <source>Mandatory CiA 301 objects missing: %1</source>
        <translation>Mandatory CiA 301 objects missing: %1</translation>
    </message>
    <message>
        <source>%1 objects without a default value (%2)</source>
        <translation>%1 objects without a default value (%2)</translation>
    </message>
    <message>
        <source>The product name is empty</source>
        <translation>The product name is empty</translation>
    </message>
    <message>
        <source>CANopen library: %1</source>
        <translation>CANopen library: %1</translation>
    </message>
    <message>
        <source>EDS warnings</source>
        <translation>EDS warnings</translation>
    </message>
    <message>
        <source>%1 loaded, with these warnings. The application works anyway.</source>
        <translation>%1 loaded, with these warnings. The application works anyway.</translation>
    </message>
</context>
<context>
    <name>MainWindow</name>
    <message>
        <source>Export logs</source>
        <translation>Export logs</translation>
    </message>
    <message>
        <source>ZIP archive (*.zip)</source>
        <translation>ZIP archive (*.zip)</translation>
    </message>
    <message>
        <source>The logs could not be saved to %1.

Cause: %2.

Choose a folder where you can write, for example Documents, and try again.</source>
        <translation>The logs could not be saved to %1.

Cause: %2.

Choose a folder where you can write, for example Documents, and try again.</translation>
    </message>
    <message>
        <source>Logs exported to %1</source>
        <translation>Logs exported to %1</translation>
    </message>
    <message>
        <source>Connected</source>
        <translation>Connected</translation>
    </message>
    <message>
        <source>Disconnected</source>
        <translation>Disconnected</translation>
    </message>
    <message>
        <source>Node %1: profile changed until disconnection</source>
        <translation>Node %1: profile changed until disconnection</translation>
    </message>
    <message>
        <source>EDS not loaded</source>
        <translation>EDS not loaded</translation>
    </message>
    <message>
        <source>The file %1 could not be used for node %2.</source>
        <translation>The file %1 could not be used for node %2.</translation>
    </message>
    <message>
        <source>Choose an .eds or .dcf file of this device, for example from the manufacturer&apos;s website. The node keeps its previous profile.</source>
        <translation>Choose an .eds or .dcf file of this device, for example from the manufacturer&apos;s website. The node keeps its previous profile.</translation>
    </message>
    <message>
        <source>Cause: the file cannot be read; it may have been moved or deleted.</source>
        <translation>Cause: the file cannot be read; it may have been moved or deleted.</translation>
    </message>
    <message>
        <source>Cause: only .eds and .dcf files describe a CANopen device.</source>
        <translation>Cause: only .eds and .dcf files describe a CANopen device.</translation>
    </message>
    <message>
        <source>Cause: the file describes no objects.</source>
        <translation>Cause: the file describes no objects.</translation>
    </message>
    <message>
        <source>Cause: the file is not a valid EDS or DCF (%1).</source>
        <translation>Cause: the file is not a valid EDS or DCF (%1).</translation>
    </message>
    <message>
        <source>%1 sent…</source>
        <translation>%1 sent…</translation>
    </message>
    <message>
        <source>Whole network</source>
        <translation>Whole network</translation>
    </message>
    <message>
        <source>Node %1</source>
        <translation>Node %1</translation>
    </message>
    <message>
        <source>The command reaches every node of the network, also those not in the list.</source>
        <translation>The command reaches every node of the network, also those not in the list.</translation>
    </message>
    <message>
        <source>Put every node of the network in Operational?</source>
        <translation>Put every node of the network in Operational?</translation>
    </message>
    <message>
        <source>The nodes start sending their PDOs: the machine can start moving.</source>
        <translation>The nodes start sending their PDOs: the machine can start moving.</translation>
    </message>
    <message>
        <source>Confirm only if the machine is in a safe condition.</source>
        <translation>Confirm only if the machine is in a safe condition.</translation>
    </message>
    <message>
        <source>Start all nodes</source>
        <translation>Start all nodes</translation>
    </message>
    <message>
        <source>Put every node of the network in Pre-operational?</source>
        <translation>Put every node of the network in Pre-operational?</translation>
    </message>
    <message>
        <source>The nodes stop sending their PDOs: a PLC or controller that uses them gets no more data until Start.</source>
        <translation>The nodes stop sending their PDOs: a PLC or controller that uses them gets no more data until Start.</translation>
    </message>
    <message>
        <source>Confirm only if no one depends on these data now.</source>
        <translation>Confirm only if no one depends on these data now.</translation>
    </message>
    <message>
        <source>Stop the PDOs of all nodes</source>
        <translation>Stop the PDOs of all nodes</translation>
    </message>
    <message>
        <source>Reset every node of the network?</source>
        <translation>Reset every node of the network?</translation>
    </message>
    <message>
        <source>Every node restarts and sends nothing for a few moments; settings not stored with 0x1010 go back to the stored values.</source>
        <translation>Every node restarts and sends nothing for a few moments; settings not stored with 0x1010 go back to the stored values.</translation>
    </message>
    <message>
        <source>Confirm only if the machine is in a safe condition and you do not need the settings not stored.</source>
        <translation>Confirm only if the machine is in a safe condition and you do not need the settings not stored.</translation>
    </message>
    <message>
        <source>Reset all nodes</source>
        <translation>Reset all nodes</translation>
    </message>
    <message>
        <source>Reset the communication of node %1?</source>
        <translation>Reset the communication of node %1?</translation>
    </message>
    <message>
        <source>The node restarts its communication with the stored parameters (COB-IDs, PDOs, heartbeat): changes not stored with 0x1010 are lost, and it sends nothing for a few moments.</source>
        <translation>The node restarts its communication with the stored parameters (COB-IDs, PDOs, heartbeat): changes not stored with 0x1010 are lost, and it sends nothing for a few moments.</translation>
    </message>
    <message>
        <source>Confirm only if you do not need the changes not stored.</source>
        <translation>Confirm only if you do not need the changes not stored.</translation>
    </message>
    <message>
        <source>Reset the communication</source>
        <translation>Reset the communication</translation>
    </message>
    <message>
        <source>Reset node %1?</source>
        <translation>Reset node %1?</translation>
    </message>
    <message>
        <source>The node restarts and sends nothing for a few moments; settings not stored with 0x1010 go back to the stored values.</source>
        <translation>The node restarts and sends nothing for a few moments; settings not stored with 0x1010 go back to the stored values.</translation>
    </message>
    <message>
        <source>Reset the node</source>
        <translation>Reset the node</translation>
    </message>
    <message>
        <source>%1 confirmed by the heartbeat</source>
        <translation>%1 confirmed by the heartbeat</translation>
    </message>
    <message>
        <source>the state did not change after %1</source>
        <translation>the state did not change after %1</translation>
    </message>
    <message>
        <source>no heartbeat after %1</source>
        <translation>no heartbeat after %1</translation>
    </message>
    <message>
        <source>%1 sent, not verifiable (heartbeat off)</source>
        <translation>%1 sent, not verifiable (heartbeat off)</translation>
    </message>
    <message>
        <source>%1 confirmed by %2 of %3 nodes</source>
        <translation>%1 confirmed by %2 of %3 nodes</translation>
    </message>
    <message>
        <source>%1 not confirmed by node %2</source>
        <translation>%1 not confirmed by node %2</translation>
    </message>
    <message>
        <source>The heartbeat did not show the expected state in time. The node may be disconnected, refuse the command in its current state, or be slower than its heartbeat period. Check the cable and the state in the list, then send the command again.</source>
        <translation>The heartbeat did not show the expected state in time. The node may be disconnected, refuse the command in its current state, or be slower than its heartbeat period. Check the cable and the state in the list, then send the command again.</translation>
    </message>
    <message>
        <source>%1 not sent, see the log</source>
        <translation>%1 not sent, see the log</translation>
    </message>
    <message>
        <source>Node %1: heartbeat missing</source>
        <translation>Node %1: heartbeat missing</translation>
    </message>
    <message>
        <source>Node %1: heartbeat back</source>
        <translation>Node %1: heartbeat back</translation>
    </message>
    <message numerus="yes">
        <source>Scan finished: %n node(s)</source>
        <translation>
            <numerusform>Scan finished: %n node</numerusform>
            <numerusform>Scan finished: %n nodes</numerusform>
        </translation>
    </message>
    <message>
        <source>Scan failed: see the log</source>
        <translation>Scan failed: see the log</translation>
    </message>
    <message>
        <source>virtual bus (demo)</source>
        <translation>virtual bus (demo)</translation>
    </message>
    <message>
        <source>Some settings were not valid and were reset: see the log for details.</source>
        <translation>Some settings were not valid and were reset: see the log for details.</translation>
    </message>
    <message>
        <source>Settings not saved (%1). Check the permissions of the settings folder.</source>
        <translation>Settings not saved (%1). Check the permissions of the settings folder.</translation>
    </message>
    <message>
        <source>Rumia Configurator</source>
        <translation>Rumia Configurator</translation>
    </message>
</context>
<context>
    <name>NmtMenu</name>
    <message>
        <source>Ask for confirmation</source>
        <translation>Ask for confirmation</translation>
    </message>
</context>
<context>
    <name>NodePanel</name>
    <message numerus="yes">
        <source>Network · %n node(s)</source>
        <translation>
            <numerusform>Network · %n node</numerusform>
            <numerusform>Network · %n nodes</numerusform>
        </translation>
    </message>
    <message>
        <source>Scan</source>
        <translation>Scan</translation>
    </message>
    <message>
        <source>Look for the nodes on the network</source>
        <translation>Look for the nodes on the network</translation>
    </message>
    <message>
        <source>No nodes yet</source>
        <translation>No nodes yet</translation>
    </message>
    <message>
        <source>Connect to the adapter, then press Scan to find the nodes on the network.</source>
        <translation>Connect to the adapter, then press Scan to find the nodes on the network.</translation>
    </message>
    <message>
        <source>Scanning…</source>
        <translation>Scanning…</translation>
    </message>
    <message>
        <source>Nodes with a heartbeat appear by themselves. Press Scan to find the others.</source>
        <translation>Nodes with a heartbeat appear by themselves. Press Scan to find the others.</translation>
    </message>
    <message>
        <source>Commands to the whole network</source>
        <translation>Commands to the whole network</translation>
    </message>
    <message>
        <source>Start</source>
        <translation>Start</translation>
    </message>
    <message>
        <source>Put every node of the network in Operational state (asks for confirmation)</source>
        <translation>Put every node of the network in Operational state (asks for confirmation)</translation>
    </message>
    <message>
        <source>Put every node of the network in Pre-operational state (asks for confirmation)</source>
        <translation>Put every node of the network in Pre-operational state (asks for confirmation)</translation>
    </message>
    <message>
        <source>Restart every node of the network (asks for confirmation)</source>
        <translation>Restart every node of the network (asks for confirmation)</translation>
    </message>
    <message>
        <source>Pre-op</source>
        <translation>Pre-op</translation>
    </message>
    <message>
        <source>Reset</source>
        <translation>Reset</translation>
    </message>
</context>
<context>
    <name>NodeRow</name>
    <message>
        <source>Node without name</source>
        <translation>Node without name</translation>
    </message>
    <message>
        <source>Heartbeat missing for %1 s</source>
        <translation>Heartbeat missing for %1 s</translation>
    </message>
    <message>
        <source>heartbeat off</source>
        <translation>heartbeat off</translation>
    </message>
    <message>
        <source>heartbeat %1 ms</source>
        <translation>heartbeat %1 ms</translation>
    </message>
    <message>
        <source>heartbeat not read</source>
        <translation>heartbeat not read</translation>
    </message>
    <message>
        <source>chosen by hand</source>
        <translation>chosen by hand</translation>
    </message>
    <message>
        <source>Node %1, %2, %3</source>
        <translation>Node %1, %2, %3</translation>
    </message>
    <message>
        <source>Associate profile…</source>
        <translation>Associate profile…</translation>
    </message>
    <message>
        <source>State unknown</source>
        <translation>State unknown</translation>
    </message>
</context>
<context>
    <name>ProfileDialog</name>
    <message>
        <source>Profile of node %1</source>
        <translation>Profile of node %1</translation>
    </message>
    <message>
        <source>Choose how the application reads node %1. The choice lasts until you disconnect.</source>
        <translation>Choose how the application reads node %1. The choice lasts until you disconnect.</translation>
    </message>
    <message>
        <source>EDS or DCF file…</source>
        <translation>EDS or DCF file…</translation>
    </message>
    <message>
        <source>No profile (only the CiA 301 objects)</source>
        <translation>No profile (only the CiA 301 objects)</translation>
    </message>
    <message>
        <source>Automatic recognition</source>
        <translation>Automatic recognition</translation>
    </message>
    <message>
        <source>EDS or DCF file</source>
        <translation>EDS or DCF file</translation>
    </message>
    <message>
        <source>Electronic data sheets (*.eds *.dcf)</source>
        <translation>Electronic data sheets (*.eds *.dcf)</translation>
    </message>
</context>
<context>
    <name>StatusBar</name>
    <message>
        <source>Not connected</source>
        <translation>Not connected</translation>
    </message>
    <message>
        <source>no adapter</source>
        <translation>no adapter</translation>
    </message>
    <message>
        <source>%1 frames/s</source>
        <translation>%1 frames/s</translation>
    </message>
    <message>
        <source>load %1</source>
        <translation>load %1</translation>
    </message>
    <message>
        <source>lost %1</source>
        <translation>lost %1</translation>
    </message>
    <message>
        <source>errors %1</source>
        <translation>errors %1</translation>
    </message>
    <message>
        <source>error active</source>
        <translation>error active</translation>
    </message>
    <message>
        <source>error passive</source>
        <translation>error passive</translation>
    </message>
    <message>
        <source>bus-off</source>
        <translation>bus-off</translation>
    </message>
    <message>
        <source>controller n/a</source>
        <translation>controller n/a</translation>
    </message>
    <message>
        <source>Connected</source>
        <translation>Connected</translation>
    </message>
    <message>
        <source>Connecting…</source>
        <translation>Connecting…</translation>
    </message>
    <message>
        <source>Adapter lost</source>
        <translation>Adapter lost</translation>
    </message>
    <message>
        <source>Ready</source>
        <translation>Ready</translation>
    </message>
</context>
<context>
    <name>TopBar</name>
    <message>
        <source>Configurator</source>
        <translation>Configurator</translation>
    </message>
    <message>
        <source>Adapter</source>
        <translation>Adapter</translation>
    </message>
    <message>
        <source>No adapter</source>
        <translation>No adapter</translation>
    </message>
    <message>
        <source>Choose the USB-CAN adapter</source>
        <translation>Choose the USB-CAN adapter</translation>
    </message>
    <message>
        <source>Bitrate of the CAN network</source>
        <translation>Bitrate of the CAN network</translation>
    </message>
    <message>
        <source>Connect</source>
        <translation>Connect</translation>
    </message>
    <message>
        <source>Virtual bus (demo)</source>
        <translation>Virtual bus (demo)</translation>
    </message>
    <message>
        <source>Disconnect</source>
        <translation>Disconnect</translation>
    </message>
    <message>
        <source>Connected</source>
        <translation>Connected</translation>
    </message>
    <message>
        <source>Connecting…</source>
        <translation>Connecting…</translation>
    </message>
    <message>
        <source>Adapter lost</source>
        <translation>Adapter lost</translation>
    </message>
    <message>
        <source>Not connected</source>
        <translation>Not connected</translation>
    </message>
    <message>
        <source>Refresh list</source>
        <translation>Refresh list</translation>
    </message>
    <message>
        <source>Other adapter…</source>
        <translation>Other adapter…</translation>
    </message>
    <message>
        <source>No adapter found</source>
        <translation>No adapter found</translation>
    </message>
    <message>
        <source>Setup wizard</source>
        <translation>Setup wizard</translation>
    </message>
    <message>
        <source>Base</source>
        <translation>Base</translation>
    </message>
    <message>
        <source>Rumia products and guided procedures</source>
        <translation>Rumia products and guided procedures</translation>
    </message>
    <message>
        <source>Expert</source>
        <translation>Expert</translation>
    </message>
    <message>
        <source>Object dictionary, PDO and bus monitor</source>
        <translation>Object dictionary, PDO and bus monitor</translation>
    </message>
    <message>
        <source>Language</source>
        <translation>Language</translation>
    </message>
    <message>
        <source>System language</source>
        <translation>System language</translation>
    </message>
    <message>
        <source>Menu</source>
        <translation>Menu</translation>
    </message>
    <message>
        <source>Theme</source>
        <translation>Theme</translation>
    </message>
    <message>
        <source>System</source>
        <translation>System</translation>
    </message>
    <message>
        <source>Light</source>
        <translation>Light</translation>
    </message>
    <message>
        <source>Dark</source>
        <translation>Dark</translation>
    </message>
    <message>
        <source>Export logs…</source>
        <translation>Export logs…</translation>
    </message>
    <message>
        <source>Quit</source>
        <translation>Quit</translation>
    </message>
</context>
<context>
    <name>Workspace</name>
    <message>
        <source>recognised by its name</source>
        <translation>recognised by its name</translation>
    </message>
    <message>
        <source>chosen by hand until disconnection</source>
        <translation>chosen by hand until disconnection</translation>
    </message>
    <message>
        <source>not recognised</source>
        <translation>not recognised</translation>
    </message>
    <message>
        <source>no profile, only the CiA 301 objects</source>
        <translation>no profile, only the CiA 301 objects</translation>
    </message>
    <message>
        <source>Profile: %1</source>
        <translation>Profile: %1</translation>
    </message>
    <message numerus="yes">
        <source>%n EDS warning(s)</source>
        <translation>
            <numerusform>%n EDS warning</numerusform>
            <numerusform>%n EDS warnings</numerusform>
        </translation>
    </message>
    <message>
        <source>Change profile…</source>
        <translation>Change profile…</translation>
    </message>
    <message>
        <source>No node selected</source>
        <translation>No node selected</translation>
    </message>
    <message>
        <source>Connect to a CAN network and choose a node in the panel on the left.</source>
        <translation>Connect to a CAN network and choose a node in the panel on the left.</translation>
    </message>
    <message>
        <source>node %1</source>
        <translation>node %1</translation>
    </message>
    <message>
        <source>Node %1</source>
        <translation>Node %1</translation>
    </message>
    <message>
        <source>Revision</source>
        <translation>Revision</translation>
    </message>
    <message>
        <source>Serial</source>
        <translation>Serial</translation>
    </message>
    <message>
        <source>Identity not available: the node did not answer 0x1018.</source>
        <translation>Identity not available: the node did not answer 0x1018.</translation>
    </message>
    <message>
        <source>Reading the identity of the node…</source>
        <translation>Reading the identity of the node…</translation>
    </message>
    <message>
        <source>NMT commands for this node</source>
        <translation>NMT commands for this node</translation>
    </message>
    <message>
        <source>Choose a node in the network panel to see its data here.</source>
        <translation>Choose a node in the network panel to see its data here.</translation>
    </message>
    <message>
        <source>Overview</source>
        <translation>Overview</translation>
    </message>
    <message>
        <source>Parameters</source>
        <translation>Parameters</translation>
    </message>
    <message>
        <source>PDO</source>
        <translation>PDO</translation>
    </message>
    <message>
        <source>Plots</source>
        <translation>Plots</translation>
    </message>
    <message>
        <source>Bus monitor</source>
        <translation>Bus monitor</translation>
    </message>
    <message>
        <source>Connect to an adapter to see the CAN traffic here.</source>
        <translation>Connect to an adapter to see the CAN traffic here.</translation>
    </message>
    <message>
        <source>Log</source>
        <translation>Log</translation>
    </message>
    <message>
        <source>The messages of the application will appear here.</source>
        <translation>The messages of the application will appear here.</translation>
    </message>
</context>
<context>
    <name>app</name>
    <message>
        <source>Demo mode</source>
        <translation>Demo mode</translation>
    </message>
    <message>
        <source>Demo mode could not start.

Cause: the virtual CAN bus with the simulated nodes did not open (%1).

Start the application without --demo, and send the logs (menu, Export logs) to Rumia support.</source>
        <translation>Demo mode could not start.

Cause: the virtual CAN bus with the simulated nodes did not open (%1).

Start the application without --demo, and send the logs (menu, Export logs) to Rumia support.</translation>
    </message>
</context>
</TS>
