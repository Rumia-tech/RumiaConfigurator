<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="it_IT">
<context>
    <name>AdapterDialog</name>
    <message>
        <source>Other adapter</source>
        <translation>Altro adattatore</translation>
    </message>
    <message>
        <source>Adapter type</source>
        <translation>Tipo di adattatore</translation>
    </message>
    <message>
        <source>Channel</source>
        <translation>Canale</translation>
    </message>
    <message>
        <source>Example: %1</source>
        <translation>Esempio: %1</translation>
    </message>
    <message>
        <source>The bitrate of this adapter is set in the operating system, not here.</source>
        <translation>Il bitrate di questo adattatore si imposta nel sistema operativo, non qui.</translation>
    </message>
</context>
<context>
    <name>ConnectionMessages</name>
    <message>
        <source>Connection lost</source>
        <translation>Connessione persa</translation>
    </message>
    <message>
        <source>The connection to %1 was lost.</source>
        <translation>La connessione con %1 si è interrotta.</translation>
    </message>
    <message>
        <source>Connection failed</source>
        <translation>Connessione non riuscita</translation>
    </message>
    <message>
        <source>Could not connect to %1.</source>
        <translation>Non è stato possibile connettersi a %1.</translation>
    </message>
    <message>
        <source>Cause: the port does not exist. The adapter is unplugged or has another name.</source>
        <translation>Causa: la porta non esiste. L&apos;adattatore è scollegato oppure ha un altro nome.</translation>
    </message>
    <message>
        <source>Plug the adapter in, choose Refresh list in the adapter menu and select it again.</source>
        <translation>Collega l&apos;adattatore, scegli Aggiorna elenco nel menu dell&apos;adattatore e selezionalo di nuovo.</translation>
    </message>
    <message>
        <source>Cause: another program is using the port, for example another configurator, a serial terminal or a second copy of this application.</source>
        <translation>Causa: un altro programma sta usando la porta, per esempio un altro configuratore, un terminale seriale o una seconda copia di questa applicazione.</translation>
    </message>
    <message>
        <source>Close the other program, or disconnect it from the port, then try again.</source>
        <translation>Chiudi l&apos;altro programma, o scollegalo dalla porta, poi riprova.</translation>
    </message>
    <message>
        <source>Cause: your user is not allowed to use serial ports on this computer.</source>
        <translation>Causa: il tuo utente non ha il permesso di usare le porte seriali su questo computer.</translation>
    </message>
    <message>
        <source>Ask the administrator to run once: sudo usermod -aG dialout $USER (uucp on Arch Linux and macOS), then log out and in again. This application never asks for administrator rights.</source>
        <translation>Chiedi all&apos;amministratore di eseguire una volta: sudo usermod -aG dialout $USER (uucp su Arch Linux e macOS), poi esci e rientra nella sessione. Questa applicazione non chiede mai i diritti di amministratore.</translation>
    </message>
    <message>
        <source>Cause: the driver or library of %2 is not installed.</source>
        <translation>Causa: il driver o la libreria di %2 non è installato.</translation>
    </message>
    <message>
        <source>Cause: the SocketCAN interface %1 is down.</source>
        <translation>Causa: l&apos;interfaccia SocketCAN %1 non è attiva.</translation>
    </message>
    <message>
        <source>Ask the administrator to bring it up with the network bitrate, for example: sudo ip link set %1 up type can bitrate 500000. For SocketCAN the bitrate is set there, not in this application.</source>
        <translation>Chiedi all&apos;amministratore di attivarla con il bitrate della rete, per esempio: sudo ip link set %1 up type can bitrate 500000. Con SocketCAN il bitrate si imposta lì, non in questa applicazione.</translation>
    </message>
    <message>
        <source>Cause: the port opened, but nothing answered like an SLCAN adapter. It may be another device, or an adapter with a different firmware.</source>
        <translation>Causa: la porta si è aperta, ma non ha risposto nessun adattatore SLCAN. Può essere un altro dispositivo, o un adattatore con un firmware diverso.</translation>
    </message>
    <message>
        <source>Choose the port of the Rumia USB-CAN interface (it is first in the list, marked RUMIA). If it is already selected, unplug it, plug it in again and retry.</source>
        <translation>Scegli la porta dell&apos;interfaccia USB-CAN Rumia (è la prima dell&apos;elenco, con l&apos;etichetta RUMIA). Se è già selezionata, scollegala, ricollegala e riprova.</translation>
    </message>
    <message>
        <source>Cause: %2 adapters cannot be used on this operating system.</source>
        <translation>Causa: gli adattatori %2 non si possono usare su questo sistema operativo.</translation>
    </message>
    <message>
        <source>Choose another adapter type in Other adapter…</source>
        <translation>Scegli un altro tipo di adattatore in Altro adattatore…</translation>
    </message>
    <message>
        <source>Cause: the connection settings are not valid (%3).</source>
        <translation>Causa: le impostazioni di connessione non sono valide (%3).</translation>
    </message>
    <message>
        <source>Check the adapter type, the channel and the bitrate in Other adapter…</source>
        <translation>Controlla tipo di adattatore, canale e bitrate in Altro adattatore…</translation>
    </message>
    <message>
        <source>Cause: only one bus can be open at a time.</source>
        <translation>Causa: si può aprire un solo bus alla volta.</translation>
    </message>
    <message>
        <source>Disconnect first, then connect to the other adapter.</source>
        <translation>Prima disconnettiti, poi connettiti all&apos;altro adattatore.</translation>
    </message>
    <message>
        <source>Cause: the adapter stopped answering. It was unplugged, or its driver reported an error.</source>
        <translation>Causa: l&apos;adattatore ha smesso di rispondere. È stato scollegato, oppure il suo driver ha segnalato un errore.</translation>
    </message>
    <message>
        <source>Plug the adapter in again and press Connect.</source>
        <translation>Ricollega l&apos;adattatore e premi Connetti.</translation>
    </message>
    <message>
        <source>Cause: the CAN library reported an error that the application does not know: %3</source>
        <translation>Causa: la libreria CAN ha segnalato un errore che l&apos;applicazione non conosce: %3</translation>
    </message>
    <message>
        <source>Try again. If it happens again, export the logs (menu, Export logs…) and send them to Rumia support.</source>
        <translation>Riprova. Se succede di nuovo, esporta i log (menu, Esporta log…) e inviali all&apos;assistenza Rumia.</translation>
    </message>
    <message>
        <source>Install the PEAK driver with the PCAN-Basic library from the manufacturer&apos;s website, then restart the application.</source>
        <translation>Installa il driver PEAK con la libreria PCAN-Basic dal sito del produttore, poi riavvia l&apos;applicazione.</translation>
    </message>
    <message>
        <source>Install the Kvaser drivers with the CANlib library from the manufacturer&apos;s website, then restart the application.</source>
        <translation>Installa i driver Kvaser con la libreria CANlib dal sito del produttore, poi riavvia l&apos;applicazione.</translation>
    </message>
    <message>
        <source>Install the IXXAT VCI driver from the manufacturer&apos;s website, then restart the application.</source>
        <translation>Installa il driver IXXAT VCI dal sito del produttore, poi riavvia l&apos;applicazione.</translation>
    </message>
    <message>
        <source>This version of the application does not include support for candleLight (gs_usb) adapters. Use an SLCAN adapter such as the Rumia USB-CAN interface.</source>
        <translation>Questa versione dell&apos;applicazione non include il supporto per gli adattatori candleLight (gs_usb). Usa un adattatore SLCAN come l&apos;interfaccia USB-CAN Rumia.</translation>
    </message>
    <message>
        <source>Install the driver of the adapter, then restart the application.</source>
        <translation>Installa il driver dell&apos;adattatore, poi riavvia l&apos;applicazione.</translation>
    </message>
