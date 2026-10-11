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
import draw_street_map  # noqa: E402

CARTE = ROOT / "assets/storyboards/a-valider/carte"
PLANS = CARTE / "plans.json"


def now():
    return datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d %H:%M")


def git_save(message, files=None):
    files = files or [str(MANIFEST.relative_to(ROOT)), "docs/storyboard-a-valider.md"]

    def run():
        with GIT_LOCK:
            try:
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
        png = draw_street_map.render_plan(plan_id, lieux, plans, meta.get(plan_id))
        build_a_valider.main()
    rel = lambda f: str(Path(f).relative_to(ROOT))  # noqa: E731
    git_save(f"Carte interactive : placement {plan_id} (rév. {clean['rev']})",
             [rel(PLANS), rel(png), rel(png.with_suffix(".svg")), "docs/storyboard-a-valider.md"])
    return plans


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


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = ThreadingHTTPServer(("0.0.0.0", port), partial(Handler, directory=str(ROOT)))
    print(f"Storyboard à valider : http://0.0.0.0:{port}/storyboard/a-valider.html", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
