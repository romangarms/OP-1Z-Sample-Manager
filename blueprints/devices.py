"""
Device Configuration Module

Centralized device configuration for OP-Z and OP-1 devices.
Provides a single source of truth for device names, constants, and capabilities.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Device:
    """Immutable device configuration.
    
    Attributes:
        id: Internal identifier (e.g., "opz", "op1")
        name: Display name (e.g., "OP-Z", "OP-1")
        display_name_short: Short display name
        display_name_long: Full product name
        storage_kb: Storage capacity in KB
        usb_vendor_id: USB vendor ID (Teenage Engineering)
        usb_product_ids: Tuple of USB product IDs for different modes
        sample_limits: Dictionary with sample/patch limits
        required_directories: Tuple of required directory structures for validation
        supported_features: Dictionary of feature flags
    """
    id: str
    name: str
    display_name_short: str
    display_name_long: str
    storage_kb: int
    usb_vendor_id: int
    usb_product_ids: tuple[int, ...]
    sample_limits: dict[str, int]
    required_directories: tuple[str, ...]
    supported_features: dict[str, bool]


# OP-Z Device Configuration
OP_Z = Device(
    id="opz",
    name="OP-Z",
    display_name_short="OP-Z",
    display_name_long="Teenage Engineering OP-Z",
    storage_kb=24000,  # 24 MB in KB
    usb_vendor_id=9063,  # 0x2367 - Teenage Engineering
    usb_product_ids=(12,),  # 0x000c - OP-Z (both normal and disk mode use same ID)
    sample_limits={},  # OP-Z doesn't have sample limits, only storage capacity
    required_directories=("samplepacks",),
    supported_features={
        "has_tape_export": False,
        "has_samplepacks": True,
        "has_drum_synth_folders": False,
    }
)

# OP-1 Device Configuration
OP_1 = Device(
    id="op1",
    name="OP-1",
    display_name_short="OP-1",
    display_name_long="Teenage Engineering OP-1",
    storage_kb=512000,  # 512 MB in KB
    usb_vendor_id=9063,  # 0x2367 - Teenage Engineering
    usb_product_ids=(2, 4),  # 0x0002 - USB Storage mode, 0x0004 - Normal/MIDI mode
    sample_limits={
        "drum_samples": 42,
        "synth_samples": 42,
        "patches": 100,
    },
    required_directories=("drum", "synth"),
    supported_features={
        "has_tape_export": True,
        "has_samplepacks": False,
        "has_drum_synth_folders": True,
    }
)


def get_device_by_id(device_id: str) -> Optional[Device]:
    """Get device configuration by ID.
    
    Args:
        device_id: Device identifier ("opz" or "op1")
        
    Returns:
        Device object if found, None otherwise
    """
    if device_id == "opz":
        return OP_Z
    elif device_id == "op1":
        return OP_1
    return None


def get_all_devices() -> tuple[Device, Device]:
    """Get all configured devices.
    
    Returns:
        Tuple of (OP_Z, OP_1) device objects
    """
    return (OP_Z, OP_1)