</context>
<context>
    <name>DemoBanner</name>
    <message>
        <source>Demo mode</source>
        <translation>Modalità demo</translation>
    </message>
    <message>
        <source>Virtual bus with simulated nodes (%1). No real device is connected: to use a sensor, restart the application without --demo.</source>
        <translation>Bus virtuale con nodi simulati (%1). Nessun dispositivo reale è collegato: per usare un sensore, riavvia l&apos;applicazione senza --demo.</translation>
    </message>
</context>
<context>
    <name>EdsWarnings</name>
    <message>
        <source>Field %1 of [DeviceInfo] is empty: read as 0</source>
        <translation>Campo %1 di [DeviceInfo] vuoto: letto come 0</translation>
    </message>
    <message>
        <source>Mandatory CiA 301 objects missing: %1</source>
        <translation>Mancano oggetti obbligatori CiA 301: %1</translation>
    </message>
    <message>
        <source>%1 objects without a default value (%2)</source>
        <translation>%1 oggetti senza valore di default (%2)</translation>
    </message>
    <message>
        <source>The product name is empty</source>
        <translation>Il nome del prodotto è vuoto</translation>
    </message>
    <message>
        <source>CANopen library: %1</source>
        <translation>Libreria CANopen: %1</translation>
    </message>
    <message>
        <source>EDS warnings</source>
        <translation>Avvisi EDS</translation>
    </message>
    <message>
        <source>%1 loaded, with these warnings. The application works anyway.</source>
        <translation>%1 caricato, con questi avvisi. L&apos;applicazione funziona comunque.</translation>
    </message>
