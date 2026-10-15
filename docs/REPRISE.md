# REPRISE DU CHANTIER — lire ce fichier en premier

Document de passation rédigé le **13 octobre 2026**, mis à jour le **14 octobre 2026** (travail en
local sous VS Code, `main` devient la branche de référence). Il contient tout ce qu'il faut savoir
pour reprendre le travail sans rien perdre et sans refaire ce qui a déjà été fait.

---

## 1. Où est le travail

| | |
|---|---|
| Dépôt | `https://github.com/Thierryaco/jeannot-slamrap.git` |
| **Branche de référence** | **`main`** : elle contient tout |
| Travail en local | sous VS Code, voir [`docs/VSCODE.md`](VSCODE.md) ; les avis donnés en local sont commités et poussés directement sur `main` |
| Branches `arena/…` | une par fil Arena ; à fusionner dans `main` par pull request |
| État git | propre, tout est poussé |

Au début d'un nouveau fil Arena (qui ouvre sa propre branche), récupérer `main` **sans rien
écraser** :

```bash
git fetch -q origin
git merge origin/main     # avance la branche du fil jusqu'à main (ou fusionne si les deux ont avancé)
```

⚠️ **Ne plus faire `git reset --hard origin/arena/5ddf5758-jeannot-slamrap`** : cette branche est
ancienne. Revenir dessus effacerait les avis du 13 octobre au soir sur P01 v23 et la préparation
VS Code. Plus généralement, jamais de `reset --hard` vers une autre branche.

Pour que le travail fait dans Arena se retrouve en local, quand l'utilisateur le demande : pousser
la branche du fil, ouvrir une pull request vers `main` et la fusionner (`gh pr merge <numéro> --merge`).

---

## 2. 🚨 LE POINT BLOQUANT : je n'ai pas la vision

**C'est la priorité absolue.** Dans le fil précédent, l'agent ne pouvait pas voir les images.
Quand il ouvre un fichier image, il reçoit littéralement :

```
[An image was provided here, but you do not have vision capabilities.]
```

**Ce n'est pas un problème de fichier.** Tout a été vérifié :

- le fichier existe au bon endroit (`assets/storyboards/a-valider/p01/p01-v21-fume.png`,
  2 849 639 octets, PNG RGB 1920×1080, ouvert sans erreur par Pillow, suivi par git) ;
- le serveur répond 200 ;
- le test décisif : une image fabriquée à la main, **200×120 pixels, 693 octets**, un carré rouge
  et un rond bleu sur fond blanc → **toujours invisible**. Idem en JPEG, idem après redémarrage
  du serveur, idem sur un recadrage et sur un redimensionnement en 960×540.

**Conclusion : c'est une capacité du modèle utilisé par la session, pas un problème de dépôt.**
Confirmé le 14 octobre : dans un autre fil, le même test a réussi (carré rouge et rond bleu vus).

### Test à faire en 30 secondes au début de chaque nouveau fil

```bash
cd /home/user/jeannot-slamrap
python3 -c "
from PIL import Image, ImageDraw
im=Image.new('RGB',(200,120),'white'); d=ImageDraw.Draw(im)
d.rectangle([20,20,90,90],fill='red'); d.ellipse([110,30,180,100],fill='blue')
im.save('_test-vision.png')"
```

Puis ouvrir `/home/user/jeannot-slamrap/_test-vision.png`.

- **Si tu vois un carré rouge et un rond bleu** → la vision marche, annonce-le et travaille
  normalement en regardant les images. Supprime `_test-vision.png`.
- **Si tu vois le message « you do not have vision capabilities »** → dis-le immédiatement à
  l'utilisateur et **ne génère plus aucune image à l'aveugle**. Utilise uniquement l'outil
  « 📍 Pointer » (voir §7) pour obtenir les positions exactes, ou demande un changement de modèle.

**Règle posée par l'utilisateur :** « tant que tu ne vois rien, on ne fait rien ».
Ne pas produire de variantes au hasard en espérant tomber juste. Il préfère s'arrêter et
changer de fil plutôt que d'accumuler des versions fausses.

---

## 3. Démarrage obligatoire — À FAIRE SANS QU'ON TE LE DEMANDE

Le serveur doit être lancé **au tout début**, avant toute autre chose. Sans lui l'utilisateur
ne peut rien voir et ne peut rien valider.

```bash
# 1. se synchroniser sur main, sans rien écraser
cd /home/user/jeannot-slamrap
git fetch -q origin && git merge origin/main

# 2. réinstaller les dépendances (les réinitialisations de sandbox les effacent)
pip install --break-system-packages -r requirements.txt

# 3. lancer le serveur (outil start_process, PAS bash — il doit survivre au tour)
python3 tools/serve_storyboard.py 8000
```

