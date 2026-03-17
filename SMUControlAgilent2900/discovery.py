"""
Provides a function to discover connected instruments using PyVISA.
"""

import pyvisa


def discover_instruments() -> tuple[str, ...]:
    """
    Discover connected instruments using PyVISA.

    Returns
    -------
    tuple[str, ...]
        A tuple of resource names for the connected instruments.
    """
    rm = pyvisa.ResourceManager()
    resources = rm.list_resources()
    return resources
