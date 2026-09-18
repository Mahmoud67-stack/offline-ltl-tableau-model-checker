from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KripkeModel:
    model_id: str
    states: tuple[str, ...]
    initials: tuple[str, ...]
    transitions: tuple[tuple[str, str], ...]
    labels: dict[str, frozenset[str]]
    expected: str | None = None
    formula: str | None = None

    def succs(self, s: str) -> list[str]:
        return [b for a, b in self.transitions if a == s]


def _parse_one(obj: dict[str, Any]) -> KripkeModel:
    states = tuple(str(x) for x in obj["states"])
    if not states or len(set(states)) != len(states):
        raise ValueError("states must be non-empty and unique")
    initials = tuple(str(x) for x in obj["initials"])
    if not initials or any(s not in states for s in initials):
        raise ValueError("initials must reference states")
    trans = tuple((str(a), str(b)) for a, b in obj["transitions"])
    if any(a not in states or b not in states for a, b in trans):
        raise ValueError("transition references unknown state")
    if any(s not in {a for a, _ in trans} for s in states):
        raise ValueError("transition relation must be total")
    raw = obj.get("labels", {})
    if any(str(s) not in states for s in raw):
        raise ValueError("label references unknown state")
    labels = {str(s): frozenset(str(x) for x in aps) for s, aps in raw.items()}
    for state in states:
        labels.setdefault(state, frozenset())
    return KripkeModel(
        str(obj.get("id", "m")),
        states,
        initials,
        trans,
        labels,
        obj.get("expected"),
        obj.get("formula"),
    )


def load_models(path: str | Path, max_size_mb: float = 5.0) -> list[KripkeModel]:
    p = Path(path)
    if p.stat().st_size > max_size_mb * 1024 * 1024:
        raise ValueError(f"JSON exceeds max_size_mb={max_size_mb}")
    data = json.loads(p.read_text(encoding="utf-8"))
    models = data["models"] if isinstance(data, dict) and "models" in data else [data]
    return [_parse_one(m) for m in models]
