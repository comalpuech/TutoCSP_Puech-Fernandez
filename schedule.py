"""Planificateur de soutenances — à compléter avec l'assistant IA.

Usage :
    python schedule.py instances/soutenances.json            # écrit planning.json
    python schedule.py instances/soutenances.json -o mon_planning.json
"""

from __future__ import annotations

import argparse
import json


def solve(instance: dict) -> list[dict] | None:
    """Calcule un planning respectant toutes les contraintes dures de l'instance.

    Renvoie une liste de soutenances au format décrit dans checker.py,
    ou None si l'instance n'admet aucune solution (instance infaisable).
    """
    raise NotImplementedError("À implémenter (Phase 2)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance")
    parser.add_argument("-o", "--output", default="planning.json")
    args = parser.parse_args()

    with open(args.instance, encoding="utf-8") as f:
        instance = json.load(f)
    planning = solve(instance)
    if planning is None:
        print("Instance infaisable : aucun planning ne respecte toutes les contraintes.")
        return
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(planning, f, indent=2, ensure_ascii=False)
    print(f"{len(planning)} soutenances écrites dans {args.output}")


if __name__ == "__main__":
    main()
