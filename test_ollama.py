import json, urllib.request

MODELE = "qwen3-8b-32k"

requete = {
"model": MODELE,
"messages": [{"role": "user", "content": "Quel temps fait-il à Gif-sur-Yvette ?"}],
"tools": [{"type": "function", "function": {
"name": "meteo",
"description": "Donne la météo actuelle d’une ville",
"parameters": {"type": "object",
"properties": {"ville": {"type": "string"}},
"required": ["ville"]}}}],
}


req = urllib.request.Request("http://localhost:11434/v1/chat/completions",
data=json.dumps(requete).encode(),
headers={"Content-Type": "application/json"})

message = json.load(urllib.request.urlopen(req, timeout=300))["choices"][0]["message"]

print("Appel d’outil :", message.get("tool_calls") or "AUCUN : modèle inadapté à OpenCode")