#!/usr/bin/env python3
"""Génère la section « à valider » du storyboard à partir du manifeste.

Source unique : assets/storyboards/a-valider/options.json
Sorties :
  - docs/storyboard-a-valider.md  (lisible directement sur GitHub)
  - storyboard/a-valider.html     (page de comparaison côte à côte)

Usage : python3 tools/build_a_valider.py
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "assets/storyboards/a-valider/options.json"
MD_OUT = ROOT / "docs/storyboard-a-valider.md"
HTML_OUT = ROOT / "storyboard/a-valider.html"

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


def build_md(man):
    out = [
        "# Storyboard — options à valider",
        "",
        "Tri plan par plan. **Toutes les options sont conservées ici** (anciennes versions récupérées "
        "dans l'historique Git + nouvelles propositions), pour ne rien perdre si un fil plante.",
        "",
        "- Fichier source : [`assets/storyboards/a-valider/options.json`](../assets/storyboards/a-valider/options.json)",
        "- Page de comparaison : [`storyboard/a-valider.html`](../storyboard/a-valider.html)",
        "- Régénérer : `python3 tools/build_a_valider.py`",
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
        if p.get("notes"):
            out += [f"Notes : {p['notes']}", ""]
        for o in p["options"]:
            src = "../" + img_path(p["plan"], o["fichier"])
            out += [
                f"**{p['plan']} · {o['id']}** — {ETATS.get(o['etat'], o['etat'])} — {o['source']}  ",
                f"{o['note']}",
                "",
                f'<img src="{src}" width="640" alt="{p["plan"]} {o["id"]}">',
                "",
            ]
    return "\n".join(out) + "\n"


def build_html(man):
    e = html.escape
    cards = []
    for p in man["plans"]:
        opts = []
        for o in p["options"]:
            src = "../" + img_path(p["plan"], o["fichier"])
            opts.append(
                f'<figure class="opt {e(o["etat"])}"><a href="{e(src)}" target="_blank">'
                f'<img loading="lazy" src="{e(src)}" alt=""></a>'
                f'<figcaption><b>{e(o["id"])}</b> · {e(ETATS.get(o["etat"], o["etat"]))}<br>'
                f'<small>{e(o["source"])}</small><br>{e(o["note"])}</figcaption></figure>'
            )
        cards.append(
            f'<section id="{p["plan"].lower()}"><h2>{e(p["plan"])} <span>{e(p["temps"])}</span> '
            f'<em>{e(STATUTS.get(p["statut"], p["statut"]))}</em></h2>'
            f'<p class="lyr">{e(p["paroles"])}</p><p class="brief">{e(p["brief"])}</p>'
            f'<div class="grid">{"".join(opts)}</div></section>'
        )
    nav = " ".join(f'<a href="#{p["plan"].lower()}">{p["plan"][1:]}</a>' for p in man["plans"])
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jeannot slamrap — storyboard à valider</title>
<style>
:root{{color-scheme:dark;font-family:system-ui,sans-serif}}
body{{margin:0;background:#0b111c;color:#edf2f8}}
header{{position:sticky;top:0;background:#0b111cee;padding:10px 16px;border-bottom:1px solid #2a3647;z-index:2}}
header h1{{margin:0 0 6px;font-size:18px}} nav a{{color:#f2bf44;margin-right:8px;text-decoration:none;font-size:14px}}
main{{padding:8px 16px 60px;max-width:1700px;margin:auto}}
section{{border-bottom:1px solid #2a3647;padding:14px 0}}
h2{{margin:0;font-size:20px}} h2 span{{color:#8fa0b5;font-weight:400;font-size:15px}} h2 em{{font-size:14px;font-style:normal;margin-left:8px}}
.lyr{{color:#f2bf44;margin:6px 0}} .brief{{color:#b5c0cf;margin:0 0 10px;max-width:1100px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:12px}}
figure{{margin:0;background:#121a28;border:2px solid #2a3647;border-radius:8px;overflow:hidden}}
figure.retenue{{border-color:#3cb371}} figure.ecartee{{opacity:.45}} figure.a-retoucher{{border-color:#e0a030}}
figure img{{width:100%;display:block}} figcaption{{padding:8px;font-size:13px;color:#cbd5e1}} small{{color:#8fa0b5}}
</style></head><body>
<header><h1>Storyboard — options à valider</h1><nav>{nav}</nav></header>
<main>{"".join(cards)}</main></body></html>
"""


def main():
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for p in man["plans"]:
        for o in p["options"]:
            f = ROOT / img_path(p["plan"], o["fichier"])
            if not f.exists():
                raise SystemExit(f"Image manquante : {f}")
    MD_OUT.write_text(build_md(man), encoding="utf-8")
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(build_html(man), encoding="utf-8")
    n = sum(len(p["options"]) for p in man["plans"])
    print(f"{len(man['plans'])} plans, {n} options -> {MD_OUT.relative_to(ROOT)}, {HTML_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