</context>
<context>
    <name>MainWindow</name>
    <message>
        <source>Export logs</source>
        <translation>Esporta log</translation>
    </message>
    <message>
        <source>ZIP archive (*.zip)</source>
        <translation>Archivio ZIP (*.zip)</translation>
    </message>
    <message>
        <source>The logs could not be saved to %1.

Cause: %2.

Choose a folder where you can write, for example Documents, and try again.</source>
        <translation>Non è stato possibile salvare i log in %1.

Causa: %2.

Scegli una cartella in cui puoi scrivere, per esempio Documenti, e riprova.</translation>
    </message>
    <message>
        <source>Logs exported to %1</source>
        <translation>Log esportati in %1</translation>
    </message>
    <message>
        <source>Connected</source>
        <translation>Connesso</translation>
    </message>
    <message>
        <source>Disconnected</source>
        <translation>Disconnesso</translation>
    </message>
    <message>
        <source>Node %1: profile changed until disconnection</source>
        <translation>Nodo %1: profilo cambiato fino alla disconnessione</translation>
    </message>
    <message>
        <source>EDS not loaded</source>
        <translation>EDS non caricato</translation>
    </message>
    <message>
        <source>The file %1 could not be used for node %2.</source>
        <translation>Non è stato possibile usare il file %1 per il nodo %2.</translation>
    </message>
    <message>
        <source>Choose an .eds or .dcf file of this device, for example from the manufacturer&apos;s website. The node keeps its previous profile.</source>
        <translation>Scegli un file .eds o .dcf di questo dispositivo, per esempio dal sito del produttore. Il nodo mantiene il profilo precedente.</translation>
    </message>
    <message>
        <source>Cause: the file cannot be read; it may have been moved or deleted.</source>
        <translation>Causa: il file non si può leggere; forse è stato spostato o cancellato.</translation>
    </message>
    <message>
        <source>Cause: only .eds and .dcf files describe a CANopen device.</source>
        <translation>Causa: solo i file .eds e .dcf descrivono un dispositivo CANopen.</translation>
    </message>
    <message>
        <source>Cause: the file describes no objects.</source>
        <translation>Causa: il file non descrive nessun oggetto.</translation>
    </message>
    <message>
        <source>Cause: the file is not a valid EDS or DCF (%1).</source>
        <translation>Causa: il file non è un EDS o DCF valido (%1).</translation>
    </message>
    <message>
        <source>%1 sent…</source>
        <translation>%1 inviato…</translation>
    </message>
    <message>
        <source>Whole network</source>
        <translation>Tutta la rete</translation>
    </message>
    <message>
        <source>Node %1</source>
        <translation>Nodo %1</translation>
    </message>
    <message>
        <source>The command reaches every node of the network, also those not in the list.</source>
        <translation>Il comando arriva a ogni nodo della rete, anche a quelli non in elenco.</translation>
    </message>
    <message>
        <source>Put every node of the network in Operational?</source>
        <translation>Mettere in Operational tutti i nodi della rete?</translation>
    </message>
    <message>
        <source>The nodes start sending their PDOs: the machine can start moving.</source>
        <translation>I nodi iniziano a trasmettere i PDO: la macchina può mettersi in movimento.</translation>
    </message>
    <message>
        <source>Confirm only if the machine is in a safe condition.</source>
        <translation>Conferma solo se la macchina è in condizioni sicure.</translation>
    </message>
    <message>
        <source>Start all nodes</source>
        <translation>Avvia tutti i nodi</translation>
    </message>
    <message>
        <source>Put every node of the network in Pre-operational?</source>
        <translation>Mettere in Pre-operational tutti i nodi della rete?</translation>
    </message>
    <message>
        <source>The nodes stop sending their PDOs: a PLC or controller that uses them gets no more data until Start.</source>
        <translation>I nodi smettono di trasmettere i PDO: un PLC o un controllore che li usa non riceve più dati fino a Start.</translation>
    </message>
    <message>
        <source>Confirm only if no one depends on these data now.</source>
        <translation>Conferma solo se in questo momento nessuno dipende da questi dati.</translation>
    </message>
    <message>
        <source>Stop the PDOs of all nodes</source>
        <translation>Ferma i PDO di tutti i nodi</translation>
    </message>
    <message>
        <source>Reset every node of the network?</source>
        <translation>Resettare tutti i nodi della rete?</translation>
    </message>
    <message>
        <source>Every node restarts and sends nothing for a few moments; settings not stored with 0x1010 go back to the stored values.</source>
        <translation>Ogni nodo si riavvia e per qualche istante non trasmette; le impostazioni non salvate con 0x1010 tornano ai valori salvati.</translation>
    </message>
    <message>
        <source>Confirm only if the machine is in a safe condition and you do not need the settings not stored.</source>
        <translation>Conferma solo se la macchina è in condizioni sicure e non ti servono le impostazioni non salvate.</translation>
    </message>
    <message>
        <source>Reset all nodes</source>
        <translation>Resetta tutti i nodi</translation>
    </message>
    <message>
        <source>Reset the communication of node %1?</source>
        <translation>Resettare la comunicazione del nodo %1?</translation>
    </message>
    <message>
        <source>The node restarts its communication with the stored parameters (COB-IDs, PDOs, heartbeat): changes not stored with 0x1010 are lost, and it sends nothing for a few moments.</source>
        <translation>Il nodo riavvia la comunicazione con i parametri salvati (COB-ID, PDO, heartbeat): le modifiche non salvate con 0x1010 si perdono, e per qualche istante non trasmette.</translation>
    </message>
    <message>
        <source>Confirm only if you do not need the changes not stored.</source>
        <translation>Conferma solo se non ti servono le modifiche non salvate.</translation>
    </message>
    <message>
        <source>Reset the communication</source>
        <translation>Resetta la comunicazione</translation>
    </message>
    <message>
        <source>Reset node %1?</source>
        <translation>Resettare il nodo %1?</translation>
    </message>
    <message>
        <source>The node restarts and sends nothing for a few moments; settings not stored with 0x1010 go back to the stored values.</source>
        <translation>Il nodo si riavvia e per qualche istante non trasmette; le impostazioni non salvate con 0x1010 tornano ai valori salvati.</translation>
    </message>
    <message>
        <source>Reset the node</source>
        <translation>Resetta il nodo</translation>
    </message>
    <message>
        <source>%1 confirmed by the heartbeat</source>
        <translation>%1 confermato dall&apos;heartbeat</translation>
    </message>
    <message>
        <source>the state did not change after %1</source>
        <translation>lo stato non è cambiato dopo %1</translation>
    </message>
    <message>
        <source>no heartbeat after %1</source>
        <translation>nessun heartbeat dopo %1</translation>
    </message>
    <message>
        <source>%1 sent, not verifiable (heartbeat off)</source>
        <translation>%1 inviato, non verificabile (heartbeat spento)</translation>
    </message>
    <message>
        <source>%1 confirmed by %2 of %3 nodes</source>
        <translation>%1 confermato da %2 nodi su %3</translation>
    </message>
    <message>
        <source>%1 not confirmed by node %2</source>
        <translation>%1 non confermato dal nodo %2</translation>
    </message>
    <message>
        <source>The heartbeat did not show the expected state in time. The node may be disconnected, refuse the command in its current state, or be slower than its heartbeat period. Check the cable and the state in the list, then send the command again.</source>
        <translation>L&apos;heartbeat non ha mostrato in tempo lo stato atteso. Il nodo può essere scollegato, rifiutare il comando nel suo stato attuale o essere più lento del suo periodo di heartbeat. Controlla il cavo e lo stato nell&apos;elenco, poi invia di nuovo il comando.</translation>
    </message>
    <message>
        <source>%1 not sent, see the log</source>
        <translation>%1 non inviato, vedi il log</translation>
    </message>
    <message>
        <source>Node %1: heartbeat missing</source>
        <translation>Nodo %1: heartbeat assente</translation>
    </message>
    <message>
        <source>Node %1: heartbeat back</source>
        <translation>Nodo %1: heartbeat tornato</translation>
    </message>
    <message numerus="yes">
        <source>Scan finished: %n node(s)</source>
        <translation>
            <numerusform>Scansione finita: %n nodo</numerusform>
            <numerusform>Scansione finita: %n nodi</numerusform>
        </translation>
    </message>
    <message>
        <source>Scan failed: see the log</source>
        <translation>Scansione non riuscita: vedi il log</translation>
    </message>
    <message>
        <source>virtual bus (demo)</source>
        <translation>bus virtuale (demo)</translation>
    </message>
    <message>
        <source>Some settings were not valid and were reset: see the log for details.</source>
        <translation>Alcune impostazioni non erano valide e sono state ripristinate: i dettagli sono nel log.</translation>
    </message>
    <message>
        <source>Settings not saved (%1). Check the permissions of the settings folder.</source>
        <translation>Impostazioni non salvate (%1). Controlla i permessi della cartella delle impostazioni.</translation>
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
        <translation>Chiede conferma</translation>
    </message>
