import streamlit as st
import streamlit.components.v1 as components
import httpx

API_URL = "http://localhost:8000/chat"

# ── Moon ─────────────────────────────────────────────────────────────────────
_MOON = """<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" width="180" height="180">
  <defs>
    <radialGradient id="mhalo" cx="50%" cy="50%" r="50%">
      <stop offset="0%"   stop-color="#8b2020" stop-opacity="0.38"/>
      <stop offset="55%"  stop-color="#5a1010" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="#000"    stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="msurf" cx="42%" cy="38%" r="50%">
      <stop offset="0%"   stop-color="#f7edcc"/>
      <stop offset="65%"  stop-color="#e8d090"/>
      <stop offset="100%" stop-color="#c8a055"/>
    </radialGradient>
    <filter id="mglow">
      <feGaussianBlur in="SourceGraphic" stdDeviation="7" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <circle cx="100" cy="100" r="98"  fill="url(#mhalo)"/>
  <circle cx="100" cy="100" r="52"  fill="url(#msurf)" filter="url(#mglow)"/>
  <circle cx="84"  cy="88"  r="7"   fill="#d4a855" opacity="0.45"/>
  <circle cx="113" cy="110" r="4.5" fill="#c89848" opacity="0.35"/>
  <circle cx="96"  cy="116" r="3.5" fill="#d4a855" opacity="0.30"/>
  <circle cx="108" cy="86"  r="2.5" fill="#c89848" opacity="0.25"/>
</svg>"""

# ── Castle (30 % bigger: 400→520 x 310→403) ───────────────────────────────
_CASTLE = """<svg viewBox="0 0 400 310" xmlns="http://www.w3.org/2000/svg" width="520" height="403">
<defs>
  <filter id="wglow" x="-150%" y="-150%" width="400%" height="400%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<style>
  .cw  { animation: cflicker  3.2s ease-in-out infinite; }
  .cw2 { animation: cflicker2 4.1s ease-in-out infinite 0.6s; }
  .cw3 { animation: cflicker3 2.7s ease-in-out infinite 1.3s; }
  @keyframes cflicker  { 0%,100%{opacity:.95} 20%{opacity:.60} 55%{opacity:1}  80%{opacity:.50} }
  @keyframes cflicker2 { 0%,100%{opacity:.90} 30%{opacity:.55} 60%{opacity:.95} 85%{opacity:.65} }
  @keyframes cflicker3 { 0%,100%{opacity:.85} 15%{opacity:.70} 50%{opacity:1}  75%{opacity:.45} }
</style>
<g fill="#1a1210">
  <polygon points="10,170 24,215 38,170"/>
  <rect x="10" y="204" width="6"  height="13"/>
  <rect x="20" y="204" width="6"  height="13"/>
  <rect x="30" y="204" width="6"  height="13"/>
  <rect x="13" y="213" width="22" height="97"/>
  <rect x="35" y="258" width="20" height="52"/>
  <polygon points="54,112 76,162 98,112"/>
  <rect x="54" y="152" width="11" height="13"/>
  <rect x="69" y="152" width="11" height="13"/>
  <rect x="84" y="152" width="11" height="13"/>
  <rect x="52" y="162" width="48" height="148"/>
  <rect x="100" y="215" width="26" height="95"/>
  <rect x="157" y="70"  width="86" height="62"/>
  <rect x="157" y="55"  width="13" height="18"/>
  <rect x="174" y="55"  width="13" height="18"/>
  <rect x="191" y="55"  width="13" height="18"/>
  <rect x="208" y="55"  width="13" height="18"/>
  <rect x="225" y="55"  width="13" height="18"/>
  <rect x="118" y="130" width="164" height="180"/>
  <rect x="118" y="116" width="17" height="17"/>
  <rect x="139" y="116" width="17" height="17"/>
  <rect x="160" y="116" width="17" height="17"/>
  <rect x="181" y="116" width="17" height="17"/>
  <rect x="202" y="116" width="17" height="17"/>
  <rect x="223" y="116" width="17" height="17"/>
  <rect x="244" y="116" width="17" height="17"/>
  <rect x="265" y="116" width="17" height="17"/>
  <path d="M172,310 L172,262 Q200,235 228,262 L228,310 Z" fill="#130808"/>
  <rect x="274" y="215" width="26" height="95"/>
  <polygon points="302,112 324,162 346,112"/>
  <rect x="302" y="152" width="11" height="13"/>
  <rect x="317" y="152" width="11" height="13"/>
  <rect x="332" y="152" width="11" height="13"/>
  <rect x="300" y="162" width="48" height="148"/>
  <rect x="345" y="258" width="20" height="52"/>
  <polygon points="362,170 376,215 390,170"/>
  <rect x="362" y="204" width="6"  height="13"/>
  <rect x="372" y="204" width="6"  height="13"/>
  <rect x="382" y="204" width="6"  height="13"/>
  <rect x="365" y="213" width="22" height="97"/>
</g>
<rect class="cw"  x="70"  y="195" width="13" height="24" rx="6"  fill="#e88a0a" filter="url(#wglow)"/>
<rect class="cw3" x="142" y="162" width="14" height="30" rx="7"  fill="#f09520" filter="url(#wglow)"/>
<rect class="cw2" x="182" y="150" width="36" height="52" rx="18" fill="#e88a0a" filter="url(#wglow)"/>
<rect class="cw"  x="248" y="162" width="14" height="30" rx="7"  fill="#f09520" filter="url(#wglow)"/>
<rect class="cw3" x="317" y="195" width="13" height="24" rx="6"  fill="#e88a0a" filter="url(#wglow)"/>
</svg>"""

