#!/usr/bin/env python3
"""Prépare l'environnement Python local du projet (Windows, macOS, Linux).

    python tools/setup_env.py            crée .venv si besoin, installe requirements.txt
    python tools/setup_env.py --rendu    ajoute les outils de rendu vidéo (requirements-render.txt)
    python tools/setup_env.py --forcer   réinstalle même si rien n'a changé

Rapide quand tout est déjà installé : l'installation n'est relancée que si un fichier de
dépendances a changé. Utilisé par la tâche VS Code « Préparer l'environnement Python ».
"""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
MARQUE = VENV / ".jeannot-dependances"
MINI = (3, 10)
VERIF = (
    "import sys, PIL, numpy, scipy, cv2, resvg_py, zoneinfo; zoneinfo.ZoneInfo('Europe/Paris'); "
    "print(f'  Python {sys.version.split()[0]} | Pillow {PIL.__version__} | numpy {numpy.__version__} | '"
    "f'scipy {scipy.__version__} | OpenCV {cv2.__version__} | resvg-py OK | fuseau Europe/Paris OK')"
)


def python_venv():
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def lancer(cmd, afficher=True):
    if afficher:
        print("  >", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.call([str(c) for c in cmd], cwd=ROOT)


def creer_venv():
    import venv
    print(f"Création de l'environnement {VENV.name} ...", flush=True)
    try:
        venv.EnvBuilder(with_pip=True).create(VENV)
    except Exception as exc:
        print(f"\nÉCHEC de la création de .venv : {exc}")
        if sys.platform.startswith("linux"):
            print("Sous Debian/Ubuntu, installe d'abord le module venv : sudo apt install python3-venv")
        shutil.rmtree(VENV, ignore_errors=True)
        return False
    return True


def verifier_git():
    git = shutil.which("git")
    if not git:
        print("ATTENTION : git est introuvable. Installe Git (https://git-scm.com) : le serveur en a "
              "besoin pour enregistrer et pousser les avis.")
        return
    for cle in ("user.name", "user.email"):
        r = subprocess.run([git, "config", cle], cwd=ROOT, capture_output=True, text=True)
        if not r.stdout.strip():
            print(f"ATTENTION : git {cle} n'est pas configuré ; les avis ne pourront pas être commités.\n"
                  f'  À faire une fois : git config --global {cle} "..."')


def main():
    args = set(sys.argv[1:])
    if sys.version_info < MINI:
        print(f"Python {sys.version.split()[0]} est trop ancien : il faut Python {MINI[0]}.{MINI[1]} ou plus "
              "récent (3.12 conseillé) — https://www.python.org/downloads/")
        return 1
    if not python_venv().exists() and not creer_venv():
        return 1
    py = python_venv()
    fichiers = [ROOT / "requirements.txt"] + ([ROOT / "requirements-render.txt"] if "--rendu" in args else [])
    empreinte = hashlib.sha256(b"".join(f.read_bytes() for f in fichiers)).hexdigest()
    deja = MARQUE.read_text(encoding="utf-8").split() if MARQUE.exists() else []
    if empreinte in deja and "--forcer" not in args:
        print("Dépendances déjà à jour dans .venv (rien à installer).")
    else:
        print("Installation des dépendances (quelques minutes la première fois) ...", flush=True)
        lancer([py, "-m", "pip", "install", "--disable-pip-version-check", "-q", "--upgrade", "pip"])
        cmd = [py, "-m", "pip", "install", "--disable-pip-version-check"]
        for f in fichiers:
            cmd += ["-r", f.relative_to(ROOT).as_posix()]
        if lancer(cmd) != 0:
            print("\nÉCHEC de l'installation des dépendances (voir les messages ci-dessus).")
            return 1
        MARQUE.write_text("\n".join(sorted(set(deja + [empreinte]))) + "\n", encoding="utf-8")
    print("Vérification :", flush=True)
    if lancer([py, "-c", VERIF], afficher=False) != 0:
        print("\nÉCHEC : un module ne se charge pas. Relance avec --forcer.")
        return 1
    verifier_git()
    print("\nEnvironnement prêt.\n"
          "  Serveur : tâche VS Code « Lancer le serveur storyboard », ou dans un terminal :\n"
          f"            {py.relative_to(ROOT)} tools/serve_storyboard.py 8000 --host 127.0.0.1\n"
          "  Page    : http://localhost:8000/storyboard/a-valider.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
