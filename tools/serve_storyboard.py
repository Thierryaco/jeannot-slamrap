#!/usr/bin/env python3
"""Petit serveur local pour la page « storyboard à valider ».

- Sert les fichiers du dépôt (images, pages).
- GET  /api/manifest : renvoie assets/storyboards/a-valider/options.json
- POST /api/avis     : enregistre un avis / un choix dans le manifeste,
                       régénère docs/storyboard-a-valider.md, puis fait un
                       commit + push Git en arrière-plan (sauvegarde anti-bug).

Usage : python3 tools/serve_storyboard.py [port]   (défaut 8000, écoute 0.0.0.0)
"""
import json
import subprocess
import sys
import threading
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "assets/storyboards/a-valider/options.json"
LOCK = threading.Lock()
GIT_LOCK = threading.Lock()
ETATS = {"a-valider", "retenue", "ecartee", "a-retoucher"}

sys.path.insert(0, str(ROOT / "tools"))
import build_a_valider  # noqa: E402


def now():
    return datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d %H:%M")


def git_save(message):
    def run():
        with GIT_LOCK:
            try:
                files = [str(MANIFEST.relative_to(ROOT)), "docs/storyboard-a-valider.md"]
                subprocess.run(["git", "add", *files], cwd=ROOT, check=True, capture_output=True)
                r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
                if r.returncode == 0:
                    return
                subprocess.run(["git", "commit", "-m", message, "--", *files], cwd=ROOT, check=True, capture_output=True)
                branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT).decode().strip()
                subprocess.run(["git", "push", "-q", "origin", branch], cwd=ROOT, capture_output=True, timeout=120)
            except Exception as exc:  # la sauvegarde locale du JSON reste faite
                print("git_save:", exc, flush=True)

    threading.Thread(target=run, daemon=True).start()


def apply(data):
    plan_id = data.get("plan")
    opt_id = data.get("option")
    texte = (data.get("texte") or "").strip()
    etat = data.get("etat")
    with LOCK:
        man = json.loads(MANIFEST.read_text(encoding="utf-8"))
        plan = next((p for p in man["plans"] if p["plan"] == plan_id), None)
        if plan is None:
            raise ValueError("plan inconnu")
        resume = [plan_id]
        if opt_id:
            opt = next((o for o in plan["options"] if o["id"] == opt_id), None)
            if opt is None:
                raise ValueError("option inconnue")
            resume.append(opt_id)
            if etat:
                if etat not in ETATS:
                    raise ValueError("état inconnu")
                if etat == "retenue":
                    for o in plan["options"]:
                        if o is not opt and o["etat"] == "retenue":
                            o["etat"] = "a-valider"
                    plan["choix"] = opt_id
                    plan["statut"] = "valide"
                elif plan.get("choix") == opt_id:
                    plan["choix"] = None
                    plan["statut"] = "en-cours"
                opt["etat"] = etat
                resume.append(etat)
            if texte:
                opt.setdefault("avis", []).append({"date": now(), "texte": texte})
                resume.append("avis")
        elif texte:
            plan.setdefault("avis", []).append({"date": now(), "texte": texte})
            if plan["statut"] == "a-valider":
                plan["statut"] = "en-cours"
            resume.append("idée/avis libre")
        else:
            raise ValueError("rien à enregistrer")
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        build_a_valider.main(html=False)
    git_save("Avis storyboard : " + " · ".join(resume))
    return man


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/storyboard/a-valider.html")
            self.end_headers()
            return
        if self.path.startswith("/api/manifest"):
            return self._json(200, json.loads(MANIFEST.read_text(encoding="utf-8")))
        return super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/api/avis"):
            return self._json(404, {"erreur": "inconnu"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            man = apply(data)
            return self._json(200, {"ok": True, "manifest": man})
        except Exception as exc:
            return self._json(400, {"ok": False, "erreur": str(exc)})


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = ThreadingHTTPServer(("0.0.0.0", port), partial(Handler, directory=str(ROOT)))
    print(f"Storyboard à valider : http://0.0.0.0:{port}/storyboard/a-valider.html", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
