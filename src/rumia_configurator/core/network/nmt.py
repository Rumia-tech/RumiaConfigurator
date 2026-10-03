"""NMT commands (CiA 301) and how their effect is checked (FR-NET-04, NFR-REL-03).

An NMT command is one frame on COB-ID 0x000: command specifier and Node-ID
(0 = every node). The protocol has no answer, so the application checks the
effect on the heartbeat: the next heartbeat must carry the new state, or a
boot-up message must arrive after a reset.
"""

from __future__ import annotations

from enum import Enum, StrEnum

import canopen

from rumia_configurator.core.network.nodes import NmtState

BROADCAST = 0  # Node-ID that addresses every node of the network


class NmtCommand(Enum):
    """Command specifier and the state the node is expected to reach."""

    START = (0x01, NmtState.OPERATIONAL)
    STOP = (0x02, NmtState.STOPPED)
    PRE_OPERATIONAL = (0x80, NmtState.PRE_OPERATIONAL)
    RESET_NODE = (0x81, NmtState.BOOTUP)
    RESET_COMMUNICATION = (0x82, NmtState.BOOTUP)

    @property
    def code(self) -> int:
        """Command specifier sent in the first byte."""
        code: int = self.value[0]
        return code

    @property
    def expected(self) -> NmtState:
        """State that confirms the command; ``BOOTUP`` for the resets."""
        state: NmtState = self.value[1]
        return state

    @property
    def is_reset(self) -> bool:
        return self.expected == NmtState.BOOTUP


class NmtOutcome(StrEnum):
    """What the heartbeat says after a command."""

    CONFIRMED = "confirmed"  # the node reached the expected state (or booted after a reset)
    NOT_CONFIRMED = "not_confirmed"  # heartbeats arrived, in another state
    NO_HEARTBEAT = "no_heartbeat"  # nothing arrived within the time
    NOT_VERIFIABLE = "not_verifiable"  # the node produces no heartbeat (0x1017 = 0)


def nmt_frame(command: NmtCommand, node_id: int = BROADCAST) -> bytes:
    """Data of the NMT frame for ``command`` to ``node_id`` (0 = every node)."""
    if not 0 <= node_id <= 127:
        raise ValueError(f"Node-ID {node_id} is not between 0 and 127")
    return bytes([command.code, node_id])


def send_nmt(network: canopen.Network, command: NmtCommand, node_id: int = BROADCAST) -> None:
    """Send ``command`` to ``node_id``; recorded as a sent frame by RecordingNetwork."""
    network.send_message(0x000, nmt_frame(command, node_id))
