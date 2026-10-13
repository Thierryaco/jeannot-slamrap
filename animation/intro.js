(() => {
  'use strict';

  const W = 1920;
  const H = 1080;
  const SEGMENT_END = 29.02;
  const canvas = document.getElementById('scene');
  const ctx = canvas.getContext('2d');
  const audio = new Audio('../audio/jeannot-slamrap.mp3');
  audio.preload = 'auto';
  audio.volume = 1;

  const playButton = document.getElementById('play');
  const restartButton = document.getElementById('restart');
  const seek = document.getElementById('seek');
  const currentLabel = document.getElementById('current');

  const lyricCues = [
    { start: 16.35, end: 18.88, text: 'Jeannot est là, et toujours là !' },
    { start: 18.88, end: 21.42, text: 'La sorcière est partie, Jeannot est encore là' },
    { start: 21.42, end: 23.95, text: 'Alors Henri s\'enfuit, Jeannot est toujours là' },
    { start: 23.95, end: 26.48, text: 'La sorcière est revenue, c\'est la merde dans la rue' },
    { start: 26.48, end: 29.02, text: 'Henri tombe des escaliers, toutes ses dents sont esquintées' }
  ];

  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const smooth = (a, b, x) => {
    const u = clamp((x - a) / (b - a));
    return u * u * (3 - 2 * u);
  };
  const easeInOut = (x) => x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
  }

  function polygon(points, fill, stroke = '#20243a', lineWidth = 8) {
    ctx.beginPath();
    points.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lineWidth; ctx.lineJoin = 'round'; ctx.stroke(); }
  }

  function line(x1, y1, x2, y2, color = '#252a3c', width = 6) {
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round'; ctx.stroke();
  }

  function drawCloud(x, y, s, alpha = 1) {
    ctx.save(); ctx.globalAlpha = alpha; ctx.fillStyle = '#f7fbfb';
    ctx.beginPath();
    ctx.ellipse(x, y, 68 * s, 25 * s, 0, 0, Math.PI * 2);
    ctx.ellipse(x - 36 * s, y + 1 * s, 36 * s, 22 * s, 0, 0, Math.PI * 2);
    ctx.ellipse(x + 32 * s, y - 10 * s, 41 * s, 32 * s, 0, 0, Math.PI * 2);
    ctx.ellipse(x + 68 * s, y + 3 * s, 35 * s, 20 * s, 0, 0, Math.PI * 2);
    ctx.fill(); ctx.restore();
  }

  function drawSky(t) {
    const sky = ctx.createLinearGradient(0, 0, 0, 690);
    sky.addColorStop(0, '#76b6d2');
    sky.addColorStop(.58, '#c1e0e4');
    sky.addColorStop(1, '#f2dfbb');
    ctx.fillStyle = sky; ctx.fillRect(0, 0, W, H);

    const glow = ctx.createRadialGradient(1450, 180, 15, 1450, 180, 300);
    glow.addColorStop(0, 'rgba(255,240,176,.9)');
    glow.addColorStop(1, 'rgba(255,240,176,0)');
    ctx.fillStyle = glow; ctx.fillRect(1100, 0, 650, 520);
    ctx.fillStyle = '#ffe39a'; ctx.beginPath(); ctx.arc(1450, 182, 72, 0, Math.PI * 2); ctx.fill();

    drawCloud((130 + t * 5) % 2100 - 100, 160, .85, .78);
    drawCloud((900 + t * 3) % 2200 - 100, 245, .65, .68);
    drawCloud((1730 + t * 2) % 2200 - 100, 120, .72, .65);

    // Collines et toits lointains de la rue.
    polygon([[0, 570], [210, 475], [355, 540], [565, 445], [760, 565], [1040, 455], [1280, 575], [1510, 470], [1920, 575], [1920, 700], [0, 700]], '#86a5a1', null);
    polygon([[0, 610], [300, 520], [480, 615], [760, 500], [1020, 620], [1290, 525], [1580, 630], [1770, 540], [1920, 595], [1920, 735], [0, 735]], '#668d87', null);
  }

  function drawHouse(x, y, w, h, wall, roof, variant = 0) {
    // Mur principal.
    ctx.fillStyle = wall; ctx.strokeStyle = '#22263a'; ctx.lineWidth = 11;
    ctx.beginPath(); ctx.rect(x, y, w, h); ctx.fill(); ctx.stroke();
    // Toiture manga, volontairement anguleuse.
    polygon([[x - 32, y + 10], [x + w * .5, y - 125], [x + w + 35, y + 10]], roof, '#22263a', 12);
    // Bandeau et corniche.
    line(x - 8, y + 19, x + w + 8, y + 19, '#493f44', 13);
    // Fenêtres.
    const wx = x + 62;
    for (let i = 0; i < 3; i++) {
      const bx = wx + i * (w - 130) / 2;
      ctx.fillStyle = variant === 2 && i === 1 ? '#43536d' : '#8dc6d4';
      ctx.strokeStyle = '#24283b'; ctx.lineWidth = 8;
      ctx.beginPath(); ctx.rect(bx, y + 75, 72, 100); ctx.fill(); ctx.stroke();
      line(bx + 36, y + 78, bx + 36, y + 172, '#24283b', 5);
      line(bx + 2, y + 126, bx + 70, y + 126, '#24283b', 5);
      ctx.fillStyle = 'rgba(255,240,178,.5)'; ctx.fillRect(bx + 8, y + 82, 20, 36);
    }
    // Porte.
    ctx.fillStyle = '#654d4d'; ctx.strokeStyle = '#24283b'; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.roundRect(x + w * .45, y + h - 160, 92, 160, 16); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#f6cf62'; ctx.beginPath(); ctx.arc(x + w * .45 + 72, y + h - 80, 7, 0, Math.PI * 2); ctx.fill();
  }

  function drawTurret(t) {
    const x = 344, y = 235, w = 210, h = 255;
    // Tour de la maison de Jeannot.
    ctx.fillStyle = '#e9c3a0'; ctx.strokeStyle = '#22263a'; ctx.lineWidth = 11;
    ctx.beginPath(); ctx.rect(x, y, w, h); ctx.fill(); ctx.stroke();
    polygon([[x - 18, y + 12], [x + w / 2, y - 120], [x + w + 18, y + 12]], '#53486d', '#22263a', 12);
    ctx.fillStyle = '#455269'; ctx.strokeStyle = '#22263a'; ctx.lineWidth = 9;
    ctx.beginPath(); ctx.roundRect(x + 50, y + 100, 110, 125, [55, 55, 5, 5]); ctx.fill(); ctx.stroke();
    line(x + 105, y + 103, x + 105, y + 222, '#22263a', 6);
    line(x + 54, y + 165, x + 156, y + 165, '#22263a', 6);
    // Lueur légère derrière la fenêtre quand la sorcière revient.
    const glow = smooth(23.7, 24.6, t) * (1 - smooth(29, 30, t));
    if (glow > 0) {
      ctx.save(); ctx.globalAlpha = glow * .5;
      const g = ctx.createRadialGradient(x + 105, y + 160, 10, x + 105, y + 160, 120);
      g.addColorStop(0, '#d47cff'); g.addColorStop(1, 'rgba(212,124,255,0)');
      ctx.fillStyle = g; ctx.fillRect(x - 15, y + 35, w + 30, h);
      ctx.restore();
    }
  }

  function drawStreet() {
    // Trottoirs en perspective.
    polygon([[0, 645], [1920, 615], [1920, 760], [0, 810]], '#d3b28e', '#4a4650', 8);
    polygon([[0, 705], [1920, 650], [1920, 1080], [0, 1080]], '#414b59', '#27303d', 8);
    polygon([[0, 705], [1920, 650], [1920, 680], [0, 742]], '#ede1c9', '#3b414b', 5);
    // Joints des pavés.
    for (let i = 0; i < 15; i++) {
      const x = i * 145 - 80;
      line(x, 720 + i * 1.7, x + 75, 718 + i * 1.7, 'rgba(77,70,67,.25)', 3);
    }
    // Marquage central qui fuit vers le fond.
    ctx.save(); ctx.setLineDash([34, 37]); ctx.lineDashOffset = 0;
    ctx.strokeStyle = 'rgba(246,220,157,.72)'; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.moveTo(1440, 685); ctx.lineTo(980, 1080); ctx.stroke(); ctx.restore();
    // Bouches d'égout et fissures stylisées.
    ctx.strokeStyle = 'rgba(29,35,45,.42)'; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.ellipse(1440, 885, 90, 22, -.12, 0, Math.PI * 2); ctx.stroke();
    for (let i = 0; i < 5; i++) line(1370 + i * 26, 879, 1365 + i * 26, 891, 'rgba(29,35,45,.36)', 3);
  }

  function drawStairs() {
    // Petit escalier extérieur chez Henri, suffisamment large pour la chute cartoon.
    const left = 1115, top = 548, stepW = 47, stepH = 24;
    for (let i = 0; i < 8; i++) {
      const x = left + i * stepW;
      const y = top + i * stepH;
      ctx.fillStyle = i % 2 ? '#ad8a70' : '#c19c7c';
      ctx.strokeStyle = '#393947'; ctx.lineWidth = 5;
      ctx.beginPath();
      ctx.moveTo(x, y); ctx.lineTo(x + stepW + 3, y); ctx.lineTo(x + stepW + 3, y + stepH); ctx.lineTo(x, y + stepH); ctx.closePath();
      ctx.fill(); ctx.stroke();
      line(x, y, x + stepW + 3, y, '#f1d2ad', 4);
    }
    // Rampe.
    line(1105, 527, 1504, 724, '#363543', 11);
    for (let i = 0; i < 7; i++) line(1125 + i * 53, 536 + i * 26, 1119 + i * 53, 572 + i * 26, '#363543', 7);
  }

  function drawTree(x, y, s, t) {
    const sway = Math.sin(t * 1.2 + x) * 5;
    ctx.fillStyle = '#755447'; ctx.strokeStyle = '#302b3b'; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.roundRect(x - 20, y - 170, 42, 190, 12); ctx.fill(); ctx.stroke();
    for (const [dx, dy, r, c] of [[0,-205,78,'#5d8f63'],[-48,-168,57,'#76a66d'],[48,-165,60,'#4e835e'],[4,-255,53,'#88b778']]) {
      ctx.fillStyle = c; ctx.strokeStyle = '#2c564d'; ctx.lineWidth = 7;
      ctx.beginPath(); ctx.ellipse(x + dx + sway * .4, y + dy, r * s, r * .82 * s, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }
  }

  function drawFourL(x, y, s, t) {
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
    // Ombre au sol.
    ctx.fillStyle = 'rgba(13,21,29,.26)'; ctx.beginPath(); ctx.ellipse(165, 138, 215, 26, 0, 0, Math.PI * 2); ctx.fill();
    // Roues ; les roues sont intactes même si la carrosserie est très vieille.
    for (const wx of [62, 286]) {
      ctx.fillStyle = '#242a34'; ctx.strokeStyle = '#111722'; ctx.lineWidth = 9;
      ctx.beginPath(); ctx.arc(wx, 112, 39, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.fillStyle = '#b8b9ad'; ctx.beginPath(); ctx.arc(wx, 112, 18, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#707779'; ctx.beginPath(); ctx.arc(wx, 112, 7, 0, Math.PI * 2); ctx.fill();
    }
    // Carrosserie carrée de 4L : peinture passée et rouille, aucun panneau arraché.
    ctx.fillStyle = '#a89068'; ctx.strokeStyle = '#202634'; ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.moveTo(18, 94); ctx.lineTo(28, 49); ctx.lineTo(68, 28); ctx.lineTo(114, 17);
    ctx.lineTo(241, 17); ctx.lineTo(285, 43); ctx.lineTo(325, 59); ctx.lineTo(336, 96);
    ctx.lineTo(329, 112); ctx.lineTo(18, 112); ctx.closePath(); ctx.fill(); ctx.stroke();
    // Fenêtres et montants.
    ctx.fillStyle = '#7faeb4'; ctx.strokeStyle = '#202634'; ctx.lineWidth = 7;
    ctx.beginPath(); ctx.moveTo(76, 31); ctx.lineTo(124, 25); ctx.lineTo(124, 67); ctx.lineTo(50, 67); ctx.lineTo(58, 46); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(137, 25); ctx.lineTo(236, 25); ctx.lineTo(270, 51); ctx.lineTo(270, 67); ctx.lineTo(137, 67); ctx.closePath(); ctx.fill(); ctx.stroke();
    line(131, 27, 131, 70, '#202634', 7);
    // Pare-chocs et phares.
    line(25, 91, 325, 91, '#dad0b6', 8);
    ctx.fillStyle = '#fff0b7'; ctx.strokeStyle = '#202634'; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.ellipse(37, 76, 14, 9, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(316, 76, 14, 9, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    // Taches de rouille décoratives.
    for (const [rx, ry, rw, rh] of [[38,55,17,8],[94,79,23,7],[214,76,19,8],[292,61,13,7],[176,40,14,5],[42,99,20,5]]) {
      ctx.fillStyle = '#9e573e'; ctx.beginPath(); ctx.ellipse(rx, ry, rw, rh, -.12, 0, Math.PI * 2); ctx.fill();
    }
    // Fumée douce d'échappement pour souligner l'âge, pas une voiture en panne.
    const puff = (t * 38) % 90;
    ctx.globalAlpha = .16 + (1 - puff / 90) * .22;
    ctx.fillStyle = '#eef1e8'; ctx.beginPath(); ctx.arc(-8 - puff * .3, 98 - puff * .25, 6 + puff * .1, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  function drawJeannot(x, groundY, t, talking = false) {
    const bob = Math.sin(t * 5.2) * 3;
    const mouth = talking ? (.5 + .5 * Math.sin(t * 19)) : 0;
    ctx.save(); ctx.translate(x, groundY + bob);
    // Jambes et chaussures.
    line(-28, -73, -34, -8, '#394b56', 25); line(27, -73, 37, -8, '#394b56', 25);
    ctx.fillStyle = '#282c39'; ctx.beginPath(); ctx.ellipse(-40, -6, 31, 13, -.12, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(45, -6, 31, 13, .08, 0, Math.PI * 2); ctx.fill();
    // Salopette de peintre et chemise.
    ctx.fillStyle = '#557b8a'; ctx.strokeStyle = '#26303e'; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.roundRect(-58, -167, 116, 106, 22); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#e1d4ba'; ctx.beginPath(); ctx.roundRect(-71, -187, 42, 58, 14); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.roundRect(29, -187, 42, 58, 14); ctx.fill(); ctx.stroke();
    line(-39, -151, 38, -151, '#b6a98d', 7);
    ctx.fillStyle = '#d2ae53'; ctx.beginPath(); ctx.arc(0, -133, 7, 0, Math.PI * 2); ctx.fill();
    // Bras et pinceau.
    line(-50, -161, -87, -105, '#e0d1b7', 24);
    line(50, -160, 83, -111, '#e0d1b7', 24);
    ctx.save(); ctx.translate(88, -119); ctx.rotate(-.36);
    ctx.fillStyle = '#805b37'; ctx.fillRect(-5, -55, 10, 71);
    ctx.fillStyle = '#d3b66d'; ctx.fillRect(-10, -67, 20, 18);
    ctx.fillStyle = '#df6757'; ctx.beginPath(); ctx.arc(0, -65, 9, 0, Math.PI * 2); ctx.fill(); ctx.restore();
    // Cou, visage, oreilles.
    ctx.fillStyle = '#d7b08d'; ctx.fillRect(-17, -220, 34, 42);
    ctx.fillStyle = '#dcb895'; ctx.strokeStyle = '#26303e'; ctx.lineWidth = 7;
    ctx.beginPath(); ctx.ellipse(0, -252, 59, 69, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    // Cheveux grisonnants en mèches, animés par le vent.
    ctx.fillStyle = '#62666d'; ctx.strokeStyle = '#303543'; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.moveTo(-54,-273); ctx.lineTo(-70,-307); ctx.lineTo(-42,-293); ctx.lineTo(-36,-324); ctx.lineTo(-17,-294); ctx.lineTo(1,-319); ctx.lineTo(17,-291); ctx.lineTo(45,-308); ctx.lineTo(42,-278); ctx.closePath(); ctx.fill(); ctx.stroke();
    // Sourcils, yeux et nez.
    line(-39, -267, -14, -270, '#5a4439', 7); line(16, -270, 39, -267, '#5a4439', 7);
    ctx.fillStyle = '#242735'; ctx.beginPath(); ctx.ellipse(-27, -254, 5, 8, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(27, -254, 5, 8, 0, 0, Math.PI * 2); ctx.fill();
    line(0, -251, -4, -232, '#9b725c', 5);
    // Barbe poivre et sel.
    ctx.fillStyle = '#6b6b6e'; ctx.strokeStyle = '#303543'; ctx.lineWidth = 6;
    ctx.beginPath(); ctx.moveTo(-48,-226); ctx.quadraticCurveTo(-47,-191,-24,-184); ctx.lineTo(-10,-203); ctx.lineTo(3,-181); ctx.lineTo(20,-203); ctx.quadraticCurveTo(47,-198,49,-229); ctx.lineTo(33,-218); ctx.lineTo(18,-229); ctx.lineTo(0,-219); ctx.lineTo(-20,-230); ctx.closePath(); ctx.fill(); ctx.stroke();
    // Bouche qui suit le flux vocal (battement provisoire, non phonémique).
    ctx.fillStyle = '#482d36';
    if (talking) { ctx.beginPath(); ctx.ellipse(0, -214, 11, 3 + mouth * 9, 0, 0, Math.PI * 2); ctx.fill(); }
    else line(-12, -213, 12, -213, '#573841', 4);
    // Gitane et fumée.
    line(42, -229, 68, -234, '#f2e8ce', 7);
    ctx.fillStyle = '#df6e4f'; ctx.beginPath(); ctx.arc(70, -234, 4, 0, Math.PI * 2); ctx.fill();
    for (let i = 0; i < 3; i++) {
      const lift = (t * 27 + i * 26) % 75;
      ctx.globalAlpha = (1 - lift / 75) * .38;
      ctx.strokeStyle = '#eef1ea'; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.arc(78 + Math.sin(t * 2 + i) * 8, -246 - lift, 7 + lift * .08, .2, Math.PI * 1.6); ctx.stroke();
    }
    ctx.restore();
  }

  function drawWitch(x, y, scale, t, alpha = 1) {
    ctx.save(); ctx.globalAlpha = alpha; ctx.translate(x, y); ctx.scale(scale, scale);
    const hover = Math.sin(t * 8) * 5;
    ctx.translate(0, hover);
    // Cape sombre.
    polygon([[-39, 3], [40, 3], [67, 142], [0, 121], [-65, 143]], '#38304f', '#242238', 8);
    // Col et visage.
    ctx.fillStyle = '#d9b293'; ctx.strokeStyle = '#242238'; ctx.lineWidth = 6;
    ctx.beginPath(); ctx.ellipse(0, -25, 34, 43, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    // Chapeau pointu.
    polygon([[-51,-55], [7,-151], [22,-61], [88,-38], [-28,-34]], '#54456f', '#242238', 8);
    ctx.fillStyle = '#cf5364'; ctx.beginPath(); ctx.arc(-2, -117, 7, 0, Math.PI * 2); ctx.fill();
    // Yeux méchants de cartoon.
    line(-24, -35, -8, -40, '#443343', 5); line(9, -40, 26, -35, '#443343', 5);
    ctx.fillStyle = '#352a38'; ctx.beginPath(); ctx.arc(-15, -25, 4, 0, Math.PI * 2); ctx.arc(16, -25, 4, 0, Math.PI * 2); ctx.fill();
    line(-8, -1, 11, -4, '#78434b', 4);
    // Manche et doigts.
    line(-36, 33, -74, 67, '#d9b293', 12);
    ctx.restore();
  }

  function drawHenri(x, groundY, t, angle = 0, tumble = 0) {
    ctx.save(); ctx.translate(x, groundY); ctx.rotate(angle);
    const bounce = tumble ? 0 : Math.sin(t * 13) * 4;
    ctx.translate(0, bounce);
    // Pantalon et chaussures.
    line(-18, -63, -26, -6, '#4c596b', 19); line(18, -63, 28, -7, '#4c596b', 19);
    ctx.fillStyle = '#282d3b'; ctx.beginPath(); ctx.ellipse(-34, -4, 25, 10, -.15, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(34, -4, 25, 10, .12, 0, Math.PI * 2); ctx.fill();
    // Veste.
    ctx.fillStyle = '#a65f4d'; ctx.strokeStyle = '#303342'; ctx.lineWidth = 7;
    ctx.beginPath(); ctx.roundRect(-43, -151, 86, 91, 18); ctx.fill(); ctx.stroke();
    // Bras en mouvement.
    line(-37, -132, -71, -105, '#dfbb98', 18); line(37, -132, 73, -111, '#dfbb98', 18);
    // Tête et cheveux bruns.
    ctx.fillStyle = '#dcb895'; ctx.strokeStyle = '#303342'; ctx.lineWidth = 6;
    ctx.beginPath(); ctx.ellipse(0, -181, 43, 50, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#5b463d';
    ctx.beginPath(); ctx.moveTo(-42,-193); ctx.lineTo(-44,-224); ctx.lineTo(-19,-216); ctx.lineTo(-7,-232); ctx.lineTo(9,-216); ctx.lineTo(32,-223); ctx.lineTo(43,-190); ctx.closePath(); ctx.fill();
    // Nez, yeux et bouche de gag.
    ctx.fillStyle = '#252938'; ctx.beginPath(); ctx.arc(-16,-184,4,0,Math.PI*2); ctx.arc(17,-184,4,0,Math.PI*2); ctx.fill();
    line(-12, -151, 12, -151, '#744047', 4);
    if (tumble > .7) {
      // Quelques dents ébréchées stylisées, sans gore.
      ctx.fillStyle = '#fff3d6'; ctx.fillRect(-13, -161, 11, 7); ctx.fillRect(2, -161, 8, 5);
    }
    ctx.restore();
  }

  function drawEnji(x, y, t, sniffing = false) {
    ctx.save(); ctx.translate(x, y);
    const wag = Math.sin(t * 13) * 17;
    const step = Math.sin(t * 9) * (sniffing ? 5 : 2);
    ctx.fillStyle = '#8a5c3c'; ctx.strokeStyle = '#302b31'; ctx.lineWidth = 6;
    ctx.beginPath(); ctx.ellipse(0, 0, 61, 35, -.04, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    // Pattes.
    for (const px of [-36, -5, 28, 48]) {
      line(px, 20, px + step * (px < 0 ? -1 : 1), 54, '#8a5c3c', 14);
      line(px - 4, 54, px + 13, 54, '#332b2b', 8);
    }
    // Queue qui remue.
    ctx.save(); ctx.translate(-52, -14); ctx.rotate(wag * Math.PI / 180);
    line(0, 0, -31, -25, '#8a5c3c', 12); ctx.restore();
    // Tête et oreilles.
    ctx.beginPath(); ctx.ellipse(54, -19, 33, 27, .05, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#5b3c35'; ctx.beginPath(); ctx.ellipse(72, -41, 12, 27, -.3, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#f1d6a1'; ctx.beginPath(); ctx.arc(64, -22, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#252430'; ctx.beginPath(); ctx.ellipse(83, -12, 11, 8, 0, 0, Math.PI * 2); ctx.fill();
    if (sniffing) {
      ctx.strokeStyle = 'rgba(249,243,215,.8)'; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.arc(95, -4, 10 + Math.sin(t * 20) * 3, -.7, .7); ctx.stroke();
    }
    ctx.restore();
  }

  function drawFarVan(t) {
    const scale = .45 + Math.sin(t * .5) * .01;
    ctx.save(); ctx.translate(1550, 618); ctx.scale(scale, scale);
    ctx.fillStyle = 'rgba(15,24,32,.24)'; ctx.beginPath(); ctx.ellipse(80, 65, 120, 14, 0, 0, Math.PI*2); ctx.fill();
    ctx.fillStyle = '#74816d'; ctx.strokeStyle = '#29323b'; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.moveTo(0, 47); ctx.lineTo(0, 6); ctx.lineTo(30, -35); ctx.lineTo(133, -35); ctx.lineTo(160, 0); ctx.lineTo(166, 47); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#91bbc0'; ctx.beginPath(); ctx.moveTo(39,-27); ctx.lineTo(83,-27); ctx.lineTo(83,3); ctx.lineTo(19,3); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(91,-27); ctx.lineTo(128,-27); ctx.lineTo(151,3); ctx.lineTo(91,3); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#20242b'; ctx.beginPath(); ctx.arc(39,48,19,0,Math.PI*2); ctx.arc(130,48,19,0,Math.PI*2); ctx.fill();
    ctx.restore();
  }

  function drawSpeedLines(t, intensity) {
    if (intensity <= 0) return;
    ctx.save(); ctx.globalAlpha = intensity * .38; ctx.strokeStyle = '#fff9e9'; ctx.lineWidth = 5;
    for (let i = 0; i < 20; i++) {
      const x = (i * 127 + t * 330) % W;
      const y = 400 + ((i * 83) % 390);
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - 110 - intensity * 80, y - 24); ctx.stroke();
    }
    ctx.restore();
  }

  function drawDust(x, y, t, amount) {
    for (let i = 0; i < 9; i++) {
      const age = (t * 1.7 + i * .13) % 1;
      const r = 10 + age * 40;
      ctx.globalAlpha = amount * (1 - age) * .42;
      ctx.fillStyle = i % 2 ? '#e9d7bc' : '#d5b98f';
      ctx.beginPath(); ctx.arc(x + Math.sin(i * 8) * age * 95, y - age * 60, r, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function drawSfx(text, x, y, scale, alpha, rotation = 0) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(rotation); ctx.globalAlpha = alpha; ctx.scale(scale, scale);
    ctx.font = '900 72px system-ui, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.lineJoin = 'round'; ctx.lineWidth = 18; ctx.strokeStyle = '#202238'; ctx.strokeText(text, 0, 0);
    ctx.fillStyle = text === 'CRAC' ? '#f05b4e' : '#ffe162'; ctx.fillText(text, 0, 0);
    ctx.restore();
  }

  function drawCaption(t) {
    const cue = lyricCues.find((c) => t >= c.start && t < c.end);
    if (!cue) return;
    const alpha = Math.min(smooth(cue.start, cue.start + .18, t), 1 - smooth(cue.end - .18, cue.end, t));
    ctx.save(); ctx.globalAlpha = alpha;
    roundRect(230, 930, 1460, 94, 22); ctx.fillStyle = 'rgba(18,24,36,.84)'; ctx.fill();
    ctx.strokeStyle = 'rgba(255,232,167,.72)'; ctx.lineWidth = 3; ctx.stroke();
    ctx.fillStyle = '#fff8e9'; ctx.font = '700 37px system-ui, sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(cue.text, 960, 978, 1380);
    ctx.restore();
  }

  function drawCartouche(t) {
    const active = (t >= 16.35 && t < 18.88) || (t >= 21.42 && t < 23.95);
    if (!active) return;
    const pulse = 1 + Math.sin(t * 11) * .018;
    ctx.save(); ctx.translate(960, 104); ctx.scale(pulse, pulse);
    roundRect(-315, -36, 630, 72, 18); ctx.fillStyle = 'rgba(24,31,48,.87)'; ctx.fill();
    ctx.strokeStyle = '#ffe170'; ctx.lineWidth = 5; ctx.stroke();
    ctx.fillStyle = '#fff3c4'; ctx.font = '800 33px system-ui, sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('Jeannot est toujours là', 0, 1);
    ctx.restore();
  }

  function currentVocal(t) {
    return lyricCues.some((c) => t >= c.start && t < c.end);
  }

  function drawFrame(t) {
    const fall = clamp((t - 26.48) / 2.54);
    const shake = t >= 26.48 && t <= 27.25 ? (1 - (t - 26.48) / .77) * 9 : 0;
    const shakeX = shake ? Math.sin(t * 79) * shake : 0;
    const shakeY = shake ? Math.cos(t * 67) * shake * .55 : 0;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.save(); ctx.translate(shakeX, shakeY);
    drawSky(t);

    // Maisons alignées sur une rue unique.
    drawHouse(195, 425, 710, 282, '#e6bd9c', '#965c51', 1);
    drawHouse(1000, 462, 620, 250, '#d7c39e', '#6e6675', 2);
    drawTurret(t);
    drawStreet();
    drawStairs();
    drawTree(1715, 760, .8, t);
    drawTree(95, 840, .65, t);
    drawFarVan(t);

    // La sorcière quitte puis regagne sa tourelle.
    const witchHome = { x: 449, y: 355 };
    let witchX = witchHome.x, witchY = witchHome.y, witchAlpha = 1;
    if (t >= 18.88 && t < 21.42) {
      const u = easeInOut((t - 18.88) / (21.42 - 18.88));
      witchX = lerp(witchHome.x, 35, u);
      witchY = lerp(witchHome.y, 740, u) - Math.sin(u * Math.PI) * 150;
      witchX += Math.sin(t * 18) * 8;
    } else if (t >= 21.42 && t < 23.95) {
      witchAlpha = .12;
    } else if (t >= 23.95 && t < 26.48) {
      const u = easeInOut((t - 23.95) / (26.48 - 23.95));
      witchX = lerp(35, witchHome.x, u);
      witchY = lerp(740, witchHome.y, u) - Math.sin(u * Math.PI) * 160;
    }
    drawWitch(witchX, witchY, .72, t, witchAlpha);

    // Vieille 4L : rouillée, mais complète et intacte.
    drawFourL(475, 750, 1.02, t);

    // Henri court, puis dévale l'escalier de façon cartoon.
    let henriX = 1260, henriY = 748, henriAngle = 0;
    if (t < 21.42) {
      henriX = 1290;
    } else if (t < 23.95) {
      const u = easeInOut((t - 21.42) / (23.95 - 21.42));
      henriX = lerp(1300, 1510, u);
      henriY = 744 + Math.sin(u * 12) * 9;
    } else if (t < 26.48) {
      const u = smooth(23.95, 26.48, t);
      henriX = lerp(1510, 1350, u);
      henriY = 744 - u * 45;
    } else {
      const u = fall;
      henriX = lerp(1335, 1510, u);
      henriY = lerp(695, 839, u);
      henriAngle = u * Math.PI * 2.2;
    }
    drawHenri(henriX, henriY, t, henriAngle, fall);

    // Jeannot reste au même endroit ; bouche animée sur les fenêtres provisoires de voix.
    drawJeannot(820, 782, t, currentVocal(t));

    // Enji observe, puis accourt renifler Henri après sa chute.
    const sniff = t >= 27.2;
    let dogX = 965;
    if (t >= 27.0) dogX = lerp(965, 1420, smooth(27.0, 29.02, t));
    drawEnji(dogX, 830, t, sniff);

    // Mouvement et énergie manga, avec flash bref à la chute.
    const witchRush = Math.max(smooth(18.88, 19.35, t) * (1 - smooth(20.85, 21.42, t)), smooth(23.95, 24.35, t) * (1 - smooth(25.95, 26.48, t)));
    const runRush = smooth(21.42, 21.75, t) * (1 - smooth(23.55, 23.95, t));
    drawSpeedLines(t, Math.max(witchRush * .7, runRush * .65, fall * .45));
    if (fall > .04 && fall < .48) drawDust(1410, 800, t, Math.sin(fall * Math.PI));
    if (fall > .06 && fall < .32) {
      ctx.save(); ctx.globalAlpha = (1 - fall / .32) * .74; ctx.fillStyle = '#fffdf2'; ctx.fillRect(0, 0, W, H); ctx.restore();
    }
    if (t >= 26.5 && t < 28.1) drawSfx('CRAC', 1485, 628, 1 + Math.sin(t * 21) * .07, 1 - smooth(27.7, 28.1, t), -.1);
    if (t >= 24.2 && t < 25.25) drawSfx('BAM', 555, 535, .85 + Math.sin(t * 20) * .06, 1 - smooth(24.95, 25.25, t), -.08);

    drawCartouche(t);
    drawCaption(t);
    ctx.restore();
  }

  function formatTime(s) {
    const minutes = Math.floor(s / 60);
    const seconds = (s % 60).toFixed(2).padStart(5, '0');
    return `${String(minutes).padStart(2, '0')}:${seconds}`;
  }

  function updateUI() {
    const t = Math.min(audio.currentTime || 0, SEGMENT_END);
    currentLabel.textContent = formatTime(t);
    seek.value = String(t);
    playButton.textContent = audio.paused ? '▶ Lire le couplet' : '❚❚ Pause';
  }

  playButton.addEventListener('click', async () => {
    if (audio.paused) {
      if ((audio.currentTime || 0) >= SEGMENT_END) audio.currentTime = 0;
      try { await audio.play(); }
      catch (err) { currentLabel.textContent = 'Lecture MP3 indisponible'; console.error(err); }
    } else {
      audio.pause();
    }
    updateUI();
  });

  restartButton.addEventListener('click', () => {
    audio.pause(); audio.currentTime = 0; updateUI();
  });

  seek.addEventListener('input', () => {
    audio.pause(); audio.currentTime = Number(seek.value); updateUI();
  });

  audio.addEventListener('timeupdate', () => {
    if (audio.currentTime >= SEGMENT_END) {
      audio.pause(); audio.currentTime = SEGMENT_END;
    }
    updateUI();
  });
  audio.addEventListener('pause', updateUI);
  audio.addEventListener('play', updateUI);

  function animate() {
    const t = Math.min(audio.currentTime || 0, SEGMENT_END);
    drawFrame(t);
    requestAnimationFrame(animate);
  }

  updateUI();
  drawFrame(0);
  requestAnimationFrame(animate);
})();
