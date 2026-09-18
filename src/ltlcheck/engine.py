from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

from ltlcheck.formula import Formula, Kind, nnf, parse, subformulas
from ltlcheck.kripke import KripkeModel

Node = FrozenSet[Formula]
Vertex = tuple[str, Node]
Lasso = tuple[list[str], list[str]]


def _closure(seed: Formula) -> list[Formula]:
    values = list(dict.fromkeys(subformulas(seed)))
    values.append(Formula(Kind.TRUE))
    values.extend(Formula(Kind.NOT, left=f) for f in values if f.kind is Kind.AP)
    return list(dict.fromkeys(values))


def _local_ok(node: Node, closure: list[Formula] | None = None) -> bool:
    if Formula(Kind.FALSE) in node or Formula(Kind.TRUE) not in node:
        return False
    for f in closure if closure is not None else node:
        if f.kind is Kind.AP:
            negated = Formula(Kind.NOT, left=f)
            if (f in node) == (negated in node):
                return False
        elif f.kind is Kind.AND:
            if (f in node) != (f.left in node and f.right in node):
                return False
        elif f.kind is Kind.OR:
            if (f in node) != (f.left in node or f.right in node):
                return False
        elif f.kind is Kind.U:
            if (f in node) != (f.right in node or (f.left in node and f in node)):
                return False
        elif f.kind is Kind.R:
            if (f in node) != (f.right in node and (f.left in node or f in node)):
                return False
    return True


def _elementary_sets(seed: Formula) -> list[Node]:
    closure = _closure(seed)
    return [
        frozenset(closure[i] for i in range(len(closure)) if mask & (1 << i))
        for mask in range(1 << len(closure))
        if _local_ok(frozenset(closure[i] for i in range(len(closure)) if mask & (1 << i)), closure)
    ]


def _label_ok(node: Node, labels: frozenset[str]) -> bool:
    return all(
        not (f.kind is Kind.AP and f.name not in labels)
        and not (
            f.kind is Kind.NOT
            and f.left is not None
            and f.left.kind is Kind.AP
            and f.left.name in labels
        )
        for f in node
    )


def _next_ok(current: Node, following: Node) -> bool:
    for f in current | following:
        if f.kind is Kind.X and ((f in current) != (f.left in following)):
            return False
        if f.kind is Kind.U:
            if (f in current) != (f.right in current or (f.left in current and f in following)):
                return False
        if f.kind is Kind.R:
            if (f in current) != (f.right in current and (f.left in current or f in following)):
                return False
    return True


def _discharges(vertex: Vertex, obligation: Formula) -> bool:
    return obligation not in vertex[1] or (
        obligation.right is not None and obligation.right in vertex[1]
    )


def _nested_dfs(
    graph: dict[Vertex, list[Vertex]], accepting: set[Formula], starts: list[Vertex]
) -> Lasso | None:
    """GBA emptiness via nested DFS on a round-robin Büchi encoding.

    Acceptance marks the *transition* that completes a full obligation sweep
    (index wraps to 0 after discharging the last obligation). Counterexample
    extraction tracks both blue and red stacks so red-only intermediates appear
    in the projected Kripke lasso.
    """
    obligations = list(accepting)
    BDState = tuple[Vertex, int]
    succ_cache: dict[BDState, list[BDState]] = {}

    def ba_succ(s: BDState) -> list[BDState]:
        if s in succ_cache:
            return succ_cache[s]
        v, idx = s
        out: list[BDState] = []
        if not obligations:
            for nxt in graph.get(v, []):
                out.append((nxt, 0))
        else:
            obl = obligations[idx]
            advance = _discharges(v, obl)
            nidx = (idx + 1) % len(obligations) if advance else idx
            for nxt in graph.get(v, []):
                out.append((nxt, nidx))
        succ_cache[s] = out
        return out

    def is_accepting_edge(src: BDState, dst: BDState) -> bool:
        if not obligations:
            return True
        # Completing a full round-robin sweep: last obligation discharged on src
        # and the successor index wraps back to 0.
        return (
            src[1] == len(obligations) - 1 and dst[1] == 0 and _discharges(src[0], obligations[-1])
        )

    blue_done: set[BDState] = set()
    cyan: set[BDState] = set()
    red_done: set[BDState] = set()
    path_stack: list[BDState] = []
    red_stack: list[BDState] = []
    found: Lasso | None = None

    def project_lasso(full: list[BDState], cycle_state: BDState) -> Lasso:
        if cycle_state in full:
            i = full.index(cycle_state)
            prefix_bd = full[:i]
            cycle_bd = full[i:]
        else:
            prefix_bd = full
            cycle_bd = [cycle_state]
        # Preserve every product transition after projection. Repeated Kripke
        # names are real temporal steps and removing them changes X semantics.
        pref = [s[0][0] for s in prefix_bd]
        cyc = [s[0][0] for s in cycle_bd] or [cycle_state[0][0]]
        return (pref, cyc)

    def extract_lasso(cycle_state: BDState) -> Lasso:
        # Keep a shared blue/red junction once, but retain the first red state
        # when red search began by traversing an accepting edge to a successor.
        red_suffix = red_stack
        if path_stack and red_stack and path_stack[-1] == red_stack[0]:
            red_suffix = red_stack[1:]
        full = path_stack + red_suffix
        return project_lasso(full, cycle_state)

    def red_dfs(s: BDState) -> bool:
        nonlocal found
        red_done.add(s)
        red_stack.append(s)
        for t in ba_succ(s):
            if t in cyan:
                found = extract_lasso(t)
                return True
            if t not in red_done:
                if red_dfs(t):
                    return True
        red_stack.pop()
        return False

    def blue_dfs(s: BDState) -> bool:
        nonlocal found
        cyan.add(s)
        path_stack.append(s)
        for t in ba_succ(s):
            if t not in blue_done and t not in cyan:
                if blue_dfs(t):
                    return True
            elif t in cyan and is_accepting_edge(s, t):
                found = extract_lasso(t)
                return True
        # Every red search is rooted *after traversing the particular accepting
        # edge*. It therefore cannot return a cycle that merely branched away
        # from some other accepting successor of s.
        for t in ba_succ(s):
            if not is_accepting_edge(s, t):
                continue
            if t in cyan:
                found = extract_lasso(t)
                return True
            red_done.clear()
            red_stack.clear()
            if red_dfs(t):
                return True
        path_stack.pop()
        cyan.remove(s)
        blue_done.add(s)
        return False

    roots: list[BDState] = [(s, 0) for s in starts]
    for r in roots:
        if r not in blue_done and r not in cyan:
            if blue_dfs(r):
                return found
    return found


