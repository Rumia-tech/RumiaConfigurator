"""Simulated CANopen nodes for demo mode and tests (FR-CON-06)."""

from rumia_configurator.core.simulator.node import SimulatedNode
from rumia_configurator.core.simulator.products import (
    INCLI_SENSE_NODE_ID,
    SMART_IMU_NODE_ID,
    IncliSenseNode,
    SmartImuNode,
)
from rumia_configurator.core.simulator.simulator import DEMO_CHANNEL, Simulator, default_demo_nodes

__all__ = [
    "DEMO_CHANNEL",
    "INCLI_SENSE_NODE_ID",
    "SMART_IMU_NODE_ID",
    "IncliSenseNode",
    "SimulatedNode",
    "Simulator",
    "SmartImuNode",
    "default_demo_nodes",
]