- le port est un argument **positionnel** ; ne pas ajouter `--host` dans Arena (cette option ne sert
  qu'en local) ;
- il écoute par défaut sur `0.0.0.0` : l'aperçu est accessible à l'utilisateur ;
- vérifier ensuite : `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/storyboard/a-valider.html` → doit renvoyer `200` ;
- **ne jamais l'arrêter**, et le relancer immédiatement s'il est tombé.

Routes principales :

| Route | Contenu |
|---|---|
| `/storyboard/a-valider.html` | la page de validation (images, avis, zoom, pointage) |
| `/storyboard/carte.html` | la carte interactive de la rue |
| `/api/manifest` | le manifeste JSON (30 plans, 64 options) |
| `/api/carte` | les données de la carte |
| `/api/avis` | POST des avis (commit + push automatiques) |

**En local (VS Code)** : voir [`docs/VSCODE.md`](VSCODE.md). La tâche « Lancer le serveur
storyboard » prépare `.venv` (avec `tools/setup_env.py`), puis lance
`serve_storyboard.py 8000 --host 127.0.0.1`. Elle démarre seule à l'ouverture du dossier.

---

## 4. Le projet en bref

Clip d'animation 2D (cartoon burlesque) sur un MP3 de slam/rap de **1 min 44,36 s** (104,36 s).
Cible : 1920×1080, 16:9, animation en cels dessinés, 10–15 dessins distincts par seconde,
export 24 fps (sur deux quand le mouvement le permet), H.264/AAC 48 kHz.

**Personnages :** Jeannot (peintre ~50 ans, barbe grisonnante, chapeau jaune, combinaison bleue,
cigarette), sa 4L vert menthe pâle vieille et rouillée **mais intacte**, Henri (son frère, un peu
plus âgé, cheveux longs hirsutes, fines lunettes rectangulaires en métal gris, cigarette, sourire
niais mais gentil, dents abîmées sans gore), la sorcière (leur sœur, cheveux teints très noirs
ébouriffés, mascara marqué, cigarette, observe depuis sa tourelle), Diego « le rat » (plombier ~50
ans, visage rond, grand nez crochu, moustache noire épaisse, casquette et salopette bleues, conduit
une vieille Estafette), Marco (son fils, restaure une Coccinelle orange avec lui), Enji (vieux
bâtard croisé berger, museau grisonnant, gag visuel sans dialogue).

**Géographie :** une seule rue. Maison de Jeannot à une extrémité, le narrateur en face,
**Henri juste à côté de Jeannot du même côté**, la tourelle de la sorcière sur la maison de
Jeannot, Diego à l'autre bout toujours du côté de Jeannot. Le combat final traverse la rue.

**Références :** `docs/storyboard.md` (les 30 plans et les règles), `docs/storyboard-images.md`,
`assets/art/` (concepts de personnages), `assets/references/jeannot-4l-reference.png`.

---

## 5. Contraintes posées par l'utilisateur — À RESPECTER STRICTEMENT

Ces règles ont toutes été énoncées explicitement. Aucune ne doit être réinventée ni assouplie.

### Méthode

1. **Travailler plan par plan**, en proposant **plusieurs options** par plan (existantes ou
   nouvellement générées).
2. **Pousser toutes les options dans « à valider »**, y compris celles qui n'ont pas été choisies,
   et **pousser souvent** pour ne rien perdre.
3. L'utilisateur doit pouvoir **laisser un avis sur n'importe quelle option**, même une option
   déjà choisie, et une idée libre (« autre idée ») sur chaque plan.
4. **Travailler par petites étapes** et terminer en disant à l'utilisateur de taper **« continue »**.
   Les tours trop longs provoquent des erreurs de mémoire.
5. **Modifier uniquement la partie de l'image qui ne va pas.** Ne jamais recomposer ni redessiner
   l'image entière.
6. **Contrôle obligatoire** après chaque génération : le style, les couleurs, l'apparence des lieux
   et des personnages, et leurs positions doivent être respectés, sauf demande explicite contraire.
   Si le résultat n'est pas bon, **recommencer jusqu'à ce qu'il soit bon**.
7. **Chaque nouvelle version doit prendre en compte à la fois les modifications de la carte ET les
   avis du storyboard.**
8. Ne pas boucler : si l'utilisateur renvoie le même message, poser une question précise au lieu de
   répéter la même correction.

### Contenu et cohérence

9. La **4L est préférée vue de derrière**, comme sur la photo de référence, et **plus déglinguée /
   rouillée**. Elle reste intacte : aucun dégât lié à l'action.
10. **Style doux et propre de v7 / v8 / v13** : pas de grain, pas d'accentuation, **mais les
    éléments ne doivent pas devenir flous ou indéfinis**. Les ajouts doivent être **aussi nets que
    les autres éléments**.
11. **Ressemblance des personnages :** Henri doit ressembler à `assets/art/henri-character-v2.png`,
    Diego à `assets/art/diego-beetle-repair-concept-v2.png`. **Pour la tête d'Henri, la référence
    est la v1 du P08** (14/10 : *« Henri que l'on voit dans la V1 du P08 qui doit être la réf pour la
    tête d'Henri »*) : `assets/storyboards/a-valider/p08/p08-v1-ancien-fil.png`, tête recadrée dans
    `assets/storyboards/a-valider/p01/work/ref-tete-henri-p08-v1.png`. Longue tignasse gris foncé en
    mèches, visage maigre et allongé, front ridé, lunettes rectangulaires à monture sombre, grand nez,
    barbe de trois jours grise.
12. **Les images générées et les aperçus doivent correspondre au placement carte en vigueur du
    plan.** Respecter exactement les positions des véhicules.
13. **« Tu modifies la carte en fonction de l'image, pas l'inverse »**, sauf changement de carte
    explicitement demandé par l'utilisateur.
14. **Ne pas déplacer la caméra de P01 sans demander** : c'est l'utilisateur qui la place.
15. Les images **écartées sont masquées** par défaut dans la page « à valider ».
16. Un bouton de suppression retire une version **même de l'historique**. L'envoi d'avis doit
    fonctionner.
17. Dans l'éditeur de carte, la position d'un personnage est son **rond coloré avec sa lettre**,
    pas la poignée de rotation. La carte interactive doit permettre l'édition **même en zoomant**,
    et quitter la carte interactive ramène à la **dernière version du plan en cours**.
18. Le bouton 🗺️ **superpose la carte sur l'image** de la version ; il n'ouvre pas l'éditeur.

### Récit et interdits (détail dans `docs/storyboard.md`)

19. Aucune parole ni dialogue ajoutés. « BAM » et « CRAC » sont des effets graphiques, pas des
    paroles ni des sons.
20. Pas de gore. La peinture atteint la **Coccinelle de Marco, jamais la 4L**.
21. Une seule 4L, à un emplacement fixe le long du trottoir gauche devant chez Jeannot, nez vers le
    point de vue du narrateur. L'Estafette est un fourgon bleu-gris distinct. Pas de doublon de 4L.
22. La fumée de Jeannot est **un seul panache** animé, attaché à la cigarette.
23. La chute d'Henri est une suite de poses lisibles, **sans rotation globale du personnage**.
24. Le prototype Canvas (`animation/intro.html`) est écarté.

### Géographie validée

25. **Carte de la rue v2 : VALIDÉE.** Les versions CARTE v1 à v4 sont écartées.
26. **Garage avant la maison** (garage d'abord, maison au bout). L'Estafette devant la maison ;
    la vue du garage ouvert avec la Coccinelle doit être dégagée.
27. Garage : **avant l'Estafette**, la rue ne doit pas se terminer sur le garage, la Coccinelle
    doit être visible. Aligné au fond avec les autres maisons, ouverture alignée avec le début du
    trottoir / l'escalier d'Henri.
28. **Fin de rue :** un passage à niveau **ouvert** après l'Estafette de Diego, **rails visibles
    entre les deux barrières** ; ensuite la route descend à environ 45°, avec des collines au fond.
29. **Tourelle** sur le côté droit (est) de la maison de Jeannot, agrandie **sans empiéter sur le
    trottoir**.

---

## 6. Où sont les choses

```
README.md                          présentation du projet
docs/storyboard.md                 les 30 plans + toutes les règles de mise en scène
docs/storyboard-a-valider.md       page « à valider » en markdown (régénérée par build_a_valider.py)
docs/storyboard-images.md          historique des images
docs/REPRISE.md                    ← ce fichier
docs/PROMPT-REPRISE.md             ← le prompt à copier pour un nouveau fil
docs/VSCODE.md                     ← travailler en local avec VS Code (installation, serveur, tâches)
.vscode/                           tâches, débogage, réglages et extensions recommandées de VS Code
requirements.txt                   dépendances Python (requirements-render.txt : rendu vidéo, optionnel)
assets/fonts/                      polices DejaVu de la carte et des calques (rendu identique partout)
_sorties/                          sorties locales des scripts (ignoré par git)
storyboard/a-valider.html          la page de validation (visionneuse zoom, avis, 📍 Pointer)
storyboard/carte.html              la carte interactive de la rue
assets/storyboards/a-valider/options.json    TOUT l'état de validation (30 plans, 64 options, avis)
assets/storyboards/a-valider/p01/*.png       les 21 options de P01
assets/storyboards/a-valider/carte/lieux.json   lieux fixes de la rue — rév. 10
assets/storyboards/a-valider/carte/plans.json   placement par plan — P01 rév. 15, P03 rév. 1
assets/storyboards/a-valider/carte/plans/p01.svg, p03.svg
assets/art/                        concepts de personnages (références de dessin)
audio/jeannot-slamrap.mp3          la bande son (104,36 s)
tools/                             les scripts
```

### Les outils

| Outil | Commande | Rôle |
|---|---|---|
| `serve_storyboard.py` | `python3 tools/serve_storyboard.py 8000` | sert la page et les API, enregistre les avis (commit + push) ; `--host 127.0.0.1` en local |
| `setup_env.py` | `python tools/setup_env.py` | en local : crée `.venv`, installe `requirements.txt`, vérifie (instantané si déjà fait) |
| `chemins.py` | — | `sortie_par_defaut(nom)` : fichier dans `_sorties/` quand un script est lancé sans sortie |
| `build_a_valider.py` | `cd tools && PYTHONPATH=. python3 build_a_valider.py` | régénère `docs/storyboard-a-valider.md` depuis `options.json` |
| `draw_street_map.py` | — | dessine `carte-rue-vX.svg` depuis `lieux.json` / `plans.json` |
| `calque.py` | — | produit le calque carte ↔ image d'un plan |
| `controle_retouche.py` | voir ci-dessous | **contrôle obligatoire** après chaque retouche |
| `depot_fichiers.py` | `python3 tools/depot_fichiers.py 8001` (processus « Dépôt d'image ») | page où l'utilisateur dépose une image (glisser, cliquer ou Ctrl+V) : enregistrée dans `assets/storyboards/a-valider/<plan>/work/`, jamais par-dessus un fichier existant, puis commitée et poussée aussitôt. À utiliser quand une pièce jointe de la conversation n'arrive pas sur le disque |
| `p01_v16…p01_v33.py` | `PYTHONPATH=tools python3 tools/p01_v21.py OUT.png` | les retouches locales de P01, une par version (sans `OUT.png` : `_sorties/vNN.png`) ; à lancer depuis la racine du dépôt. Depuis le 14/10 : `p01_v24.py A\|B` (v24 / v25, à partir de la v20), `p01_v26.py` (à partir de la v24), `p01_v27.py` (à partir de la v26), `p01_v28.py` (à partir de la v27, sans IA), `p01_v29.py` (à partir de la v28 : Henri effacé des marches, puis recollé sur le palier), `p01_v30.py` (à partir de la v28, même effacement, Henri de `work/crop-v30-ed3.png` ; affiche la zone modifiée depuis la v29), `p01_v31.py` (même base, Henri de `work/crop-v31-ed1.png`, tête d'après P08 v1 ; affiche la zone modifiée depuis la v29), `p01_v32.py [OUT] [--capture CHEMIN]` (même base, Henri repris d'une capture d'écran recalée automatiquement, par défaut `work/ed5-capture.png`), `p01_v33.py` (la v32 ; collages de la v16 et de la v17 refaits sans l'ancien flou, autour de Diego) |
| `p02_v4.py` | `python3 tools/p02_v4.py [OUT] [--masques DOSSIER]` | P02 v4 = v3 + volant côté conducteur (retiré, intérieur reconstitué net, redessiné côté éloigné) + chaussée, trottoirs, bordures au gris de P01 (une surface = la même surface dans P01) + ciel bleu pâle ; sans IA ; affiche les zones du contrôle |
| `p02_v5.py` | `python3 tools/p02_v5.py [OUT]` | P02 v5 = v4 + plaque avant noire « 1_ 67 » (caractères fins, posés en perspective) + peinture à la teinte de la 4L de P01 + rouille brune de P01 + 16 taches/points ajoutés ; masques limités à la silhouette de la 4L, mélange en RVB ; sans IA ; affiche les zones du contrôle |
| `p02_v6.py` | `python3 tools/p02_v6.py [OUT]` | P02 v6 = v5 + Jeannot et Enji comme dans P01 : retouches IA sur recadrages (p02/work/v6-*), collage de la seule silhouette (GrabCut, union ancienne/nouvelle), Jeannot recoloré matière par matière sur celui de P01 (bleu, peau, bob, taches ; `CLARTE_P01` = 0,7) ; affiche les zones du contrôle |
| `p02_v7.py` | `python3 tools/p02_v7.py [OUT] [--seam IMG]` | P02 v7 = v6 + bout de chez Jeannot (IA recalée sur la 4L par ECC, coupe de coût minimal le long du mur de pierre, 4L par GrabCut + ouverture) + sol de la route (IA, masques du sol de p02_v4, Enji/Jeannot/bottes protégés) ; affiche les zones du contrôle |
| `p02_v8.py` | `python3 tools/p02_v8.py [OUT] [--coupes IMG]` | P02 v8 = v7 + ciel (colline abaissée, ciel de P01) + escalier tout droit (jardin en deux) : retouches IA collées par **coupe de graphe** (PyMaxflow) entre zones sûres IA / v7 ; Jeannot et la 4L protégés ; affiche les zones du contrôle |
| `p02_v9.py` | `python3 tools/p02_v9.py [OUT]` | P02 v9 = **v7** + lumière de plein jour : correction de couleur du décor matière par matière sur P01 (végétation, tons moyens, surfaces claires ; `CLARTE` par matière), sol, personnages, 4L et ciel protégés ; affiche la zone du contrôle |
| `p02_v10.py` | `python3 tools/p02_v10.py [OUT] [--coupes IMG]` | P02 v10 = v9 + colline haute (coin de ciel, bleu ramené à P01, vert à la v9) + jardin plat au niveau de la terrasse (haut mur, escalier tout droit) + pied du mur (ancien portail et pilier retirés, premières marches ; couleurs accordées pierres/trottoir) ; coupes de graphe ; affiche les zones du contrôle |

**Contrôle obligatoire** (sortie 0 = CONFORME) :

```bash
cd tools && PYTHONPATH=. python3 controle_retouche.py REF.png RESULTAT.png \
  --zones "x0,y0,x1,y1;x0,y0,x1,y1" --plan P01 [--palette ../assets/storyboards/a-valider/p01/p01-v33-net.png]
```

`--palette STYLE.png` (ajoutée le 14/10 pour P02 v6) : admet aussi les couleurs d'une image de référence de
style. À n'utiliser que quand l'utilisateur demande explicitement de reprendre les couleurs de cette image
(ex. « les persos comme dans P01 ») ; sans l'option, le contrôle est inchangé.

Critères : **hors zones** inchangé (écart moyen < 1,5), couleurs déjà présentes ≥ 90 %,
**netteté ≥ 0,80** (les ajouts ne doivent pas être plus flous que leurs voisins), bord < 28.

---

## 7. L'outil « 📍 Pointer » — la béquille quand il n'y a pas la vision

Implémenté dans `storyboard/a-valider.html` (commit `0bf0d3f`), testé avec jsdom.

**Pour l'utilisateur :** ouvrir une image dans la visionneuse (loupe 🔍), cliquer sur **📍 Pointer**,
cliquer sur l'image aux endroits voulus, nommer chaque point, puis
**« 📤 Envoyer ces pointages avec mon avis »**. Les coordonnées arrivent dans `options.json`
sous forme d'avis, via `POST /api/avis` (qui commite et pousse).

**Pour l'agent :** les avis contenant

```
📍 pointages sur l'image :
1. (762, 370) — pieds d'Henri
2. (814, 324) — haut des marches
```

donnent des coordonnées **en pixels de l'image affichée** (0,0 en haut à gauche ; 1920×1080 pour
P01), dans le repère naturel du PNG. Les utiliser directement, sans les re-projeter depuis la carte.

---

## 8. État plan par plan

30 plans, 64 options au total. Un seul plan est réellement en cours de fabrication : **P01**.
Les plans P04 à P29 n'ont qu'une option d'illustration, jamais retravaillée.

| Plan | Options | État | Remarque |
|---|---:|---|---|
| CARTE | 8 | v5–v8 en attente (v1–v4 écartées) | **v8 = carte rue courante** ; v2 de la géographie validée |
| **P01** | **21** | **en cours** | le plan le plus long, celui qui donne les bases du reste |
| P02 | 2 | à valider | jamais retravaillé |
| P03 | 2 | à valider | placement carte P03 rév. 1 fait |
| P04–P10 | 1 chacun | à valider | illustration initiale |
| P11, P12 | 2 et 3 | à valider | — |
| P13–P29 | 1 chacun | à valider | illustration initiale |

Aucun plan n'a encore d'option **validée**. Aucun plan autre que P01 n'a reçu d'avis.

---

## 9. P01 — où on en est exactement

**Brief :** plan général maître de la rue, 00:00–00:05, instrumental. La 4L vert menthe unique à
l'échelle au bord du trottoir gauche devant chez Jeannot ; l'Estafette bleu-gris plus loin du même
côté.

**Règle de l'utilisateur :** « le plus long étant celui-là qui donne les bases du reste, il faut
donc être assez précis et cohérent. » La zone de la maison de Jeannot est **arrêtée et correcte**.
**Seule la zone d'Henri est en travaux.**

### Historique

| Version | Fichier | Sort |
|---|---|---|
| v1–v3 | `p01-v1…v3-ancien-fil-*.png` | écartée |
| v4–v8 | `p01-v4…v8-nouveau.png` | écartée (géographie, passage à niveau, style) |
| v9 | `p01-v9-carte-rev1.png` | écartée |
| v10–v12 | carte rev2 / rev4 / style v8 | écartée ( Henri et Diego méconnaissables ) |
| **v13** | `p01-v13-montage-rev5.png` | écartée, mais **c'est l'image de base de tout ce qui suit** |
| v16 | `p01-v16-retouche-v13.png` | écartée |
| v17 | `p01-v17-retouche-v16.png` | écartée |
| v18 | `p01-v18-retouche-v17.png` | écartée le 14/10 |
| v19 | `p01-v19-retouche-v18.png` | écartée le 14/10 |
| v20 | `p01-v20-nette.png` | écartée le 14/10 — v19 reconstruite sans flou (Diego, caisse, Estafette, tourelle) ; base de la v24 à la v33 |
| v21–v23 | — | **supprimées par l'utilisateur le 14/10** (essais de hauteur d'Henri) |
| v24 | `p01-v24-sans-portail.png` | écartée le 14/10 — v20 sans le portail ni la clôture (`tools/p01_v24.py A`) |
| v25 | `p01-v25-porte.png` | à valider — v24 + porte ; liseré clair autour de l'encadrement → remplacée par la v27 |
| v26 | `p01-v26-rampe.png` | écartée le 14/10 — v24 + rampe couleur façade du garage + trait du bas en ligne droite |
| v27 | `p01-v27-porte.png` | écartée le 14/10 — v26 + porte dans le mur sous l'escalier |
| v28 | `p01-v28-trait.png` | écartée le 14/10 — v27 + un seul trait sous la rampe et sous le palier |
| v29 | `p01-v29-henri-palier.png` | écartée le 14/10 — v28 + Henri sur le palier, penché sur le muret, fumant ; tête droite, il regarde à l'horizontale (vers la façade) |
| v30 | `p01-v30-henri-regard.png` | écartée le 14/10 — v29 avec la tête d'Henri tournée et baissée vers le bas à gauche (il semble regarder le mur) |
| v31 | `p01-v31-tete-p08.png` | écartée le 14/10 — v29 avec la tête d'Henri refaite d'après P08 v1, visage de trois quarts face, yeux baissés vers la 4L |
| v32 | `p01-v32-ed5.png` | écartée le 14/10 après la v33 — v29 avec l'Henri de l'essai ed5 (le préféré de l'utilisateur), repris de sa capture d'écran ; avis : restes de flou autour de Diego |
| **v33** | `p01-v33-net.png` | **RETENUE le 14/10 à 15 h 11** — v32 sans les restes de flou de l'ancien contrôle autour de Diego (capot, outils, fond). **C'est l'image de P01** |

Le 14/10, l'utilisateur a écarté depuis la page, sans commentaire, la v25 à la v28 et la v30, et a
passé la v29 en « à retoucher ». Le contenu de la v26 à la v28 (rampe, porte, trait unique) reste
acquis : il avait dit « tout est bon », et il est repris dans la v29 et les suivantes.

Vers 14 h 37, il a passé la v32 en « à retoucher » et écarté toutes les autres options P01 (dont la v20,
la v24, la v29 et la v31). **La v32, avec l'Henri d'ed5, est donc la base retenue**, et la v33 la retouche.

**v14 et v15 ont été rejetées et supprimées.** Ne jamais les reconstituer.

### Ce qui a déjà été corrigé sur P01

- Estafette réelle avec logo Renault (losange chromé) comme celui de la 4L ;
- sorcière nette et agrandie, elle fume, fenêtre de la tourelle agrandie ;
- façade de la tourelle avec la même patine que la maison, toit et débord cohérents ;
- Diego à genou devant sa caisse à outils ; capot de la Coccinelle ouvert, outils au sol ;
- v20 : reconstruction nette de la v19 (Diego, caisse, Estafette, tourelle) — CONFORME.

### Les deux points qui étaient ouverts (FAITS, en attente d'avis)

**1. Henri sur son palier (Henri d'ed5, v32 → v33 RETENUE).**

Avis v19 de l'utilisateur : *« Henri aura une pose penchée appuyé sur le rebord du muret sur le
palier en haut de son escalier en train de fumer, le visage tourné vers la 4L. »*

- La version v21 d'origine (commit `ffadcc4`) a été **rejetée** : *« il lévite dans les airs au
  dessus de l'escalier en regardant la façade de la maison… ni sa tête ni sa position »*.
- **Cause trouvée :** j'avais appliqué un miroir (`retourner=True`) pour le tourner vers la 4L ;
  le miroir l'a retourné face à la façade. Et je l'avais collé à un point calculé depuis la carte
  (762, 370) alors que le palier n'est pas là visuellement → effet de lévitation.
- **Corrigé depuis :** plus de miroir (`retourner=False`), regard = celui de la v20 (vers la rue).
- **14/10 : les essais de hauteur v21, v22 et v23 ont été supprimés par l'utilisateur.** On repart
  de la v20, où Henri est debout à mi-escalier (pieds vers (728, 550)), pour le placer sur le palier.

  ⚠️ **La projection de la carte s'est révélée peu fiable dans cette zone.** Ne pas recalculer la
  position depuis la carte : regarder l'image, ou utiliser le pointage de l'utilisateur (§7).
- **v29 (14/10, vision active)** — `tools/p01_v29.py`, en deux étapes :
  1. **Henri effacé des marches, au pixel et sans IA.** Les marches sont des bandes horizontales :
     chaque rangée est recopiée depuis ce qui est visible à côté d'Henri, donc les nez de marche se
     raccordent forcément. Les bouts de marche cachés sont redessinés dans la suite des bouts visibles
     (… 737, 731,5, 726, 720,5, 715 … : −5,5 px par marche). Le mur est interpolé entre gauche et
     droite, la ligne de soubassement recopiée le long de sa pente. La main courante sous ses
     chaussures est recopiée le long de la sienne (−0,53 px par rangée), depuis les rangées 532 et 550.
  2. **Henri dessiné par IA** sur le recadrage (700, 270)–(900, 470) agrandi en 1024 px
     (`work/crop-v29-1024.png` → `work/crop-v29-ed6.png`). L'IA a laissé le fond intact (écart
     médian 3) : seule sa silhouette et sa fumée sont recollées, isolées par différence (seuil 20,
     trous bouchés ; fumée : seuil 8 dans sa zone), avec un bord adouci.
  - Position : tête et cheveux ≈ x 810–840, y 354–382 ; avant-bras sur le rebord du muret
    (≈ 815–840, 395–407) ; jambes cachées par le muret, pieds sur le palier vers (820, 442).
  - Zones de contrôle depuis la v28 : `709,424,747,551;798,352,848,412` (CONFORME ; netteté
    ×0,92 et ×1,19). Fumée ≤ (170,177,184).
- **Avis du 14/10 sur la v29 :** *« je préférais l'avant-dernière génération crop-v29-ed5.png, le
  regard et la tête d'Henri étaient mieux situés »*, puis *« tourné plus franchement vers la
  voiture »*. **ed5 est perdu** : il n'avait pas été commité avant une remise à zéro de la session.
  Dans la v29 (ed6), Henri a la tête droite et regarde à l'horizontale, donc vers la façade. Or la
  4L est au premier plan, en bas à gauche : il doit regarder **vers le bas et vers la gauche**, en
  trois-quarts face. Un profil pur vers la gauche le ferait regarder la façade, comme dans la v21
  refusée.
- **v30 (14/10)** — `tools/p01_v30.py` : même effacement des marches que la v29 (fonction
  `retirer_henri` importée), puis Henri redessiné par IA :
  - deux essais proposés au choix (consigne « tête vers le coin en bas à gauche ») : **aucun retenu
    par l'utilisateur**, et rien n'a été enregistré ;
  - `work/crop-v30-ed2.png` (consigne directe « vers la gauche, vers les marches ») : tourné vers
    la droite, écarté ;
  - **`work/crop-v30-ed3.png`, retenu** : recadrage de la v29 présenté **en miroir**
    (`work/crop-v30-1024-miroir.png`), consigne « il tourne la tête vers la droite et regarde les
    marches en bas à droite », résultat remis à l'endroit. Visage de trois quarts vers la gauche,
    regard vers le bas ; corps, cigarette et fumée conservés ;
  - `work/crop-v30-ed4-miroir.png` (« tête très penchée, regard plongeant ») : tête inclinée sur le
    côté, sourire grimaçant tourné vers nous, écarté.
  - Collage : silhouette isolée par différence avec l'escalier vide (`work/crop-v29-1024.png`,
    seuil 20). La fumée est isolée **par sa couleur** (gain de B − R > 12, morceaux ≥ 30 px) et
    non par simple différence : le fond rendu par l'IA diffère de 6 à 13 niveaux, ce qui faisait
    des taches autour du filet de fumée.
  - Zone modifiée depuis la v29 : 800,354,845,409. Contrôle avec la zone `796,350,849,413` :
    CONFORME (couleurs 99 %, netteté ×1,26, raccord 0,0). Fumée ≤ (165,176,190).
  - Position inchangée : tête ≈ x 805–840, y 354–385 ; pieds cachés vers (820, 442).
  - **Écartée par l'utilisateur.** Il a ensuite envoyé une capture d'écran d'ed5, perdue à son tour
    avec une remise à zéro (la pièce jointe n'était plus sur le disque), avec ce commentaire :
    *« ce qu'il avait de mieux c'était qu'il ne donnait pas l'impression de regarder le mur ou la
    porte mais bien en direction de la 4L, et il ressemble un peu plus à Henri que l'on voit dans la
    V1 du P08 qui doit être la réf pour la tête d'Henri »*. Sur la capture : Henri au bout droit du
    palier, avant-bras sur le muret, **visage de trois quarts face**, tête légèrement inclinée, yeux
    baissés vers l'avant et vers la gauche, petit sourire.
- **v31 (14/10)** — `tools/p01_v31.py`. Demande : *« continu mais base toi sur la v29 pour les
  modif »*.
  - Retouche IA de la **tête seule** sur le recadrage de la v29 **en miroir**
    (`work/crop-v30-1024-miroir.png`), avec `work/ref-tete-henri-p08-v1.png` comme deuxième image.
    Consigne : la tête de l'homme de la 2ᵉ image, visage tourné vers nous en trois-quarts face,
    penché, regard vers le bas et légèrement à droite, vers le premier plan, « pas vers le mur ni vers
    la porte », même taille, tout le reste identique.
  - Deux propositions ; l'utilisateur a choisi la 2 (`work/crop-v31-ed1-miroir.png`, 1600 px), remise
    à l'endroit dans `work/crop-v31-ed1.png`. La proposition 1 a été perdue : la session a été remise
    à zéro pendant le choix.
  - Le modèle a redessiné légèrement tous les contours du décor (7 % des pixels à plus de 20 niveaux,
    le long de tous les traits). On ne recolle donc que la silhouette d'Henri : plus grande
    composante de la différence avec l'escalier vide (`work/crop-v29-1024.png`, seuil 25, dans la
    zone x 440–820, y 380–740 du recadrage 1024). On y ajoute les mèches fines (gain de B − R > 12
    dans la zone des cheveux, en ne gardant que les morceaux qui touchent la tête) et la fumée (même
    critère, morceaux ≥ 30 px).
  - On part de `retirer_henri(v28)` : partout ailleurs qu'Henri, l'image est exactement la v29.
  - Zone modifiée depuis la v29 : 800,354,845,409. Contrôle avec la zone `796,350,849,413` :
    CONFORME (couleurs 100 %, netteté ×1,22, raccord 0,0). Le script redonne l'image au pixel près.
  - Position inchangée : tête et cheveux ≈ x 800–845, y 354–390 ; pieds cachés vers (820, 442).
- **v32 (14/10)** — `tools/p01_v32.py`. L'utilisateur demande *« une version avec l'intégration du
  screenshot que je t'ai envoyé »*. Renvoyée dans la conversation, la capture n'est jamais arrivée
  sur le disque. Il l'a déposée par la page de dépôt (`tools/depot_fichiers.py`) :
  `work/ed5-capture.png`, 474×481, commit `d9787b5`.
  - Recalage sur la vraie capture : 82 points retenus sur 136, échelle ×2,133, rotation 0,11°,
    décalage (9,8 ; −2,7), erreur médiane 1,40 px dans le recadrage 1024 (≈ 0,3 px dans l'image).
    ed5 avait redessiné le décor avec des couleurs plus vives : correction par canal (pente
    0,87–0,92, décalage 18–28).
  - Zone modifiée depuis la v29 : 793,349,849,413. Contrôle avec la zone `789,345,853,417` :
    CONFORME (couleurs 100 %, netteté ×1,02, raccord 0,0). Le script redonne l'image au pixel près.
  - Le script recale la capture sur `work/crop-v29-1024.png` (points SIFT, puis similitude par
    RANSAC sur le décor), corrige sa teinte (droite par canal sur le décor), isole Henri comme pour
    la v31 (seuil 22) et le recolle sur `retirer_henri(v28)`.
  - Testé sur une fausse capture tirée d'ed6 (474×482, recadrée, teinte décalée, JPEG) : échelle
    et décalage retrouvés (×2,105 ; (14, 6) ; erreur médiane 0,33 px), et le résultat retombe sur
    la v29. Contrôle avec la zone `796,350,849,413` : CONFORME, netteté ×1,00.
  - Vérifier au zoom la cigarette, un fin bâtonnet clair sur fond clair : un seuil trop fort la
    rogne.
  - **Avis du 14/10 sur la v32**, avec un pointage (866, 445) (860, 622) (1119, 625) (1112, 442) :
    *« verifie la zone intérieur des points 1 2 3 et 4 il y a des reste de flou de l'ancien
    controle »*. La zone couvre le garage de Diego, la Coccinelle, Diego et l'Estafette.
- **v33 (14/10)** — `tools/p01_v33.py`, sans IA. Les restes de flou venaient de deux collages
  adoucis à l'époque de l'ancien critère « grain » du contrôle, que la v20 n'avait pas refaits :
  - `p01_v16.py` : capot ouvert, compartiment moteur et outils au sol, collés avec un flou de 0,7
    (zones ≈ (894–976, 502–564) et (882–976, 578–610)) ;
  - `p01_v17.py` (repris par la v20) : Diego et sa caisse nets, mais tout le fond autour d'eux
    (clôture, piliers, haie) collé « doux comme v16 », avec un flou de 1,1 (polygone ≈ x 940–1028,
    y 496–612).
  - Méthode : la même chaîne (p01_v16 → Diego de p01_v17 → Estafette de p01_v18 → logo de
    p01_v19) est refaite deux fois. Avec les anciens flous, elle redonne la v20, donc la v32, à
    1 niveau près dans la zone. On la refait sans flou, et seuls les pixels qui diffèrent entre
    les deux sont remplacés dans la v32 : 10 635 pixels, dans 879,493,1032,616.
  - La v32 était identique à la v20 dans cette zone : de la v24 à la v32, les retouches
    s'arrêtent avant x 863.
  - Contrôle depuis la v32 avec la zone `876,490,1035,619` : CONFORME (couleurs 97 %, netteté
    ×1,05, raccord 0,0). Le script redonne l'image au pixel près. Au zoom, la clôture, les piliers,
    la haie, le moteur et les outils sont nets, sans couture aux bords des anciens collages.
  - **Retenue par l'utilisateur** le 14/10 à 15 h 11 (v32 écartée). Avis du 14/10 à 15 h 17 :
    *« C'est ok quand le storyboard sera terminé il faudra upscale l'image pour faire du 1080p en
    augmentant la qualité et les détails de l'image sans la changer . LA après avoir mis à jour la
    position d'henri sur la carte on peut passer à la P02 enfin , on se base évidant avec la P01
    pour la réf de l'image en tenant comptes des indications de la p02 pour la position des perso
    voiture et caméra »*. Carte recalée dans la foulée (rév. 15, §10).

**2. Le portail, la rampe et la porte (FAITS : v24 → v26 → v27 → v28, en attente d'avis).**

Avis v19 : *« Il y a comme un portail avec 2 piliers qui chevauche l'escalier d'Henri en dessous…
rajoute plutôt une porte directement sur la maison »*. Avis v20 (14/10) : *« retire moi le portail
avec la clôture qu'il y a sous l'escalier d'henri »*.

- **Vraie position, vue le 14/10 (la vision fonctionnait)** : deux piliers carrés à chapeau
  (x ≈ 775–833), un portillon en bois entre eux et un petit morceau de clôture à barreaux sur muret
  (x ≈ 833–848), de y ≈ 500 à 613, au pied de l'escalier, entre son muret et le garage.
- ⚠️ **L'ancienne « zone confirmée » x ≈ 706–782, y ≈ 317–425 était fausse** (calculée sans voir
  l'image) : c'est la **porte d'entrée de l'étage**, en haut de l'escalier. Ne pas y toucher.
- v24 : portail et clôture retirés (zone de contrôle `731,484,862,624`, CONFORME).
- v25 : v24 + porte dans le mur. Le contrôle est CONFORME, mais il reste un liseré clair autour de
  l'encadrement, et la porte est à cheval sur le pan gris côté garage. → Remplacée par la v27.
- **v26** (avis du 14/10 : *« tu donneras à la partie main courante (la rampe en béton couleur
  blanche) la même couleur et texture que la façade du garage. tu remplaceras le trait noir du bas en
  forme d'escalier par une ligne rectiligne »*) :
  - les dents de scie sont remplacées par une droite de (813, 449) à (765, 552), juste au-dessus du
    trait épais déjà droit, de (818, 452) à (771, 548) ;
  - les surfaces claires de la rampe (main courante, grande face, bande étroite, muret du palier,
    poteau du bas) prennent la couleur Lab de la façade du garage, mesurée sur son jambage et le
    dessus de sa porte (≈ 75 / 4 / 11,5), avec un léger grain ; les traits noirs ne bougent pas ;
  - zone de contrôle depuis la v24 : `719,391,846,607`.
- **v27** : v26 + porte en bois avec encadrement de pierre et marche (x 799–837, y 493–593),
  dessinée sur la v26 et recollée au ras de son contour. Le bord du pan gris passe de x 819 à x 830 ;
  au-dessus de la porte, le mur continue jusqu'au palier avec la teinte du coin de mur voisin.
  Zone de contrôle depuis la v26 : `795,449,841,597`.
- **v28** (réponse du 14/10 : *« je préfère un seul trait »*) : v27 retouchée au pixel, sans IA.
  - Sous la rampe, le trait fin, la bande claire et le trait épais deviennent un seul trait droit de
    2 px, de (818,3, 450,8) au pied de l'escalier (738, 602). Les teintes de face et de mur sont
    relevées ligne par ligne, avec leur grain.
  - L'ombre douce que le dessous de l'escalier porte sur le mur suit le nouveau trait : le profil du
    mur est décalé de l'écart entre l'ancien et le nouveau trait. Sans cela, il reste une bande claire.
  - Sous le palier, le dessin avait trois traits. Le trait supérieur (814,5, 440)→(841, 448) et le
    second trait horizontal y ≈ 453, avec leurs bandes claires, sont effacés. Seul le trait inférieur
    (819, 449)→(839, 453) est gardé. Le bord du pan gris (x 829–830) remonte jusqu'à lui.
  - Zone de contrôle depuis la v27 : `733,434,845,605` (CONFORME, netteté ×1,37 : la bande floue a
    disparu ; le cœur du nouveau trait, à 53, est plus doux que celui de la main courante, à 9–35).

### Repères numériques utiles sur P01 (image 1920×1080)

- Henri tel qu'il est dessiné dans la v20 : **pieds (728, 550), tête (728, 425)**.
- Dans le recadrage (620,400)–(900,680), la composante qui est Henri : x 713..739, y 426..559.
- Repère de la touche « pieds » utilisée par `tools/p01_v21.py` : `PIEDS=(762,370)` — **à remplacer
  par le pointage de l'utilisateur**.
- Constantes de `tools/p01_v21.py` : `BX,BY,BW = 620,400,280` ; `PENCHE=10.0` ;
  `VISAGE=(0.69,0.12)` ; `FUMEE=44` ; fumée dessinée au-dessus de (206,205,202).
- Signature actuelle : `build(pieds=PIEDS, pencer=PENCHE, retourner=False, fumer=True)` ;
  `pieds=None` signifie « Henri ne bouge pas, on ajoute seulement la cigarette et la fumée ».
- Zones de contrôle utilisées pour v20 → v21 : `705,415,750,570;750,205,800,380`, plus les zones
  validées de la v20 `262,140,505,472;1005,478,1130,592;936,494,1030,614`.

---

## 10. La carte

- `lieux.json` **rév. 10** : escalier d'Henri montant vers le fond, palier en haut devant l'entrée
  (calé sur l'image). Bâtiments : `maison-jeannot`, `maison-henri`, `voisin-n1`, `garage-diego`,
  `maison-diego`, `maison-narrateur`, `voisin-s1`, `voisin-s2`, `voisin-s3`, `voisins-s4`.
- `plans.json` : **P01 rév. 15**, **P03 rév. 1**. Caméra P01 : `x -89.7, y 518.8, angle -4.8,
  fov 32.9, portée 2000, œil 1.8, inclinaison -1.6`.
- `carte-rue-v8.png` est la carte rue courante. CARTE v1–v4 écartées, v5–v8 en attente.
- Repère carte : unités = pixels d'une carte 1600×1000, **100 px ≈ 3,7 m**. Angles : 0 = vers l'est
  (bout Diego), 90 = vers le sud (côté narrateur), −90 = vers le nord (côté Jeannot), 180 = vers
  l'ouest (bout Jeannot).
- Visionneuse : `VB0 = [-300, 0, 1900, 1000]` ; le PNG fait 2 px par unité de carte avec
  `ox = 1600 - naturalWidth/2`.

**Henri recalé sur la v33 (rév. 15, 14/10)** : `(985, 381)`, angle 174 (vers la 4L), pose « penché »,
sur le palier, accoudé au muret côté rue, vers le bout du palier. Sur le calque, il tombe à la bonne
place en largeur (boîte x ≈ 802–834, Henri dessiné x ≈ 800–845). La v33 est marquée conforme à la
rév. 15, puisque c'est la carte qui a été recalée sur elle.

- **Le palier reste à 2,8 m**, donc la vue caméra montre Henri ≈ 75 px plus haut que sur l'image
  (pieds y 367 au lieu de ≈ 442). Ce n'est pas une erreur de position. À cette distance (≈ 40 m),
  l'image dessine toute la maison plus petite que la caméra calée ne le prévoit. Le pied du mur tombe
  juste (y ≈ 596), mais, mesurées par cette caméra, la porte sous l'escalier ne ferait que 1,2 m,
  le palier 1,9 m et l'avant-toit 3,4 m. Baisser le palier à 1,9 m coincerait la porte sous
  l'escalier (v27), et la caméra, calée par moindres carrés, ne bouge pas sans l'accord de
  l'utilisateur. Les autres éléments lointains ont le même petit écart vertical (haut de Diego et de
  l'Estafette ≈ 20–30 px plus haut sur le calque que sur l'image).
- Méthode : le placement a été enregistré par `POST /api/carte`, comme depuis la page carte : il
  augmente la révision, redessine `plans/p01.png`, le `.svg` et le calque, puis commite. La carte
  affiche « pose · action » : l'action ne doit pas recommencer par la pose.


### P02 : carte rév. 2 et lieux rév. 11 (14/10, avis P02 v1 + note de la carte P02 rév. 1)

- **Lieux rév. 11** (`lieux.json`, ajouts en fin de liste — `_ou` utilise `batiments[0]`) :
  - `maison-fond` : « Maison du fond », parcelle nord-ouest (x −235…−20, y 125–245), en hauteur
    (`sol` 2,6 m = rez-de-chaussée surélevé) et en retrait, 6 m de haut (`haut`) ;
  - `garage-fond` : garage devant (x −120…−25, y 245–383), porte au sud sur le trottoir,
    `haut` 2,6 m, terrasse sur le toit (`terrasse`: true) ;
  - `jardin-fond` (type `terre_plein`) : jardin surélevé de 2,6 m à côté du garage, mur côté rue ;
  - `cul-de-sac` (type `grillage`) : grillage de 1,8 m sur toute la largeur en x −258 (y 110–860) ;
  - `colline-foret` (type `colline`) : colline boisée juste derrière, pente 35°, 30 m de haut.
  - Gérés par `draw_street_map.py`, `calque.py` et `carte.html` (vue de dessus et vue caméra).
  - Calques P01, P02 et P03 identiques au pixel près ; seules les vues de dessus changent.
  - **Carte générale CARTE v9** (`carte-rue-v9.png`, « à valider ») : la v8 + ces lieux ; le reste est
    identique à la v8 au pixel près. L'utilisateur a écarté les CARTE v5, v6 et v7 le 14/10.
- **Lieux rév. 12** (message de l'utilisateur, 14/10) : « élargir la maison jusqu'à la limite de la maison
  de Jeannot », « inverser le garage/terrasse avec le jardin », « un portail d'accès avec des escaliers qui
  montent à la maison, qui coupe le jardin en 2 ».
  - `maison-fond` x −235…160 (jusqu'à la parcelle de Jeannot) ; `garage-fond` x −235…−140 (à l'ouest) ;
    `jardin-fond-ouest` x −140…−10 et `jardin-fond-est` x 30…160 (2,6 m) ; `escalier-fond` x −10…30,
    y 245–383, `montee` nord, 2,6 m ; `portail-fond` en bas de l'escalier (y 383, x −14…34, 1,6 m).
  - Outils : escaliers `montee` nord/sud (vue de dessus, calque, vue caméra, hauteur des personnages),
    étiquette `etiquette` (défaut « escalier d'Henri »), type de détail `portail`.
  - Calques P01 et P03 identiques au pixel près ; P02 montre le garage à gauche de Jeannot et le portail
    juste à sa droite. **CARTE v10** « à valider » (seule la parcelle de la maison du fond change).
- **P02 rév. 2** (`POST /api/carte`, commit serveur d9d20e7) :
  - **Le miroir** : la v1 montre la 4L garée à gauche, Jeannot côté conducteur. La 4L reste à sa
    place de P01 (trottoir nord, avant vers l'est) : le même angle de vue sur la 4L donne donc la v1
    **en miroir** — 4L à droite, Jeannot à sa gauche, côté chaussée.
  - Caméra calée sur la v1 (coins de la 4L, toit, pieds de Jeannot, horizon), écarts ≤ 37 px :
    x 493, y 519,3, angle −163,9°, champ 41,6°, œil 1,2 m, inclinaison −1,4°, soit ≈ 5 m de l'avant
    de la 4L et 32° de biais côté chaussée. Portée 2000 pour que le fond reste net.
  - Jeannot (325,3 ; 481,1), angle 13, `appuyé` contre le flanc au niveau du montant central (les
    pieds de la v1) ; Enji (325,4 ; 495,2), angle 11, `couché`, à 0,5 m à gauche de ses pieds (vue
    caméra).
  - Contrôle : `assets/storyboards/a-valider/p02/work/p02-carte-rev2-sur-v1-miroir.jpg` (calque sur
    la v1 en miroir, puis seul sur fond gris).

---

## 11. Ce qu'il reste à faire, dans l'ordre

1. **Résoudre la vision** (§2) — priorité absolue, décidé par l'utilisateur.
2. **P01 — image : FAIT.** Le 14/10 à 15 h 11, l'utilisateur a passé la **v33 en « retenue »**
   (portail retiré, rampe couleur façade, trait unique, porte, Henri d'ed5 sur le palier, plus de
   flou autour de Diego) et la v32 en « écartée ». Toutes les autres options P01 sont écartées.
   Le seul commentaire de la v32 (zone 1-2-3-4) est traité par la v33 : les autres flous des anciens
   scripts sont hors de la zone (fenêtre de la sorcière, `p01_v17.FLOU`) ou déjà retirés en v20
   (Estafette, `estafette(flou=0)`).
3. **P01 — carte : FAIT** (rév. 15, Henri recalé sur la v33, §10). **P01 est validé** : image v33
   + carte rév. 15. C'est l'image de référence du clip.
4. **P02 — EN COURS** (avis v33, avis P02 v1) : partir de la v33 de P01 comme référence d'image
   (mêmes lieux, même style, mêmes personnages), en suivant les indications de P02 pour la position
   des personnages, de la voiture et de la caméra.
   - **Carte : FAIT** (P02 rév. 2 + lieux rév. 11, §10).
   - **Images : EN COURS** — composition de la v1 en miroir (4L à droite, Jeannot adossé à sa gauche
     avec sa cigarette), Enji couchée à gauche de ses pieds ; au fond la maison en hauteur, le garage
     avec la terrasse, le jardin coupé par l'escalier du portail, le grillage du cul-de-sac et la
     colline boisée assez raide. Toutes les options vont dans « à valider » ; ensuite la carte suit
     l'image.
   - **v3** (`p02-v3-cul-de-sac.png`, « à valider », carte rév. 2 / lieux rév. 12) : IA, choisie par
     l'utilisateur parmi 2 ; brut `p02/work/p02-essai-1.png` (2784×1504, recadré x 80–2754 puis
     1920×1080). Défauts repérés : volant du côté proche (conduite à droite — une 4L française l'a de
     l'autre côté, donc sur la moitié droite du pare-brise ici) ; couleurs plus beiges que P01 (route
     beige, peu de ciel). Prochaine étape proposée : v4 = v3 avec le volant du bon côté (retouche
     locale + contrôle) et, si l'utilisateur le veut, couleurs rapprochées de P01.
   - **Avis du 14/10 sur la v3** : « plein d'inconstance dans le style par rapport à la P01 » (personnages
     pas exactement les mêmes, textures, route, bout de la maison de Jeannot, plaque, texture et état de
     la 4L) ; « tu listeras tout ça » ; corriger **2 par 2, pas plus** (sinon ça bugge).
   - **v4** (`p02-v4-volant-couleurs.png`, `tools/p02_v4.py`, contrôle CONFORME : hors zones 0,00 ;
     volant ×0,88 ; sol ×0,94 ; ciel ×1,00) = paire 1 faite. Le ciel n'a pu passer qu'au bleu pâle : le
     bleu franc de P01 n'existe pas dans la v3 et le critère « couleurs déjà dans l'image » le refuse.
     Corrigée après une réinitialisation (avant de la montrer) : le masque des bordures avait grisé la tache
     claire du genou gauche de Jeannot (x 1001–1022, y 664–699, 421 px) ; `p02_v4.py` retire désormais
     les morceaux de surface isolés dans la boîte de Jeannot. Vérifié : rien ne change dans la jambe,
     le script reproduit l'image, contrôle CONFORME.
   - **v5** (`p02-v5-plaque-rouille.png`, `tools/p02_v5.py`, contrôle CONFORME : hors zones 0,00 ;
     carrosserie couleurs 98 %, netteté ×1,40 ; arrière de la 4L derrière Jeannot 96 %, ×1,75) = paire 2
     faite (points 3 et 4), à partir de la v4. Mesures : la peinture de P01 n'est pas plus pâle mais plus
     jaune et plus sourde (RVB médian 158,171,135 contre 164,190,158) ; la rouille de P01 est plus sombre
     (141,74,42). Les tons rouille sombres de P01 n'existent pas dans la v4 : taches en tons bruns/ocre
     déjà présents (152,104,72 · 136,88,56 · 112,68,42). Les taches orangé-rouge faisaient « éclaboussure »
     (risque de lecture « sang ») : écartées. Changements limités à la carrosserie et à la plaque (vérifié
     sur la carte des pixels changés : 0 pixel de Jeannot, du mur, des vitres, de la route).
   - **v6** (`p02-v6-jeannot-enji.png`, `tools/p02_v6.py`, contrôle avec `--palette` P01 v33 CONFORME :
     hors zones 0,00 ; Enji couleurs 100 %, netteté ×1,35 ; Jeannot couleurs 100 %, netteté ×0,82) = paire 3
     faite (points 5 et 6), à partir de la v5. Retouches IA sur recadrages ×2 (Jeannot donné retourné pour
     être orienté comme son modèle de P01) ; 1er essai Jeannot écarté (bleu roi, grosses étoiles, cheveux
     gris). Silhouettes par GrabCut ; Jeannot recoloré sur celui de P01 (teinte et saturation, clarté à 70 %).
     Vérifié : seuls 2 blocs changent (Enji x 434–998, y 682–1033 ; Jeannot x 983–1199, y 261–911), 0 pixel
     sur la 4L, le mur, l'escalier, la route ; bottes de la v5 gardées, jonction propre aux chevilles.
   - **v7** (`p02-v7-maison-route.png`, `tools/p02_v7.py`, contrôle CONFORME : hors zones 0,00 ; maison
     couleurs 99 %, netteté ×1,43 ; route 100 %, ×1,83) = paire 4 faite (points 7 et 8), à partir de la v6.
     Retouches IA faites par une tentative interrompue (commit c5a042b, recadrages retrouvés par
     corrélation : maison x 1100–1920, y 0–615 retourné ×1,5 ; route x 0–1020, y 400–1080 ×1,5). L'IA maison
     avait recadré plus large (échelle 0,70) : recalage ECC sur la 4L et rééchantillonnage direct (1 px v6 ≈
     1,02 px IA). Vérifié : 0 pixel changé sur la 4L, Enji, Jeannot et ses bottes ; pas de liseré.
   - **v8** (`p02-v8-ciel-escalier.png`, `tools/p02_v8.py`, contrôle `--palette` P01 CONFORME : hors zones
     0,00 ; ciel 100 %, ×1,08 ; escalier 95 %, ×0,98) = points 11 et 12, à partir de la v7. Retouches IA
     (ciel x 0–1067, y 0–600 ; escalier x 620–1508, y 0–500 ; ×1,5, déjà alignées) collées par coupe de
     graphe. Corrigé en cours de route : cran d'ancienne colline à gauche du toit (bord du toit mesuré :
     x 994 → 962, façade x 976) ; ancienne colline entre les barreaux de la rambarde (la rambarde vient
     de l'IA, limite au haut de la dalle y ≈ 198). Vérifié : 0 pixel changé sur Jeannot, la 4L et sous
     y 480. Le bas de l'escalier (à droite du portail) est caché par Jeannot.
   - **v9** (`p02-v9-lumiere.png`, `tools/p02_v9.py`, contrôle `--palette` P01 CONFORME : couleurs 100 %,
     netteté ×1,07) = point 10, à partir de la **v7**. Mesures du décor (Lab médian, v7 → P01) : végétation
     a −7 → −10, b +15 → +12 ; tons moyens b +12 → +5, L 117 → 127 ; surfaces claires L 224 → 183 (non
     suivi : assombrir irait contre le plein jour). 0 pixel changé sur le sol, les personnages, la 4L.
   - **v10** (`p02-v10-colline-jardin.png`, `tools/p02_v10.py`, contrôle `--palette` P01 CONFORME : colline
     98 %, ×1,75 ; jardin 94 %, ×1,23 ; pied du mur 100 %, ×1,45), à partir de la v9. Faite en plusieurs
     tentatives interrompues (commits 3f3f58b → d382452) puis terminée : recadrages de la v9 (colline
     x 0–1067, y 0–600 ; jardin x 620–1508, y 0–500 ; ×1,5) et de la composition (pied x 620–1260,
     y 330–690 ×2). Corrigés au collage : ciel trop saturé (cyan) → bleu de P01 ; pierres du pied plus
     jaunes → accordées au mur ; trottoir du pied → accordé au trottoir (un accord unique calculé sur les
     pierres assombrissait le gris). 0 pixel changé sur Jeannot, Enji, la 4L et sous y 565.
   - **Grillage du trottoir de gauche (point 13)** : l'utilisateur le **garde** (14/10). La carte l'ajoutera
     quand elle suivra l'image retenue (le long du terrain vide sud-ouest).
   - **Liste des correctifs P02** (à faire dans l'ordre, une paire par version, base = dernière version) :
     1. ✅ volant du côté proche (conduite à droite) → côté conducteur (v4) ;
     2. ✅ route, trottoirs, bordures beiges → gris de P01 ; ciel gris-vert → bleu pâle (v4) ;
     3. ✅ 4L — plaque avant vide → plaque noire à caractères blancs comme l'arrière dans P01 (« 1_ 67 ») (v5) ;
     4. ✅ 4L — peinture à la teinte de P01 (vert amande plus jaune et plus sourd) et rouille en taches et
        points bruns comme P01, même état « rouillée mais intacte » (v5) ;
     5. ✅ Jeannot comme dans P01 : barbe poivre et sel, cheveux sombres et bouclés, cordon, bob jaune doré,
        bleu cobalt avec taches de peinture jaune-ocre (v6) ;
     6. ✅ Enji comme dans P01 / sa fiche : même pelage et mêmes marques, dessin plus simple (v6) ;
     7. ✅ bout de la maison de Jeannot (bord droit) : comme P01, haut mur de jardin crème le long du
        trottoir et maison en retrait (crépi crème, fenêtres à encadrement blanc) au lieu du pignon aveugle (v7) ;
     8. ✅ route : dessin comme P01 (asphalte lisse, caniveau, bordures claires) (v7) ;
     9. textures et trait comme P01 (trait net et régulier, aplats doux) — ici trait fin, hachures,
        textures dessinées (pierres, crépi, arbres) ;
     10. ✅ lumière : plein jour comme P01 (v9 = v7 + correction de couleur du décor) ;
     11. ✅ colline : la v8 l'avait **beaucoup trop abaissée** (avis du 15/10) → v10 : colline haute, coin de ciel
         bleu pâle en haut à gauche seulement ;
     12. ✅ jardin **plat au niveau de la terrasse, juste un poil plus bas** (avis du 15/10 : « le jardin qui fait
         colline ») tenu par un haut mur de soutènement ; escalier tout droit depuis le trottoir jusqu'à la porte,
         jardin coupé en deux (v10). ⚠️ plus de portail (l'ancien, coincé sous le nouveau mur, a été retiré) — à
         rajouter au pied de l'escalier si l'utilisateur le veut ;
     13. ✅ grillage le long du trottoir de gauche (côté narrateur) : **gardé** (réponse du 14/10) ; la carte
         l'ajoutera quand elle suivra l'image retenue.
     14/10 21:30 : l'utilisateur a mis la **v7 « à retoucher »** et la **v8 « écartée »** ; v9 = v7 + lumière
     (point 10). 15/10, avis sur la v8 : « la colline était beaucoup trop basse il va falloir rectifier — le
     jardin qui fait colline alors qu'il est au même niveau que la terrasse juste un poil plus bas » → v10.
     Reste le **point 9** (trait et textures, toute l'image) et, si l'utilisateur le veut, le portail.
     15/10 : passe de style IA sur toute la v10 d'après P01 (2 propositions) → **aucune retenue** par
     l'utilisateur (« continu ») : ne pas la refaire sur toute l'image. Point 9 fait **zone par zone, 2 par
     2** (colline boisée + haut mur de pierre d'abord, puis murs crépis), Jeannot, Enji et la 4L intacts.
     Les points 9 et 10 touchent toute l'image : retouche globale ou nouvelle génération guidée par P01 —
     à décider avec l'utilisateur quand on y arrivera.
5. **Cohérence P03**, puis P04 → P29.
6. **À la toute fin du storyboard** (avis v33) : agrandir toutes les images retenues pour faire du
   vrai 1080p, en augmentant la qualité et les détails **sans changer l'image**.

---

## 12. Pièges déjà rencontrés — ne pas les refaire

- **Restes de flou de l'ancien contrôle** : avant la v20, le critère « grain » du contrôle (retiré)
  faisait adoucir les collages (`FLOU`, `flou_diego`, fond « doux comme v16 », etc.). Quand
  l'utilisateur signale du flou, chercher d'abord ces adoucissements dans les scripts `p01_v16` à
  `p01_v19`. Pour corriger, refaire la chaîne sans flou et ne remplacer que les pixels qui changent
  (méthode de la v33), après avoir vérifié que la chaîne, avec les anciens flous, redonne bien
  l'image actuelle.
- **Garder TOUS les essais IA** dans `work/`, y compris ceux qu'on écarte, et les commiter tout de
  suite. L'utilisateur peut en préférer un : `crop-v29-ed5.png`, son préféré, a été perdu avec une
  remise à zéro de la session parce qu'il n'avait pas été commité. Quand l'utilisateur ne choisit
  aucune des deux images proposées au choix, rien n'est enregistré.
  - **Commiter et pousser juste après chaque choix d'image** : en v31, la session a été remise à
    zéro pendant que l'utilisateur choisissait. Seule l'image retenue a survécu ; l'autre
    proposition a été perdue.
  - **Les pièces jointes de l'utilisateur disparaissent aussi** aux remises à zéro : sa capture
    d'ed5 n'était plus dans `/home/user/uploads/`. Copier tout de suite une pièce jointe utile dans
    le dépôt et la commiter.
  - **Pire : une pièce jointe peut ne jamais arriver sur le disque**, même sans remise à zéro. Le
    14/10, la capture renvoyée était visible dans la conversation, mais `/home/user/uploads/`
    n'existait pas. Parade : lancer `tools/depot_fichiers.py 8001` et demander à l'utilisateur de
    déposer le fichier dans l'aperçu « Dépôt d'image ». Le fichier est commité et poussé tout seul.
- **Pour qu'un personnage regarde un objet du premier plan** (la 4L, plus près de nous qu'Henri) :
  visage de **trois quarts face**, yeux baissés vers l'avant. Un regard vers le bas du recadrage,
  c'est le mur et l'escalier (v30 écartée : *« impression de regarder le mur ou la porte »*).
- **Même avec « tout le reste identique », l'IA redessine légèrement tous les contours du décor**
  (v31 : 7 % des pixels à plus de 20 niveaux) : ne recoller que la silhouette du personnage. Pour
  des cheveux gris sur brique ou crépi, ajouter les mèches fines par leur teinte gris bleuté (gain de
  B − R > 12), en ne gardant que les morceaux qui touchent la tête.
- **Faire tourner un personnage vers la gauche avec l'IA** (v29, v30) : elle le tourne vers la droite
  même quand on écrit « gauche » en toutes lettres (encore le cas pour `work/crop-v30-ed2.png`).
  Deux parades ont marché :
  - v29 : obtenir d'abord un Henri dans le bon sens (essai sur le recadrage en miroir, puis remis à
    l'endroit : `work/henri-pose-v29.png`) et le donner comme **modèle de pose** à l'IA sur le vrai
    recadrage ;
  - v30, plus simple : donner le **recadrage en miroir** avec une consigne courte et « modifie
    seulement sa tête… tout le reste identique », demander qu'il regarde vers la droite, puis
    **remettre le résultat à l'endroit**. Le fond n'a bougé que de 6 à 13 niveaux, sans
    recomposition. Donner une cible visible dans le recadrage (« les marches en bas à droite »)
    plutôt qu'un objet hors champ.
- **Trop insister sur « tête très penchée, regard plongeant »** (v30, ed4) : l'IA incline la tête sur
  le côté, avec un sourire grimaçant tourné vers nous. Il vaut mieux demander une tête tournée et
  baissée, en trois-quarts face.
- **Ne jamais citer un objet hors champ dans un prompt** (« il regarde une voiture garée en bas à
  gauche ») : l'IA recompose toute la scène et dessine la voiture. En v29, un essai sur l'image en
  miroir a aussi été recomposé (`work/crop-v29-ed4-miroir.png`, inutilisable pour un collage). En
  v30, avec une consigne courte qui ne cite rien hors champ, le miroir a marché (voir plus haut).
- **Ne pas retourner un personnage accoudé** pour changer son regard : ses avant-bras suivent un
  rebord incliné (pente ≈ 0,35 sur P01), qui ne correspond plus une fois retourné.

- **Ne pas tenter de « voir » une image** en insistant : le test de 30 s (§2) suffit.
- **Le miroir retourne tout le personnage** : pour tourner Henri, ne pas utiliser
  `FLIP_LEFT_RIGHT` sans recalculer les pivots avec `(BW-1)-x` ; et surtout vérifier le sens final
  du regard avant de livrer.
- **Un masque de différence entre une retouche et sa base n'est pas un seul objet** : toujours
  étiqueter les composantes connexes et ne garder que celle voulue.
- **Coller une retouche sans la renforcer fait échouer le contrôle** (netteté ×0,78 < 0,80) :
  appliquer `UnsharpMask(1.4, 60, 0)` avant le collage, et calculer le masque de différence sur
  l'image **non renforcée**.
- `np.linspace(0,1,sm.shape[0])[...,None]` ne se diffuse pas sur un masque (H,W,1) → construire le
  fondu dans la géométrie dessinée.
- **Signe de rotation :** la bouche a besoin de `R` construit avec `+pencer` alors que PIL utilise
  `rotate(-pencer)`.
- **Une fumée au-dessus de (234,233,230) est invisible** sur ces murs ; utiliser (206,205,202).
- **jsdom n'a pas le pointer capture** : `Element.prototype.setPointerCapture` doit être simulé
  dans `beforeParse`, sinon le gestionnaire `pointerdown` lève une erreur et aucun point n'est
  enregistré.
- **Les réinitialisations de sandbox effacent aussi les paquets pip** :
  `pip install --break-system-packages -r requirements.txt` fait partie de la séquence de
  redémarrage.
- **Le code doit tourner aussi sous Windows et macOS** (travail en local) :
  - pas de chemin `/usr/share/fonts/...` en dur : utiliser `draw_street_map.FONT` / `FONT_B`
    (polices de `assets/fonts/`) ;
  - pas de `/tmp/...` en dur : utiliser `chemins.sortie_par_defaut(nom)` (dossier `_sorties/`) ;
  - toujours `encoding="utf-8"` pour lire ou écrire un fichier texte (Windows lit sinon en cp1252) ;
  - chemins passés à git en `as_posix()`.
- **Ne jamais revenir en arrière par `git reset --hard` vers une ancienne branche** : se
  synchroniser avec `git merge origin/main`.
- **Pas d'avis en même temps dans Arena et en local** : les deux modifient `options.json` sur des
  branches différentes, et il faudrait ensuite fusionner à la main.
- **Ne pas recalculer une position depuis la carte dans la zone d'Henri** : la projection s'est
  révélée fausse d'environ 180 px en hauteur.

- Le serveur garde `draw_street_map` et `calque` en mémoire. Depuis ef6ce94, il les recharge à
  chaque enregistrement de la carte ; toute autre modification de `serve_storyboard.py` demande un
  redémarrage (le relancer aussitôt).

- Après tout changement des lieux, générer aussi la carte générale (`python3 tools/draw_street_map.py
  base vN`) et l'ajouter comme option « à valider » du plan CARTE dans `options.json` : sinon
  l'utilisateur ne voit pas les nouveaux lieux dans la page « à valider » (oubli du 14/10).

- `generate_image` avec `offer_options` : seule l'image choisie par l'utilisateur est enregistrée ;
  l'autre ne l'est nulle part (pas de dossier « Unselected files ») et ne peut donc pas aller dans
  « à valider ». Le dire à l'utilisateur.

- Une zone de contrôle très large (ex. tout le sol) laisse passer une fuite de masque sur un personnage
  (P02 v4 : tache du genou de Jeannot grisée). Après une retouche par masques, regarder la carte des
  pixels changés (v_avant ≠ v_après) sur chaque personnage, pas seulement le verdict du contrôle.

- Recoloration en Lab : mélanger en RVB avec l'image d'origine (poids 0 = pixel strictement inchangé).
  Reconvertir toute une zone Lab → RVB décale d'un ou deux niveaux tous ses pixels (P02 v5, 1er essai :
  387 000 pixels « changés » au lieu de 159 000).
- Masques par couleur : les limiter à la silhouette de l'objet. P02 v5 : les pierres verdâtres du mur
  passaient pour de la peinture et les pierres brunes pour de la rouille (16 000 px) ; la zone du contrôle,
  qui englobait le fond, ne pouvait pas le voir.

- Collage d'un personnage retouché par IA : un masque « pixels nettement différents » est troué (là où
  l'ancien et le nouveau se ressemblent) et mélangerait les deux dessins. Prendre la silhouette par GrabCut
  (zones très différentes = personnage sûr, hors boîte = décor), union de l'ancienne et de la nouvelle.
- Contrôle, critère de netteté : il mesure les gradients sur l'image en gris ; une couleur plus sombre (bleu
  cobalt de P01) fait baisser le contraste des traits et passe pour « moins net » sans aucun flou. Garder une
  partie de la clarté de la retouche plutôt que d'accentuer les traits.
- Couleurs demandées « comme dans P01 » absentes de l'image retouchée : contrôle avec `--palette` P01.

- Retouche IA qui revient recadrée plus large (P02 v7 maison : échelle 0,70) : ne pas la redimensionner
  au cadre ; la recaler (ECC affine) sur une partie inchangée et rééchantillonner l'image IA d'origine.
- GrabCut rattache parfois des éléments fins voisins (descente d'eau, arête de mur) : ouverture 9×9 du
  masque. Le lissage du bord de collage déborde de 1–2 px : le remettre à zéro sur ce qui doit rester
  identique (4L, personnages).

- Collage de grandes zones (ciel, jardin) : coupe de graphe (PyMaxflow, `p02_v8.coupe_graphe`) plutôt
  qu'une limite tracée à la main — la frontière passe là où l'ancienne et la nouvelle image sont
  identiques. Si elle suit en ligne droite le bord d'une zone sûre, c'est que rien n'y est identique :
  vérifier au zoom. Éléments ajourés (rambarde, grillage) : les prendre entiers d'un seul côté.

---

## 13. Rappel sur le style d'échange

- **Parler français.**
- Terminer chaque tour en disant à l'utilisateur de taper **« continue »**.
- Ne pas rejouer indéfiniment la même correction : suivre ce qui est demandé, changer de cap quand
  il le dit, et poser une question précise s'il renvoie le même message.
