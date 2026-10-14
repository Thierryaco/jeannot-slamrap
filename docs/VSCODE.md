# Travailler en local avec VS Code

Ce guide permet de continuer le projet sur ton ordinateur (Windows, macOS ou Linux) avec
Visual Studio Code, avec **le même serveur « à valider »** que dans Arena : mêmes pages, mêmes avis,
même sauvegarde automatique sur GitHub.

---

## 1. À installer une seule fois

| Logiciel | Où le trouver | Attention |
|---|---|---|
| **Git** | <https://git-scm.com/downloads> | Windows : garder les options proposées par défaut. |
| **Python 3.12 ou plus récent** (3.10 minimum) | <https://www.python.org/downloads/> | Windows : cocher **« Add python.exe to PATH »** au début de l'installation. macOS : le Python fourni par Apple (3.9) est trop ancien, installer celui de python.org. |
| **VS Code** | <https://code.visualstudio.com> | — |

Puis, une seule fois, dans un terminal, donner ton identité à Git (le serveur signe chaque avis
avec elle) :

```bash
git config --global user.name "Ton nom"
git config --global user.email "ton-adresse@exemple.fr"
```

---

## 2. Récupérer le dépôt

**Dans VS Code :** `Ctrl+Maj+P` (`Cmd+Maj+P` sur Mac) → **« Git: Clone »** (« Git : Cloner » en
français) → coller `https://github.com/Thierryaco/jeannot-slamrap.git` → choisir un dossier →
**Ouvrir**.

**Ou dans un terminal :**

```bash
git clone https://github.com/Thierryaco/jeannot-slamrap.git
code jeannot-slamrap
```

Le dépôt pèse environ **360 Mo** (images et historique) : le premier téléchargement prend quelques
minutes. La branche à utiliser est **`main`** : elle contient tout.

---

## 3. Première ouverture du dossier

1. VS Code demande si tu fais confiance aux auteurs du dossier → **Oui** (sinon les tâches sont
   bloquées).
2. Il propose les **extensions recommandées** (Python, Pylance, Python Debugger) → **Installer**.
3. Il demande s'il peut **exécuter les tâches automatiques** de ce dossier → **Autoriser** : le
   serveur démarrera alors tout seul à chaque ouverture du dossier.
4. La première fois, la tâche **« Préparer l'environnement Python »** crée le dossier `.venv` et y
   installe les dépendances (2 à 3 minutes, environ 150 Mo). Les fois suivantes, elle est instantanée.
5. Si VS Code propose de sélectionner le nouvel environnement `.venv` → **Oui**.
   Sinon : `Ctrl+Maj+P` → **« Python: Select Interpreter »** → choisir celui qui contient `.venv`.

---

## 4. Le serveur et la page « à valider »

| | |
|---|---|
| Démarrage | automatique à l'ouverture du dossier, ou menu **Terminal → Exécuter la tâche… → « Lancer le serveur storyboard »** |
| Page « à valider » | <http://localhost:8000/storyboard/a-valider.html> : `Ctrl+clic` sur le lien affiché dans le terminal, ou tâche **« Ouvrir la page « à valider » »** |
| Carte interactive | <http://localhost:8000/storyboard/carte.html> (tâche **« Ouvrir la carte interactive »**) |
| Arrêt | icône corbeille du terminal du serveur, ou `Ctrl+C` dedans |

En local, le serveur n'écoute que sur `127.0.0.1` : la page n'est visible que depuis ton ordinateur.

Sans VS Code, depuis le dossier du dépôt (après la préparation de l'environnement) :

```bash
# Windows
.venv\Scripts\python tools\serve_storyboard.py 8000 --host 127.0.0.1
# macOS / Linux
.venv/bin/python tools/serve_storyboard.py 8000 --host 127.0.0.1
```

---

## 5. Avis, choix, carte : sauvegarde automatique

Comme dans Arena, chaque avis, choix, suppression ou placement sur la carte est écrit dans
`assets/storyboards/a-valider/options.json` (ou `carte/plans.json`). Le serveur fait ensuite **un
commit git et le pousse sur GitHub**, sur la branche en cours (`main`).

Il faut pour cela :
- l'identité Git du §1 ;
- l'accès à GitHub : VS Code (ou le gestionnaire d'identifiants de Git sous Windows) demande de se
  connecter au premier envoi.

Si l'envoi échoue (pas de réseau, par exemple), le commit reste sur ton ordinateur. Le terminal du
serveur affiche alors « commit fait mais push refusé », et le commit partira au prochain
**Synchroniser** (bouton de la vue « Contrôle de code source »).

---

## 6. Les outils

