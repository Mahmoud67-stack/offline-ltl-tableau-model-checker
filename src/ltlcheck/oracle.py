from __future__ import annotations

from functools import lru_cache

from ltlcheck.formula import Formula, Kind, nnf
from ltlcheck.kripke import KripkeModel


def eval_lasso(phi: Formula, labels: list[frozenset[str]], prefix_len: int) -> bool:
    """Evaluate an LTL formula on a finite ultimately-periodic word."""
    if not labels or not 0 <= prefix_len < len(labels):
        raise ValueError("prefix_len must identify a non-empty cycle")
    cycle_start = prefix_len
    cycle_length = len(labels) - cycle_start
    formula = nnf(phi)

    def position(index: int) -> int:
        if index < cycle_start:
            return index
        return cycle_start + (index - cycle_start) % cycle_length

    @lru_cache(maxsize=None)
    def sat(node: Formula, index: int) -> bool:
        index = position(index)
        if node.kind is Kind.TRUE:
            return True
        if node.kind is Kind.FALSE:
            return False
        if node.kind is Kind.AP:
            return node.name in labels[index]
        if node.kind is Kind.NOT:
            assert node.left is not None
            return not sat(node.left, index)
        if node.kind is Kind.AND:
            assert node.left is not None and node.right is not None
            return sat(node.left, index) and sat(node.right, index)
        if node.kind is Kind.OR:
            assert node.left is not None and node.right is not None
            return sat(node.left, index) or sat(node.right, index)
        if node.kind is Kind.X:
            assert node.left is not None
            return sat(node.left, index + 1)
        assert node.left is not None and node.right is not None
        if node.kind is Kind.U:
            values = [False] * len(labels)
            changed = True
            while changed:
                changed = False
                for i in range(len(labels) - 1, -1, -1):
                    value = sat(node.right, i) or (sat(node.left, i) and values[position(i + 1)])
                    if value and not values[i]:
                        values[i] = True
                        changed = True
            return values[index]
        if node.kind is Kind.R:
            values = [True] * len(labels)
            changed = True
            while changed:
                changed = False
                for i in range(len(labels) - 1, -1, -1):
                    value = sat(node.right, i) and (sat(node.left, i) or values[position(i + 1)])
                    if not value and values[i]:
                        values[i] = False
                        changed = True
            return values[index]
        raise ValueError("unsupported formula kind")

    return sat(formula, 0)


def all_lassos(model: KripkeModel, max_length: int | None = None) -> list[tuple[list[str], int]]:
    """Enumerate bounded ultimately-periodic paths (prefix + cycle) on the model.

    Explores walks up to `bound` states allowing revisits so nested temporal
    formulas see non-simple cycles; each time a back-edge closes a cycle the
    corresponding lasso is recorded.
    """
    n = len(model.states)
    bound = max_length if max_length is not None else max(2 * n + 2, n + 3)
    successors = {state: model.succs(state) for state in model.states}
    found: set[tuple[tuple[str, ...], int]] = set()

    def visit(path: list[str]) -> None:
        if len(path) > bound:
            return
        current = path[-1]
        for target in successors[current]:
            # Always record a lasso when target already appears (cycle close),
            # then continue expanding while under bound (revisit allowed).
            if target in path:
                start = path.index(target)
                for prefix in range(start, len(path)):
                    if path[prefix] == target:
                        found.add((tuple(path), prefix))
            if len(path) < bound:
                # Count occurrences of target to limit pathological blow-up.
                if path.count(target) >= max(2, n):
                    continue
                visit(path + [target])

    for initial in model.initials:
        visit([initial])
    return [(list(word), prefix) for word, prefix in sorted(found)]


def model_satisfies(model: KripkeModel, phi: Formula) -> bool:
    lassos = all_lassos(model)
    if not lassos:
        return True
    return all(
        eval_lasso(phi, [model.labels[state] for state in word], prefix) for word, prefix in lassos
    )


def unfolding_satisfies(
    model: KripkeModel, phi: Formula, prefix: list[str], cycle: list[str]
) -> bool:
    if not cycle:
        return False
    word = prefix + cycle
    if prefix:
        if prefix[0] not in model.initials:
            return False
        prefix_len = len(prefix)
    else:
        if cycle[0] not in model.initials:
            return False
        prefix_len = 0
    edges = list(zip(word, word[1:])) + [(cycle[-1], cycle[0])]
    if any(edge not in set(model.transitions) for edge in edges):
        return False
    return eval_lasso(phi, [model.labels[state] for state in word], prefix_len)
