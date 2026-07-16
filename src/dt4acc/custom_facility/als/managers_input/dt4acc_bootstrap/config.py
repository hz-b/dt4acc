"""Declarative ALS bootstrap configuration.

This module is intentionally small and explicit: family aliases and special
wiring live here instead of being spread through the builders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class FamilyConfig:
    canonical_name: str
    aliases: Sequence[str] = field(default_factory=tuple)
    role: str = "generic"
    translator: str = "identity"
    requires_at: bool = True


@dataclass(frozen=True)
class BootstrapConfig:
    standard_families: Sequence[str]
    family_configs: Dict[str, FamilyConfig]
    special_family_aliases: Dict[str, Sequence[str]]
    yp_tag_aliases: Dict[str, str]
    turn_by_turn_pv_prefix: str = "simulator_ring:turn_by_turn"
    master_clock_name: str = "master_clock"

    def aliases_for(self, family_name: str) -> Sequence[str]:
        if family_name in self.family_configs:
            return self.family_configs[family_name].aliases
        return self.special_family_aliases.get(family_name, ())


def als_bootstrap_config() -> BootstrapConfig:
    family_configs = {
        "QF": FamilyConfig("QF", aliases=("QF",), role="main_quadrupole", translator="energy_scaled_main_magnet"),
        "QD": FamilyConfig("QD", aliases=("QD",), role="main_quadrupole", translator="energy_scaled_main_magnet"),
        "SF": FamilyConfig("SF", aliases=("SF",), role="main_sextupole", translator="energy_scaled_main_magnet"),
        "SD": FamilyConfig("SD", aliases=("SD",), role="main_sextupole", translator="energy_scaled_main_magnet"),
        "SHF": FamilyConfig("SHF", aliases=("SHF",), role="harmonic_sextupole", translator="identity", requires_at=False),
        "SHD": FamilyConfig("SHD", aliases=("SHD",), role="harmonic_sextupole", translator="identity", requires_at=False),
        "QFA": FamilyConfig("QFA", aliases=("QFA",), role="main_quadrupole", translator="energy_scaled_main_magnet"),
        "QDA": FamilyConfig("QDA", aliases=("QDA",), role="main_quadrupole", translator="energy_scaled_main_magnet"),
        "BPM": FamilyConfig("BPM", aliases=("BPM",), role="bpm", translator="bpm_offset_scaled"),
        "BPMx": FamilyConfig("BPMx", aliases=("BPMx", "BPM"), role="bpm_x", translator="bpm_offset_scaled"),
        "BPMy": FamilyConfig("BPMy", aliases=("BPMy", "BPM"), role="bpm_y", translator="bpm_offset_scaled"),
        "BEND": FamilyConfig("BEND", aliases=("BEND", "BS"), role="bend", translator="identity"),
        "HCM": FamilyConfig("HCM", aliases=("HCM", "COR"), role="horizontal_corrector", translator="corrector_current_to_kick"),
        "VCM": FamilyConfig("VCM", aliases=("VCM", "COR"), role="vertical_corrector", translator="corrector_current_to_kick"),
        "SQSF": FamilyConfig("SQSF", aliases=("SQSF", "SFF"), role="special_sextupole", translator="identity"),
        "SQSD": FamilyConfig("SQSD", aliases=("SQSD", "SDD"), role="special_sextupole", translator="identity"),
        "RF": FamilyConfig("RF", aliases=("RF", "CAV"), role="rf_system", translator="master_clock_frequency"),
    }

    special_family_aliases = {
        "BPMx": ("BPM",),
        "BPMy": ("BPM",),
        "BEND": ("BS",),
        "HCM": ("COR",),
        "VCM": ("COR",),
        "SQSF": ("SFF",),
        "SQSD": ("SDD",),
        "RF": ("CAV",),
    }

    yp_tag_aliases = {
        "tune_correction_quadrupoles": "Tune Corrector",
    }

    standard_families = ("QF", "QD", "SF", "SD", "SHF", "SHD", "QFA", "QDA", "BPM")

    return BootstrapConfig(
        standard_families=standard_families,
        family_configs=family_configs,
        special_family_aliases=special_family_aliases,
        yp_tag_aliases=yp_tag_aliases,
    )
