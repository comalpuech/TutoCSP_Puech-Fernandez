"""Capteur calculatoire du harness : vérifie un planning avec l'oracle (checker.py).

Usage :
    python -m harness.verifier INSTANCE [PLANNING]

- avec PLANNING : vérifie le fichier de planning fourni ;
- sans PLANNING : exécute schedule.solve() sur l'instance (délai max. 60 s) puis vérifie le résultat.

Affiche un rapport JSON sur la sortie standard. Code de retour : 0 si valide, 1 sinon.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import unicodedata  # noqa: E402
from collections import Counter  # noqa: E402

from checker import CLES, check, score_preferences  # noqa: E402

MAX_VIOLATIONS_AFFICHEES = 15


def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn").lower()


# Synonymes fréquents produits par les LLM -> clé attendue (comparaison sans accents ni casse)
SYNONYMES = {
    "binome": {"binome", "binome_id", "id_binome", "id", "groupe", "equipe", "team", "group", "student_pair", "pair"},
    "creneau": {"creneau", "creneau_id", "id_creneau", "horaire", "slot", "time_slot", "timeslot", "heure", "time"},
    "salle": {"salle", "salle_id", "id_salle", "room", "lieu"},
    "jury": {"jury", "membres_jury", "jury_membres", "membres", "examinateurs", "enseignants", "jurys"},
    "tuteur": {"tuteur", "tutor", "encadrant", "president"},
    "second": {"second", "second_membre", "examinateur", "membre", "rapporteur", "second_member", "examiner", "membre_2"},
}


def _cle_canonique(cle: str) -> str | None:
    c = _sans_accents(cle).replace(" ", "_").replace("-", "_")
    return next((canon for canon, syn in SYNONYMES.items() if c in syn), None)


def _normaliser_soutenance(s):
    """Renomme les clés d'une soutenance ; renvoie (soutenance, a_change)."""
    if not isinstance(s, dict):
        return s, False
    out, change = {}, False
    for k, v in s.items():
        canon = _cle_canonique(k)
        if canon and canon != k:
            change = True
        out[canon or k] = v
    # jury donné comme objet {"tuteur": ..., "second": ...}
    jury = out.get("jury")
    if isinstance(jury, dict):
        j = {(_cle_canonique(k) or k): v for k, v in jury.items()}
        if "tuteur" in j and "second" in j:
            out["jury"], change = [j["tuteur"], j["second"]], True
    # jury donné comme deux clés séparées
    if "jury" not in out and "tuteur" in out and "second" in out:
        out["jury"], change = [out.pop("tuteur"), out.pop("second")], True
    return out, change


def normaliser(planning):
    """Tolère les écarts de format fréquents des LLM, en les signalant, pour vérifier le fond.

    - {"planning": [...]} ou toute enveloppe à une seule clé contenant une liste -> la liste ;
    - {"B01": {"creneau": ..., ...}, ...} -> liste en ajoutant la clé "binome" ;
    - clés accentuées ou synonymes ("binôme", "créneau", "room", "examinateur"...) -> clés attendues ;
    - jury sous forme d'objet {"tuteur": ..., "second": ...} -> liste [tuteur, second].
    """
    avertissements = []
    if isinstance(planning, dict) and planning:
        listes = [(k, v) for k, v in planning.items() if isinstance(v, list)]
        if len(planning) == 1 and len(listes) == 1:
            cle, planning = listes[0]
            avertissements.append(f"planning enveloppé dans la clé {cle!r} : déballé")
        elif all(isinstance(v, dict) for v in planning.values()):
            planning = [{"binome": k, **v} for k, v in planning.items()]
            avertissements.append("planning indexé par binôme : converti en liste")
    if isinstance(planning, list):
        resultats = [_normaliser_soutenance(s) for s in planning]
        if any(change for _, change in resultats):
            exemple = next((s for s in planning if isinstance(s, dict)), {})
            avertissements.append(f"clés non conformes (ex. {list(exemple)}) : renommées en {list(CLES)}")
        planning = [s for s, _ in resultats]
    if not avertissements:
        return planning, None
    return planning, " ; ".join(avertissements) + " — le format attendu est décrit dans checker.py"


def rapport(instance_path: str, planning_path: str | None) -> dict:
    instance = json.loads(Path(instance_path).read_text(encoding="utf-8"))
    r: dict = {"instance": instance_path}
    if planning_path:
        r["source"] = planning_path
        try:
            planning = json.loads(Path(planning_path).read_text(encoding="utf-8"))
        except Exception as exc:  # fichier absent ou JSON invalide
            r.update(valide=False, erreur=f"planning illisible : {exc}")
            return r
    else:
        r["source"] = "schedule.solve()"
        try:
            import importlib

            import schedule

            importlib.reload(schedule)
            t0 = time.perf_counter()
            planning = schedule.solve(instance)
            r["duree_s"] = round(time.perf_counter() - t0, 3)
        except Exception:
            r.update(valide=False, erreur="exception dans solve()", trace=traceback.format_exc(limit=3))
            return r
        if planning is None:
            r.update(
                valide=None,
                resultat="solve() renvoie None : le code déclare l'instance INFAISABLE. "
                "Ce rapport ne prouve pas l'infaisabilité ; justifiez-la (outil expliquer_infaisabilite).",
            )
            return r

    planning, avertissement = normaliser(planning)
    if avertissement:
        r["avertissement_format"] = avertissement

    # Jury absent : on vérifie le reste en plaçant provisoirement le tuteur seul,
    # et on compte un second membre manquant comme une violation C3 par binôme.
    sans_jury = []
    if isinstance(planning, list):
        tuteurs = {b["id"]: b["tuteur"] for b in instance["binomes"]}
        complete = []
        for s in planning:
            if isinstance(s, dict) and "jury" not in s and s.get("binome") in tuteurs:
                sans_jury.append(s["binome"])
                s = {**s, "jury": [tuteurs[s["binome"]], tuteurs[s["binome"]]]}
            complete.append(s)
        planning = complete
    if sans_jury:
        r["avertissement_jury"] = (
            f"{len(sans_jury)} soutenance(s) sans jury : le second membre n'a pas été attribué. "
            "Le planning résout un problème plus simple que celui posé."
        )

    violations = check(instance, planning)
    if sans_jury:
        manquants = set(sans_jury)
        violations = [
            v for v in violations
            if not (v.startswith(("C3", "C6")) and any(f" {b}" in v or f"{b} " in v for b in manquants))
        ]
        violations = violations + [f"C3 : pas de second membre de jury pour {b}" for b in sorted(manquants)]
    ok, total = score_preferences(instance, planning)
    r.update(
        valide=not violations,
        nb_soutenances=len(planning) if isinstance(planning, list) else None,
        nb_violations=len(violations),
        par_code=dict(sorted(Counter(v.split(" ")[0] for v in violations).items())),
        violations=violations[:MAX_VIOLATIONS_AFFICHEES],
    )
    if len(violations) > MAX_VIOLATIONS_AFFICHEES:
        r["violations_masquees"] = len(violations) - MAX_VIOLATIONS_AFFICHEES
    if total:
        r["preferences_satisfaites"] = f"{ok}/{total}"
    return r


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    r = rapport(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0 if r.get("valide") else 1


if __name__ == "__main__":
    sys.exit(main())