# ── Hills ─────────────────────────────────────────────────────────────────────
_HILLS = """<svg viewBox="0 0 1200 160" preserveAspectRatio="none"
     xmlns="http://www.w3.org/2000/svg" width="100%" height="160">
  <path d="M0,160 L0,88 Q130,28 250,72 Q400,118 530,50
           Q660,4 790,60 Q930,118 1060,46 Q1140,12 1200,68
           L1200,160 Z" fill="#0d0b0b"/>
  <path d="M0,160 L0,118 Q90,86 200,108 Q340,132 460,100
           Q590,70 720,108 Q850,136 980,96
           Q1080,74 1200,114 L1200,160 Z" fill="#090707"/>
</svg>"""

# ── Bat ───────────────────────────────────────────────────────────────────────
_BAT = """<svg class="bat-svg" viewBox="-32 -22 64 44"
     xmlns="http://www.w3.org/2000/svg" width="56" height="38">
  <ellipse cx="0" cy="2" rx="5" ry="6" fill="#110c0c"/>
  <polygon points="-4,-5 -8,-15 -2,-6"  fill="#110c0c"/>
  <polygon points="4,-5  8,-15  2,-6"   fill="#110c0c"/>
  <path d="M-5,0 C-12,-14 -30,-6 -30,4 C-23,10 -17,6 -11,9 C-8,5 -6,2 -5,0 Z" fill="#0e0a0a"/>
  <path d="M5,0  C12,-14  30,-6  30,4 C23,10  17,6  11,9 C8,5  6,2  5,0 Z"    fill="#0e0a0a"/>
</svg>"""