def _product(
    model: KripkeModel, formula: Formula
) -> tuple[dict[Vertex, list[Vertex]], list[Vertex], set[Formula]]:
    negated = nnf(Formula(Kind.NOT, left=formula))
    nodes = _elementary_sets(negated)
    states = [
        (state, node)
        for state in model.states
        for node in nodes
        if _label_ok(node, model.labels[state])
    ]
    starts = [v for v in states if v[0] in model.initials and negated in v[1]]
    succ_map = {s: set(model.succs(s)) for s in model.states}
    graph = {
        (state, node): [
            (destination, following)
            for destination, following in states
            if destination in succ_map[state] and _next_ok(node, following)
        ]
        for state, node in states
    }
    obligations = {f for f in subformulas(negated) if f.kind is Kind.U}
    return graph, starts, obligations


def _lift_witness(
    graph: dict[Vertex, list[Vertex]],
    starts: list[Vertex],
    obligations: set[Formula],
    witness: Lasso,
) -> tuple[list[Vertex], list[Vertex]] | None:
    """Lift a projected Kripke lasso to a connected accepting product run."""
    prefix, cycle = witness
    names = prefix + cycle
    if not names or not cycle:
        return None
    cycle_start = len(prefix)

    def search(path: list[Vertex]) -> list[Vertex] | None:
        index = len(path)
        if index == len(names):
            cycle_vertex = path[cycle_start]
            if cycle_vertex not in graph.get(path[-1], []):
                return None
            cycle_vertices = path[cycle_start:]
            if any(not any(_discharges(v, obligation) for v in cycle_vertices) for obligation in obligations):
                return None
            return path
        for nxt in graph.get(path[-1], []):
            if nxt[0] == names[index]:
                found = search(path + [nxt])
                if found is not None:
                    return found
        return None

    for start in starts:
        if start[0] == names[0]:
            found = search([start])
            if found is not None:
                return found[:cycle_start], found[cycle_start:]
    return None


@dataclass(frozen=True)
class CheckResult:
    verdict: str
    formula: str
    lasso: dict[str, list[str]] | None
    accepting_product: dict[str, object] | None = None

    def to_json_obj(self) -> dict[str, object]:
        result: dict[str, object] = {"verdict": self.verdict, "formula": self.formula}
        if self.lasso is not None:
            result["lasso"] = self.lasso
        if self.accepting_product is not None:
            result["accepting_product"] = self.accepting_product
        return result


def check_model(model: KripkeModel, formula: Formula | str) -> CheckResult:
    parsed = parse(formula) if isinstance(formula, str) else formula
    graph, starts, accepting = _product(model, parsed)
    witness = _nested_dfs(graph, accepting, starts)
    index = {vertex: i for i, vertex in enumerate(graph)}
    product: dict[str, object] = {
        "vertices": [
            {"id": i, "state": v[0], "node": sorted(f.pretty() for f in v[1])}
            for v, i in index.items()
        ],
        "edges": [[index[v], index[n]] for v, successors in graph.items() for n in successors],
        "initial": [index[v] for v in starts],
        "acceptance": [
            [index[v] for v in graph if obligation not in v[1] or obligation.right in v[1]]
            for obligation in accepting
        ],
    }
    if witness is not None:
        lasso = {"prefix": witness[0], "cycle": witness[1]}
        lifted = _lift_witness(graph, starts, accepting, witness)
        if lifted is not None:
            product["accepting_run"] = {
                "prefix_vertex_ids": [index[v] for v in lifted[0]],
                "cycle_vertex_ids": [index[v] for v in lifted[1]],
                "kripke_projection": lasso,
            }
        return CheckResult("UNSAT", parsed.pretty(), lasso, product)
    return CheckResult("SAT", parsed.pretty(), None, product)


def expand_tableau(seed: Formula) -> list[Node]:
    return _elementary_sets(nnf(seed))
