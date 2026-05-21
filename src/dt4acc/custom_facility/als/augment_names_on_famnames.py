"""Utils to add sector child suffix to family names
"""
from collections import defaultdict
from typing import Tuple


class SectorRegistry:
    """Trace of the current sector
    """
    def __init__(self):
        self._sectors = []

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"current_num={self.current_sector_number}"
            f", sectors={self._sectors}"
            ")"
        )

    def add_sector(self, sector: str) -> None:
        if not sector.startswith("SECT"):
            raise ValueError(f"{sector} is not a valid sector name")
        if sector in self._sectors:
            raise ValueError(f"{sector} is already a known sector name")
        self._sectors.append(sector)

    @property
    def current_sector_number(self) -> int:
        return len(self._sectors)


class NameCounter:
    def __init__(self):
        self._counts = defaultdict(int)

    def __repr__(self):
        return f"{self.__class__.__name__}(" f"counts={self._counts}" ")"

    def increment(self, name: str) -> int:
        self._counts[name] += 1
        return self._counts[name]


class NameFormatter:
    def format(self, name: str, sector_number: int, child_number: int) -> str:
        return f"{name}-sec_{sector_number}-chld_{child_number}"


class NameAugmenter:
    def __init__(
        self,
        sector_registry: SectorRegistry,
        counter_factory=NameCounter,
    ):
        self.sector_registry = sector_registry
        self.names_per_sector = defaultdict(counter_factory)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"sector_registry={self.sector_registry}"
            ", names_per_sector={len(self.names_per_sector)}"
        )

    def new_sector(self, name: str):
        self.sector_registry.add_sector(name)

    def sector_child_for_family_name(self, family_name: str) -> Tuple[int, int]:
        sector_number = self.sector_registry.current_sector_number
        counter = self.names_per_sector[sector_number]
        child_number = counter.increment(family_name)
        return sector_number, child_number