# ── Zombie ────────────────────────────────────────────────────────────────────
_ZOMBIE = """<svg class="zombie-svg" viewBox="-15 -46 30 48"
     xmlns="http://www.w3.org/2000/svg" width="36" height="58">
  <ellipse cx="0"    cy="-39" rx="6"   ry="7"   fill="#1a1e10"/>
  <rect    x="-5.5"  y="-32"  width="11" height="16" fill="#171b0f" rx="1"/>
  <line x1="-5.5" y1="-26" x2="-14" y2="-30" stroke="#1a1e10" stroke-width="3.5" stroke-linecap="round"/>
  <line x1="5.5"  y1="-26" x2="13"  y2="-29" stroke="#1a1e10" stroke-width="3.5" stroke-linecap="round"/>
  <g class="z-leg-l"><rect x="-5"   y="-16" width="4.5" height="14" rx="2" fill="#171b0f"/></g>
  <g class="z-leg-r"><rect x="0.5"  y="-16" width="4.5" height="14" rx="2" fill="#171b0f"/></g>
  <circle class="zombie-eye" cx="-2.5" cy="-40" r="1.3" fill="#dd1111"/>
  <circle class="zombie-eye" cx="2.5"  cy="-40" r="1.3" fill="#dd1111"/>
</svg>"""


