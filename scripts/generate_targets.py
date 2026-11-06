#!/usr/bin/env python3
"""Turn targets.csv (the human-maintained inventory) into Prometheus file_sd JSON.

Each row becomes one blackbox probe target. Labels let Grafana filter by
environment / module and link straight to the node's own monitoring page.
Prometheus re-reads the JSON automatically - no restart needed after regenerating.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REQUIRED = ["env", "module", "node", "hostname", "url"]


def load(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"targets CSV missing columns: {missing}")
        rows = [{k: (v or "").strip() for k, v in r.items()} for r in reader]

    errors, seen = [], set()
    for i, r in enumerate(rows, start=2):
        if not r["url"].startswith(("http://", "https://")):
            errors.append(f"line {i}: url must start with http(s):// -> {r['url']!r}")
        if r["url"] in seen:
            errors.append(f"line {i}: duplicate url {r['url']}")
        seen.add(r["url"])
        if any(not r[c] for c in REQUIRED):
            errors.append(f"line {i}: empty required field")
    if errors:
        raise ValueError("\n".join(errors))
    return rows


def to_file_sd(rows: list[dict]) -> list[dict]:
    return [{"targets": [r["url"]],
             "labels": {"env": r["env"], "module": r["module"], "node": r["node"], "hostname": r["hostname"]}}
            for r in rows]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, default=Path("targets.csv"))
    p.add_argument("--out", type=Path, default=Path("prometheus/targets/targets.json"))
    args = p.parse_args(argv)
    try:
        rows = load(args.csv)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(to_file_sd(rows), indent=2) + "\n")
    envs = sorted({r["env"] for r in rows})
    print(f"wrote {len(rows)} targets ({', '.join(envs)}) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
