// Outil personnalisé OpenCode — capteur calculatoire du harness.
// À copier dans .opencode/tools/ (Phase 3). Le nom de l'outil est le nom du fichier : verifier_planning.
import { tool } from "@opencode-ai/plugin"

// Interpréteur Python : celui de l'environnement virtuel activé avant de lancer opencode.
const PY = process.env.PYTHON ?? (process.platform === "win32" ? "python" : "python3")

export default tool({
  description:
    "Vérifie un planning de soutenances avec l'oracle checker.py (indépendant du solveur). " +
    "Renvoie un rapport JSON : valide (true/false/null), violations codées C0..C7, préférences satisfaites. " +
    "Sans argument planning, exécute schedule.solve() sur l'instance puis vérifie le résultat. " +
    "À appeler après CHAQUE modification de schedule.py ou production d'un planning, avant d'annoncer un résultat.",
  args: {
    instance: tool.schema
      .string()
      .describe("Chemin de l'instance JSON, par ex. instances/soutenances.json"),
    planning: tool.schema
      .string()
      .optional()
      .describe("Chemin d'un fichier planning JSON à vérifier (facultatif)"),
  },
  async execute(args, context) {
    const cible = args.planning ? [args.instance, args.planning] : [args.instance]
    const res = await Bun.$`${PY} -m harness.verifier ${cible}`.cwd(context.directory).nothrow().quiet()
    const sortie = res.stdout.toString().trim()
    const erreurs = res.stderr.toString().trim()
    return erreurs ? `${sortie}\n[stderr]\n${erreurs}` : sortie
  },
})
