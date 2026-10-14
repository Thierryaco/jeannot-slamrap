# Prompt de reprise — à copier-coller dans un nouveau fil

Copie **tout le bloc ci-dessous** (le contenu du cadre) comme premier message du nouveau fil de
discussion. Il est conçu pour que l'agent démarre sans poser de question et sans perdre de temps.

---

```
Bonjour. On reprend le projet « Jeannot slamrap » sur le dépôt
https://github.com/Thierryaco/jeannot-slamrap

AVANT TOUT, lis attentivement ces deux fichiers du dépôt, ils contiennent tout l'état du chantier :
- docs/REPRISE.md          (état complet, contraintes, ce qui reste à faire, pièges)
- docs/storyboard.md       (les 30 plans et les règles de mise en scène)

Ensuite, dans l'ordre et sans attendre que je te le demande :

1) RÉCUPÉRER LE CODE
   git fetch -q origin && git merge origin/main
   "main" est la branche de référence : elle contient tout, y compris ce que j'ai fait en local
   sous VS Code. Ne fais JAMAIS de "git reset --hard" vers une autre branche : tu effacerais du
   travail. Si la fusion signale un conflit, arrête-toi et dis-le moi.

2) RÉINSTALLER LES DÉPENDANCES (les réinitialisations de sandbox les effacent)
   pip install --break-system-packages -r requirements.txt

3) LANCER LE SERVEUR — OBLIGATOIRE ET IMMÉDIAT
   python3 tools/serve_storyboard.py 8000
   (outil de processus en arrière-plan, il doit rester vivant toute la session ;
   le port est un argument positionnel ; n'ajoute pas --host : par défaut il écoute sur 0.0.0.0,
   c'est ce qu'il faut ici)
   Vérifie ensuite que http://127.0.0.1:8000/storyboard/a-valider.html répond 200.
   Sans ce serveur je ne peux rien voir ni rien valider. Ne l'arrête jamais, relance-le tout de
   suite s'il tombe.

4) TEST DE VISION — LE PLUS IMPORTANT
   crée cette image de test :
     cd /home/user/jeannot-slamrap
     python3 -c "from PIL import Image, ImageDraw
     im=Image.new('RGB',(200,120),'white'); d=ImageDraw.Draw(im)
     d.rectangle([20,20,90,90],fill='red'); d.ellipse([110,30,180,100],fill='blue')
     im.save('_test-vision.png')"
   puis OUVRIR le fichier /home/user/jeannot-slamrap/_test-vision.png et me dire précisément ce
   que tu vois.
   - Si tu vois un carré rouge et un rond bleu : la vision fonctionne, dis-le moi et on travaille
     normalement, en regardant les images toi-même.
   - Si tu obtiens le message "[An image was provided here, but you do not have vision
     capabilities.]" : dis-le moi tout de suite. Dans ce cas, ne génère PLUS aucune image à
     l'aveugle : je préfère qu'on s'arrête et que je change de modèle plutôt que d'accumuler des
     versions fausses. On continuera alors uniquement avec l'outil « 📍 Pointer » de la page
     « à valider », qui me permet de te donner les coordonnées exactes des pixels.

RÈGLES DE TRAVAIL (détaillées dans docs/REPRISE.md, à respecter strictement) :
- on travaille en français, plan par plan, avec plusieurs options par plan, et TOUTES les options
  sont poussées dans « à valider », même celles qui ne sont pas retenues ; pousse souvent.
- on modifie uniquement la partie de l'image qui ne va pas, jamais l'image entière.
- contrôle obligatoire après chaque retouche : tools/controle_retouche.py (sortie 0 = CONFORME).
- c'est la carte qui suit l'image, pas l'inverse.
- tu travailles par petites étapes et tu termines chaque réponse en me disant de taper « continue ».
- pour que je retrouve ton travail en local (VS Code), fusionne ta branche dans main par une pull
  request quand je te le demande.

OÙ ON EN EST : le plan P01 (plan général maître de la rue) est le seul en cours de fabrication ;
c'est le plus long et celui qui donne les bases du reste. La zone de la maison de Jeannot est
terminée et correcte. Deux points sont ouverts dans la zone d'Henri :
  a) Henri doit être sur le palier en haut de son escalier, penché, appuyé au rebord du muret, en
     train de fumer, le visage tourné vers la 4L. Trois hauteurs sont proposées à comparer :
     v21 (il ne bouge pas), v22 (remonté de 59 px), v23 (remonté de 109 px). La position ne doit
     PAS être recalculée depuis la carte, la projection s'est déjà révélée fausse d'environ 180 px
     en hauteur.
  b) il faut supprimer la structure de barres verticales devant l'escalier d'Henri
     (zone x ≈ 706–782, y ≈ 317–425) et peindre à la place une porte directement dans le mur de la
     maison.

Dis-moi d'abord le résultat du test de vision, et confirme-moi que le serveur tourne. Ensuite
attends que je te dise quelle hauteur d'Henri est la bonne avant de toucher à l'image.
```

---

## Travailler en local plutôt que dans Arena

Tout est prêt pour VS Code : voir [`docs/VSCODE.md`](VSCODE.md). Le serveur démarre seul à
l'ouverture du dossier, et les avis donnés en local partent directement sur `main`.

## Si le test de vision échoue dans le nouveau fil

Le problème vient du modèle utilisé par la session Arena, pas du dépôt. Choisir un modèle qui a la
vision (les paliers Claude / ChatGPT / Gemini l'ont ; certains modèles légers ou open-source non).
Le test de 30 secondes du point 4) permet de trancher immédiatement.
