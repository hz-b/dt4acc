# python
# File: src/dt4acc/core/ai/oak_planner.py

from typing import Callable, Dict, List, Optional
from dataclasses import dataclass

from .oak_knowledge import OAKKnowledgeBase


@dataclass
class OAKAction:
    name: str
    params: Dict
    preconditions: Dict[str, bool] = None
    effects: Dict[str, bool] = None
    execute: Optional[Callable[[Dict], None]] = None  # optional execution callback

    def is_applicable(self, kb: OAKKnowledgeBase) -> bool:
        if not self.preconditions:
            return True
        for fact, val in self.preconditions.items():
            if kb.get_fact(fact) != val:
                return False
        return True


class OAKPlanner:
    """
    Very small planner: checks facts and emits actions.
    It does not do search; it produces ordered steps for common operations.
    """
    def __init__(self, kb: OAKKnowledgeBase):
        self.kb = kb

    def plan_set_property(self, obj_name: str, prop: str, value) -> List[OAKAction]:
        """
        Plan setting a property. Example rules:
          - if object locked -> refuse (raise)
          - if property change requires pre-step -> add that action
          - otherwise return a single set action
        """
        # example: refuse when locked
        if self.kb.get_fact(f"{obj_name}:locked"):
            raise RuntimeError(f"Object {obj_name} is locked")

        actions: List[OAKAction] = []

        # example rule: if changing cavity frequency and master clock is linked,
        # first set master clock reference then set cavity (customize KB facts as needed)
        if prop in ("frequency", "freq") and self.kb.get_fact("master_clock:linked"):
            # pre-action: update master clock reference (no-op execute by default)
            actions.append(
                OAKAction(
                    name="set_master_clock_ref",
                    params={"device": "master_clock", "reference_frequency": value},
                    preconditions=None,
                )
            )

        # main set action (actual execution should map this to your existing command/update flow)
        actions.append(
            OAKAction(
                name="set_property",
                params={"object": obj_name, "property": prop, "value": value},
                preconditions=None,
                effects={f"{obj_name}:{prop}:updated": True},
            )
        )

        return actions
