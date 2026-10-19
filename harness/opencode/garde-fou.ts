// Plugin OpenCode — garde-fous et traçabilité du harness.
// À copier dans .opencode/plugins/ (Phase 3).
//
//  1. Contrainte : bloque toute écriture sur les fichiers de référence (l'oracle et les tests protégés).
//  2. Traçabilité : journalise chaque appel d'outil de l'agent dans harness_log.jsonl.
//  3. Capteur pour l'humain : quand l'agent rend la main (session.idle), lance pytest
//     et consigne le résultat dans le journal.
import type { Plugin } from "@opencode-ai/plugin"
import { appendFileSync } from "node:fs"
import path from "node:path"

const PROTEGES = ["checker.py", "test_schedule.py", "instances/", "instances\\", "harness/", "harness\\", ".opencode"]
const OUTILS_ECRITURE = ["edit", "write", "patch", "apply_patch", "multiedit"]
const PY = process.env.PYTHON ?? (process.platform === "win32" ? "python" : "python3")

export const GardeFou: Plugin = async ({ $, directory }) => {
  const journal = path.join(directory, "harness_log.jsonl")
  const log = (entree: Record<string, unknown>) =>
    appendFileSync(journal, JSON.stringify({ t: new Date().toISOString(), ...entree }) + "\n")

  return {
    "tool.execute.before": async (input, output) => {
      const args = JSON.stringify(output.args ?? {})
      log({ evenement: "appel_outil", outil: input.tool, args: args.slice(0, 300) })

      const touche = PROTEGES.find((p) => args.includes(p))
      const ecrit = OUTILS_ECRITURE.includes(input.tool)
      // Commandes shell qui modifient un fichier protégé (redirection, sed -i, mv, rm, cp…)
      const shellModifiant = input.tool === "bash" && /(>|sed\s+-i|\bmv\b|\brm\b|\bcp\b|tee)/.test(args)

      if (touche && (ecrit || shellModifiant)) {
        log({ evenement: "BLOQUE", outil: input.tool, fichier: touche })
        throw new Error(
          `GARDE-FOU : ${touche} est une référence du projet (oracle ou test protégé) et ne peut pas être modifié. ` +
            `Si un test échoue, corrige schedule.py ; si tu penses que la référence est fausse, explique-le à l'utilisateur.`,
        )
      }
    },

    event: async ({ event }) => {
      if (event.type === "session.idle") {
        const r = await $`${PY} -m pytest -q test_schedule.py`.cwd(directory).nothrow().quiet()
        const resume = r.stdout.toString().trim().split("\n").pop()
        log({ evenement: "pytest_fin_de_tour", code: r.exitCode, resume })
      }
    },
  }
}