</context>
<context>
    <name>NodePanel</name>
    <message numerus="yes">
        <source>Network · %n node(s)</source>
        <translation>
            <numerusform>Rete · %n nodo</numerusform>
            <numerusform>Rete · %n nodi</numerusform>
        </translation>
    </message>
    <message>
        <source>Scan</source>
        <translation>Scansiona</translation>
    </message>
    <message>
        <source>Look for the nodes on the network</source>
        <translation>Cerca i nodi sulla rete</translation>
    </message>
    <message>
        <source>No nodes yet</source>
        <translation>Nessun nodo</translation>
    </message>
    <message>
        <source>Connect to the adapter, then press Scan to find the nodes on the network.</source>
        <translation>Connettiti all&apos;adattatore, poi premi Scansiona per trovare i nodi sulla rete.</translation>
    </message>
    <message>
        <source>Scanning…</source>
        <translation>Scansione…</translation>
    </message>
    <message>
        <source>Nodes with a heartbeat appear by themselves. Press Scan to find the others.</source>
        <translation>I nodi con heartbeat compaiono da soli. Premi Scansiona per trovare gli altri.</translation>
    </message>
    <message>
        <source>Commands to the whole network</source>
        <translation>Comandi a tutta la rete</translation>
    </message>
    <message>
        <source>Start</source>
        <translation>Start</translation>
    </message>
    <message>
        <source>Put every node of the network in Operational state (asks for confirmation)</source>
        <translation>Mette tutti i nodi della rete in Operational (chiede conferma)</translation>
    </message>
    <message>
        <source>Put every node of the network in Pre-operational state (asks for confirmation)</source>
        <translation>Mette tutti i nodi della rete in Pre-operational (chiede conferma)</translation>
    </message>
    <message>
        <source>Restart every node of the network (asks for confirmation)</source>
        <translation>Riavvia tutti i nodi della rete (chiede conferma)</translation>
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
        <translation>Nodo senza nome</translation>
    </message>
    <message>
        <source>Heartbeat missing for %1 s</source>
        <translation>Heartbeat assente da %1 s</translation>
    </message>
    <message>
        <source>heartbeat off</source>
        <translation>heartbeat spento</translation>
    </message>
    <message>
        <source>heartbeat %1 ms</source>
        <translation>heartbeat %1 ms</translation>
    </message>
    <message>
        <source>heartbeat not read</source>
        <translation>heartbeat non letto</translation>
    </message>
    <message>
        <source>chosen by hand</source>
        <translation>scelto a mano</translation>
    </message>
    <message>
        <source>Node %1, %2, %3</source>
        <translation>Nodo %1, %2, %3</translation>
    </message>
    <message>
        <source>Associate profile…</source>
        <translation>Associa profilo…</translation>
    </message>
    <message>
        <source>State unknown</source>
        <translation>Stato sconosciuto</translation>
    </message>
