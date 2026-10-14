"""Page de dépôt de fichiers (images) pour le storyboard.

Pourquoi : les pièces jointes envoyées dans la conversation n'arrivent pas toujours sur le disque de
la session (14/10 : la capture d'écran d'ed5, envoyée deux fois, n'a jamais été écrite dans
/home/user/uploads). Cette page permet de déposer une image directement dans le dépôt : elle est
enregistrée dans assets/storyboards/a-valider/<plan>/work/, puis commitée et poussée aussitôt, pour
survivre à une remise à zéro de la session.

Usage : python3 tools/depot_fichiers.py [PORT]   (défaut 8001, écoute sur 0.0.0.0)
  GET  /                                        la page de dépôt
  POST /api/depot?plan=p01&nom=NOM.png[&essai=1]  corps = le fichier brut ; essai=1 : vérifie sans
                                                 rien écrire ni commiter
"""
import io
import json
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "assets/storyboards/a-valider"
TAILLE_MAX = 40 * 1024 * 1024
EXTENSIONS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}

PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Déposer une image — Jeannot slamrap</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem;
         color: #222; background: #faf8f4; }
  h1 { font-size: 1.4rem; margin-bottom: .3rem; }
  p.aide { color: #555; margin-top: 0; }
  #zone { border: 3px dashed #b9a98a; border-radius: 12px; padding: 2rem 1rem; text-align: center;
          background: #fff; cursor: pointer; transition: background .15s; }
  #zone.survol { background: #f3ecdc; }
  #zone img { max-width: 100%; max-height: 420px; margin-top: 1rem; border: 1px solid #ccc; }
  .ligne { display: flex; gap: .8rem; align-items: center; margin: 1rem 0; flex-wrap: wrap; }
  input[type=text] { font-size: 1rem; padding: .4rem .5rem; width: 16rem; }
  select { font-size: 1rem; padding: .35rem; }
  button { font-size: 1.05rem; padding: .6rem 1.4rem; border-radius: 8px; border: 0;
           background: #2f6b3a; color: #fff; cursor: pointer; }
  button:disabled { background: #9aa99c; cursor: default; }
  #etat { margin-top: 1rem; font-size: 1.05rem; white-space: pre-line; }
  .ok { color: #1f6b2a; } .ko { color: #a12a1a; }
</style>
</head>
<body>
<h1>📤 Déposer une image dans le projet</h1>
<p class="aide">Glisse l'image dans le cadre, clique dedans pour la choisir, ou colle-la avec
<b>Ctrl+V</b>. Elle est enregistrée dans le projet, puis envoyée sur GitHub aussitôt.</p>

<div id="zone">
  <div id="invite">Dépose l'image ici (ou clique, ou Ctrl+V)</div>
  <img id="apercu" alt="" hidden>
</div>
<input type="file" id="fichier" accept="image/*" hidden>

<div class="ligne">
  <label>Plan <select id="plan"></select></label>
  <label>Nom du fichier <input type="text" id="nom" value="ed5-capture.png"></label>
</div>
<button id="envoyer" disabled>Envoyer</button>
<div id="etat"></div>

<script>
const zone = document.getElementById('zone'), choix = document.getElementById('fichier');
const apercu = document.getElementById('apercu'), invite = document.getElementById('invite');
const bouton = document.getElementById('envoyer'), etat = document.getElementById('etat');
const plan = document.getElementById('plan');
for (let i = 1; i <= 30; i++) {
  const p = 'p' + String(i).padStart(2, '0');
  plan.add(new Option(p.toUpperCase(), p, i === 1, i === 1));
}
let image = null;

function prendre(f) {
  if (!f || !f.type.startsWith('image/')) { etat.className = 'ko'; etat.textContent = "Ce n'est pas une image."; return; }
  image = f;
  apercu.src = URL.createObjectURL(f); apercu.hidden = false;
  invite.textContent = f.name ? ('Image : ' + f.name) : 'Image collée';
  bouton.disabled = false; etat.textContent = '';
}
zone.onclick = () => choix.click();
choix.onchange = () => prendre(choix.files[0]);
zone.ondragover = e => { e.preventDefault(); zone.classList.add('survol'); };
zone.ondragleave = () => zone.classList.remove('survol');
zone.ondrop = e => { e.preventDefault(); zone.classList.remove('survol'); prendre(e.dataTransfer.files[0]); };
document.onpaste = e => {
  for (const it of e.clipboardData.items) {
    if (it.type.startsWith('image/')) { prendre(it.getAsFile()); return; }
  }
};
bouton.onclick = async () => {
  if (!image) return;
  bouton.disabled = true; etat.className = ''; etat.textContent = 'Envoi en cours…';
  const url = 'api/depot?plan=' + encodeURIComponent(plan.value) + '&nom=' + encodeURIComponent(document.getElementById('nom').value);
  try {
    const r = await fetch(url, { method: 'POST', body: image, headers: { 'Content-Type': 'application/octet-stream' } });
    const j = await r.json();
    if (j.ok) {
      etat.className = 'ok';
      etat.textContent = '✅ Reçu : ' + j.largeur + '×' + j.hauteur + ' px (' + j.format + ')\\n' +
        'Enregistré dans ' + j.chemin + '\\n' +
        (j.pousse ? 'Envoyé sur GitHub (commit ' + j.commit + ').' : 'Commit ' + j.commit + ' fait ; envoi sur GitHub à refaire : ' + j.erreur) +
        '\\nTu peux revenir dans la conversation et taper « continue ».';
    } else {
      etat.className = 'ko'; etat.textContent = '❌ ' + j.erreur; bouton.disabled = false;
    }
  } catch (err) {
    etat.className = 'ko'; etat.textContent = '❌ Envoi impossible : ' + err; bouton.disabled = false;
  }
};
</script>
</body>
</html>
"""


def git(*args, timeout=120):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def deposer(plan, nom, data, essai=False):
    if not re.fullmatch(r"p\d\d", plan):
        raise ValueError("plan invalide : " + plan)
    if not data or len(data) > TAILLE_MAX:
        raise ValueError("fichier vide ou trop gros (40 Mo au plus)")
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
        im = Image.open(io.BytesIO(data))
    except Exception:
        raise ValueError("ce fichier n'est pas une image lisible (PNG, JPEG ou WEBP)")
    fmt = im.format
    if fmt not in EXTENSIONS:
        raise ValueError("format non pris en charge : %s (PNG, JPEG ou WEBP)" % fmt)
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(nom).stem).strip("-.") or "depot"
    dossier = BASE / plan / "work"
    dest = dossier / (base + EXTENSIONS[fmt])
    k = 2
    while dest.exists():                       # ne jamais écraser un fichier existant
        dest = dossier / ("%s-%d%s" % (base, k, EXTENSIONS[fmt]))
        k += 1
    rel = dest.relative_to(ROOT).as_posix()
    info = dict(ok=True, chemin=rel, largeur=im.size[0], hauteur=im.size[1], format=fmt, commit="", pousse=False)
    if essai:
        return info
    dossier.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    msg = "Dépôt : %s (%d×%d, envoyé par l'utilisateur depuis la page de dépôt)" % (rel, im.size[0], im.size[1])
    r = git("add", rel)
    if r.returncode == 0:
        r = git("commit", "-q", "-m", msg, "--", rel)
    if r.returncode:
        info["erreur"] = "fichier enregistré, mais commit impossible : " + (r.stderr or r.stdout).strip()
        return info
    info["commit"] = git("rev-parse", "--short", "HEAD").stdout.strip()
    branche = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    r = git("push", "-q", "origin", branche)
    info["pousse"] = r.returncode == 0
    if r.returncode:
        info["erreur"] = r.stderr.strip()
    print("dépôt :", rel, im.size, "commit", info["commit"], "poussé" if info["pousse"] else "NON poussé", flush=True)
    return info


class Gestionnaire(BaseHTTPRequestHandler):
    def _repondre(self, code, corps, type_="application/json; charset=utf-8"):
        if isinstance(corps, dict):
            corps = json.dumps(corps, ensure_ascii=False)
        b = corps.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if urlparse(self.path).path in ("/", "/index.html"):
            self._repondre(200, PAGE, "text/html; charset=utf-8")
        else:
            self._repondre(404, {"ok": False, "erreur": "introuvable"})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path.rstrip("/") != "/api/depot":
            self._repondre(404, {"ok": False, "erreur": "introuvable"})
            return
        q = parse_qs(u.query)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > TAILLE_MAX:
                raise ValueError("fichier vide ou trop gros (40 Mo au plus)")
            data = self.rfile.read(n)
            info = deposer(q.get("plan", ["p01"])[0].lower(), q.get("nom", ["depot.png"])[0], data,
                           essai=q.get("essai", ["0"])[0] == "1")
            self._repondre(200, info)
        except Exception as exc:
            self._repondre(400, {"ok": False, "erreur": str(exc)})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print("Page de dépôt : http://localhost:%d/  (écoute sur 0.0.0.0:%d)" % (port, port), flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Gestionnaire).serve_forever()
