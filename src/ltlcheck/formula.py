from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator


class Kind(Enum):
    TRUE = auto()
    FALSE = auto()
    AP = auto()
    NOT = auto()
    AND = auto()
    OR = auto()
    X = auto()
    U = auto()
    R = auto()


@dataclass(frozen=True)
class Formula:
    kind: Kind
    name: str = ""
    left: Formula | None = None
    right: Formula | None = None

    def pretty(self) -> str:
        k = self.kind
        if k is Kind.TRUE:
            return "true"
        if k is Kind.FALSE:
            return "false"
        if k is Kind.AP:
            return self.name
        if k is Kind.NOT:
            return f"~({self.left.pretty()})"  # type: ignore[union-attr]
        if k is Kind.AND:
            return f"({self.left.pretty()} & {self.right.pretty()})"  # type: ignore[union-attr]
        if k is Kind.OR:
            return f"({self.left.pretty()} | {self.right.pretty()})"  # type: ignore[union-attr]
        if k is Kind.X:
            return f"X({self.left.pretty()})"  # type: ignore[union-attr]
        if k is Kind.U:
            return f"({self.left.pretty()} U {self.right.pretty()})"  # type: ignore[union-attr]
        return f"({self.left.pretty()} R {self.right.pretty()})"  # type: ignore[union-attr]


def _tok(s: str) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in "()~&|":
            out.append(c)
            i += 1
            continue
        if c.isalpha() or c == "_":
            j = i + 1
            while j < len(s) and (s[j].isalnum() or s[j] == "_"):
                j += 1
            out.append(s[i:j])
            i = j
            continue
        raise ValueError(f"bad char {c!r}")
    return out


class _P:
    def __init__(self, tokens: list[str]) -> None:
        self.t = tokens
        self.i = 0

    def peek(self) -> str | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def eat(self, x: str | None = None) -> str:
        if self.i >= len(self.t):
            raise ValueError("eof")
        v = self.t[self.i]
        if x is not None and v != x:
            raise ValueError(f"expected {x} got {v}")
        self.i += 1
        return v

    def parse(self) -> Formula:
        f = self.impl()
        if self.peek() is not None:
            raise ValueError("trailing")
        return f

    def impl(self) -> Formula:
        return self.or_()

    def or_(self) -> Formula:
        a = self.and_()
        while self.peek() == "|":
            self.eat("|")
            a = Formula(Kind.OR, left=a, right=self.and_())
        return a

    def and_(self) -> Formula:
        a = self.until()
        while self.peek() == "&":
            self.eat("&")
            a = Formula(Kind.AND, left=a, right=self.until())
        return a

    def until(self) -> Formula:
        a = self.unary()
        p = self.peek()
        if p == "U":
            self.eat()
            return Formula(Kind.U, left=a, right=self.until())
        if p == "R":
            self.eat()
            return Formula(Kind.R, left=a, right=self.until())
        return a

    def unary(self) -> Formula:
        p = self.peek()
        if p == "~":
            self.eat()
            return Formula(Kind.NOT, left=self.unary())
        if p == "X":
            self.eat()
            return Formula(Kind.X, left=self.unary())
        if p == "F":
            self.eat()
            return Formula(Kind.U, left=Formula(Kind.TRUE), right=self.unary())
        if p == "G":
            self.eat()
            inner = self.unary()
            return Formula(Kind.R, left=Formula(Kind.FALSE), right=inner)
        return self.atom()

    def atom(self) -> Formula:
        p = self.peek()
        if p == "(":
            self.eat("(")
            f = self.impl()
            self.eat(")")
            return f
        if p in ("true", "TRUE"):
            self.eat()
            return Formula(Kind.TRUE)
        if p in ("false", "FALSE"):
            self.eat()
            return Formula(Kind.FALSE)
        if p is None:
            raise ValueError("atom")
        name = self.eat()
        if name in {"U", "R", "X", "F", "G"}:
            raise ValueError("bare operator")
        return Formula(Kind.AP, name=name)


def parse(text: str) -> Formula:
    return _P(_tok(text)).parse()


def nnf(f: Formula) -> Formula:
    if f.kind is Kind.NOT:
        a = f.left
        assert a is not None
        if a.kind is Kind.NOT:
            assert a.left is not None
            return nnf(a.left)
        if a.kind is Kind.TRUE:
            return Formula(Kind.FALSE)
        if a.kind is Kind.FALSE:
            return Formula(Kind.TRUE)
        if a.kind is Kind.AP:
            return Formula(Kind.NOT, left=a)
        if a.kind is Kind.AND:
            return Formula(
                Kind.OR,
                left=nnf(Formula(Kind.NOT, left=a.left)),
                right=nnf(Formula(Kind.NOT, left=a.right)),
            )
        if a.kind is Kind.OR:
            return Formula(
                Kind.AND,
                left=nnf(Formula(Kind.NOT, left=a.left)),
                right=nnf(Formula(Kind.NOT, left=a.right)),
            )
        if a.kind is Kind.X:
            return Formula(Kind.X, left=nnf(Formula(Kind.NOT, left=a.left)))
        if a.kind is Kind.U:
            return Formula(
                Kind.R,
                left=nnf(Formula(Kind.NOT, left=a.left)),
                right=nnf(Formula(Kind.NOT, left=a.right)),
            )
        if a.kind is Kind.R:
            return Formula(
                Kind.U,
                left=nnf(Formula(Kind.NOT, left=a.left)),
                right=nnf(Formula(Kind.NOT, left=a.right)),
            )
    if f.kind in (Kind.AND, Kind.OR, Kind.U, Kind.R):
        return Formula(
            f.kind, left=nnf(f.left) if f.left else None, right=nnf(f.right) if f.right else None
        )
    if f.kind is Kind.X:
        return Formula(Kind.X, left=nnf(f.left) if f.left else None)
    return f


def subformulas(f: Formula) -> Iterator[Formula]:
    yield f
    if f.left:
        yield from subformulas(f.left)
    if f.right:
        yield from subformulas(f.right)
