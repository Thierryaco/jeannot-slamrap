#!/usr/bin/env python3
"""Petit serveur local pour la page « storyboard à valider ».

- Sert les fichiers du dépôt (images, pages).
- GET  /api/manifest : renvoie assets/storyboards/a-valider/options.json
- POST /api/avis     : enregistre un avis / un choix dans le manifeste,
                       régénère docs/storyboard-a-valider.md, puis fait un
                       commit + push Git en arrière-plan (sauvegarde anti-bug).
- GET  /api/carte    : lieux + placements par plan (carte interactive)
- POST /api/carte    : enregistre le placement d'un plan (caméras, personnages,
                       véhicules, note), redessine carte/plans/pXX.png, commit + push.

Usage : python3 tools/serve_storyboard.py [port] [--host ADRESSE]
        port : défaut 8000 ; --host : défaut 0.0.0.0 (nécessaire dans le bac à sable Arena).
        En local (VS Code), la tâche « Lancer le serveur storyboard » utilise --host 127.0.0.1 :
        la page n'est alors visible que depuis ton ordinateur.
"""
import argparse
import importlib
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:  # Windows sans le paquet tzdata : on retombe sur l'heure locale de l'ordinateur
    PARIS = None

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "assets/storyboards/a-valider/options.json"
LOCK = threading.Lock()
GIT_LOCK = threading.Lock()
ETATS = {"a-valider", "retenue", "ecartee", "a-retoucher"}

sys.path.insert(0, str(ROOT / "tools"))
import build_a_valider  # noqa: E402
import draw_street_map  # noqa: E402
import calque  # noqa: E402

CARTE = ROOT / "assets/storyboards/a-valider/carte"
PLANS = CARTE / "plans.json"


def now():
    return datetime.now(PARIS).strftime("%Y-%m-%d %H:%M")


def _git(*args, timeout=60):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, timeout=timeout,
                          encoding="utf-8", errors="replace")


def git_save(message, files=None):
    files = files or [MANIFEST.relative_to(ROOT).as_posix(), "docs/storyboard-a-valider.md"]

    def run():
        with GIT_LOCK:
            try:
                r = _git("add", *files)
                if r.returncode:
                    raise RuntimeError("git add : " + r.stderr.strip())
                if _git("diff", "--cached", "--quiet", "--", *files).returncode == 0:
                    return
                r = _git("commit", "-m", message, "--", *files)
                if r.returncode:
                    raise RuntimeError("git commit : " + (r.stderr or r.stdout).strip())
                branch = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
                r = _git("push", "-q", "origin", branch, timeout=120)
                if r.returncode:  # le commit local est fait ; il partira au prochain push
                    print(f"git_save : commit fait mais push refusé ({r.stderr.strip()})", flush=True)
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
            if data.get("supprimer"):
                return supprimer(man, plan, opt)
            if texte:
                if not isinstance(opt.get("avis"), list):  # champ vide mal typé ("") -> liste
                    opt["avis"] = []
                opt["avis"].append({"date": now(), "texte": texte})
                resume.append("avis")
        elif texte:
            if not isinstance(plan.get("avis"), list):
                plan["avis"] = []
            plan["avis"].append({"date": now(), "texte": texte})
            if plan["statut"] == "a-valider":
                plan["statut"] = "en-cours"
            resume.append("idée/avis libre")
        else:
            raise ValueError("rien à enregistrer")
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        build_a_valider.main(html=False)
    git_save("Avis storyboard : " + " · ".join(resume))
    return man


def supprimer(man, plan, opt):
    """Supprime définitivement une version : retirée du manifeste ET son image effacée du dépôt.
    (Appelée sous LOCK depuis apply.)"""
    if opt.get("etat") == "retenue" or plan.get("choix") == opt["id"]:
        raise ValueError("version retenue : la remettre « à valider » avant de la supprimer")
    plan["options"] = [o for o in plan["options"] if o is not opt]
    rel = f"assets/storyboards/a-valider/{plan['plan'].lower()}/{opt['fichier']}"
    f = ROOT / rel
    encore = any(o.get("fichier") == opt["fichier"] for p in man["plans"] for o in p["options"]
                 if p["plan"] == plan["plan"])
    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    build_a_valider.main(html=False)
    files = [str(MANIFEST.relative_to(ROOT)), "docs/storyboard-a-valider.md"]
    if f.exists() and not encore:
        f.unlink()
        files.append(rel)
    git_save(f"Storyboard : version {plan['plan']} {opt['id']} supprimée définitivement", files)
    return man


def carte_payload():
    meta = [{k: p[k] for k in ("plan", "temps", "paroles", "brief")}
            for p in json.loads(MANIFEST.read_text(encoding="utf-8"))["plans"] if p["plan"].startswith("P")]
    plans = json.loads(PLANS.read_text(encoding="utf-8")) if PLANS.exists() else {}
    return {"lieux": draw_street_map.load_lieux(), "plans": plans, "meta": meta}


def _num(v, lo=-5000, hi=5000):
    v = float(v)
    if not (lo <= v <= hi):
        raise ValueError("valeur hors limites")
    return round(v, 1)


