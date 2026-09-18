from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ltlcheck.kripke import KripkeModel

# Tiny regression fixtures with known SAT/UNSAT labels for offline generation.
_CASES: list[dict[str, Any]] = [
    {
        "id": "g_p_sat",
        "states": ["s0", "s1"],
        "initials": ["s0"],
        "transitions": [["s0", "s1"], ["s1", "s1"]],
        "labels": {"s0": ["p"], "s1": ["p"]},
        "formula": "G p",
        "expected": "SAT",
    },
    {
        "id": "g_p_unsat",
        "states": ["s0", "s1"],
        "initials": ["s0"],
        "transitions": [["s0", "s1"], ["s1", "s1"]],
        "labels": {"s0": ["p"], "s1": []},
        "formula": "G p",
        "expected": "UNSAT",
    },
    {
        "id": "f_q_sat",
        "states": ["s0"],
        "initials": ["s0"],
        "transitions": [["s0", "s0"]],
        "labels": {"s0": ["q"]},
        "formula": "F q",
        "expected": "SAT",
    },
    {
        "id": "f_r_unsat_avoid",
        "states": ["a", "b"],
        "initials": ["a"],
        "transitions": [["a", "a"], ["a", "b"], ["b", "b"]],
        "labels": {"a": [], "b": ["r"]},
        "formula": "F r",
        "expected": "UNSAT",
    },
    {
        "id": "gf_p_sat",
        "states": ["a", "b"],
        "initials": ["a"],
        "transitions": [["a", "b"], ["b", "a"]],
        "labels": {"a": ["p"], "b": []},
        "formula": "G F p",
        "expected": "SAT",
    },
    {
        "id": "multi_init_u",
        "states": ["i0", "i1", "t"],
        "initials": ["i0", "i1"],
        "transitions": [["i0", "t"], ["i1", "t"], ["t", "t"]],
        "labels": {"i0": ["p"], "i1": ["p"], "t": ["q"]},
        "formula": "p U q",
        "expected": "SAT",
    },
    {
        "id": "nested_until_unsat",
        "states": ["s0", "s1"],
        "initials": ["s0"],
        "transitions": [["s0", "s1"], ["s1", "s0"]],
        "labels": {"s0": ["p"], "s1": ["p"]},
        "formula": "(p U q) & F q",
        "expected": "UNSAT",
    },
]


def generate_cases() -> list[dict[str, Any]]:
    """Return the built-in synthetic model/formula corpus with known labels."""
    return [dict(case) for case in _CASES]


def generate_models() -> list[KripkeModel]:
    from ltlcheck.kripke import _parse_one

    return [_parse_one(case) for case in generate_cases()]


def write_synthetic_json(path: str | Path) -> None:
    """Write the generator corpus to a JSON file (models wrapper)."""
    payload = {"models": generate_cases()}
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    out = root / "data" / "synthetic_kripke.json"
    write_synthetic_json(out)
    print(f"wrote {out} ({len(_CASES)} models)")


if __name__ == "__main__":
    main()
