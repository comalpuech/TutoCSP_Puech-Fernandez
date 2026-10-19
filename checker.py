"""Oracle de validation d'un planning de soutenances.

CE FICHIER EST LA RÉFÉRENCE : il ne doit pas être modifié (ni par vous, ni par l'agent).
Il vérifie un planning de façon indépendante du solveur.

Format d'un planning : liste de dictionnaires
    {"binome": "B01", "creneau": "lun-09h", "salle": "S101", "jury": ["Arnaud", "Esposito"]}
où jury[0] est le tuteur du binôme et jury[1] le second membre du jury.

Contraintes dures (codes utilisés dans les messages) :
    C0  format : clés présentes, identifiants connus
    C1  chaque binôme passe exactement une fois
    C2  une salle accueille au plus une soutenance par créneau
    C3  le jury est composé du tuteur (jury[0]) et d'un second membre différent du tuteur
    C4  un enseignant ne siège pas dans deux soutenances au même créneau
    C5  un enseignant ne siège pas sur un créneau où il est indisponible
    C6  le second membre du jury possède la compétence correspondant au thème du binôme
    C7  (si l'instance définit "charge_max") un enseignant siège dans au plus charge_max soutenances

Contrainte souple (non bloquante) :
    P1  un binôme ayant une préférence "matin" / "apres-midi" passe sur un créneau de cette période
"""

from __future__ import annotations

from collections import Counter, defaultdict

CLES = ("binome", "creneau", "salle", "jury")


def check(instance: dict, planning: list[dict] | None) -> list[str]:
    """Renvoie la liste des violations (vide si le planning est valide)."""
    if planning is None:
        return ["C0 : aucun planning fourni (None)"]
    if not isinstance(planning, list):
        recu = type(planning).__name__
        if isinstance(planning, dict):
            recu += f" avec les clés {list(planning)[:5]}"
        return [f"C0 : le planning doit être une liste JSON de soutenances [{{...}}, ...] (reçu : {recu})"]

    binomes = {b["id"]: b for b in instance["binomes"]}
    creneaux = {c["id"] for c in instance["creneaux"]}
    salles = set(instance["salles"])
    enseignants = {e["id"]: e for e in instance["enseignants"]}

    violations: list[str] = []
    valides: list[dict] = []

    # C0 : format
    for i, s in enumerate(planning):
        if not isinstance(s, dict) or any(k not in s for k in CLES):
            trouve = list(s)[:6] if isinstance(s, dict) else type(s).__name__
            violations.append(f"C0 : l'entrée n°{i} n'a pas les clés {CLES} (clés trouvées : {trouve})")
            continue
        ok = True
        if s["binome"] not in binomes:
            violations.append(f"C0 : binôme inconnu {s['binome']!r}")
            ok = False
        if s["creneau"] not in creneaux:
            violations.append(f"C0 : créneau inconnu {s['creneau']!r} ({s['binome']})")
            ok = False
        if s["salle"] not in salles:
            violations.append(f"C0 : salle inconnue {s['salle']!r} ({s['binome']})")
            ok = False
        jury = s["jury"]
        if not isinstance(jury, list) or len(jury) != 2:
            violations.append(f"C3 : le jury de {s['binome']} doit contenir exactement 2 enseignants")
            ok = False
        elif any(e not in enseignants for e in jury):
            violations.append(f"C0 : enseignant inconnu dans le jury de {s['binome']} : {jury}")
            ok = False
        if ok:
            valides.append(s)

    # C1 : chaque binôme exactement une fois
    compte = Counter(s["binome"] for s in valides)
    for b in binomes:
        if compte[b] == 0:
            violations.append(f"C1 : le binôme {b} n'a pas de soutenance")
        elif compte[b] > 1:
            violations.append(f"C1 : le binôme {b} passe {compte[b]} fois")

    # C2 : une salle par créneau
    occupation = Counter((s["creneau"], s["salle"]) for s in valides)
    for (c, salle), n in sorted(occupation.items()):
        if n > 1:
            violations.append(f"C2 : la salle {salle} accueille {n} soutenances au créneau {c}")

    siege = defaultdict(list)  # (enseignant, créneau) -> binômes
    charge = Counter()
    for s in valides:
        b = binomes[s["binome"]]
        tuteur, second = s["jury"]
        # C3 : composition du jury
        if tuteur != b["tuteur"]:
            violations.append(
                f"C3 : jury[0] de {b['id']} doit être son tuteur {b['tuteur']} (trouvé : {tuteur})"
            )
        if second == tuteur:
            violations.append(f"C3 : le second membre du jury de {b['id']} est le tuteur lui-même")
        # C6 : compétence du second membre
        if b["theme"] not in enseignants[second]["competences"]:
            violations.append(
                f"C6 : {second} n'a pas la compétence {b['theme']!r} requise pour {b['id']}"
            )
        for e in set(s["jury"]):
            siege[(e, s["creneau"])].append(b["id"])
            charge[e] += 1
            # C5 : disponibilité
            if s["creneau"] in enseignants[e]["indisponible"]:
                violations.append(
                    f"C5 : {e} est indisponible au créneau {s['creneau']} (soutenance {b['id']})"
                )

    # C4 : ubiquité
    for (e, c), bs in sorted(siege.items()):
        if len(bs) > 1:
            violations.append(f"C4 : {e} siège dans {len(bs)} soutenances au créneau {c} : {bs}")

    # C7 : charge maximale
    if "charge_max" in instance:
        for e, n in sorted(charge.items()):
            if n > instance["charge_max"]:
                violations.append(
                    f"C7 : {e} siège dans {n} soutenances (maximum {instance['charge_max']})"
                )

    return violations


def score_preferences(instance: dict, planning: list[dict] | None) -> tuple[int, int]:
    """P1 : renvoie (préférences satisfaites, préférences exprimées)."""
    periode = {c["id"]: c["periode"] for c in instance["creneaux"]}
    prefs = {b["id"]: b["prefere"] for b in instance["binomes"] if "prefere" in b}
    if not planning:
        return 0, len(prefs)
    ok = sum(
        1
        for s in planning
        if isinstance(s, dict)
        and s.get("binome") in prefs
        and periode.get(s.get("creneau")) == prefs[s["binome"]]
    )
    return ok, len(prefs)