def _inject_background() -> None:
    castle = _CASTLE.replace("`", "\\`").replace("\n", " ")
    hills  = _HILLS .replace("`", "\\`").replace("\n", " ")
    moon   = _MOON  .replace("`", "\\`").replace("\n", " ")
    bat    = _BAT   .replace("`", "\\`").replace("\n", " ")
    zombie = _ZOMBIE.replace("`", "\\`").replace("\n", " ")

    components.html(f"""
<script>
(function() {{
  var par = window.parent;
  var doc = par.document;
  if (doc.getElementById('hg-bg')) return;

  // ── CSS ──────────────────────────────────────────────────────────────
  var style = doc.createElement('style');
  style.id = 'hg-style';
  style.textContent = `
    [data-testid="stAppViewContainer"],[data-testid="stApp"],
    .main,.main>div {{ background:transparent !important; }}
    [data-testid="stHeader"] {{ background:transparent !important; box-shadow:none !important; }}
    [data-testid="stBottom"] {{ background:transparent !important; }}
    body {{ background:#050202 !important; }}
    .bat-svg {{
      animation: bat-flap 0.25s ease-in-out infinite alternate;
      overflow: visible;
    }}
    @keyframes bat-flap {{
      0%   {{ transform: scaleY(1);   }}
      100% {{ transform: scaleY(0.5); }}
    }}
    .zombie-eye {{ filter: drop-shadow(0 0 3px #cc2222); }}
    @keyframes fog-a {{ 0%,100%{{transform:translateX(0);opacity:.7}} 50%{{transform:translateX(6%);opacity:.35}} }}
    @keyframes fog-b {{ 0%,100%{{transform:translateX(0);opacity:.5}} 50%{{transform:translateX(-5%);opacity:.25}} }}
    @keyframes fog-c {{ 0%,100%{{transform:translateX(0);opacity:.55}} 50%{{transform:translateX(8%);opacity:.20}} }}
    [data-testid="stChatInputContainer"] textarea::placeholder {{
      color: rgba(180,70,70,0.55) !important;
      font-style: italic;
    }}
  `;
  doc.head.appendChild(style);

  // ── Background container ──────────────────────────────────────────────
  var bg = doc.createElement('div');
  bg.id = 'hg-bg';
  bg.style.cssText =
    'position:fixed;inset:0;z-index:-1;overflow:hidden;' +
    'background:radial-gradient(ellipse at 50% -5%,' +
      '#6b2020 0%,#3d1010 18%,#1e0a0a 40%,#0d0505 65%,#050202 100%);';
  doc.body.insertBefore(bg, doc.body.firstChild);

  // ── Star canvas ───────────────────────────────────────────────────────
  var canvas = doc.createElement('canvas');
  canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;';
  bg.appendChild(canvas);
  var ctx = canvas.getContext('2d');
  function resize() {{ canvas.width = par.innerWidth; canvas.height = par.innerHeight; }}
  resize();
  par.addEventListener('resize', resize);
  var stars = Array.from({{length: 85}}, function() {{
    return {{
      x: Math.random(), y: Math.random() * 0.60,
      r: Math.random() * 1.3 + 0.35,
      phase: Math.random() * Math.PI * 2,
      speed: 0.3 + Math.random() * 1.3,
      base:  0.3 + Math.random() * 0.7
    }};
  }});

  // ── Moon (behind castle in DOM) ───────────────────────────────────────
  var moonEl = doc.createElement('div');
  moonEl.innerHTML = `{moon}`;
  moonEl.style.cssText = 'position:absolute;bottom:310px;right:470px;opacity:0.90;';
  bg.appendChild(moonEl);

  // ── Castle ────────────────────────────────────────────────────────────
  var castleEl = doc.createElement('div');
  castleEl.innerHTML = `{castle}`;
  castleEl.style.cssText = 'position:absolute;bottom:55px;right:1%;filter:drop-shadow(0 0 22px rgba(120,30,10,0.55));';
  bg.appendChild(castleEl);

  // ── Hills ─────────────────────────────────────────────────────────────
  var hillsEl = doc.createElement('div');
  hillsEl.innerHTML = `{hills}`;
  hillsEl.style.cssText = 'position:absolute;bottom:0;left:0;right:0;';
  bg.appendChild(hillsEl);

  // ── Zombies (along the horizon) ───────────────────────────────────────
  var zombies = [];
  for (var i = 0; i < 8; i++) {{
    var zd = doc.createElement('div');
    zd.innerHTML = `{zombie}`;
    zd.style.cssText = 'position:absolute;pointer-events:none;';
    bg.appendChild(zd);
    zombies.push({{
      el:         zd,
      x:          Math.random() * par.innerWidth,
      baseBottom: 86 + Math.random() * 22,
      vx:         (0.06 + Math.random() * 0.16) * (Math.random() > 0.5 ? 1 : -1),
      phase:      Math.random() * Math.PI * 2,
      scale:      0.72 + Math.random() * 0.50
    }});
  }}

  // ── Fog layers ────────────────────────────────────────────────────────
  [
    {{ b:60,  h:48, a:'fog-a', d:'18s', dl:'0s'   }},
    {{ b:88,  h:32, a:'fog-b', d:'25s', dl:'-9s'  }},
    {{ b:112, h:22, a:'fog-c', d:'21s', dl:'-15s' }}
  ].forEach(function(f) {{
    var fog = doc.createElement('div');
    fog.style.cssText =
      'position:absolute;bottom:' + f.b + 'px;left:-10%;right:-10%;height:' + f.h + 'px;' +
      'background:radial-gradient(ellipse at 50% 80%,' +
        'rgba(200,200,220,.09) 0%,rgba(180,180,210,.04) 55%,transparent 100%);' +
      'border-radius:50%;pointer-events:none;' +
      'animation:' + f.a + ' ' + f.d + ' ease-in-out infinite ' + f.dl + ';';
    bg.appendChild(fog);
  }});

  // ── Bats (12) ─────────────────────────────────────────────────────────
  var bats = [];
  for (var i = 0; i < 12; i++) {{
    var bd = doc.createElement('div');
    bd.innerHTML = `{bat}`;
    bd.style.cssText = 'position:absolute;pointer-events:none;';
    bg.appendChild(bd);
    bats.push({{
      el:     bd,
      x:      Math.random() * par.innerWidth,
      y:      30 + Math.random() * (par.innerHeight * 0.45),
      vx:     (0.2 + Math.random() * 0.8) * (Math.random() > 0.5 ? 1 : -1),
      yAmp:   10 + Math.random() * 28,
      yFreq:  0.3 + Math.random() * 0.7,
      yPhase: Math.random() * Math.PI * 2
    }});
  }}

  // ── Animation loop ────────────────────────────────────────────────────
  function draw(t) {{
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Stars
    stars.forEach(function(s) {{
      var a = s.base * (0.5 + 0.5 * Math.sin(t * s.speed + s.phase));
      ctx.beginPath();
      ctx.arc(s.x * canvas.width, s.y * canvas.height, s.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,248,220,' + a.toFixed(3) + ')';
      ctx.fill();
    }});

    // Zombies
    zombies.forEach(function(z) {{
      z.x += z.vx;
      var W = canvas.width;
      if (z.x >  W + 40) z.x = -40;
      if (z.x < -40)     z.x =  W + 40;
      var bob = 1.8 * Math.abs(Math.sin(t * 3.5 + z.phase));
      z.el.style.left   = z.x + 'px';
      z.el.style.bottom = (z.baseBottom + bob) + 'px';
      var flip = z.vx < 0 ? 'scaleX(-1)' : 'scaleX(1)';
      z.el.style.transform = flip + ' scale(' + z.scale + ')';
      var la = Math.sin(t * 3.5 + z.phase) * 22;
      var lL = z.el.querySelector('.z-leg-l');
      var lR = z.el.querySelector('.z-leg-r');
      if (lL) lL.setAttribute('transform', 'rotate(' + la       + ' -2.75 -16)');
      if (lR) lR.setAttribute('transform', 'rotate(' + (-la)    + '  2.75 -16)');
    }});

    // Bats
    bats.forEach(function(b) {{
      b.x += b.vx;
      var W = canvas.width;
      if (b.x >  W + 40) b.x = -40;
      if (b.x < -40)     b.x =  W + 40;
      var y = b.y + b.yAmp * Math.sin(t * b.yFreq + b.yPhase);
      b.el.style.left      = b.x + 'px';
      b.el.style.top       = y   + 'px';
      b.el.style.transform = b.vx < 0 ? 'scaleX(-1)' : 'scaleX(1)';
    }});

    par.requestAnimationFrame(function(ts) {{ draw(ts / 1000); }});
  }}
  par.requestAnimationFrame(function(ts) {{ draw(ts / 1000); }});

  // ── Style stBottom + input (no blood drip) ───────────────────────────
  function styleBottom() {{
    var stBot = doc.querySelector('[data-testid="stBottom"]');
    if (stBot) {{
      stBot.style.setProperty('background', 'linear-gradient(to top,#0f0303,#1e0606)', 'important');
      stBot.style.setProperty('border-top', 'none', 'important');
      stBot.style.setProperty('box-shadow', 'none', 'important');
    }}
    var inp = doc.querySelector('[data-testid="stChatInputContainer"]');
    if (inp) {{
      inp.style.setProperty('border', '1px solid rgba(139,0,0,0.5)', 'important');
      inp.style.setProperty('border-radius', '10px', 'important');
      inp.style.setProperty('box-shadow', '0 0 12px rgba(139,0,0,0.25)', 'important');
    }}
  }}
  styleBottom();
  setTimeout(styleBottom, 350);
  setTimeout(styleBottom, 1000);
  par.addEventListener('resize', styleBottom);
}})();
</script>
""", height=0)


# ── App ───────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HorRAGor BOT",
    page_icon="🩸",
    layout="centered",
)

_inject_background()

st.title("🩸 HorRAGor BOT")
st.caption("Ton guide dans l'univers de l'horreur — cinéma, littérature, jeux vidéo.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Murmure ton sort dans l'obscurité..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("HorRAGor réfléchit..."):
            try:
                response = httpx.post(
                    API_URL,
                    json={"question": prompt},
                    timeout=60.0,
                )
                response.raise_for_status()
                answer = response.json().get("answer", "Pas de réponse reçue.")
            except httpx.ConnectError:
                answer = "Impossible de joindre le serveur. Vérifie que l'API FastAPI est lancée."
            except httpx.HTTPStatusError as e:
                answer = f"Erreur serveur ({e.response.status_code})."
            except Exception as e:
                answer = f"Erreur inattendue : {e}"

        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
