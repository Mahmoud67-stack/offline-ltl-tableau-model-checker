from __future__ import annotations

from pathlib import Path

from ltlcheck.engine import Vertex, _closure, _nested_dfs, check_model, expand_tableau
from ltlcheck.formula import Formula, Kind, nnf, parse, subformulas
from ltlcheck.kripke import KripkeModel, load_models
from ltlcheck.oracle import unfolding_satisfies
from ltlcheck.synth import generate_models

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic_kripke.json"


def test_unsat_lasso_falsifies_oracle() -> None:
    for m in list(load_models(DATA)) + generate_models():
        assert m.formula
        r = check_model(m, m.formula)
        if r.verdict != "UNSAT":
            continue
        assert r.lasso is not None
        pref = r.lasso["prefix"]
        cyc = r.lasso["cycle"]
        assert cyc, "cycle required"
        phi = parse(m.formula)
        assert unfolding_satisfies(m, phi, pref, cyc) is False


def test_parser_behavior() -> None:
    f = parse("G (p U q)")
    assert f.pretty() == "(false R (p U q))"
    n = nnf(f)
    text = n.pretty()
    assert "U" in text or "R" in text
    assert parse("p | q & r").kind.name in {"OR", "AND"}
    assert parse("X X p").kind.name == "X"
    try:
        parse("p +")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_tableau_closure_and_expand() -> None:
    seed = nnf(parse("G (p U q)"))
    cl = _closure(seed)
    assert cl
    assert any(f.kind.name == "TRUE" for f in cl)
    nodes = expand_tableau(parse("p U q"))
    assert nodes
    assert all(any(f.pretty() == "true" or f.kind.name == "TRUE" for f in node) for node in nodes)
    subs = list(subformulas(seed))
    assert seed in subs


def test_nested_dfs_finds_cycle_on_simple_graph() -> None:
    # Two-vertex product graph with a self-loop style cycle; no U obligations.
    a: Vertex = ("a", frozenset())
    b: Vertex = ("b", frozenset())
    graph = {a: [b], b: [b]}
    lasso = _nested_dfs(graph, set(), [a])
    assert lasso is not None
    pref, cyc = lasso
    assert cyc
    assert cyc[-1] in {"a", "b"} or "b" in cyc


def test_nested_dfs_preserves_repeated_temporal_steps() -> None:
    truth = Formula(Kind.TRUE)
    marker = Formula(Kind.X, left=Formula(Kind.AP, name="p"))
    a: Vertex = ("s", frozenset({truth}))
    b: Vertex = ("s", frozenset({truth, marker}))
    lasso = _nested_dfs({a: [b], b: [a]}, set(), [a])
    assert lasso is not None
    assert len(lasso[1]) >= 2


def test_multi_obligation_parity_generator() -> None:
    m = KripkeModel(
        "mo",
        ("s0", "s1"),
        ("s0",),
        (("s0", "s1"), ("s1", "s0")),
        {"s0": frozenset({"p"}), "s1": frozenset({"q"})},
        formula="(F p) & (F q)",
    )
    r = check_model(m, "(F p) & (F q)")
    assert r.verdict == "SAT"


def test_red_search_witness_has_only_real_kripke_edges() -> None:
    model = KripkeModel(
        "junction",
        ("a", "b", "c"),
        ("a",),
        (("a", "b"), ("b", "c"), ("c", "b")),
        {"a": frozenset({"p"}), "b": frozenset(), "c": frozenset()},
    )
    result = check_model(model, "G p")
    assert result.verdict == "UNSAT" and result.lasso is not None
    assert not unfolding_satisfies(
        model, parse("G p"), result.lasso["prefix"], result.lasso["cycle"]
    )
    assert result.accepting_product is not None
    run = result.accepting_product["accepting_run"]
    assert isinstance(run, dict)
    cycle_ids = run["cycle_vertex_ids"]
    assert isinstance(cycle_ids, list) and cycle_ids
    raw_edges = result.accepting_product["edges"]
    assert isinstance(raw_edges, list)
    edges = {tuple(edge) for edge in raw_edges if isinstance(edge, list)}
    assert all((a, b) in edges for a, b in zip(cycle_ids, cycle_ids[1:] + cycle_ids[:1]))
