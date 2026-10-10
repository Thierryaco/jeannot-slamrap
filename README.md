# Jeannot slamrap

Clip d'animation 2D d'action-comédie, direction manga shōnen inspirée de DBZ. Le but est une vraie animation en cels dessinés, pas une planche d'images ni des personnages géométriques.

- **Durée audio mesurée :** 104,36 s (1 min 44,36 s).
- **Format visé :** 1920 × 1080, 16:9 (à confirmer).
- **Storyboard et plans caméra :** [`docs/storyboard.md`](docs/storyboard.md).
- **Test de caméra 12 fps :** [`renders/jeannot-intro-test-12fps.mp4`](renders/jeannot-intro-test-12fps.mp4) — push-in et fumée sur l'image de référence ; pas encore de cels corporels/lipsync.
- **Chute d'Henri en 24 cels :** [`renders/henri-stairs-cels-12fps.mp4`](renders/henri-stairs-cels-12fps.mp4) — 2,50 s, 12 fps, 24 dessins différents + holds, extrait audio 00:26,48–00:28,98. Cels dans [`assets/cels/henri-fall/`](assets/cels/henri-fall/).
- **Ancien test cutout (comparaison) :** [`renders/henri-stairs-test-12fps.mp4`](renders/henri-stairs-test-12fps.mp4) — une seule silhouette pivotée.
- **Décor / source du rig Henri :** [`assets/rigs/henri-stairs-clean-plate.png`](assets/rigs/henri-stairs-clean-plate.png) et [`assets/rigs/henri-cutout-green.png`](assets/rigs/henri-cutout-green.png).
- **Scripts des tests :** [`tools/render_intro_test.py`](tools/render_intro_test.py) et [`tools/render_henri_fall_test.py`](tools/render_henri_fall_test.py), dépendances dans [`requirements-render.txt`](requirements-render.txt).
- **MP3 :** [`audio/jeannot-slamrap.mp3`](audio/jeannot-slamrap.mp3), source [Suno](https://suno.com/s/Yp6esDOipsgZOeGw).
- **Référence Jeannot + 4L fournie par l'utilisateur :** [`assets/references/jeannot-4l-reference.png`](assets/references/jeannot-4l-reference.png).
- **Image-clé Jeannot/4L mise à jour :** [`assets/art/jeannot-4l-style-frame-v2.png`](assets/art/jeannot-4l-style-frame-v2.png) — taches de peinture ajoutées, image de recherche, pas une animation finale.
- **Concept Henri révisé :** [`assets/art/henri-character-v2.png`](assets/art/henri-character-v2.png).
- **Concept de la sorcière révisé :** [`assets/art/sorciere-character-v2.png`](assets/art/sorciere-character-v2.png).
- **Concept d'Enji :** [`assets/art/enji-character.png`](assets/art/enji-character.png).
- **Source du MP3 :** [`clip-arm/clips/Jeannot slamrap.mp3`](https://github.com/Thierryaco/clip-arm/blob/arena/2748952e-clip-arm/clips/Jeannot%20slamrap.mp3), copiée ici sans modifier `clip-arm`.

## Références et direction visuelle

L'image fournie montre Jeannot avec barbe foncée/grisonnante, chapeau jaune, combinaison de travail bleue et cigarette, à côté d'une Renault 4L vert menthe pâle, ancienne et rouillée mais intacte. Cette silhouette et cette voiture sont les références à suivre, au lieu de la 4L générique du prototype précédent.

La maquette Canvas de [`animation/intro.html`](animation/intro.html) était un test technique, pas le style final : elle est considérée comme **à remplacer**. Les images de concept dans `assets/art/` servent à harmoniser les personnages et le trait ; elles ne sont pas encore des cels animés ni une validation finale du look DBZ.

## Référence audio

Le MP3 a été décodé et vérifié : **2 445 256 octets**, MP3 VBR, environ **185,8 kb/s**, **48 kHz**, stéréo, durée **104,36 s**. L'analyse d'enveloppe indique une montée de niveau vers 16 s, des passages plus calmes autour de 43–54 s et 82–86 s, puis une décroissance vers 97 s. Les transitoires suggèrent un tempo proche de **90,7 BPM** (ou 45,4 BPM en half-time).

Ces repères donnent seulement les grandes sections. Les débuts/fins des paroles, les lèvres et les impacts doivent être recalés phrase par phrase à l'écoute ; les répartitions actuelles du storyboard ne sont pas un alignement exact.

## Avancement

- [x] Paroles, personnages, géographie et intentions définis dans le brief.
- [x] MP3 ajouté et caractéristiques audio vérifiées.
- [x] Référence visuelle de Jeannot et de la 4L déplacée sous `assets/references/`.
- [x] Concepts illustrés mis à jour pour Jeannot, Henri, la sorcière et Enji.
- [x] Storyboard provisoire avec plans et mouvements de caméra pour l'ouverture.
- [x] Test vidéo de 3 s rendu en 1080p à 12 fps avec push-in et fumée animée.
- [x] Test d'action de 2,75 s rendu à 12 fps : détourage corrigé, chute d'Henri en cutout et extrait audio provisoire.
- [x] 24 cels dessinés de la chute d'Henri montés en MP4 12 fps (pull corrigé, plus de tuyau sortant du cou).
- [ ] Recaler Henri dans les marches (pieds / contact) et exporter à 24 fps sur deux.
- [ ] Valider le trait et les proportions de la 4L avant d'étendre la séquence.
- [ ] Recaler les lèvres, les actions et les coups sur les paroles et les accents musicaux.
- [ ] Étendre l'animation aux 104,36 s et rendre le MP4 H.264 avec audio AAC 48 kHz.

## Règles de mise en scène

- Les paroles restent mot pour mot celles du brief ; aucun dialogue chanté ou parlé supplémentaire.
- Une seule rue : Jeannot vit à une extrémité, en face du narrateur ; Henri habite à côté ; Diego est à l'autre extrémité. Le combat final traverse la rue.
- La 4L est vert menthe pâle selon l'image de référence, vieille et rouillée, mais ni détruite ni cassée.
- La Coccinelle de Diego est orange et en restauration avec Marco. Enji, le chien de Jeannot, doit avoir un gag visuel.
- L'orthographe exacte de l'autocollant du fourgon de Diego (« Chat Chainegaz » dans le brief) reste à confirmer.

## Personnages

- **Jeannot :** peintre d'une cinquantaine d'années, barbu et grisonnant, chapeau jaune et combinaison bleue tachés de peinture, toujours une gitane ; héros qui se relève toujours. Il vit en face du narrateur avec sa sœur, la sorcière, et son chien Enji.
- **Henri :** frère de Jeannot, un peu plus âgé ; cheveux plus longs, hirsutes et en bataille. Il fume, porte des lunettes rectangulaires fines en métal gris bon marché et a un sourire niais mais gentil. Ses dents sont jaunies, irrégulières et ébréchées, comme la 4L, sans gore. Il habite à côté et tombe des escaliers.
- **La sorcière :** sœur de Jeannot, plus âgée, laide et fatiguée dans un registre cartoon ; cheveux teints très noirs et en bataille, beaucoup de mascara. Elle fume et guette depuis sa tourelle.
- **Diego (« le rat ») :** plombier à casquette et salopette, nez et moustache façon Mario Bros. Il conduit une vieille Estafette de plombier et retape depuis des années une Coccinelle orange avec son fils Marco.
- **Marco :** fils de Diego, aide à retaper la Coccinelle.
- **Enji :** vieux bâtard croisé berger, pelage rêche et museau grisonnant ; chien fidèle de Jeannot.

## Technique prévue

Dessins originaux cohérents, poses-clés et cels d'action à 12–15 images/s, avec décors en calques, caméra 2D, lignes de vitesse, flashes d'impact et aura. Export final en 24 fps avec animation sur deux images quand le mouvement le permet, puis assemblage H.264/AAC. Le prototype vectoriel précédent n'est pas la direction de production.
