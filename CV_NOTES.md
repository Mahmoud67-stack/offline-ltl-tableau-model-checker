# CV notes

## Portfolio positioning

An offline formal-methods artifact implementing explicit-state LTL checking over
finite Kripke structures. The project demonstrates a checker pipeline and
correctness-focused testing on synthetic data; it does not claim production
verification savings, adoption, or deployment impact [evidence: data/synthetic_kripke.json]
[evidence: src/ltlcheck/synth.py].

## Truthful role evidence

- **Formal verification engineer:** implemented or exercised LTL parsing, NNF
  conversion, tableau elementary sets, generalized Büchi obligations, product
  construction, and nested DFS emptiness [evidence: src/ltlcheck/formula.py]
  [evidence: src/ltlcheck/engine.py].
- **Static analysis engineer:** built an explicit state/formula product and
  surfaced accepting product vertices, edges, acceptance sets, and projected
  lassos for inspection [evidence: src/ltlcheck/engine.py].
- **Correctness QA engineer:** separated the recursive lasso evaluator from the
  production engine and tested verdict parity, counterexample falsification,
  parser behavior, loader validation, and product-edge witnesses
  [evidence: src/ltlcheck/oracle.py] [evidence: tests/test_counterexamples.py]
  [evidence: tests/test_oracle_parity.py].

## Skills evidenced

LTL semantics, tableau construction, Büchi automata, explicit-state model
checking, property-based testing, Python packaging, CLI design, local JSON
validation, static typing, and lint-gated development are all represented in
the implementation and test suite [evidence: src/ltlcheck]
[evidence: tests] [evidence: pyproject.toml].

## Verified results

The latest objective evidence reports passing tests, Ruff, strict mypy,
compilation, dependency validation, placeholder scanning, and secret scanning
[evidence: latest objective evidence]. The acceptance tests cover bundled
CLI/oracle parity, falsifying `UNSAT` lassos, and static quality gates
[evidence: tests/test_oracle_parity.py] [evidence: tests/test_counterexamples.py].

These are bounded and synthetic results. The oracle checks bounded lasso sets,
and the review explicitly notes that this does not establish arbitrary-input
soundness or completeness [evidence: latest independent review].

## Interview talking points

- Why search the tableau for the negated formula? An accepting run then has a
  direct counterexample interpretation for the requested universal property.
- Why keep the oracle out of production? Independent implementation reduces the
  risk that the checker and its test oracle share the same decision logic.
- How is a generalized Büchi condition searched? A round-robin progress index
  records which until obligation is being discharged, while nested DFS searches
  for an accepting cycle.
- What is observable in a result? The CLI returns product structure details and,
  for a discovered counterexample, a projected lasso plus product vertex IDs.
- What would be needed before making stronger correctness claims? A complete
  independent model-level reference or a justified completeness argument for
  the bounded oracle, together with stronger evidence for acceptance handling.

## Challenges and trade-offs

The central challenge is aligning local tableau consistency, temporal successor
constraints, generalized until acceptance, product edges, and lasso projection.
The implementation favors inspectable explicit structures and a separate oracle,
accepting higher memory and scaling costs. Elementary-set enumeration can grow
exponentially; product construction broadly compares retained states; and
witness lifting uses recursive search without memoization [evidence: latest
independent review].

The current `explain` command is count-based rather than formula-specific.
Nested DFS and the custom acceptance conversion have targeted regression tests,
not exhaustive or independently derived completeness evidence
[evidence: latest independent review].

## Description options

1. “Offline explicit-state LTL model checker for finite Kripke structures, with
   tableau construction, generalized Büchi product search, lasso witnesses, and
   an independent semantic test oracle.”
2. “Python formal-verification artifact that checks synthetic Kripke models with
   an inspectable tableau/product pipeline and correctness-focused regression
   and property tests.”
3. “LTL tableau and Büchi-product checker demonstrating model-checking
   implementation, counterexample construction, and bounded oracle parity.”

## Bullet options

- Built an offline Python LTL checker that parses a closed grammar, constructs a
  tableau/product for the negated property, and searches it with nested DFS
  [evidence: src/ltlcheck/formula.py] [evidence: src/ltlcheck/engine.py].
- Implemented JSON Kripke loading with structural validation, local-only file
  operation, and an input-size guard [evidence: src/ltlcheck/kripke.py].
- Added accepting product and finite lasso output, with tests confirming that
  counterexample unfoldings falsify the requested formula and that accepting
  cycles follow emitted product edges [evidence: tests/test_counterexamples.py].
- Built an independently coded bounded LTL-on-lasso oracle and property tests to
  compare checker verdicts on synthetic and generated cases
  [evidence: src/ltlcheck/oracle.py] [evidence: tests/test_oracle_parity.py].
- Documented the assurance boundary: bounded parity and synthetic regression do
  not prove general soundness or completeness [evidence: latest independent review].

## Claims to avoid

Do not describe this artifact as production-ready verification infrastructure,
a complete correctness proof, a complete independent oracle, or evidence of
business savings. The supplied review identifies bounded-oracle and scalability
limitations that should remain explicit [evidence: latest independent review].