"""Interactive 3D hero.

A canopy point cloud rendered with hand-written perspective projection on a
2D canvas — no Three.js, no CDN, ~3KB of inline JS. It runs inside Streamlit's
sandboxed component iframe, which is the only place scripts execute.

Guards: pauses when the tab is hidden, renders a single static frame under
`prefers-reduced-motion`, and drops to a static gradient below 768px or on
coarse-pointer devices.
"""

import streamlit as st

HERO_HEIGHT = 340

_HTML = """
<!doctype html>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: transparent; overflow: hidden; }
  #wrap {
    position: relative; height: 340px; border-radius: 20px; overflow: hidden;
    border: 1px solid rgba(255,255,255,.09);
    background: linear-gradient(168deg, #121B1F, #0A1113 60%, #070B0D);
    box-shadow: 0 22px 46px -22px rgba(0,0,0,.8), inset 0 1px 0 rgba(255,255,255,.06);
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
  }
  canvas { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
  #fallback {
    position: absolute; inset: 0; display: none;
    background:
      radial-gradient(28rem 18rem at 78% 30%, rgba(63,217,140,.20), transparent 62%),
      radial-gradient(22rem 16rem at 62% 78%, rgba(84,142,255,.14), transparent 64%);
  }
  #scrim {
    position: absolute; inset: 0;
    background: linear-gradient(90deg, rgba(7,11,13,.95) 0%, rgba(7,11,13,.82) 42%,
                rgba(7,11,13,.25) 70%, transparent 88%);
  }
  #copy {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    justify-content: center; gap: .75rem; padding: 0 clamp(1.3rem, 4vw, 2.6rem);
    max-width: 40rem;
  }
  .tag {
    display: inline-flex; align-items: center; gap: .5rem; width: fit-content;
    padding: .34rem .7rem; border-radius: 999px;
    background: rgba(63,217,140,.1); border: 1px solid rgba(63,217,140,.3);
    color: #8DEBBB; font-size: .68rem; font-weight: 700;
    letter-spacing: .12em; text-transform: uppercase;
  }
  .tag i {
    width: 6px; height: 6px; border-radius: 50%; background: #3FD98C;
    box-shadow: 0 0 0 3px rgba(63,217,140,.2);
  }
  h1 {
    margin: 0; color: #E8EFEA; letter-spacing: -0.032em; line-height: 1.08;
    font-size: clamp(1.5rem, 3.6vw, 2.3rem); font-weight: 700;
  }
  h1 span {
    background: linear-gradient(92deg, #3FD98C, #7FE9C0 55%, #A7D9FF);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  p {
    margin: 0; color: #A9B8AF; font-size: clamp(.84rem, 1.3vw, .95rem);
    line-height: 1.6; max-width: 30rem;
  }
  @media (max-width: 768px) {
    #wrap { height: 300px; }
    canvas { display: none; }
    #fallback { display: block; }
    #scrim { background: linear-gradient(180deg, rgba(7,11,13,.86), rgba(7,11,13,.6)); }
  }
</style>

<div id="wrap">
  <canvas id="c"></canvas>
  <div id="fallback"></div>
  <div id="scrim"></div>
  <div id="copy">
    <span class="tag"><i></i>Canopy analysis</span>
    <h1>Tree crown detection &amp;<br><span>canopy area estimation</span></h1>
    <p>Detect individual crowns in aerial imagery and measure the area they
       cover — with every number traceable to how it was computed.</p>
  </div>
</div>

<script>
(function () {
  var canvas = document.getElementById('c');
  var ctx = canvas.getContext('2d');
  var fallback = document.getElementById('fallback');
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Touch-primary devices only. A touchscreen laptop reports `any-pointer:
  // coarse` but still has a mouse, and should keep the 3D scene.
  var liteMode = window.matchMedia('(max-width: 768px), (hover: none) and (pointer: coarse)');

  var W = 0, H = 0, DPR = Math.min(window.devicePixelRatio || 1, 2);

  function resize() {
    var r = canvas.getBoundingClientRect();
    W = r.width; H = r.height;
    canvas.width = W * DPR; canvas.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  // ── Scene: clustered points forming crown domes on a ground disc ──────
  var crowns = [], points = [];
  (function build() {
    var rand = (function (s) {          // deterministic, so the scene is stable
      return function () { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
    })(20240917);

    for (var i = 0; i < 26; i++) {
      var a = rand() * Math.PI * 2, rad = 70 + rand() * 200;
      var cx = Math.cos(a) * rad, cz = Math.sin(a) * rad;
      var size = 13 + rand() * 17;
      crowns.push({ x: cx, z: cz, y: -size * 0.5, r: size });
      var n = 4 + Math.floor(rand() * 4);
      for (var j = 0; j < n; j++) {
        var t = rand() * Math.PI * 2, u = rand();
        points.push({
          x: cx + Math.cos(t) * size * u,
          y: -size * (0.3 + rand() * 0.9),
          z: cz + Math.sin(t) * size * u,
          s: 1.1 + rand() * 2.0,
          tw: rand() * Math.PI * 2
        });
      }
    }
  })();

  var focal = 460, dist = 600, pitch = 0.46, spin = 0;
  var mx = 0, my = 0, tmx = 0, tmy = 0;

  document.addEventListener('pointermove', function (e) {
    tmx = (e.clientX / window.innerWidth - 0.5) * 2;
    tmy = (e.clientY / window.innerHeight - 0.5) * 2;
  });
  document.addEventListener('pointerleave', function () { tmx = 0; tmy = 0; });

  // Yaw about Y, then pitch about X — an aerial three-quarter view, which is
  // what gives the canopy real vertical spread instead of a flat band.
  function project(p, cos, sin, cosP, sinP) {
    var x = p.x * cos - p.z * sin;
    var zr = p.x * sin + p.z * cos;
    var y = p.y * cosP - zr * sinP;
    var z = p.y * sinP + zr * cosP + dist;
    if (z < 30) return null;
    var k = focal / z;
    return { sx: W * 0.63 + x * k, sy: H * 0.52 + y * k, k: k, z: z };
  }

  function frame(t) {
    ctx.clearRect(0, 0, W, H);
    mx += (tmx - mx) * 0.05;
    my += (tmy - my) * 0.05;
    if (!reduced) spin += 0.0016;
    var yaw = spin + mx * 0.26;
    var cos = Math.cos(yaw), sin = Math.sin(yaw);
    var pit = pitch + my * 0.1;
    var cosP = Math.cos(pit), sinP = Math.sin(pit);

    // Ground plane — the depth reference the crowns sit on
    ctx.strokeStyle = 'rgba(120,180,150,.10)';
    ctx.lineWidth = 1;
    for (var g = -300; g <= 300; g += 60) {
      ctx.beginPath();
      var drawn = false;
      for (var s = -300; s <= 300; s += 30) {
        var q = project({ x: g, y: 0, z: s }, cos, sin, cosP, sinP);
        if (!q) { drawn = false; continue; }
        if (!drawn) { ctx.moveTo(q.sx, q.sy); drawn = true; } else ctx.lineTo(q.sx, q.sy);
      }
      ctx.stroke();
      ctx.beginPath(); drawn = false;
      for (var s2 = -300; s2 <= 300; s2 += 30) {
        var q2 = project({ x: s2, y: 0, z: g }, cos, sin, cosP, sinP);
        if (!q2) { drawn = false; continue; }
        if (!drawn) { ctx.moveTo(q2.sx, q2.sy); drawn = true; } else ctx.lineTo(q2.sx, q2.sy);
      }
      ctx.stroke();
    }

    // Detection brackets — the product's own motif, cycling slowly
    var beat = t * 0.00035;
    for (var ci = 0; ci < crowns.length; ci++) {
      var phase = Math.sin(beat + ci * 1.7);
      if (phase < 0.72) continue;
      var c = crowns[ci];
      var pc = project(c, cos, sin, cosP, sinP);
      if (!pc) continue;
      var half = c.r * pc.k * 1.45;
      var alpha = (phase - 0.72) / 0.28 * 0.55;
      ctx.strokeStyle = 'rgba(63,217,140,' + alpha.toFixed(3) + ')';
      ctx.lineWidth = 1.2;
      var arm = half * 0.42;
      [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(function (d) {
        var x = pc.sx + d[0] * half, y = pc.sy + d[1] * half;
        ctx.beginPath();
        ctx.moveTo(x - d[0] * arm, y); ctx.lineTo(x, y); ctx.lineTo(x, y - d[1] * arm);
        ctx.stroke();
      });
    }

    // Canopy points, painter's algorithm so near crowns occlude far ones
    var proj = [];
    for (var i = 0; i < points.length; i++) {
      var p = points[i];
      var q = project(p, cos, sin, cosP, sinP);
      if (q) { q.p = p; proj.push(q); }
    }
    proj.sort(function (a, b) { return b.z - a.z; });

    for (var n = 0; n < proj.length; n++) {
      var d = proj[n];
      var depth = Math.max(0, Math.min(1, (900 - d.z) / 620));
      var rr = Math.max(0.6, d.p.s * d.k * 1.9);
      var tw = reduced ? 1 : 0.82 + 0.18 * Math.sin(t * 0.0011 + d.p.tw);
      var a = (0.16 + depth * 0.62) * tw;
      var grad = ctx.createRadialGradient(d.sx, d.sy, 0, d.sx, d.sy, rr * 2.6);
      grad.addColorStop(0, 'rgba(126,233,185,' + a.toFixed(3) + ')');
      grad.addColorStop(0.45, 'rgba(63,217,140,' + (a * 0.42).toFixed(3) + ')');
      grad.addColorStop(1, 'rgba(63,217,140,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(d.sx, d.sy, rr * 2.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  var raf = null, running = false;
  function loop(t) {
    if (W > 0) frame(t);
    raf = requestAnimationFrame(loop);
  }
  function start() { if (!running) { running = true; raf = requestAnimationFrame(loop); } }
  function stop() { running = false; if (raf) cancelAnimationFrame(raf); raf = null; }

  // Streamlit sizes the component iframe after the script runs, so mode and
  // canvas size are re-evaluated on every layout change rather than once.
  function applyMode() {
    if (liteMode.matches) {
      stop();
      fallback.style.display = 'block';
      canvas.style.display = 'none';
    } else {
      fallback.style.display = 'none';
      canvas.style.display = 'block';
      resize();
      if (reduced) { stop(); frame(0); } else { start(); }
    }
  }

  if (liteMode.addEventListener) liteMode.addEventListener('change', applyMode);
  else liteMode.addListener(applyMode);

  if (window.ResizeObserver) {
    new ResizeObserver(function () {
      if (!liteMode.matches) { resize(); if (reduced) frame(0); }
    }).observe(document.getElementById('wrap'));
  }
  window.addEventListener('resize', applyMode);
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stop();
    else if (!reduced && !liteMode.matches) start();
  });

  applyMode();
})();
</script>
"""


def render() -> None:
    """Draw the hero. Falls back to a static gradient on mobile/touch.

    `_HTML` is a static literal with no interpolated input, so passing it to
    st.iframe (which embeds raw HTML unsanitized) carries no injection risk.
    """
    st.iframe(_HTML, height=HERO_HEIGHT + 8)
