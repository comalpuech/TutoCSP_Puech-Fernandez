"""Tests de référence (fichier protégé : ne pas modifier).

Vos propres tests vont dans test_eleves.py.
"""

import json
from pathlib import Path

from checker import check
from schedule import solve

INSTANCES = Path(__file__).parent / "instances"


def charger(nom: str) -> dict:
    return json.loads((INSTANCES / nom).read_text(encoding="utf-8"))


def test_instance_de_base_valide():
    instance = charger("soutenances.json")
    planning = solve(instance)
    assert planning is not None, "l'instance de base est faisable : solve() ne doit pas renvoyer None"
    assert check(instance, planning) == []


def test_instance_infaisable_detectee():
    instance = charger("soutenances_infaisable.json")
    assert solve(instance) is None, "l'instance est infaisable : solve() doit renvoyer None"
