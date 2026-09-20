"""Clinical data adapters implementing ClinicalDataPort."""

from packages.tui.adapters.http_adapter import HttpClinicalAdapter
from packages.tui.adapters.memory_adapter import InMemoryClinicalAdapter

__all__ = ["HttpClinicalAdapter", "InMemoryClinicalAdapter"]
