"""Design system: colour tokens, elevation, glass surfaces and component styling.

All styling hangs off Streamlit's stable hooks — `data-testid` attributes and
the `.st-key-<key>` class that `key=` adds to containers and widgets. Nothing
here targets the hashed `st-emotion-cache-*` classes, which change between
Streamlit releases.
"""

import streamlit as st

_CSS = """
<style>
:root {
  --tct-bg: #070B0D;
  --tct-surface-1: #0D1417;
  --tct-surface-2: #121B1F;
  --tct-line: rgba(255,255,255,0.08);
  --tct-line-strong: rgba(255,255,255,0.14);
  --tct-text: #E8EFEA;
  --tct-muted: #93A49B;
  --tct-accent: #3FD98C;
  --tct-accent-dim: #1C7A51;
  --tct-warn: #F5B544;
  --tct-danger: #F0616D;

  --tct-e1: 0 1px 2px rgba(0,0,0,.45);
  --tct-e2: 0 6px 18px -6px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);
  --tct-e3: 0 22px 46px -22px rgba(0,0,0,.8), 0 3px 10px -3px rgba(0,0,0,.45),
            inset 0 1px 0 rgba(255,255,255,.06);
  --tct-glow: 0 0 0 1px rgba(63,217,140,.28), 0 10px 30px -12px rgba(63,217,140,.35);

  --tct-r-sm: 10px;
  --tct-r-md: 14px;
  --tct-r-lg: 20px;
  --tct-ease: cubic-bezier(.2,.7,.3,1);
}

/* ── Shell ─────────────────────────────────────────────────────────────── */
html, body, .stApp { background: var(--tct-bg); }

.stApp {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* Ambient depth behind the whole page — two soft light sources, no banding */
.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(58rem 32rem at 12% -8%, rgba(63,217,140,.07), transparent 60%),
    radial-gradient(46rem 28rem at 92% 4%, rgba(84,142,255,.055), transparent 62%);
}

/* Translucent scrim so content scrolling under the toolbar stays readable */
[data-testid="stHeader"] {
  background: linear-gradient(180deg, rgba(7,11,13,.94), rgba(7,11,13,.6) 65%, transparent);
  backdrop-filter: blur(8px);
}
[data-testid="stMain"] { position: relative; z-index: 1; }

[data-testid="stMainBlockContainer"] {
  max-width: 1180px;
  padding-top: 2.2rem;
  padding-bottom: 5rem;
}

/* ── Typography ────────────────────────────────────────────────────────── */
[data-testid="stHeading"] h1,
[data-testid="stHeading"] h2,
[data-testid="stHeading"] h3 {
  letter-spacing: -0.02em;
  color: var(--tct-text);
}
[data-testid="stHeading"] h2 { font-size: clamp(1.15rem, 1.6vw, 1.4rem); font-weight: 650; }
[data-testid="stHeading"] h3 { font-size: clamp(1rem, 1.3vw, 1.12rem); font-weight: 650; }

[data-testid="stCaptionContainer"] { color: var(--tct-muted); }
[data-testid="stMarkdown"] p, [data-testid="stMarkdown"] li { color: #CBD8CF; }
[data-testid="stMarkdown"] strong { color: var(--tct-text); }

/* Section eyebrow — a real <h2> so the document keeps its outline for screen
   readers, styled down to a small uppercase label. */
h2.tct-eyebrow {
  display: flex; align-items: center; gap: .55rem;
  font-size: .69rem; font-weight: 700; letter-spacing: .13em;
  text-transform: uppercase; color: var(--tct-muted);
  margin: 0 0 .75rem; padding: 0;
}
h2.tct-eyebrow::after {
  content: ""; flex: 1; height: 1px;
  background: linear-gradient(90deg, var(--tct-line), transparent);
}

/* Visually hidden, still announced */
.tct-sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

/* ── Surfaces: keyed containers rendered as panels ─────────────────────── */
.st-key-limitations,
.st-key-threshold_panel,
.st-key-viz_panel,
.st-key-hist_panel,
.st-key-export_panel,
.st-key-spotcheck_panel,
.st-key-upload_panel,
.st-key-scale_panel {
  background: linear-gradient(168deg, var(--tct-surface-2), var(--tct-surface-1));
  border: 1px solid var(--tct-line);
  border-radius: var(--tct-r-lg);
  box-shadow: var(--tct-e2);
  padding: 1.3rem 1.4rem;
}

/* The disclosure card is deliberately the most present surface on the page:
   it is a permanent requirement, not a dismissible warning. */
.st-key-limitations {
  background:
    linear-gradient(168deg, rgba(245,181,68,.055), rgba(245,181,68,.012) 42%),
    linear-gradient(168deg, var(--tct-surface-2), var(--tct-surface-1));
  border: 1px solid rgba(245,181,68,.26);
  box-shadow: var(--tct-e3), inset 0 0 0 1px rgba(245,181,68,.04);
  backdrop-filter: blur(14px) saturate(1.08);
}
.st-key-limitations [data-testid="stMarkdown"] li { margin-bottom: .42rem; line-height: 1.62; }
.st-key-limitations [data-testid="stMarkdown"] ul { padding-left: 1.05rem; }

/* ── KPI stat cards ────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  position: relative;
  background: linear-gradient(165deg, var(--tct-surface-2), var(--tct-surface-1));
  border: 1px solid var(--tct-line);
  border-radius: var(--tct-r-md);
  padding: 1rem 1.05rem 1.05rem;
  box-shadow: var(--tct-e2);
  overflow: hidden;
  transition: transform .4s var(--tct-ease), box-shadow .4s var(--tct-ease),
              border-color .4s var(--tct-ease);
  will-change: transform;
}
/* Specular sheen along the top edge — reads as a lit surface, not a flat box */
[data-testid="stMetric"]::after {
  content: "";
  position: absolute; inset: 0 0 auto 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.18) 30%,
              rgba(255,255,255,.18) 70%, transparent);
  opacity: .7;
}
[data-testid="stMetricLabel"] {
  font-size: .72rem !important; font-weight: 600; letter-spacing: .07em;
  text-transform: uppercase; color: var(--tct-muted) !important;
}
[data-testid="stMetricValue"] {
  font-size: clamp(1.35rem, 2.4vw, 1.85rem) !important;
  font-weight: 680; letter-spacing: -0.025em; color: var(--tct-text) !important;
  line-height: 1.15;
}
/* No metric on this page uses the delta slot for an actual change — one is a
   unit conversion, the other a provenance label. Streamlit's green "up arrow"
   would read as an increase, so the arrow is hidden and the text neutralised. */
[data-testid="stMetricDelta"] {
  font-size: .76rem !important;
  color: var(--tct-muted) !important;
  gap: 0 !important;
}
[data-testid^="stMetricDeltaIcon"] { display: none !important; }

@media (hover: hover) and (pointer: fine) {
  [data-testid="stMetric"]:hover {
    transform: perspective(900px) rotateX(3.2deg) rotateY(-2.4deg) translateY(-5px);
    box-shadow: var(--tct-e3);
    border-color: var(--tct-line-strong);
  }
}

/* ── Buttons ───────────────────────────────────────────────────────────── */
[data-testid="stBaseButton-primary"] {
  background: linear-gradient(180deg, var(--tct-accent), #29B872);
  color: #04150C;
  font-weight: 660;
  border: 1px solid rgba(255,255,255,.16);
  border-radius: var(--tct-r-sm);
  box-shadow: 0 5px 14px -8px rgba(63,217,140,.55), inset 0 1px 0 rgba(255,255,255,.3);
  transition: transform .2s var(--tct-ease), box-shadow .25s var(--tct-ease),
              filter .2s var(--tct-ease);
}
[data-testid="stBaseButton-primary"]:hover {
  transform: translateY(-2px);
  filter: brightness(1.06);
  box-shadow: 0 10px 22px -10px rgba(63,217,140,.6), inset 0 1px 0 rgba(255,255,255,.35);
}
[data-testid="stBaseButton-primary"]:active { transform: translateY(0); }

[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondaryFormSubmit"],
[data-testid="stDownloadButton"] button {
  background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.02));
  border: 1px solid var(--tct-line-strong);
  border-radius: var(--tct-r-sm);
  color: var(--tct-text);
  font-weight: 560;
  box-shadow: var(--tct-e1);
  transition: transform .2s var(--tct-ease), border-color .2s var(--tct-ease),
              background .2s var(--tct-ease);
}
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stBaseButton-secondaryFormSubmit"]:hover,
[data-testid="stDownloadButton"] button:hover {
  transform: translateY(-2px);
  border-color: rgba(63,217,140,.45);
  background: linear-gradient(180deg, rgba(63,217,140,.1), rgba(63,217,140,.03));
  color: var(--tct-text);
}

/* ── Upload dropzones ──────────────────────────────────────────────────── */
[data-testid="stFileUploaderDropzone"] {
  background: linear-gradient(165deg, rgba(255,255,255,.035), rgba(255,255,255,.012));
  border: 1px dashed rgba(255,255,255,.18);
  border-radius: var(--tct-r-md);
  transition: transform .3s var(--tct-ease), border-color .3s var(--tct-ease),
              box-shadow .3s var(--tct-ease);
}
@media (hover: hover) and (pointer: fine) {
  [data-testid="stFileUploaderDropzone"]:hover {
    transform: translateY(-3px);
    border-color: rgba(63,217,140,.5);
    box-shadow: var(--tct-glow);
  }
}
[data-testid="stFileUploaderDropzoneInstructions"] { color: var(--tct-muted); }

/* ── Slider ────────────────────────────────────────────────────────────── */
[data-testid="stSliderThumbValue"] { color: var(--tct-accent) !important; font-weight: 650; }
[data-testid="stSliderTickBar"] { color: var(--tct-muted); }

/* ── Inputs ────────────────────────────────────────────────────────────── */
[data-testid="stNumberInputContainer"] {
  background: rgba(255,255,255,.03);
  border: 1px solid var(--tct-line-strong);
  border-radius: var(--tct-r-sm);
  transition: border-color .2s var(--tct-ease), box-shadow .2s var(--tct-ease);
}
[data-testid="stNumberInputContainer"]:focus-within {
  border-color: rgba(63,217,140,.55);
  box-shadow: 0 0 0 3px rgba(63,217,140,.14);
}
[data-testid="stWidgetLabel"] p {
  font-size: .82rem; font-weight: 560; color: #BECBC3;
}

/* ── Keyboard focus ────────────────────────────────────────────────────── */
:where(button, input, select, textarea, a, [role="button"], [tabindex]):focus-visible {
  outline: 2px solid var(--tct-accent);
  outline-offset: 2px;
}

/* ── Alerts ────────────────────────────────────────────────────────────── */
[data-testid="stAlertContainer"] {
  border-radius: var(--tct-r-md);
  border: 1px solid var(--tct-line);
  box-shadow: var(--tct-e1);
}

/* Chart panel fills its column so it sits level with the imagery beside it.
   Streamlit nests a stLayoutWrapper between the column and the container,
   and that wrapper defaults to `flex: 0 1 auto` — so it has to grow too. */
[data-testid="stColumn"]:has(.st-key-hist_panel) [data-testid="stLayoutWrapper"] {
  flex: 1 1 auto;
}
.st-key-hist_panel { flex: 1 1 auto; justify-content: center; }

/* Export row: keep the fallback note optically centred against the button */
.st-key-export_panel [data-testid="stColumn"] {
  display: flex; flex-direction: column; justify-content: center;
}
.st-key-hist_panel [data-testid="stImage"] img { border: none; box-shadow: none; }

/* ── Imagery panel — deliberately flat. This is data under inspection;
      tilting or tinting it would misrepresent what the model saw. ─────── */
.st-key-viz_panel [data-testid="stImage"] img {
  border-radius: var(--tct-r-md);
  border: 1px solid var(--tct-line);
  box-shadow: var(--tct-e2);
}
[data-testid="stImageCaption"] { color: var(--tct-muted) !important; font-size: .8rem !important; }

/* ── Trust chip — scale provenance ─────────────────────────────────────── */
.tct-chip {
  display: inline-flex; align-items: center; gap: .5rem;
  padding: .42rem .78rem;
  border-radius: 999px;
  font-size: .79rem; font-weight: 600;
  border: 1px solid transparent;
}
.tct-chip .tct-dot {
  width: 7px; height: 7px; border-radius: 50%; flex: none;
}
.tct-chip--verified {
  background: rgba(63,217,140,.1); border-color: rgba(63,217,140,.32); color: #8DEBBB;
}
.tct-chip--verified .tct-dot {
  background: var(--tct-accent); box-shadow: 0 0 0 3px rgba(63,217,140,.18);
}
.tct-chip--unverified {
  background: rgba(245,181,68,.1); border-color: rgba(245,181,68,.34); color: #F7CE85;
}
.tct-chip--unverified .tct-dot {
  background: var(--tct-warn); box-shadow: 0 0 0 3px rgba(245,181,68,.18);
}
.tct-chip-note {
  margin: .55rem 0 0; font-size: .82rem; color: var(--tct-muted); line-height: 1.55;
}

/* ── Divider ───────────────────────────────────────────────────────────── */
hr, [data-testid="stDivider"] hr {
  border: none; height: 1px;
  background: linear-gradient(90deg, transparent, var(--tct-line) 18%,
              var(--tct-line) 82%, transparent);
}

/* ── Entrance motion — one pass, no looping ambient animation ──────────── */
@keyframes tctRise {
  from { opacity: 0; transform: translate3d(0, 10px, 0); }
  to   { opacity: 1; transform: none; }
}
[data-testid="stMainBlockContainer"] > div > div > [data-testid="stVerticalBlock"] > div {
  animation: tctRise .5s var(--tct-ease) both;
}

/* ── Spinner ───────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] svg { color: var(--tct-accent); }

/* ── Responsive ────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  [data-testid="stMainBlockContainer"] { padding-top: 1.2rem; padding-bottom: 3rem; }
  [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
  }
  [data-testid="stMetric"]:hover { transform: none; }
}
</style>
"""


def inject() -> None:
    """Apply the design system. Safe to call once per script run.

    Uses st.markdown rather than st.html: a style-only st.html block is
    silently dropped when it is the first element rendered after
    st.set_page_config (reproduced on Streamlit 1.63).
    """
    st.markdown(_CSS, unsafe_allow_html=True)


def page_heading(text: str) -> None:
    """The document's h1. The visible title lives in the hero iframe, which is
    a separate document, so the page needs its own heading for screen readers."""
    st.html(f'<h1 class="tct-sr-only">{text}</h1>')


def eyebrow(text: str) -> None:
    """Section heading, styled as a small uppercase label with a trailing rule."""
    st.html(f'<h2 class="tct-eyebrow">{text}</h2>')


def trust_chip(verified: bool, label: str, note: str = "") -> None:
    """Provenance indicator for a value the rest of the page depends on."""
    variant = "verified" if verified else "unverified"
    note_html = f'<p class="tct-chip-note">{note}</p>' if note else ""
    st.html(
        f'<div><span class="tct-chip tct-chip--{variant}">'
        f'<span class="tct-dot"></span>{label}</span></div>{note_html}'
    )
