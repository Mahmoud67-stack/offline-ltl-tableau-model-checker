# Architecture

## Scope and deployment shape

`ltlcheck` is a single-process Python package for finite Kripke structures. It
loads local JSON, performs explicit-state checking, and emits JSON from its CLI.
It has no network listeners, external services, or runtime dependencies beyond
the Python standard library [evidence: pyproject.toml] [evidence: src/ltlcheck/cli.py].

## Components

### Formula front end

`formula.py` tokenizes and parses atoms, constants, Boolean operators, `X`,
`F`, `G`, `U`, `R`, and parentheses. It converts formulas to negation normal
form and provides subformula traversal. `F` and `G` are represented through
until and release forms during parsing [evidence: src/ltlcheck/formula.py].

### Kripke model loader

`kripke.py` loads either a model object or a `models` collection from JSON. It
validates nonempty, unique states, initial-state references, transition
references, total outgoing transitions, and label references. It checks the
file size before reading and applies a configurable `max_size_mb` limit
[evidence: src/ltlcheck/kripke.py].

### Tableau and product engine

`engine.py` builds truth-consistent elementary tableau sets for the negation of
the requested formula. It retains sets compatible with model labels and links
them with temporal successor constraints. The explicit product pairs a Kripke
state with a tableau node. Until subformulas become generalized Büchi
obligations.

The nested DFS uses a round-robin index to track progress through those
obligations. An accepting product run is serialized with product vertex IDs,
product edges, acceptance sets, and its Kripke projection. For an accepting
run of the negated formula, the result is `UNSAT` for the requested formula and
contains a finite lasso with a nonempty cycle [evidence: src/ltlcheck/engine.py].

### Oracle

`oracle.py` independently evaluates LTL on finite ultimately periodic words and
enumerates bounded model lassos. It is used by tests rather than by the
production engine. `unfolding_satisfies` also checks that a reported lasso
starts correctly, follows model edges, and falsifies the requested formula
when the tests expect a counterexample [evidence: src/ltlcheck/oracle.py].

### CLI and synthetic data

`cli.py` exposes `check` and `explain`. Both commands load a selected local
model and invoke the same engine; `explain` adds a generic product-count
sentence. `synth.py` supplies small in-repository regression cases and can
write them to `data/synthetic_kripke.json` [evidence: src/ltlcheck/cli.py]
[evidence: src/ltlcheck/synth.py].

## Data flow

1. The CLI receives a model path, optional model ID, optional formula, and size
   limit.
2. The loader reads and validates the local JSON model.
3. The parser produces a formula tree; the engine negates it and converts it to
   NNF.
4. Tableau elementary sets are generated and filtered against state labels.
5. Compatible tableau transitions are combined with real Kripke transitions to
   form the explicit product graph.
6. Nested DFS searches reachable product behavior for a round-robin accepting
   cycle.
7. The engine serializes the product and returns either `SAT` or `UNSAT` with a
   projected lasso when a witness is found.
8. Tests independently evaluate bundled and generated cases through the oracle.

## Control flow and engineering decisions

The checker searches the negated property because an accepting run directly
represents a counterexample to the requested universal model-checking claim.
The product is explicit rather than symbolic so product vertices, edges, and
accepting runs can be inspected in CLI output and tested directly.

Generalized until acceptance is handled with a round-robin progress index rather
than requiring a separate search implementation for each obligation. Nested
blue/red DFS is used for emptiness and witness discovery. The implementation
then lifts the projected state-name lasso back to product vertices so tests can
verify that the reported accepting cycle uses emitted product edges
[evidence: tests/test_counterexamples.py].

The oracle is deliberately separate from the production engine. This keeps the
semantic evaluator slower and independently coded, making it useful for parity
tests without becoming part of the verdict path.

## Alternatives and trade-offs

- **Explicit product versus symbolic representation:** explicit vertices and
  edges make witnesses and debugging inspectable, but product construction and
  tableau enumeration can become expensive.
- **Tableau closure enumeration versus a more specialized construction:** closure
  subsets are direct and easy to exercise with unit tests, but enumeration has
  exponential behavior and the current product construction broadly compares
  retained states [evidence: latest independent review].
- **Nested DFS versus SCC-based emptiness:** nested DFS matches the selected
  Büchi-emptiness design and has targeted tests; the current evidence does not
  provide exhaustive or independently derived completeness evidence for the
  custom acceptance conversion [evidence: latest independent review].
- **Bounded lasso oracle versus a complete reference model checker:** bounded
  lasso evaluation is independent and practical for small synthetic cases, but
  its path bound has no supplied completeness argument and cannot justify
  arbitrary-input correctness [evidence: src/ltlcheck/oracle.py] [evidence: latest independent review].
- **Projected witness plus lifting versus preserving the discovered product
  path:** projection gives a readable Kripke trace, while the current recursive,
  non-memoized lifting step can add search cost and is a known implementation
  trade-off [evidence: latest independent review].

## Verification status

The latest objective gates passed, including tests, lint, typing, compilation,
dependency validation, and security scans [evidence: latest objective evidence].
The evidence supports the bundled acceptance criteria and targeted regressions;
it does not establish general soundness or completeness over the full supported
grammar.