def save_carte(data):
    plan_id = str(data.get("plan", "")).upper()
    d = data.get("data") or {}
    lieux = draw_street_map.load_lieux()
    ids = {k["id"] for k in lieux["catalogue"]}
    meta = {p["plan"]: p for p in json.loads(MANIFEST.read_text(encoding="utf-8"))["plans"]}
    if plan_id not in meta or not plan_id.startswith("P"):
        raise ValueError("plan inconnu")
    cams = []
    for c in (d.get("cameras") or [])[:2]:
        cams.append({"x": _num(c["x"]), "y": _num(c["y"]), "angle": _num(c["angle"], -720, 720),
                     "fov": _num(c["fov"], 1, 180), "portee": _num(c["portee"], 10, 3000),
                     "hauteur": str(c.get("hauteur", ""))[:60]})
        if c.get("oeil") not in (None, ""):
            cams[-1]["oeil"] = _num(c["oeil"], 0, 60)
        if c.get("inclinaison") not in (None, ""):
            cams[-1]["inclinaison"] = _num(c["inclinaison"], -89, 89)
    if not cams:
        raise ValueError("il faut au moins une caméra")
    els = {}
    for eid, e in (d.get("elements") or {}).items():
        if eid in ids:
            els[eid] = {"x": _num(e["x"]), "y": _num(e["y"]), "angle": _num(e.get("angle", 0), -720, 720),
                        "visible": bool(e.get("visible", True))}
            if e.get("pose"):
                els[eid]["pose"] = str(e["pose"])[:40]
            if str(e.get("action", "")).strip():
                els[eid]["action"] = str(e["action"]).strip()[:200]
    clean = {"cameras": cams, "elements": els, "note": str(d.get("note", ""))[:2000]}
    with LOCK:
        plans = json.loads(PLANS.read_text(encoding="utf-8")) if PLANS.exists() else {}
        clean["rev"] = int(plans.get(plan_id, {}).get("rev", 0)) + 1
        clean["maj"] = now()
        plans[plan_id] = clean
        plans = dict(sorted(plans.items()))
        PLANS.write_text(json.dumps(plans, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        importlib.reload(draw_street_map)  # outils de dessin à jour sans redémarrer le serveur
        importlib.reload(calque)
        png = draw_street_map.render_plan(plan_id, lieux, plans, meta.get(plan_id))
        cq = png.with_name(f"{plan_id.lower()}-calque.png")
        calque.calque(plan_id).save(cq)
        build_a_valider.main()
    rel = lambda f: Path(f).relative_to(ROOT).as_posix()  # noqa: E731
    git_save(f"Carte interactive : placement {plan_id} (rév. {clean['rev']})",
             [rel(PLANS), rel(png), rel(png.with_suffix(".svg")), rel(cq), "docs/storyboard-a-valider.md"])
    return plans


class Handler(SimpleHTTPRequestHandler):
    # Types imposés : sous Windows, le registre peut annoncer de mauvais types (ex. .js en text/plain)
    extensions_map = {
        ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".mjs": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
        ".md": "text/markdown; charset=utf-8", ".txt": "text/plain; charset=utf-8",
        ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".mp3": "audio/mpeg", ".mp4": "video/mp4",
    }

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
        if self.path.startswith("/api/carte"):
            return self._json(200, carte_payload())
        if self.path.startswith("/api/manifest"):
            return self._json(200, json.loads(MANIFEST.read_text(encoding="utf-8")))
        return super().do_GET()

    def do_POST(self):
        if not self.path.startswith(("/api/avis", "/api/carte")):
            return self._json(404, {"erreur": "inconnu"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            if self.path.startswith("/api/carte"):
                return self._json(200, {"ok": True, "plans": save_carte(data)})
            man = apply(data)
            return self._json(200, {"ok": True, "manifest": man})
        except Exception as exc:
            return self._json(400, {"ok": False, "erreur": str(exc)})


class Serveur(ThreadingHTTPServer):
    # Sous Windows, SO_REUSEADDR laisserait démarrer un 2e serveur sur le même port (avis perdus) :
    # on le désactive pour obtenir une erreur claire à la place.
    allow_reuse_address = os.name != "nt"


def main():
    ap = argparse.ArgumentParser(description="Serveur de la page « storyboard à valider ».")
    ap.add_argument("port", nargs="?", type=int, default=8000, help="port (défaut 8000)")
    ap.add_argument("--host", default="0.0.0.0",
                    help="adresse d'écoute (défaut 0.0.0.0 ; 127.0.0.1 = visible seulement depuis cet ordinateur)")
    o = ap.parse_args()
    try:
        srv = Serveur((o.host, o.port), partial(Handler, directory=str(ROOT)))
    except OSError as exc:
        print(f"Impossible d'ouvrir le port {o.port} ({exc}).\n"
              f"Le serveur tourne peut-être déjà : ouvre http://localhost:{o.port}/storyboard/a-valider.html\n"
              f"Sinon choisis un autre port : python tools/serve_storyboard.py {o.port + 1}", flush=True)
        sys.exit(1)
    print(f"Storyboard à valider : http://localhost:{o.port}/storyboard/a-valider.html", flush=True)
    print(f"   carte interactive : http://localhost:{o.port}/storyboard/carte.html", flush=True)
    print(f"   (écoute sur {o.host}:{o.port} — Ctrl+C pour arrêter)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("Serveur arrêté.", flush=True)


if __name__ == "__main__":
    main()