</context>
<context>
    <name>ProfileDialog</name>
    <message>
        <source>Profile of node %1</source>
        <translation>Profilo del nodo %1</translation>
    </message>
    <message>
        <source>Choose how the application reads node %1. The choice lasts until you disconnect.</source>
        <translation>Scegli come l&apos;applicazione legge il nodo %1. La scelta vale fino alla disconnessione.</translation>
    </message>
    <message>
        <source>EDS or DCF file…</source>
        <translation>File EDS o DCF…</translation>
    </message>
    <message>
        <source>No profile (only the CiA 301 objects)</source>
        <translation>Nessun profilo (solo gli oggetti CiA 301)</translation>
    </message>
    <message>
        <source>Automatic recognition</source>
        <translation>Riconoscimento automatico</translation>
    </message>
    <message>
        <source>EDS or DCF file</source>
        <translation>File EDS o DCF</translation>
    </message>
    <message>
        <source>Electronic data sheets (*.eds *.dcf)</source>
        <translation>Electronic data sheet (*.eds *.dcf)</translation>
    </message>
</context>
<context>
    <name>StatusBar</name>
    <message>
        <source>Not connected</source>
        <translation>Non connesso</translation>
    </message>
    <message>
        <source>no adapter</source>
        <translation>nessun adattatore</translation>
    </message>
    <message>
        <source>%1 frames/s</source>
        <translation>%1 frame/s</translation>
    </message>
    <message>
        <source>load %1</source>
        <translation>carico %1</translation>
    </message>
    <message>
        <source>lost %1</source>
        <translation>persi %1</translation>
    </message>
    <message>
        <source>errors %1</source>
        <translation>errori %1</translation>
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
        <translation>controller n/d</translation>
    </message>
    <message>
        <source>Connected</source>
        <translation>Connesso</translation>
    </message>
    <message>
        <source>Connecting…</source>
        <translation>Connessione…</translation>
    </message>
    <message>
        <source>Adapter lost</source>
        <translation>Adattatore perso</translation>
    </message>
    <message>
        <source>Ready</source>
        <translation>Pronto</translation>
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
        <translation>Adattatore</translation>
    </message>
    <message>
        <source>No adapter</source>
        <translation>Nessun adattatore</translation>
    </message>
    <message>
        <source>Choose the USB-CAN adapter</source>
        <translation>Scegli l&apos;adattatore USB-CAN</translation>
    </message>
    <message>
        <source>Bitrate of the CAN network</source>
        <translation>Bitrate della rete CAN</translation>
    </message>
    <message>
        <source>Connect</source>
        <translation>Connetti</translation>
    </message>
    <message>
        <source>Virtual bus (demo)</source>
        <translation>Bus virtuale (demo)</translation>
    </message>
    <message>
        <source>Disconnect</source>
        <translation>Disconnetti</translation>
    </message>
    <message>
        <source>Connected</source>
        <translation>Connesso</translation>
    </message>
    <message>
        <source>Connecting…</source>
        <translation>Connessione…</translation>
    </message>
    <message>
        <source>Adapter lost</source>
        <translation>Adattatore perso</translation>
    </message>
    <message>
        <source>Not connected</source>
        <translation>Non connesso</translation>
    </message>
    <message>
        <source>Refresh list</source>
        <translation>Aggiorna elenco</translation>
    </message>
    <message>
        <source>Other adapter…</source>
        <translation>Altro adattatore…</translation>
    </message>
    <message>
        <source>No adapter found</source>
        <translation>Nessun adattatore trovato</translation>
    </message>
    <message>
        <source>Setup wizard</source>
        <translation>Procedura guidata</translation>
    </message>
    <message>
        <source>Base</source>
        <translation>Base</translation>
    </message>
    <message>
        <source>Rumia products and guided procedures</source>
        <translation>Prodotti Rumia e procedure guidate</translation>
    </message>
    <message>
        <source>Expert</source>
        <translation>Esperto</translation>
    </message>
    <message>
        <source>Object dictionary, PDO and bus monitor</source>
        <translation>Object Dictionary, PDO e monitor del bus</translation>
    </message>
    <message>
        <source>Language</source>
        <translation>Lingua</translation>
    </message>
    <message>
        <source>System language</source>
        <translation>Lingua del sistema</translation>
    </message>
    <message>
        <source>Menu</source>
        <translation>Menu</translation>
    </message>
    <message>
        <source>Theme</source>
        <translation>Tema</translation>
    </message>
    <message>
        <source>System</source>
        <translation>Sistema</translation>
    </message>
    <message>
        <source>Light</source>
        <translation>Chiaro</translation>
    </message>
    <message>
        <source>Dark</source>
        <translation>Scuro</translation>
    </message>
    <message>
        <source>Export logs…</source>
        <translation>Esporta log…</translation>
    </message>
    <message>
        <source>Quit</source>
        <translation>Esci</translation>
    </message>
