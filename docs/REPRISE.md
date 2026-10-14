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
    Diego à `assets/art/diego-beetle-repair-concept-v2.png`.
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
assets/storyboards/a-valider/carte/plans.json   placement par plan — P01 rév. 14, P03 rév. 1
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
| `p01_v16…p01_v30.py` | `PYTHONPATH=tools python3 tools/p01_v21.py OUT.png` | les retouches locales de P01, une par version (sans `OUT.png` : `_sorties/vNN.png`) ; à lancer depuis la racine du dépôt. Depuis le 14/10 : `p01_v24.py A\|B` (v24 / v25, à partir de la v20), `p01_v26.py` (à partir de la v24), `p01_v27.py` (à partir de la v26), `p01_v28.py` (à partir de la v27, sans IA), `p01_v29.py` (à partir de la v28 : Henri effacé des marches, puis recollé sur le palier), `p01_v30.py` (à partir de la v28, même effacement, Henri de `work/crop-v30-ed3.png` ; affiche la zone modifiée depuis la v29) |

**Contrôle obligatoire** (sortie 0 = CONFORME) :

```bash
cd tools && PYTHONPATH=. python3 controle_retouche.py REF.png RESULTAT.png \
  --zones "x0,y0,x1,y1;x0,y0,x1,y1" --plan P01
```

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
| v18 | `p01-v18-retouche-v17.png` | à retoucher |
| v19 | `p01-v19-retouche-v18.png` | à retoucher |
| **v20** | `p01-v20-nette.png` | **base sûre** (v19 reconstruite sans flou) — on repart d'elle le 14/10 |
| v21–v23 | — | **supprimées par l'utilisateur le 14/10** (essais de hauteur d'Henri) |
| v24 | `p01-v24-sans-portail.png` | à valider — v20 sans le portail ni la clôture (`tools/p01_v24.py A`) |
| v25 | `p01-v25-porte.png` | à valider — v24 + porte ; liseré clair autour de l'encadrement → remplacée par la v27 |
| v26 | `p01-v26-rampe.png` | à valider — v24 + rampe couleur façade du garage + trait du bas en ligne droite |
| v27 | `p01-v27-porte.png` | à valider — v26 + porte dans le mur sous l'escalier |
| v28 | `p01-v28-trait.png` | à valider — v27 + un seul trait sous la rampe et sous le palier |
| v29 | `p01-v29-henri-palier.png` | à valider — v28 + Henri sur le palier, penché sur le muret, fumant ; tête droite, il regarde à l'horizontale (vers la façade) |
| **v30** | `p01-v30-henri-regard.png` | à valider — v29 avec la tête d'Henri tournée et baissée vers le bas à gauche, franchement vers la 4L (**version la plus avancée**) |

**v14 et v15 ont été rejetées et supprimées.** Ne jamais les reconstituer.

### Ce qui a déjà été corrigé sur P01

- Estafette réelle avec logo Renault (losange chromé) comme celui de la 4L ;
- sorcière nette et agrandie, elle fume, fenêtre de la tourelle agrandie ;
- façade de la tourelle avec la même patine que la maison, toit et débord cohérents ;
- Diego à genou devant sa caisse à outils ; capot de la Coccinelle ouvert, outils au sol ;
- v20 : reconstruction nette de la v19 (Diego, caisse, Estafette, tourelle) — CONFORME.

### Les deux points qui étaient ouverts (FAITS, en attente d'avis)

**1. Henri sur son palier (FAIT en v29, regard corrigé en v30, en attente d'avis).**

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
- `plans.json` : **P01 rév. 14**, **P03 rév. 1**. Caméra P01 : `x -89.7, y 518.8, angle -4.8,
  fov 32.9, portée 2000, œil 1.8, inclinaison -1.6`.
- `carte-rue-v8.png` est la carte rue courante. CARTE v1–v4 écartées, v5–v8 en attente.
- Repère carte : unités = pixels d'une carte 1600×1000, **100 px ≈ 3,7 m**. Angles : 0 = vers l'est
  (bout Diego), 90 = vers le sud (côté narrateur), −90 = vers le nord (côté Jeannot), 180 = vers
  l'ouest (bout Jeannot).
- Visionneuse : `VB0 = [-300, 0, 1900, 1000]` ; le PNG fait 2 px par unité de carte avec
  `ox = 1600 - naturalWidth/2`.

⚠️ **À corriger quand la position d'Henri sera arrêtée :** le point « Henri » de la carte est calé
sur l'ancienne hauteur (palier à 2,8 m → image y 367). Comme l'utilisateur l'a demandé, **c'est la
carte qui devra suivre l'image**, pas l'inverse.

---

## 11. Ce qu'il reste à faire, dans l'ordre

1. **Résoudre la vision** (§2) — priorité absolue, décidé par l'utilisateur.
2. **P01 — portail, rampe, porte, trait unique :** faits en v24 → v26 → v27 → v28, en attente de
   l'avis de l'utilisateur.
3. **P01 — Henri :** sur le palier, penché sur le muret, fumant, en v29. Regard corrigé en v30 :
   tête baissée vers le bas à gauche, franchement vers la 4L. En attente de l'avis de l'utilisateur.
4. **P01 — carte :** recaler le point Henri de `plans.json` sur la position retenue dans l'image
   (v29 / v30 : sur le palier, pieds cachés vers (820, 442) ; la carte suit l'image).
5. **Valider P01**, première image de référence du clip.
6. **Cohérence P02 / P03** : jamais retravaillés, c'est la suite logique annoncée.
7. Puis P04 → P29.

---

## 12. Pièges déjà rencontrés — ne pas les refaire

- **Garder TOUS les essais IA** dans `work/`, y compris ceux qu'on écarte, et les commiter tout de
  suite. L'utilisateur peut en préférer un : `crop-v29-ed5.png`, son préféré, a été perdu avec une
  remise à zéro de la session parce qu'il n'avait pas été commité. Quand l'utilisateur ne choisit
  aucune des deux images proposées au choix, rien n'est enregistré.
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

---

## 13. Rappel sur le style d'échange

- **Parler français.**
- Terminer chaque tour en disant à l'utilisateur de taper **« continue »**.
- Ne pas rejouer indéfiniment la même correction : suivre ce qui est demandé, changer de cap quand
  il le dit, et poser une question précise s'il renvoie le même message.
