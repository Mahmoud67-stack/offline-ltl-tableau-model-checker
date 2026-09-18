from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from ltlcheck.engine import check_model
from ltlcheck.formula import parse
from ltlcheck.kripke import KripkeModel, load_models
from ltlcheck.oracle import model_satisfies
from ltlcheck.synth import generate_models

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic_kripke.json"


def test_cli_json_matches_oracle_bundled() -> None:
    models = load_models(DATA)
    for m in models:
        assert m.formula
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "ltlcheck.cli",
                "check",
                "--model",
                str(DATA),
                "--id",
                m.model_id,
                "--formula",
                m.formula,
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
            env={
                **dict(**{k: v for k, v in __import__("os").environ.items()}),
                "PYTHONPATH": str(ROOT / "src"),
            },
        )
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout)
        oracle_sat = model_satisfies(m, parse(m.formula))
        want = "SAT" if oracle_sat else "UNSAT"
        assert payload["verdict"] == want
        if m.expected:
            assert payload["verdict"] == m.expected


def test_engine_parity_bundled() -> None:
    for m in list(load_models(DATA)) + generate_models():
        assert m.formula
        r = check_model(m, m.formula)
        o = model_satisfies(m, parse(m.formula))
        assert (r.verdict == "SAT") is o
        if m.expected:
            assert r.verdict == m.expected


@st.composite
def tiny_models(draw: st.DrawFn) -> tuple[KripkeModel, str]:
    n = draw(st.integers(min_value=1, max_value=4))
    states = tuple(f"s{i}" for i in range(n))
    n_init = draw(st.integers(min_value=1, max_value=n))
    init = tuple(
        draw(st.lists(st.sampled_from(states), min_size=n_init, max_size=n_init, unique=True))
    )
    trans = []
    for s in states:
        k = draw(st.integers(min_value=1, max_value=n))
        dests = draw(st.lists(st.sampled_from(states), min_size=1, max_size=k))
        for d in dests:
            trans.append((s, d))
    labels = {}
    for s in states:
        aps = draw(st.lists(st.sampled_from(["p", "q", "r"]), max_size=3, unique=True))
        labels[s] = frozenset(aps)
    atoms = st.sampled_from(["p", "q", "r"])
    formulas = st.recursive(
        atoms,
        lambda child: st.one_of(
            child.map(lambda x: f"X ({x})"),
            child.map(lambda x: f"F ({x})"),
            child.map(lambda x: f"G ({x})"),
            st.tuples(child, child).map(lambda xs: f"({xs[0]}) & ({xs[1]})"),
            st.tuples(child, child).map(lambda xs: f"({xs[0]}) | ({xs[1]})"),
            st.tuples(child, child).map(lambda xs: f"({xs[0]}) U ({xs[1]})"),
            st.tuples(child, child).map(lambda xs: f"({xs[0]}) R ({xs[1]})"),
        ),
        max_leaves=4,
    )
    form = draw(formulas)
    m = KripkeModel("h", states, init, tuple(trans), labels)
    return m, form


@settings(max_examples=75, deadline=None)
@given(tiny_models())
def test_hypothesis_oracle(pair: tuple[KripkeModel, str]) -> None:
    m, form = pair
    r = check_model(m, form)
    o = model_satisfies(m, parse(form))
    assert (r.verdict == "SAT") is o


def test_synth_generator_nonempty() -> None:
    models = generate_models()
    assert len(models) >= 5
    assert all(m.formula and m.expected in {"SAT", "UNSAT", None} or m.formula for m in models)


def test_loader_rejects_malformed_and_oversized_json(tmp_path: Path) -> None:
    malformed = tmp_path / "bad.json"
    malformed.write_text(
        '{"states": ["s"], "initials": ["missing"], "transitions": []}', encoding="utf-8"
    )
    import pytest

    with pytest.raises(ValueError, match="initials"):
        load_models(malformed)
    oversized = tmp_path / "large.json"
    oversized.write_text("{}" + " " * 1024, encoding="utf-8")
    with pytest.raises(ValueError, match="max_size_mb"):
        load_models(oversized, max_size_mb=0.0001)


def test_explain_has_distinct_evidence_output() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "ltlcheck.cli", "explain", "--model", str(DATA), "--id", "m1"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
    )
    assert proc.returncode == 0, proc.stderr
    assert "explanation" in json.loads(proc.stdout)
