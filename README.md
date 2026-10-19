# TutoCSP — planificateur de soutenances

Le LLM modélise, le solveur résout, l'oracle vérifie, le harness encadre.

```
instances/                 3 instances (de base, infaisable, v2 avec charge et préférences)
checker.py                 ORACLE : vérifie un planning (ne pas modifier)
schedule.py                squelette à compléter : solve(instance) -> planning | None
test_schedule.py           tests de référence (ne pas modifier)
harness/verifier.py        capteur : python -m harness.verifier INSTANCE [PLANNING]
harness/opencode/          briques de harness à installer au fil des phases
opencode.json              fournisseurs locaux (Ollama, LM Studio)
```

Installation :

```
python3 -m venv .venv && source .venv/bin/activate     # Windows : .venv\Scripts\activate
pip install -r requirements.txt
git init && git add . && git commit -m "Etat initial"
```

Lancez toujours `opencode` depuis la racine du projet, environnement virtuel activé.
