# Jeannot slamrap

Clip d'animation 2D d'action-comédie, esthétique manga/DBZ stylisée faite maison — pas une production de studio japonais.

- **Durée audio mesurée :** 104,36 s (1 min 44,36 s).
- **Format visé :** 1920 × 1080, 16:9 (à confirmer).
- **Storyboard :** [`docs/storyboard.md`](docs/storyboard.md).
- **Musique :** [Suno](https://suno.com/s/Yp6esDOipsgZOeGw).
- **MP3 dans ce dépôt :** [`audio/jeannot-slamrap.mp3`](audio/jeannot-slamrap.mp3).
- **Source du MP3 :** [`clip-arm/clips/Jeannot slamrap.mp3`](https://github.com/Thierryaco/clip-arm/blob/arena/2748952e-clip-arm/clips/Jeannot%20slamrap.mp3) — copié ici sans modifier `clip-arm`.

## Référence audio

Le fichier a été décodé et vérifié : **2 445 256 octets**, MP3 VBR, environ **185,8 kb/s**, **48 kHz**, stéréo, durée **104,36 s**. L'analyse d'enveloppe montre une montée nette vers 16 s, des passages plus calmes autour de 43–54 s et 82–86 s, puis une décroissance vers 97 s. L'analyse des transitoires suggère un tempo proche de **90,7 BPM** (ou 45,4 BPM en half-time).

Ces repères donnent le découpage général. Les timecodes phrase par phrase du storyboard restent des estimations à confirmer à l'écoute avant la synchronisation labiale et les impacts.

## Avancement

- [x] Paroles, personnages, géographie et style définis dans le brief.
- [x] MP3 de référence ajouté et caractéristiques audio vérifiées.
- [x] Première proposition de storyboard, avec repères de sections mesurés et cues de paroles estimés.
- [ ] Confirmer à l'écoute les débuts/fins exacts des paroles, puis verrouiller la synchronisation labiale et les impacts.
- [ ] Concevoir l'animation articulée 2D (Canvas ou SVG) et les mouvements de caméra.
- [ ] Rendre image par image avec Chromium/Puppeteer, puis assembler le MP4 avec ffmpeg.
- [ ] Vérifier le rendu final en H.264, avec l'audio AAC 48 kHz.

## Direction artistique et règles

- Animation 2D manga/DBZ : lignes de vitesse, aura, cheveux dressés pour la transformation de Jeannot, flashes blancs aux impacts, tremblements d'écran, énergie figurée par la peinture et onomatopées visuelles (« BAM », « CRAC »).
- Cartouche récurrent : « Jeannot est toujours là ».
- Les paroles restent mot pour mot celles du brief ; aucun dialogue chanté ou parlé supplémentaire. La bouche et les impacts suivent le MP3.
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
