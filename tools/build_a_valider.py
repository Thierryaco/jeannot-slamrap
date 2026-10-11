#!/usr/bin/env python3
"""Génère la section « à valider » du storyboard à partir du manifeste.

Source unique : assets/storyboards/a-valider/options.json
Sorties :
  - docs/storyboard-a-valider.md  (lisible directement sur GitHub)
La page storyboard/a-valider.html lit directement le manifeste (JS) ; elle
permet d'ajouter des avis via tools/serve_storyboard.py.

Usage : python3 tools/build_a_valider.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "assets/storyboards/a-valider/options.json"
MD_OUT = ROOT / "docs/storyboard-a-valider.md"

STATUTS = {
    "a-valider": "⏳ À valider",
    "en-cours": "🛠️ En cours",
    "valide": "✅ Validé",
}
ETATS = {
    "a-valider": "⏳ à valider",
    "retenue": "✅ retenue",
    "ecartee": "❌ écartée",
    "a-retoucher": "🔁 à retoucher",
}


def img_path(plan, fichier):
    return f"assets/storyboards/a-valider/{plan.lower()}/{fichier}"


CARTE = ROOT / "assets/storyboards/a-valider/carte"


def carte_state():
    plans = json.loads((CARTE / "plans.json").read_text(encoding="utf-8")) if (CARTE / "plans.json").exists() else {}
    lieux = json.loads((CARTE / "lieux.json").read_text(encoding="utf-8"))
    return plans, lieux.get("rev", 1)


def badge(plan, o, plans, lrev):
    if not plan.startswith("P"):
        return ""
    cp = plans.get(plan)
    c = o.get("carte")
    if not c:
        return " · ⚪ faite sans carte du plan"
    if cp and c.get("plan_rev") == cp.get("rev") and c.get("lieux_rev") == lrev:
        return f" · 🟢 conforme à la carte actuelle (rév. {cp.get('rev')})"
    return f" · 🟠 faite d'après la carte rév. {c.get('plan_rev')} — la carte a changé depuis"


def build_md(man):
    plans, lrev = carte_state()
    out = [
        "# Storyboard — options à valider",
        "",
        "Tri plan par plan. **Toutes les options sont conservées ici** (anciennes versions récupérées "
        "dans l'historique Git + nouvelles propositions), pour ne rien perdre si un fil plante.",
        "",
        "- Fichier source : [`assets/storyboards/a-valider/options.json`](../assets/storyboards/a-valider/options.json)",
        "- Page de comparaison avec avis : lancer `python3 tools/serve_storyboard.py` puis ouvrir `/storyboard/a-valider.html`",
        "- Régénérer ce fichier : `python3 tools/build_a_valider.py`",
        "",
        "## Avancement",
        "",
        "| Plan | Temps | Statut | Options | Choix |",
        "|---|---:|---|---:|---|",
    ]
    for p in man["plans"]:
        out.append(
            f"| [{p['plan']}](#{p['plan'].lower()}) | {p['temps']} | {STATUTS.get(p['statut'], p['statut'])} "
            f"| {len(p['options'])} | {p.get('choix') or '—'} |"
        )
    out.append("")
    for p in man["plans"]:
        out += [
            f"## {p['plan']}",
            "",
            f"**{p['temps']}** · {p['paroles']} · {STATUTS.get(p['statut'], p['statut'])}"
            + (f" · choix : **{p['choix']}**" if p.get("choix") else ""),
            "",
            f"> {p['brief']}",
            "",
        ]
        cp = plans.get(p["plan"])
        if cp:
            out += [f"🗺️ Carte du plan (rév. {cp.get('rev')}, {cp.get('maj', '')}) :", "",
                    f'<img src="../assets/storyboards/a-valider/carte/plans/{p["plan"].lower()}.png" width="420" alt="carte {p["plan"]}">', ""]
        if p.get("notes"):
            out += [f"Notes : {p['notes']}", ""]
        if p.get("avis"):
            out += ["**Avis / idées sur le plan :**", ""]
            out += [f"- *{a['date']}* — {a['texte']}" for a in p["avis"]]
            out.append("")
        for o in p["options"]:
            src = "../" + img_path(p["plan"], o["fichier"])
            out += [
                f"**{p['plan']} · {o['id']}** — {ETATS.get(o['etat'], o['etat'])} — {o['source']}{badge(p['plan'], o, plans, lrev)}  ",
                f"{o['note']}",
                "",
                f'<img src="{src}" width="640" alt="{p["plan"]} {o["id"]}">',
                "",
            ]
            if o.get("avis"):
                out += [f"- 💬 *{a['date']}* — {a['texte']}" for a in o["avis"]]
                out.append("")
    return "\n".join(out) + "\n"


def main(html=False):  # html : ignoré (page JS statique)
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for p in man["plans"]:
        for o in p["options"]:
            f = ROOT / img_path(p["plan"], o["fichier"])
            if not f.exists():
                raise SystemExit(f"Image manquante : {f}")
    MD_OUT.write_text(build_md(man), encoding="utf-8")
    n = sum(len(p["options"]) for p in man["plans"])
    print(f"{len(man['plans'])} plans, {n} options -> {MD_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