| Tâche VS Code | Rôle |
|---|---|
| Préparer l'environnement Python | crée `.venv` et installe `requirements.txt` ; à relancer si ce fichier change |
| Lancer le serveur storyboard | la page « à valider », la carte et les API (port 8000) |
| Ouvrir la page « à valider » / Ouvrir la carte interactive | ouvre le navigateur |
| **Contrôle obligatoire d'une retouche** | demande l'image de référence, l'image retouchée, les zones autorisées et le plan, puis affiche **CONFORME** ou **À REFAIRE**. La feuille de contrôle est écrite dans `_sorties/controle.jpg` |
| Régénérer docs/storyboard-a-valider.md | recrée le récapitulatif markdown depuis `options.json` |
| Installer aussi les outils de rendu vidéo (optionnel) | PyAV + ffmpeg pour les scripts `tools/render_*.py` |

**Scripts de retouche** (`tools/p01_v16.py` … `tools/p01_v21.py`) :
- avec le bouton ▷ de VS Code, sans argument, l'image produite va dans `_sorties/` (dossier ignoré
  par git) ;
- avec un chemin de sortie : `python tools/p01_v21.py _sorties/essai.png`, ou la configuration de
  débogage « Script Python ouvert, avec arguments » ;
- ils se lancent toujours **depuis la racine du dépôt** (les chemins des images sont relatifs à
  elle) ; VS Code est réglé pour le faire.

**Débogage (F5)** : la configuration « Serveur storyboard (débogage) » démarre le serveur sous le
débogueur et ouvre la page. Ne pas l'utiliser pendant que la tâche du serveur tourne : le port
8000 serait déjà pris.

---

## 7. Alterner entre VS Code et Arena

- **La référence est `main`.** Avant de travailler en local, **Synchroniser** pour récupérer ce qui
  a été fait ailleurs. VS Code vérifie régulièrement s'il y a du nouveau sur GitHub.
- Les avis donnés en local partent automatiquement sur `main`.
- Dans un nouveau fil Arena, le prompt de `docs/PROMPT-REPRISE.md` demande à l'agent de repartir
  de `main`.
- Le travail fait dans Arena arrive sur une branche `arena/…`. Pour le retrouver en local, il faut
  le fusionner dans `main` : demander à l'agent d'ouvrir et de fusionner une pull request.

---

## 8. En cas de problème

| Symptôme | Solution |
|---|---|
| `python3`, `python` ou `py` introuvable | installer Python (§1). Windows : cocher « Add python.exe to PATH » ou utiliser le lanceur `py`, puis redémarrer VS Code |
| « Impossible d'ouvrir le port 8000 » | le serveur tourne déjà (autre terminal, autre fenêtre) : ouvrir simplement la page. Sinon, remplacer `8000` dans `.vscode/tasks.json` |
| L'installation des dépendances échoue | version de Python trop ancienne ou trop récente : installer Python 3.12 ou 3.13, supprimer le dossier `.venv`, relancer « Préparer l'environnement Python » |
| L'environnement semble cassé | supprimer le dossier `.venv`, puis relancer « Préparer l'environnement Python » |
| Avis enregistré mais absent de GitHub | « commit fait mais push refusé » dans le terminal : **Synchroniser**, vérifier la connexion GitHub de VS Code |
| « Author identity unknown » | faire les deux `git config --global` du §1 |
| Le serveur ne démarre pas à l'ouverture | `Ctrl+Maj+P` → « Tasks: Manage Automatic Tasks » → autoriser, ou lancer la tâche à la main |
| macOS propose d'installer les « outils de ligne de commande » | installer plutôt Python depuis python.org (§1) |

---

## 9. Ce qui a été adapté pour le travail en local

- `requirements.txt` : les dépendances, plus `tzdata`, sans lequel le fuseau Europe/Paris des avis
  plante sous Windows.
- `tools/setup_env.py` : crée `.venv`, installe, vérifie. Rapide quand c'est déjà fait.
- `assets/fonts/` : les polices DejaVu utilisées par la carte et les calques, livrées avec le dépôt.
  Les images produites sont identiques au pixel près sur toutes les machines.
- `tools/serve_storyboard.py` :
  - option `--host` facultative (par défaut `0.0.0.0`, comme avant, pour Arena) ;
  - message clair si le port est déjà pris ;
  - types de fichiers imposés ;
  - erreurs git visibles dans le terminal.
- Scripts de retouche : sortie par défaut dans `_sorties/` au lieu de `/tmp/w` (qui n'existe pas
  sous Windows).
- `.gitattributes` (fins de ligne LF partout) et `.gitignore` (`.venv`, `_sorties`).
- `.vscode/` : réglages, tâches, configurations de débogage, extensions recommandées.
