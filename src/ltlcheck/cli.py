from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from ltlcheck.engine import check_model
from ltlcheck.kripke import load_models


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ltlcheck")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("check", "explain"):
        c = sub.add_parser(name)
        c.add_argument("--model", required=True)
        c.add_argument("--id", dest="mid", default=None)
        c.add_argument("--formula", default=None)
        c.add_argument("--max-size-mb", type=float, default=5.0)
    args = p.parse_args(list(argv) if argv is not None else None)
    try:
        models = load_models(args.model, max_size_mb=args.max_size_mb)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    if args.mid:
        models = [m for m in models if m.model_id == args.mid]
        if not models:
            print(json.dumps({"error": "unknown id"}), file=sys.stderr)
            return 2
    if not models:
        print(json.dumps({"error": "no models"}), file=sys.stderr)
        return 2
    m = models[0]
    formula = args.formula or m.formula
    if not formula:
        print(json.dumps({"error": "no formula"}), file=sys.stderr)
        return 2
    try:
        res = check_model(m, formula)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    payload = res.to_json_obj()
    if args.cmd == "explain":
        product = res.accepting_product or {}
        vertices = product.get("vertices", [])
        acceptance = product.get("acceptance", [])
        vertex_count = len(vertices) if isinstance(vertices, list) else 0
        acceptance_count = len(acceptance) if isinstance(acceptance, list) else 0
        payload["explanation"] = (
            f"The {vertex_count}-vertex product has an accepting run across "
            f"{acceptance_count} until-obligation sets; its vertex IDs and Kripke projection "
            "witness a path satisfying the negated formula."
            if res.verdict == "UNSAT"
            else f"The {vertex_count}-vertex product has no reachable accepting cycle across "
            f"{acceptance_count} until-obligation sets for the negated formula."
        )
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
