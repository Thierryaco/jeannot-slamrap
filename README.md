# Jeannot slamrap

Projet de clip d'animation 2D d'action-comédie, avec une esthétique manga/DBZ stylisée faite maison — pas une production de studio japonais.

- **Durée cible :** 1 min 44 s (104 s), d'après le brief audio.
- **Format visé :** 1920 × 1080, 16:9 (à confirmer).
- **Storyboard provisoire :** [`docs/storyboard.md`](docs/storyboard.md).
- **Musique :** [Suno](https://suno.com/s/Yp6esDOipsgZOeGw).

> **État du média :** le MP3 `audio/jeannot-slamrap.mp3` n'est pas présent dans ce checkout. Selon le brief, il dure 1:44 (187 kb/s, stéréo 48 kHz), mais ces données n'ont pas pu être vérifiées ici. Les timecodes du storyboard sont donc des estimations, pas une synchronisation mesurée.

## Avancement

- [x] Paroles, personnages, géographie et style définis dans le brief.
- [x] Première proposition de storyboard et de découpage temporel dans [`docs/storyboard.md`](docs/storyboard.md).
- [ ] Ajouter le MP3 de référence dans `audio/jeannot-slamrap.mp3`.
- [ ] Mesurer les entrées de voix et les temps forts, puis verrouiller les timecodes et la synchronisation labiale.
- [ ] Concevoir l'animation articulée 2D (Canvas ou SVG) et les mouvements de caméra.
- [ ] Rendre image par image avec Chromium/Puppeteer, puis assembler le MP4 avec ffmpeg.
- [ ] Vérifier le rendu final avec la musique, en H.264 et audio AAC 48 kHz.

## Direction artistique et règles

- Animation 2D manga/DBZ : lignes de vitesse, aura, cheveux dressés pour la transformation de Jeannot, flashes blancs aux impacts, tremblements d'écran, énergie figurée par la peinture et onomatopées visuelles (« BAM », « CRAC »).
- Cartouche récurrent : « Jeannot est toujours là ».
- Les paroles doivent rester mot pour mot celles du brief ; aucun dialogue chanté ou parlé supplémentaire. La bouche et les impacts suivront le MP3 lorsqu'il sera disponible.
- Une seule rue : Jeannot vit à une extrémité, en face du narrateur ; Henri habite à côté ; Diego est à l'autre extrémité. Le combat final traverse la rue.
- La 4L de Jeannot est vieille et rouillée, mais ne doit pas être représentée comme détruite ou cassée.
- La Coccinelle de Diego est orange et en restauration avec Marco. Enji, le chien de Jeannot, doit avoir un gag visuel.
- L'orthographe exacte de l'autocollant du fourgon de Diego (« Chat Chainegaz » dans le brief) reste à confirmer.

## Personnages

- **Jeannot :** peintre d'une cinquantaine d'années, barbu et grisonnant, toujours une gitane ; héros qui se relève toujours. Il vit en face du narrateur avec sa sœur, la sorcière, et son chien Enji.
- **Henri :** frère de Jeannot, voisin immédiat ; chute des escaliers et dents esquintées comme gag de cartoon.
- **La sorcière :** sœur de Jeannot, méchante de cartoon dans sa tourelle.
- **Diego (« le rat ») :** plombier à casquette et salopette, nez et moustache façon Mario Bros. Il conduit une vieille Estafette de plombier et retape depuis des années une Coccinelle orange avec son fils Marco.
- **Marco :** fils de Diego, aide à retaper la Coccinelle.
- **Enji :** chien de Jeannot.

## Chaîne de production envisagée

Personnages articulés et animation écrite en Canvas ou SVG, puis rendu image par image avec Chromium headless/Puppeteer et assemblage ffmpeg (H.264, CRF 18, audio AAC 48 kHz). Aucun générateur vidéo IA n'est prévu : le résultat visé est un clip animé stylisé fait maison.
