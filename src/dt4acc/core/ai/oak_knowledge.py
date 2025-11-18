# python
# File: src/dt4acc/core/ai/oak_knowledge.py

from typing import Any, Dict, Optional


class OAKKnowledgeBase:
    """
    Minimal knowledge base for objects and facts.
    Store object attributes and boolean facts used by the planner.
    """
    def __init__(self):
        self.objects: Dict[str, Dict[str, Any]] = {}
        self.facts: Dict[str, bool] = {}

    def add_object(self, name: str, attrs: Optional[Dict[str, Any]] = None):
        self.objects[name] = dict(attrs or {})

    def set_object_prop(self, name: str, prop: str, value: Any):
        self.objects.setdefault(name, {})[prop] = value

    def get_object_prop(self, name: str, prop: str, default=None):
        return self.objects.get(name, {}).get(prop, default)

    def set_fact(self, key: str, value: bool = True):
        self.facts[key] = bool(value)

    def get_fact(self, key: str) -> bool:
        return self.facts.get(key, False)
