# ltl-kripke-tableau-checker

Offline LTL model checking for finite Kripke structures. The project is a
formal-methods portfolio artifact: it measures checker behavior on synthetic
models rather than claiming production verification savings, deployment, or
user adoption.

## Problem

Given a finite, total Kripke structure and an LTL property, the checker decides
whether every path from every initial state satisfies the property. When the
negated property has an accepting product run, the checker returns `UNSAT` and
emits a finite ultimately periodic Kripke lasso whose unfolding is checked
against the property by the test oracle.

The supported parser handles atoms, Boolean operators, constants, `X`, `F`,
`G`, `U`, `R`, and parentheses. The implementation is local-only: models are
loaded from JSON files, oversized input is rejected through `max_size_mb`, and
there are no network listeners or external services.

## Architecture

The single-process Python package contains:

- a lexer/parser, negation-normal-form conversion, and subformula traversal;
- a validating JSON loader for finite total Kripke models;
- tableau elementary-set construction for the negated formula;
- an explicit Kripke/tableau product with generalized-until acceptance;
- nested blue/red DFS using a round-robin Büchi encoding;
- JSON-producing `check` and `explain` CLI commands;
- a separate recursive lasso-semantics module used as a test oracle; and
- an in-repository synthetic model/formula generator.

The oracle is not used by the production decision procedure. See
[ARCHITECTURE.md](ARCHITECTURE.md) for data flow, control flow, decisions,
alternatives, and trade-offs.

## Setup

Python 3.12 is required by the project configuration. Install the package and
development tools in a virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e "い.[dev]"
```

The repository's reproducibility command is:

```bash
python -m venv .venv && pip install -e .[dev] && pytest -q
```

The development dependencies are pytest, Hypothesis, Ruff, and mypy; runtime
dependencies are from the Python standard library.

## Local execution

Run a check against the bundled local data:

```bash
python -m ltlcheck.cli check \
  --model data/synthetic_kripke.json --id m1 --formula "G p"
```

Request the count-based product explanation:

```bash
python -m ltlcheck.cli explain \
  --model data/synthetic_kripke.json --id m2 --formula "F q"
```

Refresh the synthetic JSON corpus with the in-repository generator:

```bash
python -m ltlcheck.synth
```

Successful CLI calls return exit status zero and print JSON containing the
verdict, normalized formula, and product details. An `UNSAT` result includes a
nonempty `lasso` cycle and may include product vertex IDs for the accepting run.
Input and formula errors are reported as JSON on stderr with a nonzero exit
status.

## Tests and verified results

The objective gates passed in the latest evidence: the test suite passed, Ruff
passed, strict mypy passed, compilation passed, dependency validation passed,
and secret scanning passed [evidence: latest objective evidence]. The suite
covers parser behavior, tableau closure and expansion, nested DFS, accepting
product edges, bundled CLI/oracle parity, counterexample falsification, loader
validation, and property-based parity against the recursive oracle
[evidence: tests/test_counterexamples.py] [evidence: tests/test_oracle_parity.py].

The bundled acceptance checks are:

- CLI verdicts agree with the oracle on the bundled synthetic cases
  [evidence: tests/test_oracle_parity.py];
- emitted `UNSAT` lassos are rejected by the oracle when unfolded
  [evidence: tests/test_counterexamples.py]; and
- static typing and lint gates pass for the implementation
  [evidence: latest objective evidence].

These results are regression and bounded property-test evidence, not a proof of
soundness and completeness for every finite model and formula in the grammar.

## Data provenance

`data/synthetic_kripke.json` is an in-repository synthetic dataset. Its models
and expected labels are maintained by `ltlcheck.synth`; no external source,
network access, authentication, or personal data is involved
[evidence: data/synthetic_kripke.json] [evidence: src/ltlcheck/synth.py].

## Limitations

The independent oracle enumerates only bounded ultimately periodic paths. Its
bound is not accompanied by a completeness argument tied to the formula or
product size. Consequently, oracle parity does not establish correctness for
arbitrary accepted inputs. General soundness and completeness over the full
supported grammar have not been established.

The randomized parity campaign is intentionally small and bounded: it uses
models with at most four states, formulas with at most four leaves, and a
configured campaign of 75 examples [evidence: tests/test_oracle_parity.py].
The round-robin acceptance conversion and nested DFS have targeted regression
tests but no exhaustive or independently derived completeness evidence.

Tableau elementary-set enumeration is exponential in the closure, product
construction compares many retained states, and witness lifting uses recursive
search without memoization. These choices limit scalability. The `explain`
output is a generic count-based sentence rather than formula-specific tableau
reasoning [evidence: latest independent review].

## Future work

Evidence-backed next steps are to replace bounded oracle parity with a complete
independent model-level reference, add a completeness argument or stronger
cross-check for generalized Büchi acceptance and nested DFS, improve product
construction and witness preservation, and make explanations expose
formula-specific obligations. These changes would address the assurance,
scaling, and observability limitations identified in review rather than imply
current production readiness.