</context>
<context>
    <name>Workspace</name>
    <message>
        <source>recognised by its name</source>
        <translation>riconosciuto dal nome</translation>
    </message>
    <message>
        <source>chosen by hand until disconnection</source>
        <translation>scelto a mano fino alla disconnessione</translation>
    </message>
    <message>
        <source>not recognised</source>
        <translation>non riconosciuto</translation>
    </message>
    <message>
        <source>no profile, only the CiA 301 objects</source>
        <translation>nessun profilo, solo gli oggetti CiA 301</translation>
    </message>
    <message>
        <source>Profile: %1</source>
        <translation>Profilo: %1</translation>
    </message>
    <message numerus="yes">
        <source>%n EDS warning(s)</source>
        <translation>
            <numerusform>%n avviso EDS</numerusform>
            <numerusform>%n avvisi EDS</numerusform>
        </translation>
    </message>
    <message>
        <source>Change profile…</source>
        <translation>Cambia profilo…</translation>
    </message>
    <message>
        <source>No node selected</source>
        <translation>Nessun nodo selezionato</translation>
    </message>
    <message>
        <source>Connect to a CAN network and choose a node in the panel on the left.</source>
        <translation>Connettiti a una rete CAN e scegli un nodo nel pannello a sinistra.</translation>
    </message>
    <message>
        <source>node %1</source>
        <translation>nodo %1</translation>
    </message>
    <message>
        <source>Node %1</source>
        <translation>Nodo %1</translation>
    </message>
    <message>
        <source>Revision</source>
        <translation>Revisione</translation>
    </message>
    <message>
        <source>Serial</source>
        <translation>Seriale</translation>
    </message>
    <message>
        <source>Identity not available: the node did not answer 0x1018.</source>
        <translation>Identità non disponibile: il nodo non ha risposto a 0x1018.</translation>
    </message>
    <message>
        <source>Reading the identity of the node…</source>
        <translation>Lettura dell&apos;identità del nodo…</translation>
    </message>
    <message>
        <source>NMT commands for this node</source>
        <translation>Comandi NMT per questo nodo</translation>
    </message>
    <message>
        <source>Choose a node in the network panel to see its data here.</source>
        <translation>Scegli un nodo nel pannello della rete per vederne qui i dati.</translation>
    </message>
    <message>
        <source>Overview</source>
        <translation>Panoramica</translation>
    </message>
    <message>
        <source>Parameters</source>
        <translation>Parametri</translation>
    </message>
    <message>
        <source>PDO</source>
        <translation>PDO</translation>
    </message>
    <message>
        <source>Plots</source>
        <translation>Grafici</translation>
    </message>
    <message>
        <source>Bus monitor</source>
        <translation>Monitor bus</translation>
    </message>
    <message>
        <source>Connect to an adapter to see the CAN traffic here.</source>
        <translation>Connettiti a un adattatore per vedere qui il traffico CAN.</translation>
    </message>
    <message>
        <source>Log</source>
        <translation>Log</translation>
    </message>
    <message>
        <source>The messages of the application will appear here.</source>
        <translation>Qui compariranno i messaggi dell&apos;applicazione.</translation>
    </message>
</context>
<context>
    <name>app</name>
    <message>
        <source>Demo mode</source>
        <translation>Modalità demo</translation>
    </message>
    <message>
        <source>Demo mode could not start.

Cause: the virtual CAN bus with the simulated nodes did not open (%1).

Start the application without --demo, and send the logs (menu, Export logs) to Rumia support.</source>
        <translation>Non è stato possibile avviare la modalità demo.

Causa: il bus CAN virtuale con i nodi simulati non si è aperto (%1).

Avvia l&apos;applicazione senza --demo e invia i log (menu, Esporta log) all&apos;assistenza Rumia.</translation>
    </message>
</context>
</TS>
