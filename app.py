import streamlit as st
import re, feedparser, time, random, os, json
# torch + transformers imported lazily in load_model() to keep initial render light (avoids OOM on Render free tier)
from datetime import datetime, timezone
import hashlib, email.utils as _eu
import urllib.request
import urllib.error
try:
    import tweepy as _tweepy; _TWEEPY_OK = True
except ImportError:
    _TWEEPY_OK = False

try:
    import instaloader as _instaloader; _IL_OK = True
except ImportError:
    _IL_OK = False

try:
    import plotly.graph_objects as go
    _PLOTLY_OK = True
except ImportError:
    _PLOTLY_OK = False

import itertools, urllib.parse as _urlparse

def _get_secret(key: str, default: str = "") -> str:
    """Safe secrets access for Render/cloud where .streamlit/secrets.toml may be missing."""
    try:
        if hasattr(st, "secrets") and st.secrets is not None:
            v = st.secrets.get(key, default)
            return str(v).strip() if v is not None else default
    except Exception:
        pass
    return os.environ.get(key, default) or default

st.set_page_config(page_title="CrediAI", page_icon="🛡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');

:root {
  --bg:        #060D1A;
  --bg-m:      #0A1628;
  --bg-l:      #0F1E35;
  --card:      #0D1B2E;
  --card-h:    #122236;
  --border:    #1A2F4A;
  --border-h:  #213A5C;

  --blue:      #2563EB;
  --blue-m:    #3B82F6;
  --blue-l:    #60A5FA;
  --blue-b:    rgba(37,99,235,.15);
  --blue-glow: rgba(37,99,235,.3);

  --cyan:      #06B6D4;
  --cyan-l:    #22D3EE;
  --cyan-b:    rgba(6,182,212,.12);

  --green:     #059669;
  --green-m:   #10B981;
  --green-l:   #34D399;
  --green-b:   rgba(16,185,129,.1);

  --red:       #DC2626;
  --red-m:     #EF4444;
  --red-l:     #FCA5A5;
  --red-b:     rgba(239,68,68,.1);

  --amber:     #D97706;
  --amber-m:   #F59E0B;
  --amber-l:   #FCD34D;

  --text:      #F1F5F9;
  --text-m:    #CBD5E1;
  --text-d:    #94A3B8;
  --text-dd:   #64748B;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Inter', sans-serif !important;
  -webkit-font-smoothing: antialiased;
}
.stApp { background: var(--bg) !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
.stDeployButton, header[data-testid="stHeader"],
footer, [data-testid="stToolbar"] { display: none !important; }

/* ── NAV ──────────────────────────────────────────────────────── */
.nav {
  background: rgba(6,13,26,.94);
  border-bottom: 1px solid var(--border);
  padding: .75rem 2.4rem;
  display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 200;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 1px 0 var(--border), 0 4px 24px rgba(0,0,0,.45);
}
.nav-brand { display: flex; align-items: center; gap: .6rem; }
.nav-icon {
  width: 32px; height: 32px; border-radius: 8px;
  background: linear-gradient(135deg, var(--blue) 0%, var(--cyan) 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: .8rem; font-weight: 800; color: #fff;
  box-shadow: 0 2px 14px var(--blue-glow); flex-shrink: 0;
}
.nav-name { font-size: 1.05rem; font-weight: 700; color: var(--text); letter-spacing: -.3px; }
.nav-name span { color: var(--blue-m); }
.nav-badge {
  display: flex; align-items: center; gap: .35rem;
  background: var(--green-b); border: 1px solid rgba(16,185,129,.25);
  border-radius: 99px; padding: .2rem .7rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: .55rem; letter-spacing: .12em; text-transform: uppercase; color: var(--green-m);
}
.live-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--green-m); animation: pulse 1.8s infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1);} 50%{opacity:.3;transform:scale(.8);} }
.nav-pills { display: flex; gap: .4rem; }
.nav-pill {
  font-family: 'JetBrains Mono', monospace;
  font-size: .5rem; letter-spacing: .08em;
  background: var(--bg-l); border: 1px solid var(--border);
  border-radius: 6px; padding: .2rem .55rem; color: var(--text-d);
}

/* ── HERO ─────────────────────────────────────────────────────── */
.hero {
  background: linear-gradient(160deg, var(--bg-m) 0%, var(--bg) 50%, var(--bg-m) 100%);
  border-bottom: 1px solid var(--border);
  padding: 1.5rem 2.4rem 0.4rem;
  position: relative; overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent 0%, var(--blue) 40%, var(--cyan) 60%, transparent 100%);
}
.hero-glow1 {
  position: absolute; top: -120px; left: -80px;
  width: 500px; height: 500px; border-radius: 50%;
  background: radial-gradient(circle, rgba(37,99,235,.1) 0%, transparent 60%);
  pointer-events: none;
}
.hero-glow2 {
  position: absolute; bottom: -100px; right: -60px;
  width: 440px; height: 440px; border-radius: 50%;
  background: radial-gradient(circle, rgba(6,182,212,.07) 0%, transparent 60%);
  pointer-events: none;
}
.hero-inner { position: relative; z-index: 2; max-width: 1200px; margin: 0 auto; }
.hero-tag {
  display: inline-flex; align-items: center; gap: .45rem;
  background: var(--blue-b); border: 1px solid rgba(37,99,235,.3);
  border-radius: 99px; padding: .24rem .85rem; margin-bottom: 1.3rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: .56rem; letter-spacing: .16em; text-transform: uppercase; color: var(--blue-m);
}
.hero-h1 {
  font-size: clamp(2.6rem, 4.5vw, 4.5rem);
  font-weight: 800; line-height: 1.0;
  letter-spacing: -2px; color: var(--text); margin-bottom: 1rem;
}
.hero-h1 .accent {
  background: linear-gradient(90deg, var(--blue-m) 0%, var(--cyan-l) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.hero-sub {
  font-size: .94rem; font-weight: 400; color: var(--text-d);
  max-width: 480px; line-height: 1.75; margin-bottom: 2rem;
}
.hero-pills { display: flex; gap: .55rem; flex-wrap: wrap; }
.hpill {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 99px; padding: .32rem .95rem;
  font-size: .76rem; font-weight: 500; color: var(--text-m);
  display: flex; align-items: center; gap: .4rem;
  box-shadow: 0 2px 8px rgba(0,0,0,.2);
}
.pip { width: 6px; height: 6px; border-radius: 50%; }
.pip-en { background: linear-gradient(135deg, var(--blue-m), var(--cyan)); }
.pip-ta { background: linear-gradient(135deg, var(--cyan), var(--green-m)); }

/* ── BODY ─────────────────────────────────────────────────────── */
.body { max-width: 1200px; margin: 0 auto; padding: 0 2.4rem 4rem; }

/* ── COLUMN ALIGNMENT ─────────────────────────────────────────── */
[data-testid="column"] { display: flex !important; flex-direction: column !important; }
[data-testid="column"] > div:first-child { flex: 1 !important; }
div[data-testid="stHorizontalBlock"] { align-items: stretch !important; gap: 0 !important; }
[data-testid="column"] .panel { height: 100% !important; }

/* ── PANEL ────────────────────────────────────────────────────── */
.panel {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden;
  box-shadow: 0 4px 24px rgba(0,0,0,.35), 0 1px 0 var(--border);
  transition: border-color .2s;
}
.panel:hover { border-color: var(--border-h); }
.ph {
  padding: .75rem 1.2rem; background: var(--bg-l);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: .5rem;
}
.ph-bar { width: 3px; height: 14px; border-radius: 2px; flex-shrink: 0; }
.ph-blue  { background: linear-gradient(180deg, var(--blue-m), var(--cyan)); }
.ph-cyan  { background: linear-gradient(180deg, var(--cyan), var(--green-m)); }
.ph-green { background: linear-gradient(180deg, var(--green-m), var(--cyan)); }
.ph-lbl {
  font-family: 'JetBrains Mono', monospace;
  font-size: .58rem; letter-spacing: .14em; text-transform: uppercase;
  color: var(--text-d); font-weight: 600;
}
.pb { padding: 1.2rem; }

/* ── TEXTAREA ─────────────────────────────────────────────────── */
.stTextArea textarea {
  background: var(--bg-l) !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; color: var(--text) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: .9rem !important; line-height: 1.7 !important;
  padding: .95rem 1rem !important; caret-color: var(--blue-m);
  box-shadow: none !important; resize: none !important;
  transition: border-color .2s, box-shadow .2s !important;
}
.stTextArea textarea:focus {
  border-color: var(--blue-m) !important;
  box-shadow: 0 0 0 3px var(--blue-b) !important;
  background: var(--bg-m) !important;
}
.stTextArea textarea::placeholder { color: var(--text-dd) !important; }
.stTextArea label { display: none !important; }
.stTextArea > div { border: none !important; box-shadow: none !important; background: transparent !important; }

/* ── BUTTON ───────────────────────────────────────────────────── */
/* Universal button base reset */
.stButton > button,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"],
[data-testid="stDownloadButton"] > button {
  height: auto !important;
  min-height: unset !important;
  line-height: 1.4 !important;
  white-space: nowrap !important;
  cursor: pointer !important;
  transition: all .18s ease !important;
}
/* Primary button */
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%) !important;
  color: #fff !important; border: none !important; border-radius: 8px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: .58rem !important; font-weight: 600 !important; letter-spacing: .08em !important;
  text-transform: uppercase !important;
  padding: .38rem 1.1rem !important;
  box-shadow: 0 2px 12px rgba(59,130,246,.35) !important;
}
.stButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
  background: linear-gradient(135deg, #60A5FA 0%, #22D3EE 100%) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 20px rgba(59,130,246,.55) !important;
}
/* Secondary / default button */
.stButton > button:not([kind="primary"]),
[data-testid="stBaseButton-secondary"] {
  background: rgba(15,30,53,.9) !important; border: 1px solid var(--border) !important;
  border-radius: 7px !important; color: var(--text-d) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: .52rem !important; letter-spacing: .07em !important; text-transform: uppercase !important;
  padding: .32rem .75rem !important;
  box-shadow: none !important;
}
.stButton > button:not([kind="primary"]):hover,
[data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--cyan) !important; color: var(--cyan-l) !important;
  background: rgba(6,182,212,.08) !important;
  box-shadow: 0 0 10px rgba(6,182,212,.15) !important;
}
/* Download button */
[data-testid="stDownloadButton"] > button {
  background: rgba(15,30,53,.9) !important; border: 1px solid var(--border) !important;
  border-radius: 7px !important; color: var(--text-d) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: .52rem !important; letter-spacing: .07em !important; text-transform: uppercase !important;
  padding: .32rem .75rem !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: var(--green-m) !important; color: var(--green-l) !important;
  background: rgba(16,185,129,.08) !important;
}
/* ── WIDGET LABELS (compact) ──────────────────────────────────── */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: .48rem !important; font-weight: 600 !important;
  letter-spacing: .12em !important; text-transform: uppercase !important;
  color: var(--text-dd) !important;
}
/* ── SELECTBOX (compact) ──────────────────────────────────────── */
[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child {
  min-height: unset !important;
  padding: .28rem .65rem !important;
  background: rgba(10,22,40,.9) !important;
  border-color: var(--border) !important;
  border-radius: 7px !important;
  font-size: .65rem !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child:hover {
  border-color: var(--cyan) !important;
}
/* ── SLIDER (compact) ─────────────────────────────────────────── */
[data-testid="stSlider"] { padding-bottom: .2rem !important; }
[data-testid="stSlider"] > div > div { padding-top: .1rem !important; }
/* ── TOGGLE (compact) ─────────────────────────────────────────── */
[data-testid="stToggle"] { gap: .4rem !important; }

/* ── VERDICT CARDS ────────────────────────────────────────────── */
.vc {
  border-radius: 10px; padding: 1.2rem 1.3rem; margin: .5rem 0;
  border: 1px solid; position: relative; overflow: hidden;
}
.vc::after {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
}
.vc-real  { background: var(--green-b);             border-color: rgba(16,185,129,.25); }
.vc-real::after  { background: linear-gradient(90deg, var(--green-m), var(--cyan)); }
.vc-fake  { background: var(--red-b);               border-color: rgba(239,68,68,.25); }
.vc-fake::after  { background: linear-gradient(90deg, var(--red-m), #F97316); }
.vc-warn  { background: rgba(217,119,6,.08);         border-color: rgba(245,158,11,.25); }
.vc-warn::after  { background: linear-gradient(90deg, var(--amber-m), #F97316); }

.vc-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: .5rem; letter-spacing: .18em; text-transform: uppercase; margin-bottom: .4rem;
}
.vc-real .vc-label { color: var(--green-m); }
.vc-fake .vc-label { color: var(--red-m); }
.vc-warn .vc-label { color: var(--amber-m); }
.vc-row  { display: flex; align-items: baseline; gap: .55rem; }
.vc-verdict { font-size: 1.55rem; font-weight: 800; line-height: 1; letter-spacing: -.5px; }
.vc-real .vc-verdict { color: var(--green-l); }
.vc-fake .vc-verdict { color: var(--red-l); }
.vc-warn .vc-verdict { color: var(--amber-l); }
.vc-conf { font-family: 'JetBrains Mono', monospace; font-size: .68rem; color: var(--text-dd); }
.vc-body { font-size: .82rem; color: var(--amber-m); margin-top: .4rem; line-height: 1.6; }

/* ── BARS ─────────────────────────────────────────────────────── */
.brow  { display: flex; align-items: center; gap: .6rem; margin: .4rem 0; }
.blbl  {
  font-family: 'JetBrains Mono', monospace; font-size: .5rem;
  letter-spacing: .1em; text-transform: uppercase; color: var(--text-dd);
  width: 2.4rem; flex-shrink: 0;
}
.btrack {
  flex: 1; height: 5px; background: var(--bg-l);
  border-radius: 99px; overflow: hidden; border: 1px solid var(--border);
}
.bf-fake { height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--red-m), #F97316); }
.bf-real { height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--blue-m), var(--cyan)); }
.bpct   {
  font-family: 'JetBrains Mono', monospace; font-size: .62rem;
  font-weight: 600; color: var(--text); width: 2.4rem; text-align: right; flex-shrink: 0;
}

/* ── CHIPS ────────────────────────────────────────────────────── */
.chips { display: grid; grid-template-columns: repeat(3,1fr); gap: .35rem; margin-top: .5rem; }
.chip  {
  background: var(--bg-l); border: 1px solid var(--border);
  border-radius: 8px; padding: .5rem .3rem; text-align: center;
  transition: border-color .15s;
}
.chip:hover { border-color: var(--border-h); }
.cn  { font-size: 1.05rem; font-weight: 700; color: var(--text); display: block; line-height: 1; }
.cn.ok  { color: var(--green-m); }
.cn.bad { color: var(--red-m); }
.ct  {
  font-family: 'JetBrains Mono', monospace; font-size: .42rem;
  letter-spacing: .1em; text-transform: uppercase; color: var(--text-dd);
  display: block; margin-top: .16rem;
}

/* ── TAGS ─────────────────────────────────────────────────────── */
.tag {
  display: inline-flex; align-items: center; gap: .28rem;
  border-radius: 99px; padding: .18rem .6rem; margin: 0 .25rem .4rem 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: .5rem; letter-spacing: .1em; text-transform: uppercase;
}
.t-blue  { background: var(--blue-b);  border: 1px solid rgba(59,130,246,.3); color: var(--blue-l); }
.t-cyan  { background: var(--cyan-b);  border: 1px solid rgba(6,182,212,.3);  color: var(--cyan-l); }
.t-green { background: var(--green-b); border: 1px solid rgba(16,185,129,.3); color: var(--green-l); }
.tdot { width: 4px; height: 4px; border-radius: 50%; background: currentColor; }

/* ── SECTION LABEL ────────────────────────────────────────────── */
.slbl {
  font-family: 'JetBrains Mono', monospace; font-size: .5rem;
  letter-spacing: .16em; text-transform: uppercase;
  color: var(--text-dd); margin: .8rem 0 .38rem;
  padding-bottom: .3rem; border-bottom: 1px solid var(--border);
}

/* ── IDLE STATE ───────────────────────────────────────────────── */
.idle {
  border: 1px dashed var(--border-h); border-radius: 10px;
  padding: 3.5rem 1.5rem; text-align: center; background: var(--bg-l);
}
.idle-icon { font-size: 2rem; opacity: .25; display: block; margin-bottom: .5rem; }
.idle-text {
  font-family: 'JetBrains Mono', monospace; font-size: .52rem;
  letter-spacing: .18em; text-transform: uppercase; color: var(--text-dd);
}

/* ── NEWS PANEL ───────────────────────────────────────────────── */
.nh {
  padding: .75rem 1.1rem; background: var(--bg-l);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: .35rem;
}
.nh-lbl {
  font-family: 'JetBrains Mono', monospace;
  font-size: .55rem; letter-spacing: .14em; text-transform: uppercase;
  color: var(--text-d); font-weight: 600;
  display: flex; align-items: center; gap: .35rem;
}
.rdot { width: 5px; height: 5px; border-radius: 50%; background: var(--red-m); animation: pulse 1.4s infinite; }
.nbody { padding: .85rem; }

.nc {
  display: block; text-decoration: none !important;
  background: var(--bg-l); border: 1px solid var(--border);
  border-radius: 9px; padding: .65rem .8rem; margin-bottom: .38rem;
  position: relative; overflow: hidden;
  transition: border-color .15s, background .15s, box-shadow .15s;
}
.nc::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px;
  background: linear-gradient(180deg, var(--blue-m), var(--cyan));
  opacity: 0; transition: opacity .15s;
}
.nc:hover {
  border-color: var(--blue-m); background: rgba(37,99,235,.06);
  box-shadow: 0 2px 12px rgba(37,99,235,.12); text-decoration: none !important;
}
.nc:hover::before { opacity: 1; }
.nc-r1 { display: flex; align-items: center; gap: .3rem; margin-bottom: .08rem; overflow: hidden; }
.nc-ico { width: 12px; height: 12px; border-radius: 3px; object-fit: contain; flex-shrink: 0; }
.nc-fb {
  width: 12px; height: 12px; border-radius: 3px;
  background: var(--border); display: inline-flex;
  align-items: center; justify-content: center;
  font-size: .34rem; color: var(--text-d); flex-shrink: 0;
}
.nc-src {
  font-family: 'JetBrains Mono', monospace; font-size: .46rem;
  letter-spacing: .08em; text-transform: uppercase; color: var(--text-dd);
  flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.nc-cat {
  border-radius: 4px; padding: .05rem .25rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: .4rem; letter-spacing: .07em; text-transform: uppercase; flex-shrink: 0;
}
.c-en { background: var(--bg-m); border: 1px solid var(--border); color: var(--text-d); }
.c-ta { background: var(--cyan-b); border: 1px solid rgba(6,182,212,.25); color: var(--cyan-l); }
.nc-t  { font-family: 'JetBrains Mono', monospace; font-size: .42rem; color: var(--text-dd); margin: .06rem 0 .22rem; }
.nc-hl { font-size: .75rem; font-weight: 500; color: var(--text-m); line-height: 1.38; margin: 0; }
.nc-cta { font-family: 'JetBrains Mono', monospace; font-size: .42rem; color: var(--text-dd); margin-top: .25rem; }

/* ── SIDEBAR ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: var(--bg-m) !important; border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] > div { padding-top: 1rem !important; }
section[data-testid="stSidebar"] * { color: var(--text) !important; }
section[data-testid="stSidebar"] .stRadio label p {
  font-family: 'Inter', sans-serif !important; font-size: .82rem !important; font-weight: 500 !important;
}
section[data-testid="stSidebar"] .stRadio > label {
  font-family: 'JetBrains Mono', monospace !important; font-size: .5rem !important;
  letter-spacing: .15em !important; text-transform: uppercase !important; color: var(--text-dd) !important;
}

hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1rem 0 !important; }
.stSpinner > div { border-top-color: var(--blue-m) !important; }
div[data-testid="stHorizontalBlock"] { align-items: flex-start !important; gap: 1.4rem !important; }

/* ── TABS (Verify / Social / Dashboard / History) ───────────────── */
@keyframes tab-glow {
  0%, 100% {
    box-shadow: 0 0 8px rgba(59,130,246,.15), 0 0 18px rgba(6,182,212,.08);
    text-shadow: 0 0 10px rgba(96,165,250,.25);
  }
  50% {
    box-shadow: 0 0 16px rgba(59,130,246,.32), 0 0 28px rgba(6,182,212,.18);
    text-shadow: 0 0 16px rgba(96,165,250,.55), 0 0 28px rgba(6,182,212,.3);
  }
}
@keyframes tab-glow-active {
  0%, 100% {
    box-shadow: 0 0 14px rgba(59,130,246,.4), 0 0 28px rgba(6,182,212,.22);
    text-shadow: 0 0 12px rgba(255,255,255,.6), 0 0 24px rgba(96,165,250,.7);
  }
  50% {
    box-shadow: 0 0 24px rgba(59,130,246,.6), 0 0 42px rgba(6,182,212,.38);
    text-shadow: 0 0 18px rgba(255,255,255,.9), 0 0 36px rgba(96,165,250,.9), 0 0 54px rgba(6,182,212,.5);
  }
}
.stTabs [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 1.8rem !important;
  padding: 0 2rem !important;
  margin-top: -1.4rem !important;
}
.stTabs [data-baseweb="tab"] {
  background: rgba(10,22,40,.8) !important;
  border: 1px solid rgba(26,47,74,.7) !important;
  border-radius: 7px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: .5rem !important;
  font-weight: 500 !important;
  letter-spacing: .2em !important;
  text-transform: uppercase !important;
  color: rgba(100,116,139,.95) !important;
  padding: .35rem .65rem !important;
  margin-right: 0 !important;
  transition: color .25s, border-color .25s, box-shadow .25s, transform .2s, text-shadow .25s !important;
  animation: tab-glow 4s ease-in-out infinite;
}
.stTabs [data-baseweb="tab"]:hover {
  color: var(--cyan-l) !important;
  border-color: rgba(6,182,212,.5) !important;
  transform: translateY(-1px);
  box-shadow: 0 0 14px rgba(6,182,212,.2);
  text-shadow: 0 0 12px rgba(6,182,212,.6);
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  color: #e2e8f0 !important;
  border-color: rgba(96,165,250,.85) !important;
  background: linear-gradient(135deg, rgba(37,99,235,.3) 0%, rgba(6,182,212,.15) 100%) !important;
  animation: tab-glow-active 2.5s ease-in-out infinite;
}
.stTabs [data-baseweb="tab-highlight"] {
  background: linear-gradient(90deg, var(--blue-m), var(--cyan)) !important;
  height: 2px !important; border-radius: 0 0 2px 2px;
  box-shadow: 0 0 10px var(--cyan), 0 0 20px var(--blue-m);
}
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }

/* ── STREAMLIT METRIC (fallback) ──────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--bg-l) !important; border: 1px solid var(--border) !important;
  border-radius: 10px !important; padding: .75rem 1rem !important;
}
[data-testid="stMetricLabel"] p {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: .48rem !important; letter-spacing: .12em !important;
  text-transform: uppercase !important; color: var(--text-dd) !important;
}
[data-testid="stMetricValue"] {
  font-size: 1.1rem !important; font-weight: 700 !important; color: var(--text) !important;
}
.stAlert { background: var(--bg-l) !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; color: var(--text-d) !important; }

/* ── SOCIAL MEDIA MONITOR ─────────────────────────────────────────────── */
/* Feed column header card */
.feed-card-hdr {
  display: flex; align-items: center; gap: .55rem;
  border-radius: 10px; padding: .5rem .75rem;
  margin-bottom: .55rem; overflow: hidden;
  border: 1px solid;
}
.feed-ig {
  background: linear-gradient(135deg, rgba(16,8,16,.95) 0%, rgba(20,8,12,.9) 100%);
  border-color: rgba(188,24,136,.2);
}
.feed-tw {
  background: linear-gradient(135deg, rgba(8,14,24,.95) 0%, rgba(10,18,30,.9) 100%);
  border-color: rgba(29,155,240,.18);
}
.feed-icon {
  width: 1.7rem; height: 1.7rem; border-radius: 7px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: .85rem; font-weight: 900;
}
.feed-icon-ig {
  background: linear-gradient(135deg, #f09433, #dc2743, #bc1888);
}
.feed-icon-tw {
  background: #000; border: 1px solid #2a2a2a; color: #fff;
  font-size: .9rem;
}
.feed-hdr-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: .1rem; }
.feed-hdr-name {
  font-size: .76rem; font-weight: 700; color: #f1f5f9; letter-spacing: -.01em; line-height: 1;
}
.feed-hdr-src {
  font-family: 'JetBrains Mono', monospace;
  font-size: .43rem; letter-spacing: .1em; text-transform: uppercase; opacity: .9;
}
.feed-hdr-stats {
  display: flex; flex-direction: column; align-items: flex-end; gap: .12rem; flex-shrink: 0;
}
.feed-stat {
  font-family: 'JetBrains Mono', monospace;
  font-size: .43rem; color: #64748b; letter-spacing: .06em;
}
/* Legacy classes kept for compatibility */
.platform-hdr {
  padding: .65rem 1rem; background: var(--bg-m);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: .55rem;
}
.ph-stat {
  font-family: 'JetBrains Mono', monospace;
  font-size: .48rem; color: var(--text-dd); margin-left: auto;
}
.post-feed { display: flex; flex-direction: column; gap: .6rem; padding: .7rem; }
.pcard {
  background: var(--bg-l); border: 1px solid var(--border);
  border-radius: 10px; overflow: hidden;
  transition: border-color .2s; position: relative;
}
.pcard:hover { border-color: var(--border-h); }
.pcard-risk-bar { height: 3px; width: 100%; }
.prb-critical { background: linear-gradient(90deg,#DC2626,#EF4444); }
.prb-high     { background: linear-gradient(90deg,#D97706,#F59E0B); }
.prb-medium   { background: linear-gradient(90deg,#CA8A04,#EAB308); }
.prb-low      { background: linear-gradient(90deg,#059669,#10B981); }
.prb-very_low { background: linear-gradient(90deg,#2563EB,#3B82F6); }
.pcard-top {
  padding: .6rem .75rem .4rem;
  display: flex; align-items: center; gap: .4rem;
}
.pcard-av {
  width: 28px; height: 28px; border-radius: 50%;
  background: linear-gradient(135deg,var(--blue),var(--cyan));
  display: flex; align-items: center; justify-content: center;
  font-size: .65rem; font-weight: 800; color: #fff; flex-shrink: 0;
}
.pcard-info { flex: 1; min-width: 0; }
.pcard-author {
  font-size: .77rem; font-weight: 600; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.pcard-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: .43rem; color: var(--text-dd);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.pcard-age { font-family:'JetBrains Mono',monospace; font-size:.44rem; color:var(--text-dd); flex-shrink:0; }
.pcard-body { padding: 0 .75rem .45rem; }
.pcard-cap { font-size:.77rem; color:var(--text-m); line-height:1.5; margin-bottom:.3rem; }
.pcard-tags { font-size:.65rem; color:var(--blue-m); font-weight:500; }
.pcard-media {
  background: var(--bg); height: 52px; margin: 0 .75rem .45rem;
  border-radius: 6px; border: 1px dashed var(--border);
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: .44rem; color: var(--text-dd); letter-spacing: .1em; text-transform: uppercase;
}
.pcard-eng {
  padding: .32rem .75rem .5rem;
  display: flex; gap: .8rem; border-top: 1px solid var(--border);
}
.eng-item { font-family:'JetBrains Mono',monospace; font-size:.46rem; color:var(--text-dd); }
.eng-val  { font-weight:700; color:var(--text-m); }
.score-gauge {
  padding: .42rem .75rem;
  display: flex; align-items: center; gap: .5rem;
  background: var(--bg); border-top: 1px solid var(--border);
}
.sg-num { font-family:'JetBrains Mono',monospace; font-size:1.15rem; font-weight:800; line-height:1; min-width:2.2rem; }
.sg-critical { color: #EF4444; }
.sg-high     { color: #F59E0B; }
.sg-medium   { color: #EAB308; }
.sg-low      { color: #10B981; }
.sg-very_low { color: #60A5FA; }
.sg-track {
  flex: 1; height: 6px; background: var(--bg-l);
  border-radius: 99px; overflow: hidden; border: 1px solid var(--border);
}
.sg-fill { height: 100%; border-radius: 99px; }
.risk-badge {
  display: inline-flex; align-items: center; gap: .26rem;
  border-radius: 99px; padding: .12rem .48rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: .44rem; letter-spacing: .09em; text-transform: uppercase; font-weight: 700;
}
.rb-critical { background:rgba(239,68,68,.15); border:1px solid rgba(239,68,68,.4);  color:#FCA5A5; }
.rb-high     { background:rgba(245,158,11,.12); border:1px solid rgba(245,158,11,.35);color:#FCD34D; }
.rb-medium   { background:rgba(234,179,8,.1);   border:1px solid rgba(234,179,8,.35); color:#FDE68A; }
.rb-low      { background:var(--green-b);        border:1px solid rgba(16,185,129,.3); color:var(--green-l); }
.rb-very_low { background:var(--blue-b);         border:1px solid rgba(59,130,246,.3); color:var(--blue-l); }
.blink-red { width:6px;height:6px;border-radius:50%;background:#EF4444;display:inline-block;animation:blink-r .75s infinite; }
.blink-amb { width:6px;height:6px;border-radius:50%;background:#F59E0B;display:inline-block;animation:blink-a 1.1s infinite; }
@keyframes blink-r { 0%,100%{opacity:1;transform:scale(1.2)} 50%{opacity:.15;transform:scale(.75)} }
@keyframes blink-a { 0%,100%{opacity:1} 50%{opacity:.2} }
.ablock {
  padding: .5rem .75rem .65rem;
  border-top: 1px solid var(--border);
  background: var(--bg);
}
.ablock-lbl {
  font-family: 'JetBrains Mono', monospace;
  font-size: .43rem; letter-spacing: .13em; text-transform: uppercase;
  color: var(--text-dd); margin-bottom: .28rem;
}
.ablock-just { font-size:.72rem; color:var(--text-d); line-height:1.55; margin-bottom:.38rem; }
.ablock-flags { display:flex; flex-wrap:wrap; gap:.2rem; margin:.25rem 0; }
.aflag {
  border-radius:99px; padding:.1rem .42rem;
  font-family:'JetBrains Mono',monospace;
  font-size:.41rem; letter-spacing:.07em; text-transform:uppercase;
}
.af-fake { background:rgba(239,68,68,.1);  border:1px solid rgba(239,68,68,.28);  color:#FCA5A5; }
.af-real { background:var(--green-b);      border:1px solid rgba(16,185,129,.22); color:var(--green-l); }
.fc-link {
  font-size:.64rem; color:var(--cyan-l); text-decoration:none;
  border-bottom:1px dashed rgba(34,211,238,.28);
  display:inline-flex; align-items:center; gap:.22rem; margin-right:.5rem;
  transition:border-color .15s;
}
.fc-link:hover { border-color:var(--cyan-l); }
.social-disclaimer {
  background: rgba(217,119,6,.07); border: 1px solid rgba(245,158,11,.2);
  border-radius: 8px; padding: .55rem .85rem; margin-bottom: .85rem;
  font-size: .72rem; color: var(--amber-m); line-height: 1.5;
}
.arch-note {
  margin-top:1.2rem; padding:.75rem 1rem;
  background:var(--card); border:1px solid var(--border); border-radius:10px;
}
/* ── ACCOUNT VALIDATION BADGES ───────────────────────────────────────────── */
.acct-badge {
  display:inline-flex;align-items:center;gap:.26rem;border-radius:5px;
  padding:.14rem .44rem;font-family:'JetBrains Mono',monospace;
  font-size:.43rem;letter-spacing:.09em;text-transform:uppercase;font-weight:700;
}
.ab-verified  {background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.3);color:#93C5FD;}
.ab-public    {background:rgba(16,185,129,.10);border:1px solid rgba(16,185,129,.28);color:#6EE7B7;}
.ab-low       {background:rgba(245,158,11,.10);border:1px solid rgba(245,158,11,.28);color:#FCD34D;}
.ab-private   {background:rgba(100,116,139,.1);border:1px solid rgba(100,116,139,.3);color:#94A3B8;}
.ab-suspended {background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.3); color:#FCA5A5;}
.ab-restricted{background:rgba(245,158,11,.10);border:1px solid rgba(245,158,11,.28);color:#FCD34D;}
.ab-notfound  {background:rgba(100,116,139,.1);border:1px solid rgba(100,116,139,.3);color:#94A3B8;}
/* ── RISK LABELS ─────────────────────────────────────────────────────────── */
.rl-high     {background:rgba(239,68,68,.15); border:1px solid rgba(239,68,68,.4); color:#FCA5A5;}
.rl-needs    {background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.35);color:#FCD34D;}
.rl-reliable {background:var(--green-b);      border:1px solid rgba(16,185,129,.3); color:var(--green-l);}
/* ── BURST BADGE ─────────────────────────────────────────────────────────── */
.burst-badge {
  display:inline-flex;align-items:center;gap:.2rem;
  background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);
  border-radius:99px;padding:.08rem .36rem;
  font-family:'JetBrains Mono',monospace;font-size:.4rem;color:var(--amber-m);
}
/* ── INVALID ACCOUNT CARD ────────────────────────────────────────────────── */
.invalid-card {
  background:var(--bg-l);border:1px dashed var(--border);border-radius:10px;
  padding:1rem 1.1rem;display:flex;align-items:center;gap:.7rem;
}
.invalid-icon  {font-size:1.3rem;opacity:.45;flex-shrink:0;}
.invalid-handle{font-size:.77rem;font-weight:600;color:var(--text-d);}
.invalid-reason{font-size:.68rem;color:var(--text-dd);margin-top:.14rem;line-height:1.45;}
/* ── COMMENT SENTIMENT ───────────────────────────────────────────────────── */
.sent-bar {display:flex;height:5px;border-radius:99px;overflow:hidden;margin:.28rem 0;}
.sent-pos {background:#10B981;} .sent-neg {background:#EF4444;} .sent-neu {background:#64748B;}
.sent-legend {display:flex;gap:.55rem;flex-wrap:wrap;margin-top:.18rem;}
.sl-pos{font-family:'JetBrains Mono',monospace;font-size:.42rem;color:#10B981;}
.sl-neg{font-family:'JetBrains Mono',monospace;font-size:.42rem;color:#EF4444;}
.sl-neu{font-family:'JetBrains Mono',monospace;font-size:.42rem;color:#64748B;}
.comment-item {
  padding:.24rem .4rem;border-radius:5px;margin:.14rem 0;
  font-size:.67rem;color:var(--text-d);line-height:1.4;
}
.ci-pos{background:rgba(16,185,129,.06);border-left:2px solid #10B981;}
.ci-neg{background:rgba(239,68,68,.06); border-left:2px solid #EF4444;}
.ci-neu{background:rgba(100,116,139,.06);border-left:2px solid #64748B;}
/* ── OCR BLOCK ───────────────────────────────────────────────────────────── */
.ocr-block {
  background:var(--bg);border:1px solid var(--border);
  border-radius:7px;padding:.4rem .55rem;margin:.32rem 0;
}
.ocr-mismatch {border-color:rgba(245,158,11,.4);background:rgba(245,158,11,.05);}
.ocr-lbl      {font-family:'JetBrains Mono',monospace;font-size:.42rem;letter-spacing:.11em;text-transform:uppercase;color:var(--text-dd);}
.ocr-text-val {font-size:.7rem;color:var(--text-m);font-style:italic;margin-top:.13rem;}
/* ── CONTROL SECTION WRAPPER ──────────────────────────────────────────────── */
.ctrl-section-top {
  height: 0;
  background: var(--card);
  border: 1px solid var(--border);
  border-bottom: none;
  border-radius: 10px 10px 0 0;
  margin: 0;
}
.ctrl-section-bottom {
  height: .4rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-top: none;
  border-radius: 0 0 10px 10px;
  margin-bottom: .7rem;
}
/* Style the block between top/bottom wrappers */
.ctrl-section-top + div [data-testid="stHorizontalBlock"] {
  background: var(--card) !important;
  border-left: 1px solid var(--border) !important;
  border-right: 1px solid var(--border) !important;
  padding: .55rem .9rem .45rem !important;
}
/* ── SELECTBOX (compact) ──────────────────────────────────────────────────── */
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  min-height: unset !important;
  height: auto !important;
  background: rgba(10,22,40,.9) !important;
  border-color: var(--border) !important;
  border-radius: 7px !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover {
  border-color: var(--cyan) !important;
}
/* Target the value container to reduce inner padding */
[data-testid="stSelectbox"] [data-baseweb="select"] > div > div {
  padding: 4px 8px !important;
  min-height: unset !important;
  height: auto !important;
  line-height: 1.4 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stSelectbox"] [data-baseweb="select"] div[data-testid] {
  font-size: .65rem !important;
  font-family: 'JetBrains Mono', monospace !important;
  color: var(--text-m) !important;
}
/* Dropdown list items */
[data-baseweb="menu"] li {
  font-size: .65rem !important;
  font-family: 'JetBrains Mono', monospace !important;
  padding: .3rem .7rem !important;
  min-height: unset !important;
}
/* ── TRENDING BAR ────────────────────────────────────────────────────────── */
.trending-bar {
  background:rgba(10,16,26,.9);border:1px solid var(--border);border-radius:8px;
  padding:.42rem .8rem;margin-bottom:.6rem;
  display:flex;align-items:center;gap:.55rem;flex-wrap:wrap;
}
.tb-lbl {font-family:'JetBrains Mono',monospace;font-size:.46rem;letter-spacing:.14em;text-transform:uppercase;color:var(--red-m);flex-shrink:0;}
.trtopic {
  display:inline-flex;align-items:center;gap:.24rem;
  background:var(--red-b);border:1px solid rgba(239,68,68,.22);
  border-radius:99px;padding:.12rem .46rem;
  font-family:'JetBrains Mono',monospace;font-size:.44rem;color:var(--red-l);
}
/* ── HISTORY PANEL ───────────────────────────────────────────────────────── */
.hist-row {
  display:flex;align-items:center;gap:.6rem;padding:.45rem .7rem;
  background:var(--bg-l);border:1px solid var(--border);border-radius:8px;margin:.3rem 0;
}
.hist-score {font-family:'JetBrains Mono',monospace;font-size:.9rem;font-weight:800;min-width:2rem;}
.hist-info  {flex:1;min-width:0;}
.hist-cap   {font-size:.72rem;color:var(--text-m);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.hist-meta  {font-family:'JetBrains Mono',monospace;font-size:.42rem;color:var(--text-dd);margin-top:.1rem;}
/* ── STREAMLIT TABS (role selector fallback) ───────────────────── */
.stTabs { width: 100%; }
.stTabs [role="tab"]{
  background: rgba(10,22,40,.8);
  border: 1px solid rgba(26,47,74,.7);
  border-radius: 7px;
  padding: .35rem .65rem !important;
  margin-right: 0;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: .5rem !important;
  font-weight: 500 !important;
  letter-spacing: .2em !important;
  text-transform: uppercase;
  color: rgba(100,116,139,.95) !important;
  transition: color .25s, border-color .25s, box-shadow .25s, transform .2s, text-shadow .25s;
  animation: tab-glow 4s ease-in-out infinite;
}
.stTabs [role="tab"]:hover{
  transform: translateY(-1px);
  border-color: rgba(6,182,212,.5);
  box-shadow: 0 0 14px rgba(6,182,212,.2);
  color: var(--cyan-l) !important;
  text-shadow: 0 0 12px rgba(6,182,212,.6);
}
.stTabs [role="tab"][aria-selected="true"]{
  background: linear-gradient(135deg, rgba(37,99,235,.3) 0%, rgba(6,182,212,.15) 100%);
  border-color: rgba(96,165,250,.85);
  color: #e2e8f0 !important;
  animation: tab-glow-active 2.5s ease-in-out infinite;
}
.stTabs [role="tablist"]{ gap: 1.8rem !important; margin-top: -1.4rem !important; }

/* ── MOBILE (phone view only) ───────────────────────────────────── */
@media (max-width: 768px) {
  .nav {
    flex-wrap: wrap;
    padding: .6rem 1rem;
    gap: .5rem;
  }
  .nav-brand { flex: 0 0 auto; }
  .nav-badge { order: 3; width: 100%; justify-content: center; margin-top: .2rem; }
  .nav-pills {
    flex-wrap: wrap;
    gap: .35rem;
    justify-content: flex-end;
    max-width: 50%;
  }
  .nav-pill { font-size: .48rem !important; padding: .28rem .5rem !important; }
  .hero { padding: 1rem 1rem .3rem; }
  .hero-inner { max-width: 100%; }
  .hero-tag { font-size: .5rem; padding: .2rem .6rem; }
  .hero-h1 { font-size: 1.85rem; margin-bottom: .6rem; }
  .hero-sub { font-size: .82rem; margin-bottom: 1.2rem; max-width: 100%; }
  .hero-pills { gap: .4rem; }
  .hpill { padding: .4rem .75rem; font-size: .7rem; }
  .body { padding: 0 1rem 3rem; max-width: 100%; }
  div[data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
  }
  [data-testid="column"] {
    min-width: 100% !important;
    flex: 1 1 100% !important;
  }
  .panel { margin-bottom: .8rem; }
  .ph { padding: .6rem 1rem; }
  .ph-lbl { font-size: .52rem; }
  .pb { padding: 1rem; }
  .stTabs [role="tablist"] {
    gap: .5rem !important;
    flex-wrap: wrap !important;
    margin-top: -1.2rem !important;
  }
  .stTabs [role="tab"] {
    padding: .5rem .75rem !important;
    font-size: .48rem !important;
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .stTextArea textarea { font-size: .85rem !important; padding: .8rem !important; min-height: 120px; }
  .stButton > button { min-height: 44px !important; padding: .5rem 1rem !important; }
}
</style>
""", unsafe_allow_html=True)

# Pre-trained models only (no local training required). Best-accuracy HF models.
ARTICLE_MODEL  = "hamzab/roberta-fake-news-classification"  # English
HEADLINE_MODEL = ARTICLE_MODEL  # same model for headlines
TAMIL_MODEL    = "mdosama39/bert-base-multilingual-cased-FakeNews-Dravidian-mBert"  # Dravidian ~83% acc

# Indic (Hindi, Telugu, Malayalam, Kannada): one multilingual XLM-RoBERTa fake-news model
XLM_FAKE_NEWS  = "Sajib-006/fake_news_detection_xlmRoberta"
MODEL_REGISTRY = {
    "Tamil":     TAMIL_MODEL,
    "Hindi":     XLM_FAKE_NEWS,
    "Telugu":    XLM_FAKE_NEWS,
    "Malayalam": XLM_FAKE_NEWS,
    "Kannada":   XLM_FAKE_NEWS,
}
SUPPORTED_LANGS = ["English", "Tamil", "Hindi", "Telugu", "Malayalam", "Kannada"]
SUPPORTED_LANGS_BADGES = "EN · TA · HI · TE · ML · KN"

# Known (fake_idx, real_idx) for output logits. Model card / dataset order.
# hamzab: zip(["Fake","Real"], softmax(logits)[0]) → index 0 = Fake, 1 = Real.
LABEL_ORDER_BY_MODEL = {
    "hamzab/roberta-fake-news-classification": (0, 1),
    "mdosama39/bert-base-multilingual-cased-FakeNews-Dravidian-mBert": (0, 1),
}

def is_hf_model_id(path):
    """True if path looks like a HuggingFace repo id (org/name), not a local dir."""
    if not path or not isinstance(path, str):
        return False
    if os.path.isdir(path) or os.path.exists(path):
        return False
    return "/" in path and not path.startswith(".")

def can_use_model(path):
    """True if we can load this model (local dir or HF id)."""
    return path and (os.path.isdir(path) or is_hf_model_id(path))

# Reported metrics for pre-trained HF models (for Dashboard display when no local metrics.json)
PRETRAINED_MODEL_METRICS = {
    # hamzab model card does not publish a single accuracy number; show as "reported" unknown.
    "hamzab/roberta-fake-news-classification": {"accuracy": None, "f1": None, "note": "RoBERTa fake-news (English)"},
    "mdosama39/bert-base-multilingual-cased-FakeNews-Dravidian-mBert": {"accuracy": 0.8307, "f1": 0.8305, "precision": 0.83, "recall": 0.83, "note": "Dravidian mBERT (Tamil, Malayalam, Kannada, Telugu)"},
    # Sajib model card reports "almost 100%" accuracy on a 2k sample (author-reported).
    "Sajib-006/fake_news_detection_xlmRoberta": {"accuracy": 0.99, "f1": 0.99, "note": "XLM-RoBERTa multilingual (author-reported ~99% on 2k sample)"},
}

# Optional: override/extend metrics with locally computed values (e.g. evaluation scripts).
# File format:
# {
#   "hamzab/roberta-fake-news-classification": {"accuracy": 0.91, "f1": 0.90, "note": "...", "source": "local_eval"}
# }
try:
    _pm_path = os.path.join(os.path.dirname(__file__), "pretrained_metrics.json")
    if os.path.isfile(_pm_path):
        with open(_pm_path, "r", encoding="utf-8") as _f:
            _local_pm = json.load(_f) or {}
        if isinstance(_local_pm, dict):
            for _k, _v in _local_pm.items():
                if isinstance(_v, dict):
                    PRETRAINED_MODEL_METRICS[_k] = {**PRETRAINED_MODEL_METRICS.get(_k, {}), **_v}
except Exception:
    pass

@st.cache_resource
def load_model(name):
    import torch
    from transformers.models.auto.tokenization_auto import AutoTokenizer
    from transformers.models.auto.modeling_auto import AutoModelForSequenceClassification
    t = AutoTokenizer.from_pretrained(name)
    m = AutoModelForSequenceClassification.from_pretrained(name)
    m.eval()
    fake_idx, real_idx = _resolve_fake_real_indices(m, name)
    return t, m, fake_idx, real_idx

def _resolve_fake_real_indices(model, model_name=None):
    """
    Best-effort mapping from a HF classification model's output indices
    to (fake, real) probabilities. Some model cards use swapped label order.
    """
    if model_name and model_name in LABEL_ORDER_BY_MODEL:
        return LABEL_ORDER_BY_MODEL[model_name]

    num_labels = getattr(model.config, "num_labels", 2) or 2
    if num_labels < 2:
        return 0, 1

    fake_words = ("fake", "liar", "hoax", "false", "misinformation", "rumour", "rumor")
    real_words = ("real", "true", "legit", "genuine", "verified", "truth")

    # Prefer id2label because it gives index -> label_name.
    id2label = getattr(model.config, "id2label", None) or {}
    label_map = {}
    try:
        # id2label keys may be strings; coerce to int where possible.
        for k, v in id2label.items():
            try:
                label_map[int(k)] = str(v)
            except Exception:
                continue
    except Exception:
        label_map = {}

    fake_candidates = []
    real_candidates = []
    for idx, lbl in label_map.items():
        s = (lbl or "").lower()
        if any(w in s for w in fake_words):
            fake_candidates.append(idx)
        if any(w in s for w in real_words):
            real_candidates.append(idx)

    # Fallback: use label2id (label_name -> index).
    if (not fake_candidates or not real_candidates) and hasattr(model.config, "label2id"):
        label2id = getattr(model.config, "label2id", None) or {}
        for lbl, idx in label2id.items():
            s = (str(lbl) or "").lower()
            try:
                i = int(idx)
            except Exception:
                continue
            if any(w in s for w in fake_words) and i not in fake_candidates:
                fake_candidates.append(i)
            if any(w in s for w in real_words) and i not in real_candidates:
                real_candidates.append(i)

    if fake_candidates and real_candidates:
        return fake_candidates[0], real_candidates[0]
    if fake_candidates and not real_candidates:
        real_idx = 1 if fake_candidates[0] == 0 and num_labels >= 2 else 0
        return fake_candidates[0], real_idx
    if real_candidates and not fake_candidates:
        fake_idx = 1 if real_candidates[0] == 0 and num_labels >= 2 else 0
        return fake_idx, real_candidates[0]

    # Last resort: keep original assumption.
    return 0, 1

def infer(text, tok, mdl, fake_idx, real_idx, model_name=None):
    import torch
    # hamzab model expects "<title> TITLE <content> CONTENT <end>"
    if model_name == "hamzab/roberta-fake-news-classification" and text.strip():
        if len(text.split()) <= 25:
            text = f"<title> {text.strip()} <content> <end>"
        else:
            title = text.strip()[:200]
            body = text.strip()[200:500]
            text = f"<title> {title} <content> {body} <end>"
    inp = tok(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
    with torch.no_grad():
        p = torch.nn.functional.softmax(mdl(**inp).logits, dim=-1)[0]
    return p[fake_idx].item(), p[real_idx].item()

# ─── RSS ───────────────────────────────────────────────────────────────────
RSS = [
    ("BBC World","https://feeds.bbci.co.uk/news/world/rss.xml","https://www.google.com/s2/favicons?domain=bbc.co.uk&sz=32","EN"),
    ("Reuters","https://feeds.reuters.com/reuters/topNews","https://www.google.com/s2/favicons?domain=reuters.com&sz=32","EN"),
    ("NDTV","https://feeds.feedburner.com/ndtvnews-top-stories","https://www.google.com/s2/favicons?domain=ndtv.com&sz=32","EN"),
    ("The Hindu","https://www.thehindu.com/news/feeder/default.rss","https://www.google.com/s2/favicons?domain=thehindu.com&sz=32","EN"),
    ("Times of India","https://timesofindia.indiatimes.com/rssfeedstopstories.cms","https://www.google.com/s2/favicons?domain=timesofindia.indiatimes.com&sz=32","EN"),
    ("Dinamalar","https://www.dinamalar.com/rss/dynamicfeed.asp","https://www.google.com/s2/favicons?domain=dinamalar.com&sz=32","TA"),
    ("Vikatan","https://www.vikatan.com/rss.xml","https://www.google.com/s2/favicons?domain=vikatan.com&sz=32","TA"),
    ("Puthiya","https://www.puthiyathalaimurai.com/feed","https://www.google.com/s2/favicons?domain=puthiyathalaimurai.com&sz=32","TA"),
]

def _pt(s):
    try:
        import email.utils
        return email.utils.parsedate_to_datetime(s).strftime("%b %d · %H:%M")
    except: return "Today"

_RSS_TIMEOUT = 4  # seconds per feed so the page doesn't hang on slow RSS

@st.cache_data(ttl=60, show_spinner=False)
def fetch_news(_seed, n=6):
    pool=[]
    errs=[]
    for src,url,fav,cat in RSS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CrediAI/1.0"})
            with urllib.request.urlopen(req, timeout=_RSS_TIMEOUT) as resp:
                raw = resp.read()
            parsed = feedparser.parse(raw)
            if getattr(parsed, "bozo", 0):
                # feedparser sets bozo=1 on parse errors; bozo_exception may exist
                ex = getattr(parsed, "bozo_exception", None)
                errs.append({"src": src, "url": url, "error": str(ex) if ex else "RSS parse error"})
                continue
            entries = getattr(parsed, "entries", []) or []
            if not entries:
                errs.append({"src": src, "url": url, "error": "No entries returned"})
                continue
            for e in entries[:5]:
                t=e.get("title","").strip(); l=e.get("link","").strip()
                if t and l: pool.append({"src":src,"fav":fav,"cat":cat,"title":t,"link":l,"time":_pt(e.get("published",""))})
        except Exception as ex:
            errs.append({"src": src, "url": url, "error": str(ex)})
            continue
    if not pool: return [], errs
    random.seed(_seed); random.shuffle(pool); return pool[:n], errs

# ─── PREDICTION ENGINE ─────────────────────────────────────────────────────
# Unicode script ranges: Tamil U+0B80-0BFF, Hindi (Devanagari) U+0900-097F,
# Telugu U+0C00-0C7F, Kannada U+0C80-0CFF, Malayalam U+0D00-0D7F
def detect_lang(text):
    if not (text and text.strip()):
        return "English"
    t = text.strip()
    n = max(len(t), 1)
    # Count per script (Kannada 0C80-0CFF vs Telugu 0C00-0C7F)
    counts = {
        "Hindi":     len(re.findall(r'[\u0900-\u097F]', t)),
        "Tamil":     len(re.findall(r'[\u0B80-\u0BFF]', t)),
        "Telugu":    len(re.findall(r'[\u0C00-\u0C7F]', t)),
        "Kannada":   len(re.findall(r'[\u0C80-\u0CFF]', t)),
        "Malayalam": len(re.findall(r'[\u0D00-\u0D7F]', t)),
    }
    best = max(counts, key=lambda k: counts[k])
    if counts[best] / n >= 0.10:
        return best
    return "English"

def is_headline(text):
    return len(text.split()) < 45 and not bool(re.search(r'\w\.\s+[A-Z]', text))

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def safe_preview(text, n=120):
    s = " ".join((text or "").strip().split())
    return (s[:n] + "…") if len(s) > n else s

def ensure_session_state():
    if "seed" not in st.session_state:
        st.session_state.seed = int(time.time())
    if "history" not in st.session_state:
        st.session_state.history = []

def load_metrics_artifact(path_dir):
    """
    Loads `metrics.json` created by train_model.py.
    Returns dict or None.
    """
    try:
        p = os.path.join(path_dir, "metrics.json")
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return None
    return None

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def llm_is_configured():
    return bool(os.getenv("OPENAI_API_KEY", "").strip())

@st.cache_data(ttl=3600, show_spinner=False)
def llm_explain_cached(cache_key: str, payload: dict):
    """
    Cached wrapper for the LLM explanation call. `cache_key` must include
    all inputs that should invalidate the cache.
    """
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        return None, "OPENAI_API_KEY is not set."

    url = f"{base_url}/chat/completions"
    req_body = {
        "model": model,
        "temperature": 0.3,
        "messages": payload["messages"],
    }

    data = json.dumps(req_body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            j = json.loads(raw)
            content = (j.get("choices") or [{}])[0].get("message", {}).get("content", "")
            if not content:
                return None, "LLM returned empty response."
            return content, None
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(e)
        return None, f"LLM HTTP error: {e.code} — {detail}"
    except Exception as e:
        return None, f"LLM error: {e}"

def build_llm_messages(lang, verdict, conf, mode, meta, matches, text_preview):
    out_lang = lang if lang in SUPPORTED_LANGS else "English"
    system = (
        "You are an explanation generator for a fake news detection demo called CrediAI. "
        "Explain results clearly for judges: short, structured, and evidence-based. "
        "Never claim certainty; use cautious language. "
        f"Respond in {out_lang}."
    )
    user = f"""
Input type: {mode}
Language: {lang}
Verdict: {verdict}
Confidence: {conf:.1f}%

Hybrid signals:
- matched_real_patterns: {matches.get('real_count', 0)}
- matched_fake_patterns: {matches.get('fake_count', 0)}
- signal_fake_score: {meta.get('sig_fake', 0.0)}
- signal_real_score: {meta.get('sig_real', 0.0)}
- fallback_used: {bool(meta.get('fallback'))}
- fallback_reason: {meta.get('fallback_reason')}

Text (preview): {text_preview}

Write:
1) One-sentence summary.
2) 3-5 bullet reasons grounded in the signals and text characteristics.
3) A “What to check next” section with 3 actionable verification steps.
""".strip()

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

def template_explanation(lang, verdict, conf, mode, meta, st_d, matches):
    if lang == "Tamil":
        return (
            f"**சுருக்கம்:** இது **{conf:.1f}%** நம்பகத்தன்மையுடன் **{('போலி' if verdict=='FAKE' else 'உண்மை')}** என்று கணிக்கப்பட்டுள்ளது.\n\n"
            f"**காரணங்கள் (மாதிரி + சிக்னல்கள்):**\n"
            f"- உள்ளீடு வகை: {('தலைப்பு' if mode=='headline' else 'கட்டுரை')}.\n"
            f"- உண்மை சிக்னல்கள்: {matches.get('real_count',0)} | போலி சிக்னல்கள்: {matches.get('fake_count',0)}.\n"
            f"- எண்/மேற்கோள்: {('உள்ளது' if st_d.get('n') else 'இல்லை')} / {('உள்ளது' if st_d.get('q') else 'இல்லை')}.\n"
            f"- அதிர்ச்சி குறிகள் (!): {st_d.get('e',0)} | CAPS: {st_d.get('c',0)}.\n"
            + (f"- **Fallback** பயன்படுத்தப்பட்டது: {meta.get('fallback_reason')}\n" if meta.get("fallback") else "")
            + "\n**அடுத்ததாக சரிபார்க்க வேண்டியது:**\n"
            "- நம்பகமான மூலங்களில் (The Hindu/Reuters/BBC போன்றவை) இதே செய்தி இருக்கிறதா?\n"
            "- முதன்மை ஆதாரம்/அறிக்கை/அதிகாரப்பூர்வ அறிக்கை இணைப்பு உள்ளதா?\n"
            "- தேதி/இடம்/பெயர்கள் சரியாக உள்ளதா? பழைய செய்தியை மீண்டும் பகிர்கிறார்களா?\n"
        )
    if lang == "Hindi":
        v_hi = "झूठ/फेक" if verdict == "FAKE" else "विश्वसनीय"
        return (
            f"**सार:** **{conf:.1f}%** विश्वास के साथ **{v_hi}** भविष्यवाणी।\n\n"
            f"**कारण (मॉडल + सिग्नल):**\n"
            f"- इनपुट: **{mode}**। रियल सिग्नल: {matches.get('real_count',0)} | फेक सिग्नल: {matches.get('fake_count',0)}।\n"
            f"- संख्याएँ/उद्धरण: {'हाँ' if st_d.get('n') else 'नहीं'} / {'हाँ' if st_d.get('q') else 'नहीं'}। विस्मयादिबोधक: {st_d.get('e',0)}, CAPS: {st_d.get('c',0)}।\n"
            + (f"- **Fallback:** {meta.get('fallback_reason')}\n" if meta.get("fallback") else "")
            + "\n**आगे क्या जाँचें:**\n"
            "- कई विश्वसनीय स्रोतों पर यही खबर मिलती है?\n"
            "- मूल स्रोत, तारीख और स्थान सत्यापित करें।\n"
        )
    return (
        f"**Summary:** Predicted **{verdict}** with **{conf:.1f}%** confidence.\n\n"
        f"**Reasons (model + signals):**\n"
        f"- Input type detected: **{mode}**.\n"
        f"- Matched credibility patterns: **{matches.get('real_count',0)} real** vs **{matches.get('fake_count',0)} fake**.\n"
        f"- Specificity indicators: numbers={'yes' if st_d.get('n') else 'no'}, quotes={'yes' if st_d.get('q') else 'no'}.\n"
        f"- Sensational markers: exclamations={st_d.get('e',0)}, ALL-CAPS tokens={st_d.get('c',0)}.\n"
        + (f"- **Fallback used:** {meta.get('fallback_reason')}\n" if meta.get("fallback") else "")
        + "\n**What to check next:**\n"
        "- Look for the same claim on multiple reputable outlets and official statements.\n"
        "- Verify the original source, date, and location (old stories often resurface).\n"
        "- Cross-check images/videos via reverse search and inspect the full context.\n"
    )

# ── FAKE SIGNALS ─────────────────────────────────────────────────────────────
FAKE_SIGS = [
    (r'!!!',                                                                   5),
    (r'!!',                                                                    3),
    (r'\b(SHOCKING|EXPOSED|MIRACLE|URGENT|ALERT|WARNING)\b',                  4),
    (r'\b(BREAKING(?!\s+news\b))\b',                                           3),
    (r"(they don't want|share before|delete this|wake up|must share)",         4),
    (r'(miracle cure|one weird trick|doctors hate|big pharma)',                5),
    (r'(100% proof|banned video|censored truth|going viral)',                  4),
    (r'(secret plan|hidden agenda|they are hiding|cover.?up)',                 3),
    (r'\b(hoax|rumour|rumor|misinformation|disinformation|debunked)\b',        3),
    (r'(you won\'t believe|won\'t believe what|can\'t believe this)',          4),
    (r'(share now|forward this|send to everyone|don\'t ignore)',               4),
    (r'(watch before (it\'s |they )deleted?|banned everywhere)',               5),
    (r'(natural remedy|home remedy|cures (cancer|diabetes|blindness))',        5),
    (r'\b(MUST (READ|WATCH|SHARE)|VIRAL|LEAKED|BOMBSHELL)\b',                  4),
    (r'(illuminati|deep state|new world order|flat earth|chemtrail)',          5),
    (r'(microchip|5G causes|vaccine kills|vaccine death)',                      5),
    (r'(மீண்டும் அறிமுகமா\?|மீண்டும் வருகிறதா\?|திரும்பி வருமா\?)',        4),
    (r'(ரகசிய திட்டம்|ரகசிய சதி|ரகசியமாக திட்டம்|மறைமுக திட்டம்)',         5),
    (r'(உண்மை என்ன\?|நம்ப முடியுமா\?|நம்ப வேண்டாம்)',                       3),
    (r'(அதிர்ச்சி தகவல்|அதிர்ச்சியான செய்தி|நம்ப முடியவில்லை)',             4),
    (r'(நீக்கப்படும் முன்|மறைக்கப்படுகிறது|தடை செய்யப்படும்)',               5),
    (r'(நம்ப முடியாத|எல்லா நோய்|மூலிகை குணம்|அதிசய மருந்து|குணமாகும்)',    5),
    (r'(ரகசியம் அம்பலம்|மறைத்த உண்மை|வெளியானது ரகசியம்)',                    4),
    (r'(வைரலாகும்|வைரல் வீடியோ|வைரல் செய்தி)',                                3),
    (r'(உடனே பகிருங்கள்|பகிர்ந்து கொள்ளுங்கள்|அனைவருக்கும் அனுப்புங்கள்)',  4),
    (r'(அவசர செய்தி|அவசரம் பாருங்கள்)',                                        3),
    (r'(தடுப்பூசி ஆபத்து|5ஜி கோபுரம் ஆபத்து)',                                5),
]

# ── REAL SIGNALS ─────────────────────────────────────────────────────────────
REAL_SIGS = [
    (r'\b(said|told|stated|announced|confirmed|according to|sources said|officials said|reported|disclosed|revealed|informed)\b', 3),
    (r'\b(press release|spokesperson|official statement|statement issued|PTI|ANI|Reuters|AFP|AP)\b', 4),
    (r'\b(CID|SIT|CBI|ED|NIA|EOW|ACB|DGP|IPS|IAS)\b',                         3),
    (r'\b(remand(ed)?|custody|arrested?|detained?|nabbed|chargesheet)\b',      3),
    (r'\b(bail|FIR|complaint|accused|suspect|undertrial)\b',                   2),
    (r'\b(court|magistrate|judge|verdict|sentenced?|convicted?|acquitted?)\b', 3),
    (r'\b(high court|supreme court|HC|SC|sessions court|special court)\b',     3),
    (r'\b(IPC|CrPC|PMLA|NDPS|UAPA|section\s*\d+|BNS)\b',                      2),
    (r'\b(prison|jail|imprisonment|judicial custody|police custody)\b',        2),
    (r'\b(DMK|BJP|AIADMK|Congress|INC|TMC|AAP|NDA|UPA|JDS|JDU|RJD|SP|BSP|CPI|CPM)\b', 2),
    (r'\b(MLA|MLC|MP|minister|chief minister|CM|governor|cabinet)\b',          2),
    (r'\b(prime minister|president|vice president|Lok Sabha|Rajya Sabha)\b',   2),
    (r'\b(election|parliament|budget|policy|scheme|ruling|judgment|petition)\b', 2),
    (r'\b(launched|inaugurated|approved|signed|passed|cancelled)\b',           1),
    (r'\b(resigned|appointed|transferred|promoted|dismissed|expelled)\b',      2),
    (r'\b(Karnataka|Tamil Nadu|Maharashtra|Delhi|Kerala|Andhra Pradesh|Telangana|Bengal|Bihar|Rajasthan|Gujarat|Punjab|Haryana|Odisha|Assam|Goa)\b', 1),
    (r'\b(Bengaluru|Bangalore|Chennai|Mumbai|Hyderabad|Kolkata|Ahmedabad|Pune|Jaipur|Lucknow)\b', 1),
    (r'\b(Coimbatore|Madurai|Trichy|Salem|Mysuru|Mangaluru)\b',                1),
    (r'\b(Madras HC|Bombay HC|Delhi HC|Calcutta HC|Karnataka HC|Kerala HC)\b', 2),
    (r'\b(ANI|PTI|NDTV|Reuters|AFP|AP|The Hindu|Times of India|Indian Express|Deccan Herald|BBC|CNN)\b', 3),
    (r'Rs\.?\s*[\d,]+',                                                         2),
    (r'\d+\s*(crore|lakh|percent|%)',                                           2),
    (r'\b(February|January|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*20\d\d\b', 2),
    (r'\b(murder|death|killed|accident|flood|fire|blast|attack|robbery|fraud|scam)\b', 1),
    (r'\b(United States|USA|United Kingdom|UK|China|Russia|Pakistan|Bangladesh|Sri Lanka|Ukraine|Israel|France|Germany|Japan|Australia|Canada)\b', 1),
    (r'\b(United Nations|UN|NATO|WHO|IMF|World Bank|G20|G7|EU)\b',             2),
    (r'\b(war|conflict|ceasefire|treaty|sanctions|diplomacy|summit)\b',        1),
    (r'\b(earthquake|tsunami|hurricane|cyclone|wildfire|disaster)\b',          1),
    (r'\b(GDP|inflation|recession|interest rate|Federal Reserve|RBI|Sensex|Nifty)\b', 2),
    (r'\b(vaccine|virus|pandemic|outbreak|hospital|surgery|medicine|disease)\b', 1),
    (r'\b(NASA|ISRO|space|satellite|rocket|launch|mission)\b',                  2),
    (r'\b(technology|AI|startup|CEO|merger|IPO)\b',                             1),
    (r'\b(actor|actress|singer|composer|director|musician|celebrity)\b',        1),
    (r'\b(married|marriage|wedding|divorced?|separated|separation|engaged)\b',  1),
    (r'\b(film|movie|album|song|music|concert|release|box office|OTT)\b',       1),
    (r'\b(award|National Award|Oscar|Grammy|Filmfare|nominated|won)\b',         1),
    (r'\b(cricket|IPL|Test|ODI|T20|World Cup|match|tournament|league|player)\b', 2),
    (r'\b(football|FIFA|Premier League|Champions League|Olympic|medal)\b',      1),
    (r'\b(officially|formally|confirmed|finalized|completed|concluded)\b',      2),
    (r'\d+\s*years?\s*(of|in|together|marriage|relationship|career|service)',   2),
    (r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+(said|arrested|remanded|sentenced|convicted|announced)\b', 2),
    # ── Additional strong real-news signals ───────────────────────────────────
    (r'\b(report(s|ed|ing)?|data shows|study finds|survey reveals|research shows)\b', 3),
    (r'\b(percent|%|crore|lakh|million|billion|Rs\.?\s*\d)',                    2),
    (r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',         1),
    (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b', 1),
    (r'\b(The Hindu|NDTV|Times of India|Indian Express|Deccan Herald|BBC|CNN|Reuters|AFP|PTI|ANI)\b', 4),
    (r'\b(beats?|defeats?|wins?|loses?|draws?|qualifies?)\b',                  1),
    (r'\b(inaugurated|launched|unveiled|commissioned|dedicated)\b',             2),
    (r'\b(resigned?|appointed|transferred|promoted|dismissed|expelled|sacked)\b', 2),
    (r'\b(minister|secretary|director|officer|official|authority)\b',           1),
    (r'\d{4}',                                                                   1),  # 4-digit year
]

# ── TAMIL REAL SIGNALS ────────────────────────────────────────────────────────
TAMIL_REAL_SIGS = [
    # ── Court / Legal ──────────────────────────────────────────────────────────
    (r'(நீதிமன்றம்|தண்டனை|சிறைத்தண்டனை|நீதிபதி|மாஜிஸ்திரேட்|மெட்ரோபாலிட்டன்)', 5),
    (r'(வழக்கு|குற்றவாளி|கைது|போலீஸ்|எக்மூர்|சென்னை நீதிமன்றம்)',                5),
    (r'(உயர் நீதிமன்றம்|உச்ச நீதிமன்றம்|செஷன்ஸ் கோர்ட்|விசேஷ நீதிமன்றம்)',       5),
    (r'(ஜாமீன்|சிறை|காவல்|விசாரணை|குற்றப்பத்திரிகை|சார்ஜ்ஷீட்)',                  4),
    (r'(சிபிஐ|இடி|என்ஐஏ|டிஜிபி|ஐபிஎஸ்|ஐஏஎஸ்)',                                    4),
    # ── Politics / Government ──────────────────────────────────────────────────
    (r'(திமுக|அதிமுக|பாஜக|காங்கிரஸ்|முதலமைச்சர்|ஆளுநர்|அமைச்சர்)',               4),
    (r'(தேர்தல் ஆணையம்|தேர்தல் அட்டவணை|வாக்குப்பதிவு|தொகுதி)',                    5),
    (r'(சட்டமன்றம்|நாடாளுமன்றம்|மக்களவை|ராஜ்யசபா|எம்எல்ஏ|எம்பி)',                4),
    (r'(அரசு அறிவிப்பு|அரசு உத்தரவு|அரசாணை|அரசு திட்டம்)',                         4),
    (r'(மத்திய அரசு|மாநில அரசு|தமிழ்நாடு அரசு|மத்திய அமைச்சர்)',                   3),
    (r'(ஸ்டாலின்|மோடி|அமித் ஷா|ராகுல் காந்தி|பன்னீர்செல்வம்|பழனிசாமி)',            3),
    # ── Reporting verbs (key credibility markers) ──────────────────────────────
    (r'(தெரிவித்தார்|கூறினார்|அறிவித்தார்|உறுதிப்படுத்தினார்|தெரிவித்துள்ளார்)',   5),
    (r'(தெரியவந்துள்ளது|கண்டறியப்பட்டது|உறுதிசெய்யப்பட்டது)',                      4),
    (r'(அறிவிக்கப்பட்டது|வெளியிடப்பட்டது|பதிவு செய்யப்பட்டது)',                    4),
    (r'(நடைபெற்றது|நடைபெற்றன|நடைமுறைப்படுத்தப்பட்டது|தொடங்கப்பட்டது)',            3),
    (r'(என்று தெரிவிக்கப்படுகிறது|என்று செய்திகள் தெரிவிக்கின்றன)',                 4),
    (r'(என்று அதிகாரிகள் தெரிவித்தனர்|என்று போலீஸ் தெரிவித்தது)',                   5),
    # ── Weather / IMD ──────────────────────────────────────────────────────────
    (r'(வானிலை ஆய்வு மையம்|இந்திய வானிலை|ஐஎம்டி|மழை எச்சரிக்கை)',                 5),
    (r'(மழை பெய்யும்|மழை வாய்ப்பு|இடியுடன் கூடிய மழை|வெப்பநிலை)',                  4),
    (r'(தென் மாவட்டங்கள்|கடலோர பகுதி|வடக்கு மாவட்டங்கள்|உள்நாட்டு பகுதி)',         3),
    (r'(செம்மழை|மிதமான மழை|லேசான மழை|கன மழை|ஆரஞ்சு அலெர்ட்|மஞ்சள் அலெர்ட்)',     4),
    # ── Numbers / Specificity ──────────────────────────────────────────────────
    (r'(கோடி ரூபாய்|லட்சம் ரூபாய்|சதவீதம்|\d+\s*ஆண்டு|\d+\s*மாதம்)',               3),
    (r'\d+\s*(கோடி|லட்சம்|சதவீதம்|பேர்|மாவட்டம்|இடம்)',                             3),
    (r'(பிப்ரவரி|மார்ச்|ஏப்ரல்|மே|ஜூன்|ஜூலை|ஆகஸ்ட்|செப்டம்பர்|அக்டோபர்|நவம்பர்|டிசம்பர்|ஜனவரி)', 2),
    # ── Economy / Finance ──────────────────────────────────────────────────────
    (r'(பங்குச்சந்தை|ரிசர்வ் வங்கி|வட்டி விகிதம்|பணவீக்கம்|பட்ஜெட்)',               3),
    (r'(ஏற்றுமதி|இறக்குமதி|வர்த்தகம்|முதலீடு|திட்டம் அறிவிப்பு)',                   3),
    # ── Sources / Institutions ─────────────────────────────────────────────────
    (r'(ஆய்வு அறிக்கை|ஆண்டு அறிக்கை|புள்ளிவிவரம்|அதிகாரப்பூர்வ)',                  4),
    (r'(மாவட்ட ஆட்சியர்|மாவட்ட நிர்வாகம்|துறை அதிகாரி|அரசு அதிகாரி)',               3),
    (r'(பிடிஐ|ஏஎன்ஐ|தி இந்து|டைம்ஸ் ஆஃப் இந்தியா|தினமணி|தினகரன்|தினமலர்)',          5),
    # ── Entertainment / Celebrity ──────────────────────────────────────────────
    (r'(நடிகர்|நடிகை|இசையமைப்பாளர்|இயக்குனர்|பாடகர்|பாடகி)',                       2),
    (r'(திருமணம் முடிந்தது|விவாகரத்து பெற்றனர்|பிரிந்தனர்|மணமுடித்தனர்)',           3),
    (r'(ஜி\.வி\. பிரகாஷ்|சைந்தவி|விஜய்|அஜித்|ரஜினி|தனுஷ்|நயன்தாரா|சமந்தா)',       2),
    (r'(விருது பெற்றார்|தேசிய விருது|ஃபிலிம்ஃபேர்|தேசிய திரைப்பட விருது)',          3),
    (r'(படம் வெளியானது|படப்பிடிப்பு தொடங்கியது|திரை விமர்சனம்|வசூல்)',               2),
    # ── Sports ────────────────────────────────────────────────────────────────
    (r'(கிரிக்கெட்|ஐபிஎல்|வீரர்|அணி|போட்டி|சாம்பியன்|ஒலிம்பிக்|பதக்கம்)',           3),
    (r'(இந்தியா வென்றது|தோல்வி|சாதனை|சதம்|விக்கெட்|ஓட்டங்கள்)',                     2),
    # ── Health / Science ──────────────────────────────────────────────────────
    (r'(மருத்துவமனை|சிகிச்சை|ஆராய்ச்சி|கண்டுபிடிப்பு|இஸ்ரோ|நாசா)',                 3),
    (r'(தடுப்பூசி|நோய்|சுகாதாரம்|ஆரோக்கியம்|மருத்துவர் தெரிவித்தார்)',               3),
    # ── Crime / Disaster ──────────────────────────────────────────────────────
    (r'(கொலை|தாக்குதல்|விபத்து|தீ விபத்து|வெள்ளம்|நிவாரணம்)',                       2),
    (r'(கைது செய்யப்பட்டனர்|தப்பி ஓடினார்|சரண் அடைந்தார்)',                          3),
]

# ── TAMIL FAKE SIGNALS ────────────────────────────────────────────────────────
TAMIL_FAKE_SIGS = [
    (r'(ரகசிய திட்டம்|ரகசிய சதி|மறைமுக திட்டம்)',                                   5),
    (r'(மீண்டும் வருகிறதா\?|மீண்டும் அறிமுகமா\?|திரும்பி வருமா\?)',                4),
    (r'(நீக்கப்படும் முன்|மறைக்கப்படுகிறது)',                                         5),
    (r'(நம்ப முடியாத|எல்லா நோய்|மூலிகை குணம்|அதிசய மருந்து|குணமாகும்)',            5),
    (r'(ரகசியம் அம்பலம்|உண்மை வெளியானது|மறைத்த உண்மை)',                             4),
    (r'(அதிர்ச்சி தகவல்|அதிர்ச்சியான செய்தி|நம்ப முடியவில்லை)',                     4),
    (r'(வைரலாகும்|வைரல் வீடியோ|வைரல் செய்தி)',                                       3),
    (r'(உடனே பகிருங்கள்|பகிர்ந்து கொள்ளுங்கள்|அனைவருக்கும் அனுப்புங்கள்)',          4),
    (r'(அவசர செய்தி|அவசரம் பாருங்கள்)',                                               3),
    (r'(தடுப்பூசி ஆபத்து|5ஜி கோபுரம் ஆபத்து)',                                       5),
]

# ── HINDI (Devanagari) FAKE / REAL SIGNALS ────────────────────────────────────
HINDI_FAKE_SIGS = [
    (r'(शेयर करें|तुरंत शेयर|सबको भेजें|फॉर्वर्ड करें)',                              4),
    (r'(वायरल|विरल|झूठ|अफवाह|फेक न्यूज)',                                           4),
    (r'(सच्चाई सामने|छुपा रहे|साजिश|रहस्य)',                                        4),
    (r'(चौंकाने वाला|डरावना|अविश्वसनीय|अलर्ट|वॉर्निंग)',                              3),
    (r'(मीडिया चुप|सरकार छुपा रही|सच सामने)',                                       4),
    (r'(देखें पहले डिलीट|डिलीट होने से पहले)',                                        5),
]
HINDI_REAL_SIGS = [
    (r'(सरकार|अदालत|पुलिस|मंत्री|अधिकारी)',                                          3),
    (r'(बोला|कहा|दावा|पुष्टि|रिपोर्ट|सूत्रों)',                                      4),
    (r'(पीटीआई|एएनआई|भाषा|रॉयटर्स)',                                                4),
    (r'(न्यूज|समाचार|खबर|रिपोर्ट)',                                                 2),
    (r'(करोड़|लाख|प्रतिशत|रुपये)',                                                  2),
    (r'(जिला|राज्य|देश|महानगर)',                                                    1),
]

# ── SHARED INDIC (Telugu / Malayalam / Kannada) — Roman + script cues ─────────
# Use when no language-specific signals yet; English + punctuation still apply
INDIC_FAKE_SIGS = [
    (r'(share\s*(now|fast|quick)|forward\s*this|send\s*to\s*all)', 4),
    (r'(viral|fake|rumour|hoax|misinformation)', 3),
    (r'!!!|!!', 3),
]
INDIC_REAL_SIGS = [
    (r'(said|reported|confirmed|according to|sources)', 3),
    (r'(government|court|police|minister|official)', 2),
]


def score_text(text, lang="English"):
    """Returns (fake_score, real_score). lang in English|Tamil|Hindi|Telugu|Malayalam|Kannada."""
    fake_score = 0.0
    real_score = 0.0
    for pattern, weight in FAKE_SIGS:
        if re.search(pattern, text, re.I):
            fake_score += weight
    for pattern, weight in REAL_SIGS:
        if re.search(pattern, text, re.I):
            real_score += weight
    if lang == "Tamil":
        for pattern, weight in TAMIL_FAKE_SIGS:
            if re.search(pattern, text):
                fake_score += weight
        for pattern, weight in TAMIL_REAL_SIGS:
            if re.search(pattern, text):
                real_score += weight
    elif lang == "Hindi":
        for pattern, weight in HINDI_FAKE_SIGS:
            if re.search(pattern, text):
                fake_score += weight
        for pattern, weight in HINDI_REAL_SIGS:
            if re.search(pattern, text):
                real_score += weight
    elif lang in ("Telugu", "Malayalam", "Kannada"):
        for pattern, weight in INDIC_FAKE_SIGS:
            if re.search(pattern, text, re.I):
                fake_score += weight
        for pattern, weight in INDIC_REAL_SIGS:
            if re.search(pattern, text, re.I):
                real_score += weight
    # Punctuation penalties
    excl   = text.count('!') + text.count('।')
    caps   = len(re.findall(r'\b[A-Z]{4,}\b', text))
    q_mark = text.count('?')
    if excl > 1:              fake_score += (excl - 1) * 2.0
    if caps > 3:              fake_score += (caps - 3) * 1.5
    if q_mark >= 1 and real_score < 5:
        fake_score += q_mark * 1.5
    return fake_score, real_score


def scores_to_probs(fake_score, real_score):
    """
    Convert raw scores → calibrated probabilities.
    Max confidence capped at 95% to stay realistic but show strong signals clearly.
    """
    total = fake_score + real_score
    if total == 0:
        return 0.50, 0.50
    fp = fake_score / total
    rp = real_score / total
    # Sharpening factor: 1.35x for stronger differentiation
    if fp >= rp:
        fp = min(0.95, fp * 1.35)
    else:
        rp = min(0.95, rp * 1.35)
    t = fp + rp
    return fp / t, rp / t


def _blend(model_fake, sig_fake, sig_real):
    """Blend transformer model output with signal engine. Prefer model when confident."""
    sig_fp, _ = scores_to_probs(sig_fake, sig_real)

    # When model is very confident, trust it (fixes fake→real flip)
    if model_fake >= 0.85:
        fp = max(model_fake * 0.9, 0.75)
    elif model_fake <= 0.15:
        fp = min(model_fake * 1.1, 0.25)
    elif sig_fake == 0 and sig_real == 0:
        # No signals → trust model fully (no cap toward real)
        fp = model_fake
    elif sig_fake > 0 and sig_real == 0:
        fp = 0.35 * model_fake + 0.65 * sig_fp
    elif sig_real > 0 and sig_fake == 0:
        fp = 0.40 * model_fake + 0.60 * sig_fp
    else:
        fp = 0.55 * model_fake + 0.45 * sig_fp

    # Mild overrides only when signals are very strong (avoid overpowering model)
    if sig_real >= 10 and sig_fake == 0 and model_fake < 0.6:
        fp = min(fp, 0.20)
    if sig_fake >= 10 and sig_real == 0 and model_fake > 0.4:
        fp = max(fp, 0.80)

    return max(0.05, min(0.95, fp))

def matched_signals(text, lang="English"):
    """Returns dict: {fake:[...], real:[...], fake_count, real_count}."""
    m_fake, m_real = [], []
    for pattern, _ in FAKE_SIGS:
        if re.search(pattern, text, re.I):
            m_fake.append(pattern)
    for pattern, _ in REAL_SIGS:
        if re.search(pattern, text, re.I):
            m_real.append(pattern)
    if lang == "Tamil":
        for pattern, _ in TAMIL_FAKE_SIGS:
            if re.search(pattern, text):
                m_fake.append(pattern)
        for pattern, _ in TAMIL_REAL_SIGS:
            if re.search(pattern, text):
                m_real.append(pattern)
    elif lang == "Hindi":
        for pattern, _ in HINDI_FAKE_SIGS:
            if re.search(pattern, text):
                m_fake.append(pattern)
        for pattern, _ in HINDI_REAL_SIGS:
            if re.search(pattern, text):
                m_real.append(pattern)
    elif lang in ("Telugu", "Malayalam", "Kannada"):
        for pattern, _ in INDIC_FAKE_SIGS:
            if re.search(pattern, text, re.I):
                m_fake.append(pattern)
        for pattern, _ in INDIC_REAL_SIGS:
            if re.search(pattern, text, re.I):
                m_real.append(pattern)
    return {
        "fake": m_fake[:12],
        "real": m_real[:12],
        "fake_count": len(m_fake),
        "real_count": len(m_real),
    }

def predict_en(text):
    mode = "headline" if is_headline(text) else "article"
    mp   = HEADLINE_MODEL if (mode == "headline" and can_use_model(HEADLINE_MODEL)) else ARTICLE_MODEL
    sig_fake, sig_real = score_text(text, "English")
    try:
        tok, mdl, fake_idx, real_idx = load_model(mp)
        model_fake, _ = infer(text, tok, mdl, fake_idx, real_idx, mp)
        fp = _blend(model_fake, sig_fake, sig_real)
        return fp, 1 - fp, mode, {"model": mp, "fallback": False, "fallback_reason": None, "sig_fake": sig_fake, "sig_real": sig_real}
    except Exception:
        return _signal_only_fallback(
            "English",
            mode,
            sig_fake,
            sig_real,
            reason_override=f"English transformer model load failed; used signal-only engine. ({mp})",
        )


def _signal_only_fallback(lang, mode, sig_fake, sig_real, reason_override=None):
    """Shared fallback when no transformer model is available for this language."""
    reason = reason_override or f"{lang} transformer model not found; used signal-only engine."
    if sig_fake == 0 and sig_real == 0:
        return 0.38, 0.62, mode, {"model": None, "fallback": True, "fallback_reason": reason, "sig_fake": sig_fake, "sig_real": sig_real}
    total = sig_fake + sig_real
    raw_fp = sig_fake / total
    raw_rp = sig_real / total
    if raw_fp >= raw_rp:
        raw_fp = min(0.95, raw_fp * 1.60)
    else:
        raw_rp = min(0.95, raw_rp * 1.60)
    t = raw_fp + raw_rp
    fp, rp = raw_fp / t, raw_rp / t
    if sig_real >= 12 and sig_fake == 0: fp = min(fp, 0.09)
    if sig_real >= 8  and sig_fake == 0: fp = min(fp, 0.13)
    if sig_real >= 5  and sig_fake == 0: fp = min(fp, 0.18)
    if sig_real >= 3  and sig_fake == 0: fp = min(fp, 0.25)
    if sig_fake >= 12 and sig_real == 0: fp = max(fp, 0.91)
    if sig_fake >= 8  and sig_real == 0: fp = max(fp, 0.87)
    if sig_fake >= 5  and sig_real == 0: fp = max(fp, 0.82)
    if sig_fake >= 3  and sig_real == 0: fp = max(fp, 0.75)
    return max(0.05, fp), max(0.05, 1 - fp), mode, {"model": None, "fallback": True, "fallback_reason": reason, "sig_fake": sig_fake, "sig_real": sig_real}


def predict_ta(text):
    mode = "headline" if is_headline(text) else "article"
    sig_fake, sig_real = score_text(text, "Tamil")
    if can_use_model(TAMIL_MODEL):
        try:
            tok, mdl, fake_idx, real_idx = load_model(TAMIL_MODEL)
            model_fake, _ = infer(text, tok, mdl, fake_idx, real_idx, TAMIL_MODEL)
            fp = _blend(model_fake, sig_fake, sig_real)
            return fp, 1 - fp, mode, {"model": TAMIL_MODEL, "fallback": False, "fallback_reason": None, "sig_fake": sig_fake, "sig_real": sig_real}
        except Exception:
            return _signal_only_fallback(
                "Tamil",
                mode,
                sig_fake,
                sig_real,
                reason_override=f"Tamil transformer model load failed; used signal-only engine. ({TAMIL_MODEL})",
            )
    return _signal_only_fallback("Tamil", mode, sig_fake, sig_real)


def predict_indic(text, lang):
    """Hindi, Telugu, Malayalam, Kannada — use MODEL_REGISTRY (pre-trained HF); fallback to signal-only."""
    mode = "headline" if is_headline(text) else "article"
    sig_fake, sig_real = score_text(text, lang)
    model_path = MODEL_REGISTRY.get(lang)
    if model_path and can_use_model(model_path):
        try:
            tok, mdl, fake_idx, real_idx = load_model(model_path)
            model_fake, _ = infer(text, tok, mdl, fake_idx, real_idx, model_path)
            fp = _blend(model_fake, sig_fake, sig_real)
            return fp, 1 - fp, mode, {"model": model_path, "fallback": False, "fallback_reason": None, "sig_fake": sig_fake, "sig_real": sig_real}
        except Exception:
            return _signal_only_fallback(
                lang,
                mode,
                sig_fake,
                sig_real,
                reason_override=f"{lang} transformer model load failed; used signal-only engine. ({model_path})",
            )
    return _signal_only_fallback(lang, mode, sig_fake, sig_real)


def get_stats(text):
    return {
        "w":  len(text.split()),
        "n":  bool(re.search(r'\d', text)),
        "q":  bool(re.search(r'["\']', text)),
        "e":  text.count('!') + text.count('।'),
        "qm": text.count('?'),
        "c":  len(re.findall(r'\b[A-Z]{3,}\b', text))
    }

# ─── SOCIAL MEDIA MONITOR v2 ───────────────────────────────────────────────
# Architecture: API → Account Validator → Post Fetcher → 6-Step Pipeline → UI
# Data ingestion (production): Instagram Graph API / Twitter v2 (public only)
# Validation engine: existence · public status · credibility signals
# Analysis engine: NLP · OCR · comment analysis · authenticity · scoring
# NOTE: Posts are simulated public-facing data. Replace _get_social_posts()
#       with real API calls — tweepy.Client / GET /{user-id}/media.
#       Only PUBLIC accounts are targeted. Private/suspended excluded.

# ── LIVE DATA FETCHING ────────────────────────────────────────────────────────
# Priority chain (tried in order, first success wins):
#
#  Instagram  1. instaloader (authenticated session via sidebar credentials)
#             2. Google News RSS (real current headlines, same orgs)
#
#  Twitter/X  1. Twitter API v2 Bearer Token (requires Basic plan $100/mo)
#             2. Google News RSS (real current headlines, same orgs)
#
# Cache TTL = 300 s (5 min).  All fetched posts carry 'live': True.

# Instagram handles to fetch (in order)
_IG_HANDLES = ["reuters", "bbcnews", "natgeo", "who", "nypost", "dailymail"]

# Twitter/X handles → account_id mapping
_TW_HANDLE_MAP = {
    "Reuters": "reuters", "AP": "ap", "nytimes": "nytimes",
    "NASA": "nasa", "nypost": "nypost", "DailyMail": "dailymail",
    "WHO": "who", "BBCWorld": "bbcnews",
}

# Google News RSS URLs — one per real account (fallback for both platforms)
_GNEWS_RSS = {
    "reuters":   "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
    "bbcnews":   "https://news.google.com/rss/search?q=site:bbc.co.uk+news&hl=en-US&gl=US&ceid=US:en",
    "natgeo":    "https://news.google.com/rss/search?q=site:nationalgeographic.com&hl=en-US&gl=US&ceid=US:en",
    "who":       "https://news.google.com/rss/search?q=site:who.int&hl=en-US&gl=US&ceid=US:en",
    "nypost":    "https://news.google.com/rss/search?q=site:nypost.com&hl=en-US&gl=US&ceid=US:en",
    "dailymail": "https://news.google.com/rss/search?q=site:dailymail.co.uk&hl=en-US&gl=US&ceid=US:en",
    "ap":        "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en",
    "nytimes":   "https://news.google.com/rss/search?q=site:nytimes.com&hl=en-US&gl=US&ceid=US:en",
    "nasa":      "https://news.google.com/rss/search?q=site:nasa.gov&hl=en-US&gl=US&ceid=US:en",
}

def _rss_age_min(entry):
    """Parse RSS published timestamp → minutes ago."""
    try:
        if getattr(entry, "published_parsed", None):
            from calendar import timegm
            pub = datetime.fromtimestamp(timegm(entry.published_parsed), tz=timezone.utc)
        else:
            pub = _eu.parsedate_to_datetime(entry.get("published","")).astimezone(timezone.utc)
        return max(1, int((datetime.now(timezone.utc) - pub).total_seconds() / 60))
    except Exception:
        return 60

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_rss_account(account_id):
    """Fetch top 3 real headlines from Google News RSS for one account.
    Returns list of post dicts with live=True and source='rss'."""
    url = _GNEWS_RSS.get(account_id)
    if not url:
        return []
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "CrediAI/1.0"})
        posts = []
        for e in feed.entries[:3]:
            raw   = e.get("title", "")
            # Strip trailing " - Source Name" appended by Google News
            title = re.sub(r"\s*[-–]\s*[^-–]{2,60}$", "", raw).strip() or raw
            # Google News summary is always the title repeated — use title only
            cap   = title[:300]
            posts.append({
                "account_id":       account_id,
                "caption":          cap,
                "hashtags":         [],
                "likes":            0,
                "comments_count":   0,
                "shares":           0,
                "post_age_minutes": _rss_age_min(e),
                "has_media":        False,
                "media_type":       "none",
                "ocr_text":         None,
                "ocr_mismatch":     False,
                "comments_sample":  [],
                "source_link":      e.get("link", ""),
                "live":             True,
                "source":           "rss",
            })
        return posts
    except Exception:
        return []

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_ig_profile(username, ig_user="", ig_pass=""):
    """Fetch up to 3 real posts from a public Instagram account via instaloader.
    Requires ig_user+ig_pass — Instagram blocks ALL anonymous SSL connections.
    Returns [] immediately if no credentials or instaloader not installed."""
    if not _IL_OK:
        return []
    # Instagram actively blocks anonymous connections with an SSL EOF.
    # There is no point attempting without credentials — skip instantly.
    if not ig_user.strip() or not ig_pass.strip():
        return []
    try:
        L = _instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            compress_json=False,
            save_metadata=False,
            quiet=True,
            max_connection_attempts=1,   # fail fast — no retries
        )
        try:
            L.login(ig_user.strip(), ig_pass.strip())
        except Exception:
            return []   # Login failed → don't attempt anonymous fetch
        profile = _instaloader.Profile.from_username(L.context, username)
        posts = []
        for post in itertools.islice(profile.get_posts(), 3):
            try:
                cap = (post.caption or "").strip()[:500]
                tags = list(post.caption_hashtags)[:10] if post.caption else []
                pub_dt = post.date_utc.replace(tzinfo=timezone.utc)
                age_min = max(1, int((datetime.now(timezone.utc) - pub_dt).total_seconds() / 60))
                shortcode = post.shortcode
                posts.append({
                    "account_id":       username.lower().replace(".", "").replace("_", ""),
                    "caption":          cap,
                    "hashtags":         tags,
                    "likes":            post.likes,
                    "comments_count":   post.comments,
                    "shares":           0,
                    "post_age_minutes": age_min,
                    "has_media":        True,
                    "media_type":       "video" if post.is_video else "image",
                    "ocr_text":         None,
                    "ocr_mismatch":     False,
                    "comments_sample":  [],
                    "source_link":      f"https://www.instagram.com/p/{shortcode}/",
                    "live":             True,
                    "ig_username":      username,
                })
            except Exception:
                continue
        return posts
    except Exception:
        return []

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_tw_api(bearer_token):
    """Fetch one real tweet per account from Twitter/X API v2.
    Returns list of post dicts with live=True.  Returns [] on any error."""
    # Decode URL-encoded token (e.g. %3D → =) before passing to tweepy
    token = _urlparse.unquote(bearer_token.strip())
    if not _TWEEPY_OK or not token:
        return []
    try:
        client = _tweepy.Client(bearer_token=token, wait_on_rate_limit=False)
        posts = []
        for handle, acc_id in _TW_HANDLE_MAP.items():
            try:
                ur = client.get_user(
                    username=handle,
                    user_fields=["public_metrics", "created_at", "verified"],
                )
                if not ur or not ur.data:
                    continue
                uid  = ur.data.id
                tr = client.get_users_tweets(
                    uid,
                    max_results=5,
                    tweet_fields=["created_at", "public_metrics", "entities"],
                    exclude=["retweets", "replies"],
                )
                if not tr or not tr.data:
                    continue
                tw = tr.data[0]
                age = 60
                if tw.created_at:
                    age = max(1, int((datetime.now(timezone.utc) - tw.created_at).total_seconds() / 60))
                pm  = tw.public_metrics or {}
                # Extract hashtags from entities
                tags = []
                if tw.entities and "hashtags" in tw.entities:
                    tags = [h.get("tag", "") for h in tw.entities["hashtags"]]
                posts.append({
                    "account_id":       acc_id,
                    "caption":          tw.text,
                    "hashtags":         tags,
                    "likes":            pm.get("like_count", 0),
                    "comments_count":   pm.get("reply_count", 0),
                    "shares":           pm.get("retweet_count", 0),
                    "quote_count":      pm.get("quote_count", 0),
                    "post_age_minutes": age,
                    "has_media":        False,
                    "media_type":       "none",
                    "ocr_text":         None,
                    "ocr_mismatch":     False,
                    "comments_sample":  [],
                    "source_link":      f"https://x.com/{handle}/status/{tw.id}",
                    "live":             True,
                    "tw_handle":        handle,
                })
            except Exception:
                continue
        return posts
    except Exception:
        return []

# ── DATA SCHEMA: AccountProfile ─────────────────────────────────────────────
# handle, name, is_valid, validation_status, validation_reason,
# account_age_days, followers, following, verified,
# posts_per_day, avg_engagement_rate, content_niche, burst_detected
_ACCOUNT_PROFILES = {
    # ── Real, publicly verifiable accounts ──────────────────────────────────
    # All handles below exist on Instagram / Twitter-X and can be looked up.
    # Post content in _IG_POST_DATA / _TW_POST_DATA is SIMULATED for demo purposes.
    "reuters":    {"handle":"@reuters","name":"Reuters","account_age_days":5200,"followers":3_200_000,"following":856,"verified":True,"posts_per_day":40.0,"is_valid":True,"validation_status":"public","avg_engagement_rate":0.003,"content_niche":["news","world","politics","breaking"],"burst_detected":False},
    "bbcnews":    {"handle":"@bbcnews","name":"BBC News","account_age_days":5110,"followers":21_000_000,"following":120,"verified":True,"posts_per_day":20.0,"is_valid":True,"validation_status":"public","avg_engagement_rate":0.004,"content_niche":["news","science","health","world"],"burst_detected":False},
    "natgeo":     {"handle":"@natgeo","name":"National Geographic","account_age_days":5480,"followers":290_000_000,"following":280,"verified":True,"posts_per_day":4.0,"is_valid":True,"validation_status":"public","avg_engagement_rate":0.012,"content_niche":["science","nature","climate","exploration"],"burst_detected":False},
    "who":        {"handle":"@who","name":"World Health Organization","account_age_days":4380,"followers":13_000_000,"following":145,"verified":True,"posts_per_day":3.0,"is_valid":True,"validation_status":"public","avg_engagement_rate":0.005,"content_niche":["health","medicine","global","pandemic"],"burst_detected":False},
    "nasa":       {"handle":"@nasa","name":"NASA","account_age_days":5110,"followers":97_000_000,"following":67,"verified":True,"posts_per_day":3.0,"is_valid":True,"validation_status":"public","avg_engagement_rate":0.015,"content_niche":["science","space","climate","research"],"burst_detected":False},
    "ap":         {"handle":"@ap","name":"The Associated Press","account_age_days":5480,"followers":5_800_000,"following":420,"verified":True,"posts_per_day":50.0,"is_valid":True,"validation_status":"public","avg_engagement_rate":0.003,"content_niche":["news","breaking","world","politics"],"burst_detected":False},
    "nytimes":    {"handle":"@nytimes","name":"The New York Times","account_age_days":5200,"followers":12_000_000,"following":310,"verified":True,"posts_per_day":18.0,"is_valid":True,"validation_status":"public","avg_engagement_rate":0.007,"content_niche":["news","politics","culture","opinion"],"burst_detected":False},
    "nypost":     {"handle":"@nypost","name":"New York Post","account_age_days":4745,"followers":3_100_000,"following":890,"verified":True,"posts_per_day":35.0,"is_valid":True,"validation_status":"public","avg_engagement_rate":0.018,"content_niche":["news","tabloid","politics","celebrity"],"burst_detected":False},
    "dailymail":  {"handle":"@dailymail","name":"Daily Mail","account_age_days":4380,"followers":3_500_000,"following":980,"verified":True,"posts_per_day":45.0,"is_valid":True,"validation_status":"public","avg_engagement_rate":0.022,"content_niche":["tabloid","celebrity","health","politics"],"burst_detected":False},
    # ── Invalid / excluded accounts (fictional handles — demo only) ──────────
    # NOTE: Handles below are intentionally fictional to demonstrate account
    # validation exclusion. Do NOT look these up — they do not exist.
    "demo_private":    {"handle":"@healthtips.private.demo","name":"HealthTips Private","is_valid":False,"validation_status":"private","validation_reason":"Account is set to private — posts are not accessible","followers":0,"following":0,"verified":False,"account_age_days":0},
    "demo_suspended":  {"handle":"@viraltruth.demo.suspended","name":"ViralTruth (Demo)","is_valid":False,"validation_status":"suspended","validation_reason":"Account suspended for repeated policy violations","followers":0,"following":0,"verified":False,"account_age_days":0},
    "demo_notfound":   {"handle":"@newsflash.demo.notfound","name":"NewsFlash (Demo)","is_valid":False,"validation_status":"not_found","validation_reason":"Account not found — may have been deleted or never existed","followers":0,"following":0,"verified":False,"account_age_days":0},
    "demo_restricted": {"handle":"@conspiracyhub.demo.restricted","name":"ConspiracyHub (Demo)","is_valid":False,"validation_status":"restricted","validation_reason":"Account content restricted by platform policy","followers":0,"following":0,"verified":False,"account_age_days":0},
}

# ── DATA SCHEMA: Post ────────────────────────────────────────────────────────
# account_id, caption, hashtags, likes, comments_count, shares, post_age_minutes,
# has_media, media_type, ocr_text, ocr_mismatch, comments_sample[{text,sentiment}]
# NOTE: All account_id values below map to real accounts in _ACCOUNT_PROFILES.
# Post captions are SIMULATED examples for educational/demo purposes only.
# IG = Instagram feed  |  TW = Twitter/X feed
_IG_POST_DATA = [
    # @reuters — Likely Reliable
    {"account_id":"reuters","caption":"UN Secretary-General announced a new global climate resilience framework signed by 127 nations at the Geneva summit on Thursday. Full report at reuters.com #UN #climate #worldnews","hashtags":["UN","climate","news","worldnews"],"likes":8900,"comments_count":1200,"shares":4500,"post_age_minutes":35,"has_media":False,"media_type":"none","ocr_text":None,"ocr_mismatch":False,"comments_sample":[{"text":"Important step forward for climate action.","sentiment":"positive"},{"text":"Which nations specifically signed?","sentiment":"neutral"},{"text":"More empty promises from the UN.","sentiment":"negative"},{"text":"Finally! The world needed this.","sentiment":"positive"}]},
    # @bbcnews — Likely Reliable
    {"account_id":"bbcnews","caption":"Researchers at Oxford University published findings on an Alzheimer's treatment showing 34% improvement in cognitive function in early-stage patients. Phase 2 clinical trial published in Nature Medicine. #science #health #alzheimers","hashtags":["science","health","alzheimers","research"],"likes":15600,"comments_count":2100,"shares":6200,"post_age_minutes":180,"has_media":True,"media_type":"image","ocr_text":"Oxford University — Nature Medicine — Phase 2 Clinical Trial Results — March 2026","ocr_mismatch":False,"comments_sample":[{"text":"Incredible hope for Alzheimer's families.","sentiment":"positive"},{"text":"Phase 2 still needs Phase 3 to confirm.","sentiment":"neutral"},{"text":"What is the timeline for Phase 3 trials?","sentiment":"neutral"},{"text":"Praying this becomes available soon.","sentiment":"positive"}]},
    # @natgeo — Likely Reliable
    {"account_id":"natgeo","caption":"NASA and NOAA data confirms 2025 was the hottest year on record — 1.52°C above pre-industrial levels. The data is unambiguous. Report in Science journal. #climate #globalwarming #NASA #science","hashtags":["climate","globalwarming","science","NASA"],"likes":42300,"comments_count":5890,"shares":18400,"post_age_minutes":240,"has_media":True,"media_type":"image","ocr_text":"NASA/NOAA Global Surface Temperature Analysis 2025 — +1.52°C above pre-industrial baseline","ocr_mismatch":False,"comments_sample":[{"text":"The data is undeniable. We must act now.","sentiment":"positive"},{"text":"Scientists have warned about this for decades.","sentiment":"neutral"},{"text":"Some politicians still refuse to accept the data.","sentiment":"negative"},{"text":"Stunning and terrifying at the same time.","sentiment":"neutral"}]},
    # @nypost — Needs Verification (tabloid sensational style)
    {"account_id":"nypost","caption":"EXCLUSIVE: Leaked CDC documents reveal agency buried alarming side-effect data that was never disclosed to the public — whistleblower drops bombshell files 🚨 #exclusive #CDC #health #breaking","hashtags":["exclusive","CDC","health","breaking"],"likes":28500,"comments_count":9400,"shares":31200,"post_age_minutes":22,"has_media":True,"media_type":"image","ocr_text":"EXCLUSIVE — BOMBSHELL LEAK — CDC INTERNAL MEMO — DO NOT DISTRIBUTE","ocr_mismatch":True,"comments_sample":[{"text":"Where is the actual document? Post the source.","sentiment":"neutral"},{"text":"This is irresponsible journalism. Check facts first.","sentiment":"negative"},{"text":"Finally someone is exposing them!","sentiment":"positive"},{"text":"Reuters or AP haven't reported this. Red flag.","sentiment":"negative"},{"text":"SHARE before they take this down!","sentiment":"positive"},{"text":"Snopes.com says the document is unverified.","sentiment":"negative"}]},
    # @who — Likely Reliable
    {"account_id":"who","caption":"WHO situation report: No new global health emergency declared as of March 2026. Monitoring ongoing on respiratory illness outbreaks in South-East Asia. Full report at who.int #WHO #publichealth","hashtags":["WHO","publichealth","global","health"],"likes":8700,"comments_count":1400,"shares":3200,"post_age_minutes":120,"has_media":False,"media_type":"none","ocr_text":None,"ocr_mismatch":False,"comments_sample":[{"text":"Thank you for the official update.","sentiment":"positive"},{"text":"Good to know. Please keep monitoring.","sentiment":"positive"},{"text":"Which specific regions in South-East Asia?","sentiment":"neutral"},{"text":"Stay safe everyone. Follow official guidance.","sentiment":"positive"}]},
    # @dailymail — Needs Verification (tabloid sensational style)
    {"account_id":"dailymail","caption":"WORLD EXCLUSIVE: How Big Tech billionaires are secretly funding shadowy experiments to 'hack' the human body — and what they're hiding from you 👀 #bigtech #health #exclusive #shocking","hashtags":["bigtech","health","exclusive","shocking"],"likes":19800,"comments_count":6200,"shares":14300,"post_age_minutes":55,"has_media":True,"media_type":"image","ocr_text":"EXCLUSIVE INVESTIGATION — WHAT THEY DON'T WANT YOU TO KNOW","ocr_mismatch":True,"comments_sample":[{"text":"Clickbait headline. Article says nothing.","sentiment":"negative"},{"text":"This sounds terrifying if true! Share!","sentiment":"positive"},{"text":"No named sources anywhere in the article.","sentiment":"negative"},{"text":"FactCheck.org rated the headline misleading.","sentiment":"negative"},{"text":"Share this before it disappears!!","sentiment":"positive"}]},
    # @demo_private — Invalid: private account (fictional demo handle)
    {"account_id":"demo_private","caption":None,"hashtags":[],"likes":0,"comments_count":0,"shares":0,"post_age_minutes":0,"has_media":False,"media_type":"none","ocr_text":None,"ocr_mismatch":False,"comments_sample":[]},
]
_TW_POST_DATA = [
    # @ap — Likely Reliable
    {"account_id":"ap","caption":"BREAKING: Federal Reserve raised interest rates by 0.25% at today's FOMC meeting per official statement. Chair Jerome Powell cited continued inflation concerns. Full coverage at apnews.com #Fed #economy #news","hashtags":["Fed","economy","FederalReserve","news"],"likes":12400,"comments_count":2800,"shares":8900,"post_age_minutes":45,"has_media":False,"media_type":"none","ocr_text":None,"ocr_mismatch":False,"comments_sample":[{"text":"Expected move given current inflation data.","sentiment":"neutral"},{"text":"This will hurt regular working families.","sentiment":"negative"},{"text":"Markets already priced this in last week.","sentiment":"neutral"},{"text":"Good for savers. Tough for borrowers.","sentiment":"neutral"}]},
    # @nytimes — Likely Reliable
    {"account_id":"nytimes","caption":"A new Senate investigation found that social media algorithms amplified vaccine misinformation to millions of users despite platform moderation policies. Full investigation at nytimes.com #socialmedia #health #tech","hashtags":["socialmedia","health","tech","politics"],"likes":18900,"comments_count":4100,"shares":9800,"post_age_minutes":90,"has_media":True,"media_type":"image","ocr_text":"Senate Investigation Report — Social Media Algorithm Amplification — March 2026","ocr_mismatch":False,"comments_sample":[{"text":"This is what researchers have documented for years.","sentiment":"neutral"},{"text":"Platforms need to be held accountable.","sentiment":"negative"},{"text":"Good investigative journalism. Important story.","sentiment":"positive"},{"text":"Follow the money. Engagement = profit.","sentiment":"neutral"}]},
    # @nypost — Needs Verification
    {"account_id":"nypost","caption":"CAUGHT: Shocking new video shows what the government officials don't want you to see about the border — footage obtained EXCLUSIVELY by The Post 🚨 #breaking #exclusive #border","hashtags":["breaking","exclusive","border","politics"],"likes":34200,"comments_count":12800,"shares":28900,"post_age_minutes":18,"has_media":True,"media_type":"video","ocr_text":"NYPOST EXCLUSIVE — BORDER CRISIS EXPOSED — UNCUT FOOTAGE","ocr_mismatch":False,"comments_sample":[{"text":"Share everywhere before they take it down!","sentiment":"positive"},{"text":"Context matters. This seems very one-sided.","sentiment":"negative"},{"text":"Where is the full unedited video?","sentiment":"neutral"},{"text":"AP and Reuters reported a different version.","sentiment":"negative"},{"text":"This is important. Everyone needs to see this!","sentiment":"positive"}]},
    # @who — Likely Reliable
    {"account_id":"who","caption":"The WHO confirms mpox vaccines are safe and effective based on data from 48 countries. Routine immunisation is recommended for high-risk groups. Full guidance at who.int #mpox #health #vaccines","hashtags":["mpox","health","vaccines","WHO"],"likes":6700,"comments_count":980,"shares":2800,"post_age_minutes":200,"has_media":False,"media_type":"none","ocr_text":None,"ocr_mismatch":False,"comments_sample":[{"text":"Thank you WHO for clear guidance.","sentiment":"positive"},{"text":"How accessible are these vaccines in low-income countries?","sentiment":"neutral"},{"text":"Good. Science-based policy is essential.","sentiment":"positive"},{"text":"Which countries have the vaccines available now?","sentiment":"neutral"}]},
    # @dailymail — Needs Verification
    {"account_id":"dailymail","caption":"BOMBSHELL: Scientists you've never heard of claim eating THIS common food every day dramatically SLASHES cancer risk — doctors are baffled 😱 #health #cancer #exclusive #shocking","hashtags":["health","cancer","exclusive","shocking"],"likes":41800,"comments_count":15200,"shares":38700,"post_age_minutes":30,"has_media":True,"media_type":"image","ocr_text":"SHOCKING STUDY — MIRACLE FOOD DOCTORS WON'T TELL YOU ABOUT","ocr_mismatch":True,"comments_sample":[{"text":"Clickbait. The study had 40 participants.","sentiment":"negative"},{"text":"Every week it's a different miracle food.","sentiment":"negative"},{"text":"Share with family! This could save lives!","sentiment":"positive"},{"text":"No peer review? No named researchers? Pass.","sentiment":"negative"},{"text":"Snopes and WebMD say this is massively overstated.","sentiment":"negative"},{"text":"Finally real health news!","sentiment":"positive"}]},
    # @nasa — Likely Reliable
    {"account_id":"nasa","caption":"New data from JWST confirms the existence of carbon dioxide in the atmosphere of exoplanet K2-18b — a key biosignature indicator. This is a landmark in the search for life beyond Earth. #NASA #JWST #space #science","hashtags":["NASA","JWST","space","science"],"likes":198000,"comments_count":24500,"shares":87000,"post_age_minutes":300,"has_media":True,"media_type":"image","ocr_text":"NASA / ESA / CSA — James Webb Space Telescope — K2-18b Atmospheric Spectra — CO2 Detection","ocr_mismatch":False,"comments_sample":[{"text":"This is one of the most exciting science stories of the decade.","sentiment":"positive"},{"text":"CO2 alone doesn't confirm life. But it is remarkable.","sentiment":"neutral"},{"text":"Absolutely mind-blowing. Humanity is at a historic moment.","sentiment":"positive"},{"text":"Still a long way from confirmation, but what a finding!","sentiment":"neutral"}]},
    # @demo_suspended — Invalid: suspended (fictional demo handle)
    {"account_id":"demo_suspended","caption":None,"hashtags":[],"likes":0,"comments_count":0,"shares":0,"post_age_minutes":0,"has_media":False,"media_type":"none","ocr_text":None,"ocr_mismatch":False,"comments_sample":[]},
]
_FACTCHECK_DB = [
    ("Snopes","https://www.snopes.com"),("PolitiFact","https://www.politifact.com"),
    ("FactCheck.org","https://www.factcheck.org"),("AP Fact Check","https://apnews.com/hub/ap-fact-check"),
    ("Reuters FactCheck","https://www.reuters.com/fact-check"),
    ("WHO MythBusters","https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters"),
    ("Boom Live","https://www.boomlive.in"),("AltNews","https://www.altnews.in"),
]
_TRENDING_FLAGS = ["#5G vaccines","#election fraud","#miracle cures","#big pharma","#microchip conspiracy","#vaccine death"]

def _fmt_count(n):
    if n>=1_000_000: return f"{n/1_000_000:.1f}M"
    if n>=1_000:     return f"{n/1_000:.1f}K"
    return str(n)
def _acct_age_label(d):
    if d<30:  return f"{d}d old"
    if d<365: return f"{d//30}mo old"
    y=d//365; m=(d%365)//30; return f"{y}yr"+( f" {m}mo" if m else "")+" old"
def _post_age_label(m):
    if m<60:   return f"{m}m ago"
    if m<1440: return f"{m//60}h ago"
    return f"{m//1440}d ago"

def _score_account(profile):
    if not profile.get("is_valid",True): return 0
    pts=0; age=profile.get("account_age_days",0)
    if age>=1825: pts+=30
    elif age>=730: pts+=22
    elif age>=365: pts+=15
    elif age>=90: pts+=8
    elif age>=30: pts+=3
    fol=max(1,profile.get("followers",1)); fng=max(1,profile.get("following",1)); r=fol/fng
    if r>=50: pts+=35
    elif r>=20: pts+=28
    elif r>=10: pts+=22
    elif r>=5: pts+=16
    elif r>=2: pts+=10
    elif r>=1: pts+=5
    if fol>=1_000_000: pts+=25
    elif fol>=100_000: pts+=18
    elif fol>=10_000: pts+=12
    elif fol>=1_000: pts+=7
    elif fol>=500: pts+=3
    if profile.get("verified"): pts+=10
    return min(100,pts)

def _score_engagement_anomaly(post):
    lk=max(1,post.get("likes",1)); sh=max(0,post.get("shares",0))
    cm=max(0,post.get("comments_count",0))
    fol=max(1,_ACCOUNT_PROFILES.get(post.get("account_id",""),{}).get("followers",1))
    s=0; slr=sh/lk
    if slr>2.0: s+=40
    elif slr>1.0: s+=22
    elif slr>0.5: s+=10
    lr=lk/fol
    if lr>1.0: s+=30
    elif lr>0.5: s+=15
    if cm/lk<0.02:s+=15
    return min(100,s)

def validate_account(account_id):
    """Step 0: Validate account — existence, public status, credibility extraction."""
    p=_ACCOUNT_PROFILES.get(account_id)
    if not p: return {"is_valid":False,"status":"not_found","reason":"Account not found or does not exist"}
    if not p.get("is_valid",True): return {"is_valid":False,"status":p["validation_status"],"reason":p.get("validation_reason","Account unavailable")}
    cred=_score_account(p)
    return {"is_valid":True,"status":"public","handle":p["handle"],"name":p["name"],"verified":p["verified"],
            "account_age_days":p["account_age_days"],"followers":p["followers"],"following":p["following"],
            "credibility_score":cred,"burst_detected":p.get("burst_detected",False),"posts_per_day":p.get("posts_per_day",0)}

def _nlp_analysis(caption, hashtags):
    """Step 2a: NLP — signal engine + clickbait + emotional manipulation detection."""
    full=caption+" "+" ".join(f"#{h}" for h in hashtags)
    lang=detect_lang(full)
    if lang not in SUPPORTED_LANGS: lang="English"
    sf,sr=score_text(full,lang); matches=matched_signals(full,lang)
    cb=sum(1 for p in [r"you won.t believe|shocking revelation",r"!!!",r"\b[A-Z]{5,}\b",r"\b(MUST (READ|WATCH|SHARE)|VIRAL|BOMBSHELL)\b"] if re.search(p,caption,re.I))
    em=sum(1 for p in [r"\b(outrage|furious|your children|wake up|they want you)\b",r"(share before|forward this|send to everyone)",r"\b(EXPOSED|ALERT|WARNING|URGENT)\b"] if re.search(p,caption,re.I))
    return {"lang":lang,"sig_fake":sf,"sig_real":sr,"matches":matches,"clickbait":cb,"emotional":em}

def _ocr_analysis(post):
    """Step 2b: OCR — extract image text and compare with caption intent."""
    if not post.get("has_media") or not post.get("ocr_text"): return {"has_ocr":False,"mismatch":False,"text":None}
    return {"has_ocr":True,"mismatch":post.get("ocr_mismatch",False),"text":post.get("ocr_text",""),
            "mismatch_reason":"Image promotes commercial product while caption frames content as free information" if post.get("ocr_mismatch") else None}

def _comment_analysis(samples):
    """Step 3: Comment sentiment, spam detection, fact-check reference detection."""
    if not samples: return {"total":0,"pos":0,"neg":0,"neu":0,"pos_pct":0,"neg_pct":0,"neu_pct":0,"factcheck_refs":0,"spam_signals":0,"samples":[]}
    t=len(samples); pos=sum(1 for c in samples if c["sentiment"]=="positive"); neg=sum(1 for c in samples if c["sentiment"]=="negative"); neu=t-pos-neg
    fc=sum(1 for c in samples if re.search(r'\b(snopes|politifact|factcheck|debunked|false|rated false|WHO|AP fact|reuters fact)\b',c["text"],re.I))
    sp=sum(1 for c in samples if re.search(r'\b(share|forward|send|viral|spread|everyone)\b',c["text"],re.I))
    return {"total":t,"pos":pos,"neg":neg,"neu":neu,"pos_pct":int(pos/t*100),"neg_pct":int(neg/t*100),"neu_pct":int(neu/t*100),"factcheck_refs":fc,"spam_signals":sp,"samples":samples[:4]}

def _authenticity_checks(post, profile, nlp):
    """Step 4: Authenticity — burst patterns, niche mismatch, engagement spikes, OCR."""
    flags=[]
    if profile.get("burst_detected"): flags.append(f"Burst posting detected ({profile.get('posts_per_day',0):.0f} posts/day — abnormal frequency)")
    niche=[n.lower() for n in profile.get("content_niche",[])]; htags=[h.lower() for h in post.get("hashtags",[])]; cap_l=post.get("caption","").lower()
    if niche and not any(any(n in h or n in cap_l for h in htags) for n in niche): flags.append("Content topic doesn't align with account's established niche")
    fol=profile.get("followers",1); lk=post.get("likes",0); avg_er=profile.get("avg_engagement_rate",0.01); per=lk/max(1,fol)
    if per>avg_er*3: flags.append(f"Engagement rate {per:.1%} is {per/max(avg_er,0.001):.1f}x above account average")
    if profile.get("account_age_days",999)<90 and post.get("shares",0)>1000: flags.append(f"New account ({profile.get('account_age_days',0)}d old) with abnormally high viral spread ({_fmt_count(post.get('shares',0))} shares)")
    if post.get("ocr_mismatch"): flags.append("Caption-to-image text inconsistency detected via OCR")
    return flags

def _compute_score(profile, nlp, eng_anom, auth_flags, comments, ocr):
    """Step 5: Composite misinformation score 0–100 with transparent weighting."""
    sf=nlp["sig_fake"]; sr=nlp["sig_real"]; ts=sf+sr+0.001; ac=_score_account(profile)
    raw=(sf/ts)*0.35+((100-ac)/100)*0.25+(eng_anom/100)*0.15+min(1.0,len(auth_flags)*0.14)*0.12+(0.15 if ocr.get("mismatch") else 0)*0.08+min(1.0,nlp.get("clickbait",0)*0.04)*0.03+min(1.0,nlp.get("emotional",0)*0.05)*0.02-min(0.15,comments.get("factcheck_refs",0)*0.05)
    if profile.get("verified") and ac>=70:           raw=min(raw,0.35)
    if sf>=10 and sr==0:                             raw=min(1.0,max(raw,0.75))
    if profile.get("account_age_days",999)<30 and profile.get("burst_detected"): raw=min(1.0,raw+0.18)
    score=max(0,min(100,int(raw*100)))
    risk="high" if score>=75 else "needs_verification" if score>=45 else "likely_reliable"
    return score,risk

def run_analysis_pipeline(post):
    """Run full 6-step misinformation analysis pipeline for one post."""
    aid=post.get("account_id",""); profile=_ACCOUNT_PROFILES.get(aid,{})
    val=validate_account(aid)
    if not val["is_valid"] or not post.get("caption"): return {"valid":False,"validation":val,"account_id":aid}
    eng=_score_engagement_anomaly(post); nlp=_nlp_analysis(post.get("caption",""),post.get("hashtags",[])); ocr=_ocr_analysis(post)
    cmts=_comment_analysis(post.get("comments_sample",[])); auth=_authenticity_checks(post,profile,nlp)
    score,risk=_compute_score(profile,nlp,eng,auth,cmts,ocr)
    _rl={"high":"High Risk","needs_verification":"Needs Verification","likely_reliable":"Likely Reliable"}
    rf=list(auth)
    if nlp["matches"]["fake_count"]>0: rf.append(f"{nlp['matches']['fake_count']} misinformation language pattern(s)")
    if eng>=40: rf.append("Unusual engagement pattern (share-to-like anomaly)")
    if ocr.get("mismatch"): rf.append("Caption vs. image text inconsistency (OCR)")
    if cmts.get("spam_signals",0)>=2: rf.append(f"{cmts['spam_signals']} spam-like comments detected")
    tr=[]
    if val.get("verified"):                     tr.append("Verified account")
    if nlp["matches"]["real_count"]>0:         tr.append(f"{nlp['matches']['real_count']} credibility signal(s)")
    if cmts.get("factcheck_refs",0)>0:         tr.append(f"{cmts['factcheck_refs']} fact-check reference(s) in comments")
    if val.get("credibility_score",0)>=70:      tr.append("High-credibility account profile")
    leads={"high":"Multiple strong misinformation indicators detected across content, account profile, and engagement signals.","needs_verification":"Mixed credibility signals found. Independent verification strongly recommended before sharing.","likely_reliable":"Content and account signals indicate high reliability. Standard verification still advisable."}
    parts=[leads[risk]]
    if rf: parts.append("Concerns: "+"; ".join(rf[:3])+".")
    if tr: parts.append("Trust factors: "+"; ".join(tr[:2])+".")
    cap_l=(post.get("caption","")+" ".join(post.get("hashtags",[]))).lower(); fc=[]
    if any(k in cap_l for k in ["vaccine","cure","medicine","covid","microchip"]): fc+=[_FACTCHECK_DB[5],_FACTCHECK_DB[0]]
    if any(k in cap_l for k in ["election","fraud","vote","stolen","ballot"]): fc+=[_FACTCHECK_DB[1],_FACTCHECK_DB[2]]
    if any(k in cap_l for k in ["breaking","secret","exposed","hidden","cover"]): fc+=[_FACTCHECK_DB[3],_FACTCHECK_DB[0]]
    if any(k in cap_l for k in ["india","tamil","bjp","modi"]): fc+=[_FACTCHECK_DB[6],_FACTCHECK_DB[7]]
    if not fc: fc=[_FACTCHECK_DB[4],_FACTCHECK_DB[0]]
    seen=set(); fcd=[]
    for item in fc:
        if item[0] not in seen: seen.add(item[0]); fcd.append(item)
    return {"valid":True,"validation":val,"account_id":aid,"score":score,"risk":risk,"risk_label":_rl[risk],"red_flags":rf,"trust_factors":tr,"justification":" ".join(parts),"nlp":nlp,"ocr":ocr,"comments":cmts,"auth_flags":auth,"eng_anom":eng,"acct_cred":val.get("credibility_score",0),"fc_links":fcd[:3]}

def _get_social_posts(platform, seed, n=5, bearer_token="", ig_user="", ig_pass=""):
    """Return up to n real posts for the given platform.

    Sources (strictly):
      Instagram → instaloader with optional login (real public IG posts)
      Twitter/X → Twitter API v2 via tweepy (real tweets, Bearer Token required)

    Every result list ends with one invalid-account sentinel (exclusion demo).
    Falls back to static demo data ONLY if the live API returns nothing at all.
    """
    invalid_id = "demo_private" if platform == "instagram" else "demo_suspended"
    _sentinel = {
        "account_id": invalid_id, "caption": None, "hashtags": [],
        "likes": 0, "comments_count": 0, "shares": 0, "post_age_minutes": 0,
        "has_media": False, "media_type": "none", "ocr_text": None,
        "ocr_mismatch": False, "comments_sample": [],
        "source_link": "", "live": False, "platform": platform,
    }

    # handle → account_id mapping for Instagram
    _ig_id_map = {
        "reuters": "reuters", "bbcnews": "bbcnews", "natgeo": "natgeo",
        "who": "who", "nypost": "nypost", "dailymail": "dailymail",
    }

    # ── Instagram: instaloader (creds required) → RSS fallback ───────────
    if platform == "instagram":
        live_posts  = []
        _has_creds  = bool(ig_user.strip() and ig_pass.strip())
        for handle in _IG_HANDLES:
            if len(live_posts) >= n:
                break
            fetched = []
            if _has_creds:
                # Only attempt instaloader when credentials are available —
                # anonymous access always triggers an SSL EOF from Instagram.
                fetched = _fetch_ig_profile(handle, ig_user=ig_user, ig_pass=ig_pass)
            if fetched:
                p = dict(fetched[0])
                p["account_id"] = _ig_id_map.get(handle, handle)
                p["platform"]   = "instagram"
                p["source"]     = "ig_api"
                live_posts.append(p)
            else:
                # RSS fallback — real-time headlines from the same organisation
                rss = _fetch_rss_account(handle)
                for rp in rss[:1]:
                    p = dict(rp)
                    p["account_id"] = _ig_id_map.get(handle, handle)
                    p["platform"]   = "instagram"
                    live_posts.append(p)
                    break
        if live_posts:
            live_posts.append(_sentinel)
            return live_posts

    # ── Twitter/X: Bearer API v2 → RSS fallback ───────────────────────────
    if platform == "twitter":
        tw_api_used = False
        live = []
        if bearer_token.strip() and _TWEEPY_OK:
            live = _fetch_tw_api(bearer_token)
            if live:
                tw_api_used = True
                for p in live:
                    p["platform"] = "twitter"
                    p.setdefault("source", "tw_api")

        if not live:
            # RSS fallback — deduplicated account list
            seen_acc = set()
            for acc_id in list(_TW_HANDLE_MAP.values()):
                if acc_id in seen_acc or len(live) >= n:
                    continue
                seen_acc.add(acc_id)
                rss = _fetch_rss_account(acc_id)
                for rp in rss[:1]:
                    p = dict(rp)
                    p["platform"] = "twitter"
                    live.append(p)
                    break

        if live:
            live = live[:n]
            live.append(_sentinel)
            return live
        # Nothing at all
        _sentinel["_tw_no_token"] = not bearer_token.strip()
        return [_sentinel]

    # ── Static fallback (only if live fetch returned nothing) ─────────────
    pool = _IG_POST_DATA if platform == "instagram" else _TW_POST_DATA
    rng  = random.Random(seed + (0 if platform == "instagram" else 9999))
    posts = rng.sample(pool, min(n, len(pool)))
    result = []
    for p in posts:
        post = dict(p); post["platform"] = platform; post["live"] = False
        if post.get("caption"):
            post["post_age_minutes"] = rng.randint(5, 360)
        result.append(post)
    result.append(_sentinel)
    return result

_RISK_CSS={"high":("rl-high","prb-critical","sg-critical","#EF4444"),"needs_verification":("rl-needs","prb-high","sg-high","#F59E0B"),"likely_reliable":("rl-reliable","prb-low","sg-low","#10B981")}
_RISK_LABEL={"high":"High Risk","needs_verification":"Needs Verification","likely_reliable":"Likely Reliable"}
_SENT_EMOJI={"positive":"😊","negative":"😠","neutral":"😐"}

def _render_invalid_card(post):
    p=_ACCOUNT_PROFILES.get(post.get("account_id",""),{}); st=p.get("validation_status","unknown")
    icons={"private":"🔒","suspended":"🚫","not_found":"❓","restricted":"⚠️"}
    bc_map={"private":"ab-private","suspended":"ab-suspended","not_found":"ab-notfound","restricted":"ab-restricted"}
    bl_map={"private":"Private","suspended":"Suspended","not_found":"Not Found","restricted":"Restricted"}
    return f"""<div class="invalid-card">
  <div class="invalid-icon">{icons.get(st,'❓')}</div>
  <div style="flex:1">
    <div class="invalid-handle">{p.get('name','Unknown')} <span style="color:var(--text-dd)">{p.get('handle','')}</span></div>
    <div style="margin:.2rem 0"><span class="acct-badge {bc_map.get(st,'ab-notfound')}">{bl_map.get(st,'Unavailable')}</span></div>
    <div class="invalid-reason">⚠ {p.get('validation_reason','Account unavailable')}. Post excluded from analysis.</div>
    <div class="invalid-reason" style="font-size:.6rem;color:var(--text-dd);margin-top:.1rem">Disclaimer: Automated system — excluded per privacy/availability policy.</div>
  </div>
</div>"""

def render_post_card(post, analysis, show_details):
    """Build full HTML post card with 6-step analysis overlay."""
    if not analysis.get("valid"): return _render_invalid_card(post)
    val=analysis["validation"]; score=analysis["score"]; risk=analysis["risk"]
    rl_cls,prb_cls,sg_cls,color=_RISK_CSS.get(risk,_RISK_CSS["needs_verification"]); rlbl=_RISK_LABEL.get(risk,"Unknown")
    blink={"high":'<span class="blink-red"></span>',"needs_verification":'<span class="blink-amb"></span>'}.get(risk,"")
    profile=_ACCOUNT_PROFILES.get(post.get("account_id",""),{})
    fol=val.get("followers",0); fng=max(1,val.get("following",1)); av=val.get("name","?")[0].upper()
    vbadge=' <span style="color:#60A5FA;font-size:.75rem">✓</span>' if val.get("verified") else ""
    burst='<span class="burst-badge">⚡ Burst posting</span>' if val.get("burst_detected") else ""
    acred=analysis.get("acct_cred",0)
    ab_cls="ab-verified" if val.get("verified") else ("ab-public" if acred>=60 else "ab-low")
    ab_lbl="Verified ✓" if val.get("verified") else ("Public ✓" if acred>=60 else "Low Credibility")
    is_live = post.get("live", False)
    live_badge = '<span style="background:#EF4444;color:#fff;font-size:.5rem;font-weight:700;padding:.08rem .35rem;border-radius:99px;letter-spacing:.07em;margin-left:.3rem">🔴 LIVE</span>' if is_live else '<span style="background:var(--bg-l);color:var(--text-dd);font-size:.5rem;font-weight:600;padding:.08rem .35rem;border-radius:99px;letter-spacing:.07em;margin-left:.3rem">DEMO</span>'
    cap=post.get("caption",""); cap_d=cap[:240]+("…" if len(cap)>240 else "")
    tags=" ".join(f"#{h}" for h in post.get("hashtags",[])[:4])
    media=""
    if post.get("has_media") and post.get("media_type","none")!="none":
        icon="▶  VIDEO" if post.get("media_type")=="video" else "🖼  IMAGE"
        media=f'<div class="pcard-media">{icon} · simulation mode</div>'
    src_link = post.get("source_link","")
    _platform = post.get("platform","")
    if src_link:
        if _platform == "instagram":
            _src_lbl = "📷 View on Instagram"
            _src_col = "#E1306C"
        elif _platform == "twitter":
            _src_lbl = "𝕏 View on Twitter / X"
            _src_col = "#1D9BF0"
        else:
            _src_lbl = "↗ Read article"
            _src_col = "var(--blue-l)"
        read_btn = f'<a href="{src_link}" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:.5rem;font-size:.62rem;font-weight:600;color:{_src_col};text-decoration:none;border:1px solid {_src_col}44;border-radius:6px;padding:.18rem .55rem;background:{_src_col}11">{_src_lbl}</a>'
    else:
        read_btn = ""
    html=f"""<div class="pcard">
  <div class="pcard-risk-bar {prb_cls}"></div>
  <div class="pcard-top">
    <div class="pcard-av">{av}</div>
    <div class="pcard-info">
      <div class="pcard-author">{val.get('name','')}{vbadge} {burst}{live_badge}</div>
      <div class="pcard-meta">{val.get('handle','')} · {_acct_age_label(val.get('account_age_days',0))} · {_fmt_count(fol)} followers · {fol/fng:.1f}x ratio</div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:.2rem;flex-shrink:0">
      <span class="pcard-age">{_post_age_label(post.get('post_age_minutes',0))}</span>
      <span class="acct-badge {ab_cls}">{ab_lbl}</span>
    </div>
  </div>
  <div class="pcard-body"><div class="pcard-cap">{cap_d}</div><div class="pcard-tags">{tags}</div>{read_btn}</div>
  {media}
  <div class="pcard-eng">
    <span class="eng-item">♥ <span class="eng-val">{_fmt_count(post.get('likes',0))}</span></span>
    <span class="eng-item">💬 <span class="eng-val">{_fmt_count(post.get('comments_count',0))}</span></span>
    <span class="eng-item">↻ <span class="eng-val">{_fmt_count(post.get('shares',0))}</span></span>
  </div>
  <div class="score-gauge">
    <div class="sg-num {sg_cls}">{score}</div>
    <div class="sg-track"><div class="sg-fill" style="width:{score}%;background:{color}"></div></div>
    <div style="display:flex;align-items:center;gap:.3rem">{blink}<span class="risk-badge {rl_cls}">{rlbl}</span></div>
  </div>"""
    if show_details:
        ac_col="#10B981" if acred>=65 else "#F59E0B" if acred>=35 else "#EF4444"
        eng_a=analysis.get("eng_anom",0); ea_col="#EF4444" if eng_a>=60 else "#F59E0B" if eng_a>=30 else "#10B981"
        cmts=analysis.get("comments",{}); pp=cmts.get("pos_pct",0); np_=cmts.get("neg_pct",0); nup=cmts.get("neu_pct",0)
        sent_bar=f"""<div class="ablock-lbl" style="margin-top:.35rem">Sentiment <span style="color:var(--text-dd);font-weight:400">· {cmts.get('total',0)} sampled</span></div>
<div class="sent-bar"><div class="sent-pos" style="width:{pp}%"></div><div class="sent-neg" style="width:{np_}%"></div><div class="sent-neu" style="width:{nup}%"></div></div>
<div class="sent-legend"><span class="sl-pos">▮ {pp}%</span><span class="sl-neg">▮ {np_}%</span><span class="sl-neu">▮ {nup}%</span>{"<span style='color:var(--red-m);margin-left:.3rem'>· "+str(cmts.get('factcheck_refs',0))+" fc ref(s)</span>" if cmts.get('factcheck_refs',0)>0 else ""}</div>"""
        _SENT_CLS_MAP = {"positive":"ci-pos","negative":"ci-neg","neutral":"ci-neu"}
        cmt_items="".join(f'<div class="comment-item {_SENT_CLS_MAP.get(c["sentiment"],"ci-neu")}">{_SENT_EMOJI.get(c["sentiment"],"")} {c["text"]}</div>' for c in cmts.get("samples",[]))
        ocr=analysis.get("ocr",{}); ocr_html=""
        if ocr.get("has_ocr"):
            mc="ocr-mismatch" if ocr.get("mismatch") else ""; mw=f'<div style="font-size:.64rem;color:var(--amber-m);margin-top:.12rem">⚠ MISMATCH: {ocr.get("mismatch_reason","Caption and image text conflict detected.")}</div>' if ocr.get("mismatch") else '<div style="font-size:.62rem;color:var(--green-l);margin-top:.1rem">✓ Image text consistent with caption</div>'
            ocr_html=f'<div class="ocr-block {mc}"><div class="ocr-lbl">OCR extracted text</div><div class="ocr-text-val">"{ocr.get("text","")}"</div>{mw}</div>'
        rf_html="".join(f'<span class="aflag af-fake">⚠ {f}</span>' for f in analysis.get("red_flags",[]))
        tr_html="".join(f'<span class="aflag af-real">✓ {t}</span>' for t in analysis.get("trust_factors",[]))
        fc_html="".join(f'<a class="fc-link" href="{u}" target="_blank" rel="noopener noreferrer">🔍 {n}</a>' for n,u in analysis.get("fc_links",[]))
        html+=f"""<div class="ablock">
  <div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.3rem">
    <span class="ablock-lbl" style="margin:0">Analysis</span>
    <span style="font-family:'JetBrains Mono',monospace;font-size:.44rem;color:var(--text-dd)">·</span>
    <span class="risk-badge {rl_cls}" style="font-size:.42rem;padding:.06rem .38rem">{score}/100 · {rlbl}</span>
  </div>
  <div class="ablock-just">{analysis['justification']}</div>
  <div style="display:flex;gap:.5rem;margin:.28rem 0">
    <div style="flex:1"><div class="ablock-lbl">Credibility</div><div style="display:flex;align-items:center;gap:.35rem"><div style="flex:1;height:3px;background:var(--bg-l);border-radius:99px;overflow:hidden"><div style="width:{acred}%;height:100%;border-radius:99px;background:{ac_col}"></div></div><span style="font-family:'JetBrains Mono',monospace;font-size:.44rem;color:var(--text-m);font-weight:700">{acred}</span></div></div>
    <div style="flex:1"><div class="ablock-lbl">Eng. Anomaly</div><div style="display:flex;align-items:center;gap:.35rem"><div style="flex:1;height:3px;background:var(--bg-l);border-radius:99px;overflow:hidden"><div style="width:{eng_a}%;height:100%;border-radius:99px;background:{ea_col}"></div></div><span style="font-family:'JetBrains Mono',monospace;font-size:.44rem;color:var(--text-m);font-weight:700">{eng_a}</span></div></div>
  </div>
  {ocr_html}
  {sent_bar}
  <div style="margin-top:.28rem">{cmt_items}</div>
  <div class="ablock-flags" style="margin-top:.35rem">{rf_html}{tr_html}</div>
  {('<div class="ablock-lbl" style="margin-top:.4rem">Fact-check</div><div style="margin-top:.14rem">' + fc_html + '</div>') if fc_html else ''}
</div>"""
    html+="</div>"
    return html

# History log for social monitor
_social_history = []  # [{ts, platform, handle, score, risk_label, cap_preview}]

# ─── SESSION ───────────────────────────────────────────────────────────────
ensure_session_state()

# ── NAV ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="nav">
  <div class="nav-brand">
    <div class="nav-icon">C</div>
    <span class="nav-name">Credi<span>AI</span></span>
  </div>
  <div class="nav-badge"><span class="live-dot"></span>Live Intelligence</div>
  <div class="nav-pills">
    <span class="nav-pill">""" + SUPPORTED_LANGS_BADGES + """</span>
    <span class="nav-pill">Headlines &amp; Articles</span>
  </div>
</div>""", unsafe_allow_html=True)

# ── HERO ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-glow1"></div>
  <div class="hero-glow2"></div>
  <div class="hero-inner">
    <div class="hero-tag">🛡 News Credibility Intelligence</div>
    <h1 class="hero-h1">One paste.<br><span class="accent">Instant truth.</span></h1>
    <p class="hero-sub">Analyze news in 6 languages. Auto-detect or choose: English, Tamil, Hindi, Telugu, Malayalam, Kannada. Hybrid AI + signal scoring.</p>
    <div class="hero-pills">
      <div class="hpill"><span class="pip pip-en"></span>English</div>
      <div class="hpill"><span class="pip pip-ta"></span>தமிழ் · हिंदी · తెలుగు · മലയാളം · ಕನ್ನಡ</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:.5rem;letter-spacing:.18em;text-transform:uppercase;color:var(--text-dd);margin-bottom:.45rem;">⚙ Language</div>', unsafe_allow_html=True)
    language_mode = st.radio("lm", ["Auto-detect"] + SUPPORTED_LANGS, label_visibility="collapsed")
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:.5rem;letter-spacing:.18em;text-transform:uppercase;color:var(--text-dd);margin-bottom:.45rem;">📌 Panels</div>', unsafe_allow_html=True)
    show_debug = st.toggle("Show explanation panel", value=True)
    keep_history = st.toggle("Save to history", value=True)
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:.5rem;letter-spacing:.18em;text-transform:uppercase;color:var(--text-dd);margin-bottom:.45rem;">📊 Metrics</div>', unsafe_allow_html=True)
    st.caption("Open the **Dashboard** tab to view accuracy & F1 for all models (pre-trained and local).")
    st.markdown("<hr/>", unsafe_allow_html=True)
    # ── Twitter/X Live Feed ──────────────────────────────────────────────
    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:.5rem;letter-spacing:.18em;text-transform:uppercase;color:var(--text-dd);margin-bottom:.45rem;">𝕏 Twitter / X</div>', unsafe_allow_html=True)
    _secret_bearer = _urlparse.unquote(_get_secret("TW_BEARER", ""))
    tw_bearer = st.text_input(
        "Bearer Token",
        value=_secret_bearer,
        type="password",
        placeholder="Paste Twitter/X Bearer Token…",
        help="Auto-loaded from .streamlit/secrets.toml. Get yours at developer.twitter.com → Your App → Keys & Tokens.",
        key="tw_bearer",
    )
    if tw_bearer.strip():
        st.caption("✅ Bearer Token active — real live tweets.")
    else:
        st.caption("⚠️ No token — Twitter feed unavailable.")

    # ── Instagram Live Feed ──────────────────────────────────────────────
    st.markdown("<hr style='border-color:#1e3a5f;margin:.6rem 0'/>", unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:.5rem;letter-spacing:.18em;text-transform:uppercase;color:var(--text-dd);margin-bottom:.45rem;">📷 Instagram</div>', unsafe_allow_html=True)
    st.caption("Instagram blocks anonymous API access. Log in with any Instagram account to enable real post fetching.")
    _secret_ig_user = _get_secret("IG_USERNAME", "")
    _secret_ig_pass = _get_secret("IG_PASSWORD", "")
    ig_username = st.text_input(
        "Instagram Username",
        value=_secret_ig_user,
        placeholder="your_instagram_username",
        help="Used only for authenticated instaloader requests. Stored locally in secrets.toml — never sent anywhere else.",
        key="ig_username",
    )
    ig_password = st.text_input(
        "Instagram Password",
        value=_secret_ig_pass,
        type="password",
        placeholder="your_instagram_password",
        help="Used only for authenticated instaloader requests. Stored locally in secrets.toml.",
        key="ig_password",
    )
    if ig_username.strip() and ig_password.strip():
        st.caption("✅ Instagram credentials set — real posts will be fetched.")
    else:
        st.caption("⚠️ No credentials — Instagram feed unavailable.")

# ── BODY ───────────────────────────────────────────────────────────────────
st.markdown('<div class="body">', unsafe_allow_html=True)

tab_verify, tab_social, tab_dash, tab_hist = st.tabs(["🛡 Verify", "📱 Social Monitor", "📊 Dashboard", "🧾 History"])

with tab_verify:
    c1, c2, c3 = st.columns([1, 1, 1], gap="large")

    # ═══ INPUT ═════════════════════════════════════════════════════════════════
    with c1:
        st.markdown('<div class="panel"><div class="ph"><div class="ph-bar ph-blue"></div><span class="ph-lbl">Input</span></div><div class="pb">', unsafe_allow_html=True)
        injected  = st.session_state.pop("inject", "")
        news_text = st.text_area("t", value=injected, height=295,
            placeholder="Paste any headline or full article here…\nEnglish or Tamil, both supported.",
            key="inp", label_visibility="collapsed")
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        run = st.button("🛡  Analyse Now", type="primary", use_container_width=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    # ═══ RESULT ════════════════════════════════════════════════════════════════
    with c2:
        st.markdown('<div class="panel"><div class="ph"><div class="ph-bar ph-cyan"></div><span class="ph-lbl">Verification Result</span></div><div class="pb">', unsafe_allow_html=True)

        if not run:
            st.markdown('<div class="idle"><span class="idle-icon">🛡</span><div class="idle-text">Awaiting analysis</div></div>', unsafe_allow_html=True)
        elif not news_text or not news_text.strip():
            st.markdown('<div class="vc vc-warn"><div class="vc-label">No input</div><div class="vc-row"><div class="vc-verdict">Nothing entered</div></div><div class="vc-body">Paste a headline or article on the left.</div></div>', unsafe_allow_html=True)
        else:
            al = detect_lang(news_text)
            if language_mode != "Auto-detect" and al != language_mode:
                st.markdown(f'<div class="vc vc-warn"><div class="vc-label">Language mismatch</div><div class="vc-row"><div class="vc-verdict">Wrong language</div></div><div class="vc-body">Text is in <b>{al}</b> but mode is <b>{language_mode}</b>.<br>Switch sidebar or use Auto-detect.</div></div>', unsafe_allow_html=True)
            else:
                with st.spinner(""):
                    if al == "English":
                        fs, rs, mode, meta = predict_en(news_text)
                        matches = matched_signals(news_text, "English")
                    elif al == "Tamil":
                        fs, rs, mode, meta = predict_ta(news_text)
                        matches = matched_signals(news_text, "Tamil")
                    else:
                        fs, rs, mode, meta = predict_indic(news_text, al)
                        matches = matched_signals(news_text, al)

                    # Normalise so fake + real always = 100%
                    _t  = fs + rs
                    fs  = fs / _t if _t > 0 else 0.5
                    rs  = rs / _t if _t > 0 else 0.5
                    is_fake = fs > rs
                    conf    = max(fs, rs) * 100
                    st_d    = get_stats(news_text)

                    if keep_history:
                        st.session_state.history.insert(0, {
                            "ts": utc_now_iso(),
                            "preview": safe_preview(news_text),
                            "lang": al,
                            "mode": mode,
                            "verdict": "FAKE" if is_fake else "REAL",
                            "confidence": float(conf),
                            "fake_pct": float(fs * 100.0),
                            "real_pct": float(rs * 100.0),
                            "model": meta.get("model"),
                            "fallback": bool(meta.get("fallback")),
                            "fallback_reason": meta.get("fallback_reason"),
                            "signal_fake_score": float(meta.get("sig_fake", 0.0)),
                            "signal_real_score": float(meta.get("sig_real", 0.0)),
                            "signal_fake_matches": int(matches.get("fake_count", 0)),
                            "signal_real_matches": int(matches.get("real_count", 0)),
                        })

                mlb = "📰 Headline" if mode == "headline" else "📄 Article"
                mt  = "t-blue" if mode == "headline" else "t-cyan"
                st.markdown(f'<span class="tag {mt}"><span class="tdot"></span>{mlb} · {st_d["w"]} words</span><span class="tag t-green"><span class="tdot"></span>{al}</span>', unsafe_allow_html=True)

                if meta.get("fallback"):
                    st.markdown(f'<span class="tag t-blue"><span class="tdot"></span>Fallback · Signal-only</span>', unsafe_allow_html=True)
                else:
                    used = meta.get("model") or "model"
                    st.markdown(f'<span class="tag t-cyan"><span class="tdot"></span>Model · {used}</span>', unsafe_allow_html=True)

                if is_fake:
                    st.markdown(f'<div class="vc vc-fake"><div class="vc-label">🛡 Analysis complete</div><div class="vc-row"><div class="vc-verdict">Likely Fake</div><div class="vc-conf">{conf:.1f}% confidence</div></div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="vc vc-real"><div class="vc-label">🛡 Analysis complete</div><div class="vc-row"><div class="vc-verdict">Likely Real</div><div class="vc-conf">{conf:.1f}% confidence</div></div></div>', unsafe_allow_html=True)

                if meta.get("fallback_reason"):
                    st.caption(meta["fallback_reason"])

                st.markdown('<div class="slbl">Score breakdown</div>', unsafe_allow_html=True)
                st.markdown(f"""<div>
                  <div class="brow"><div class="blbl">Fake</div>
                    <div class="btrack"><div class="bf-fake" style="width:{fs*100:.1f}%"></div></div>
                    <div class="bpct">{fs*100:.1f}%</div></div>
                  <div class="brow"><div class="blbl">Real</div>
                    <div class="btrack"><div class="bf-real" style="width:{rs*100:.1f}%"></div></div>
                    <div class="bpct">{rs*100:.1f}%</div></div>
                </div>""", unsafe_allow_html=True)

                st.markdown('<div class="slbl">Signal indicators</div>', unsafe_allow_html=True)
                nc="ok" if st_d["n"] else "bad"; qc="ok" if st_d["q"] else "bad"
                cc="bad" if st_d["c"]>4 else "ok"; ec="bad" if st_d["e"]>2 else "ok"
                st.markdown(f"""<div class="chips">
                  <div class="chip"><span class="cn">{st_d['w']}</span><span class="ct">Words</span></div>
                  <div class="chip"><span class="cn {nc}">{'✓' if st_d['n'] else '✗'}</span><span class="ct">Numbers</span></div>
                  <div class="chip"><span class="cn {qc}">{'✓' if st_d['q'] else '✗'}</span><span class="ct">Quotes</span></div>
                  <div class="chip"><span class="cn {ec}">{st_d['e']}</span><span class="ct">Excl.</span></div>
                  <div class="chip"><span class="cn">{st_d['qm']}</span><span class="ct">Questions</span></div>
                  <div class="chip"><span class="cn {cc}">{st_d['c']}</span><span class="ct">CAPS</span></div>
                </div>""", unsafe_allow_html=True)

        st.markdown('</div></div>', unsafe_allow_html=True)

    # ═══ NEWS ══════════════════════════════════════════════════════════════════
    with c3:
        arts, rss_errs = fetch_news(st.session_state.seed, n=6)
        st.markdown('<div class="panel"><div class="nh"><div class="nh-lbl"><span class="rdot"></span>Live Headlines</div></div><div class="nbody">', unsafe_allow_html=True)
        if not arts:
            st.markdown('<div style="font-size:.7rem;color:var(--text-dd);text-align:center;padding:1.2rem;">No headlines available</div>', unsafe_allow_html=True)
        else:
            for a in arts:
                bc = "c-ta" if a["cat"]=="TA" else "c-en"
                bl = "தமிழ்" if a["cat"]=="TA" else "EN"
                st.markdown(f"""<a class="nc" href="{a['link']}" target="_blank" rel="noopener noreferrer">
                  <div class="nc-r1">
                    <img class="nc-ico" src="{a['fav']}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';" alt="">
                    <span class="nc-fb" style="display:none">{a['src'][:2]}</span>
                    <span class="nc-src">{a['src']}</span>
                    <span class="nc-cat {bc}">{bl}</span>
                  </div>
                  <div class="nc-t">{a['time']}</div>
                  <p class="nc-hl">{a['title']}</p>
                  <div class="nc-cta">↗ Open and paste to verify</div>
                </a>""", unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
        if rss_errs:
            with st.expander(f"RSS status ({len(rss_errs)} source issues)", expanded=False):
                st.write("Some sources failed to load this minute (network or RSS format). This is expected occasionally; refresh to retry.")
                st.json(rss_errs)
        if st.button("↺ Refresh", use_container_width=True):
            st.session_state.seed = int(time.time())
            st.cache_data.clear(); st.rerun()

with tab_social:
    # ── Session state ──────────────────────────────────────────────────────
    if "social_seed"         not in st.session_state: st.session_state.social_seed         = int(time.time())
    if "social_last_refresh" not in st.session_state: st.session_state.social_last_refresh = time.time()
    if "social_history"      not in st.session_state: st.session_state.social_history      = []

    _tw_bearer    = _urlparse.unquote(st.session_state.get("tw_bearer", ""))
    _ig_user      = st.session_state.get("ig_username", "")
    _ig_pass      = st.session_state.get("ig_password", "")
    _has_tw_token = _TWEEPY_OK and bool(_tw_bearer.strip())
    _has_ig_creds = _IL_OK and bool(_ig_user.strip()) and bool(_ig_pass.strip())
    _has_ig_api   = _IL_OK

    # ── compact status pill row ────────────────────────────────────────────
    _ig_dot = "🔴" if _has_ig_creds else "📰"
    _tw_dot = "🔴" if _has_tw_token else "📰"
    st.markdown(
        f'<div style="display:flex;gap:.7rem;align-items:center;'
        f'margin-bottom:.6rem;padding:.3rem .7rem;background:#080f1c;'
        f'border:1px solid #1a2f4a;border-radius:7px">'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.44rem;'
        f'letter-spacing:.18em;color:#3a6a9a;text-transform:uppercase">SOURCES</span>'
        f'<span style="width:1px;height:.8rem;background:#1a2f4a;flex-shrink:0"></span>'
        f'<span style="font-size:.58rem;color:#a0b8d0;display:flex;align-items:center;gap:.3rem">'
        f'{_ig_dot} <strong style="color:#e2e8f0;font-weight:600">Instagram</strong>'
        f'<span style="color:#3a5a7a;font-size:.5rem">{"· auth" if _has_ig_creds else "· RSS"}</span></span>'
        f'<span style="color:#1a2f4a;font-size:.6rem">·</span>'
        f'<span style="font-size:.58rem;color:#a0b8d0;display:flex;align-items:center;gap:.3rem">'
        f'{_tw_dot} <strong style="color:#e2e8f0;font-weight:600">Twitter / X</strong>'
        f'<span style="color:#3a5a7a;font-size:.5rem">{"· API v2" if _has_tw_token else "· RSS"}</span></span>'
        f'</div>',
        unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 2 · TRENDING TOPICS BAR
    # ══════════════════════════════════════════════════════════════════════════
    trending_html = "".join(f'<span class="trtopic">{t}</span>' for t in _TRENDING_FLAGS)
    st.markdown(
        f'<div class="trending-bar"><span class="tb-lbl">🔥 TRENDING MISINFO TOPICS</span>{trending_html}</div>',
        unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 3 · CONTROL BAR
    # ══════════════════════════════════════════════════════════════════════════
    secs_ago  = int(time.time() - st.session_state.social_last_refresh)
    _last_str = (f"{secs_ago}s ago" if secs_ago < 60 else f"{secs_ago//60}m {secs_ago%60}s ago")
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:.28rem .6rem;margin-bottom:.4rem">'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.43rem;'
        f'color:var(--text-dd);letter-spacing:.1em">⏱ UPDATED <span style="color:var(--cyan-l)">{_last_str}</span></span>'
        f'</div>',
        unsafe_allow_html=True)
    st.markdown('<div class="ctrl-section-top"></div>', unsafe_allow_html=True)
    cc1, cc2, cc3, cc4 = st.columns([1.6, 1, 1.4, .9], gap="medium")
    with cc1:
        n_posts = st.select_slider("Posts per feed", options=[3, 4, 5, 6], value=5, key="social_n")
    with cc2:
        show_det = st.toggle("Analysis details", value=True, key="social_det")
    with cc3:
        interval_opt = st.selectbox("Auto-refresh", ["Manual", "30s", "1 min", "5 min"], key="social_interval")
    with cc4:
        st.markdown("<div style='height:1.55rem'></div>", unsafe_allow_html=True)
        if st.button("↺  Refresh", key="social_ref"):
            st.cache_data.clear()
            st.session_state.social_seed = int(time.time())
            st.session_state.social_last_refresh = time.time()
            st.rerun()
    st.markdown('<div class="ctrl-section-bottom"></div>', unsafe_allow_html=True)

    _imap  = {"30s": 30, "1 min": 60, "5 min": 300, "Manual": 0}
    _isecs = _imap.get(interval_opt, 0)
    if _isecs > 0:
        _elapsed = time.time() - st.session_state.social_last_refresh
        if _elapsed >= _isecs:
            st.cache_data.clear()
            st.session_state.social_seed = int(time.time())
            st.session_state.social_last_refresh = time.time()
            st.rerun()
        else:
            _rem = int(_isecs - _elapsed)
            st.markdown(
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.46rem;'
                f'color:var(--text-dd);margin-bottom:.4rem">⏱ Next refresh in {_rem}s</div>',
                unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 4 · SIDE-BY-SIDE LIVE FEEDS
    # ══════════════════════════════════════════════════════════════════════════
    col_ig, col_tw = st.columns(2, gap="medium")

    # ── 4a · INSTAGRAM (instaloader → real public posts) ──────────────────
    with col_ig:
        with st.spinner("Fetching Instagram posts…"):
            ig_posts = _get_social_posts("instagram", st.session_state.social_seed, n_posts, _tw_bearer, ig_user=_ig_user, ig_pass=_ig_pass)
        ig_analyses = [run_analysis_pipeline(p) for p in ig_posts]
        ig_valid    = [(p, a) for p, a in zip(ig_posts, ig_analyses) if a.get("valid", True)]
        ig_invalid  = [(p, a) for p, a in zip(ig_posts, ig_analyses) if not a.get("valid", True)]
        hr_ig       = sum(1 for _, a in ig_valid if a.get("risk") == "high")
        avg_ig      = (sum(a["score"] for _, a in ig_valid) // max(1, len(ig_valid))) if ig_valid else 0

        for p, a in ig_valid:
            st.session_state.social_history = ([{
                "ts": datetime.now().strftime("%H:%M:%S"),
                "platform": "📷 Instagram",
                "handle":   a.get("handle", "?"),
                "score":    a["score"],
                "risk_label": _RISK_LABEL.get(a.get("risk", ""), "Unknown"),
                "cap_preview": (p.get("caption") or "")[:70],
            }] + st.session_state.social_history)[:50]

        _ig_api_n = sum(1 for p, _ in ig_valid if p.get("source") == "ig_api")
        _ig_rss_n = sum(1 for p, _ in ig_valid if p.get("source") == "rss")
        if _ig_api_n > 0:
            _ig_src_lbl = "LIVE · API"
            _ig_src_col = "#e1306c"
            _ig_src_dot = "🔴"
        elif _ig_rss_n > 0:
            _ig_src_lbl = "LIVE · RSS"
            _ig_src_col = "#f59e0b"
            _ig_src_dot = "📰"
        else:
            _ig_src_lbl = "DEMO"
            _ig_src_col = "#5a7a9a"
            _ig_src_dot = "⚪"
        _hr_ig_col = "#ef4444" if hr_ig > 0 else "#10b981"
        st.markdown(
            f'<div class="feed-card-hdr feed-ig">'
            f'<span class="feed-icon feed-icon-ig">📷</span>'
            f'<div class="feed-hdr-info">'
            f'<span class="feed-hdr-name">Instagram</span>'
            f'<span class="feed-hdr-src" style="color:{_ig_src_col}">{_ig_src_dot} {_ig_src_lbl}</span>'
            f'</div>'
            f'<div class="feed-hdr-stats">'
            f'<span class="feed-stat">{len(ig_valid)} posts</span>'
            f'<span class="feed-stat" style="color:{_hr_ig_col}">⚠ {hr_ig} risk</span>'
            f'<span class="feed-stat">avg {avg_ig}</span>'
            f'</div></div>',
            unsafe_allow_html=True)

        for post, analysis in zip(ig_posts, ig_analyses):
            st.markdown(render_post_card(post, analysis, show_det), unsafe_allow_html=True)

    # ── 4b · TWITTER / X (tweepy → real tweets) ───────────────────────────
    with col_tw:
        with st.spinner("Fetching real tweets from Twitter/X API v2…"):
            tw_posts = _get_social_posts("twitter", st.session_state.social_seed, n_posts, _tw_bearer)
        tw_analyses = [run_analysis_pipeline(p) for p in tw_posts]
        tw_valid    = [(p, a) for p, a in zip(tw_posts, tw_analyses) if a.get("valid", True)]
        tw_invalid  = [(p, a) for p, a in zip(tw_posts, tw_analyses) if not a.get("valid", True)]
        hr_tw       = sum(1 for _, a in tw_valid if a.get("risk") == "high")
        avg_tw      = (sum(a["score"] for _, a in tw_valid) // max(1, len(tw_valid))) if tw_valid else 0
        for p, a in tw_valid:
            st.session_state.social_history = ([{
                "ts": datetime.now().strftime("%H:%M:%S"),
                "platform": "𝕏 Twitter/X",
                "handle":   a.get("handle", "?"),
                "score":    a["score"],
                "risk_label": _RISK_LABEL.get(a.get("risk", ""), "Unknown"),
                "cap_preview": (p.get("caption") or "")[:70],
            }] + st.session_state.social_history)[:50]

        _tw_api_n = sum(1 for p, _ in tw_valid if p.get("source") == "tw_api")
        _tw_rss_n = sum(1 for p, _ in tw_valid if p.get("source") == "rss")
        if _tw_api_n > 0:
            _tw_src_lbl = "LIVE · API v2"
            _tw_src_col = "#1d9bf0"
            _tw_src_dot = "🔴"
        elif _tw_rss_n > 0:
            _tw_src_lbl = "LIVE · RSS"
            _tw_src_col = "#f59e0b"
            _tw_src_dot = "📰"
        elif not _has_tw_token:
            _tw_src_lbl = "No Token"
            _tw_src_col = "#EAB308"
            _tw_src_dot = "⚠"
        else:
            _tw_src_lbl = "DEMO"
            _tw_src_col = "#5a7a9a"
            _tw_src_dot = "⚪"
        _hr_tw_col = "#ef4444" if hr_tw > 0 else "#10b981"
        st.markdown(
            f'<div class="feed-card-hdr feed-tw">'
            f'<span class="feed-icon feed-icon-tw">𝕏</span>'
            f'<div class="feed-hdr-info">'
            f'<span class="feed-hdr-name">Twitter / X</span>'
            f'<span class="feed-hdr-src" style="color:{_tw_src_col}">{_tw_src_dot} {_tw_src_lbl}</span>'
            f'</div>'
            f'<div class="feed-hdr-stats">'
            f'<span class="feed-stat">{len(tw_valid)} posts</span>'
            f'<span class="feed-stat" style="color:{_hr_tw_col}">⚠ {hr_tw} risk</span>'
            f'<span class="feed-stat">avg {avg_tw}</span>'
            f'</div></div>',
            unsafe_allow_html=True)

        for post, analysis in zip(tw_posts, tw_analyses):
            st.markdown(render_post_card(post, analysis, show_det), unsafe_allow_html=True)

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

with tab_dash:
    st.markdown('<div class="panel"><div class="ph"><div class="ph-bar ph-green"></div><span class="ph-lbl">Model Metrics &amp; Visuals</span></div><div class="pb">', unsafe_allow_html=True)

    # ── Session Command Center ─────────────────────────────────────────────
    st.markdown("""
    <div style="margin-bottom:1.2rem">
      <div style="font-size:1.15rem;font-weight:800;color:var(--text);margin-bottom:.2rem">⚡ Session Command Center</div>
      <div style="font-size:.78rem;color:var(--text-dd)">Live KPIs, charts, and a drill-down from your recent predictions.</div>
    </div>
    """, unsafe_allow_html=True)

    _dash_hist = (st.session_state.get("history", []) or []) if hasattr(st, "session_state") else []
    if not _dash_hist:
        st.info("Run an analysis in the `Verify` tab to populate the dashboard.")
    else:
        _total = len(_dash_hist)
        _fake_n = sum(1 for h in _dash_hist if (h.get("verdict") == "FAKE"))
        _real_n = sum(1 for h in _dash_hist if (h.get("verdict") == "REAL"))
        _avg_conf = sum(float(h.get("confidence", 0.0)) for h in _dash_hist) / max(1, _total)
        _fb_n = sum(1 for h in _dash_hist if bool(h.get("fallback")))
        _fb_rate = _fb_n / max(1, _total)

        c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4, gap="large")
        c_kpi1.metric("Avg Confidence", f"{_avg_conf:.1f}%")
        c_kpi2.metric("Real vs Fake", f"{_real_n} : {_fake_n}", delta=f"{(_real_n / max(1, _total)) * 100:.0f}% real")
        c_kpi3.metric("Fallback Rate", f"{_fb_rate * 100:.0f}%")
        c_kpi4.metric("Predictions (session)", f"{_total}")

        # BI-style chart layout (Power BI / Tableau look)
        _layout_bi = dict(
            paper_bgcolor="#060D1A",
            plot_bgcolor="#0F1E35",
            font=dict(family="Inter, sans-serif", color="#F1F5F9", size=12),
            margin=dict(l=52, r=32, t=44, b=48),
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(26, 47, 74, 0.7)",
                zeroline=False,
                showline=True,
                linecolor="#1A2F4A",
                tickfont=dict(size=11),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(26, 47, 74, 0.7)",
                zeroline=False,
                showline=True,
                linecolor="#1A2F4A",
                tickfont=dict(size=11),
            ),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
            hovermode="x unified",
            bargap=0.35,
            bargroupgap=0.05,
        )

        _langs = ["English", "Tamil", "Hindi", "Telugu", "Malayalam", "Kannada"]
        _sum_by_lang = {l: 0.0 for l in _langs}
        _cnt_by_lang = {l: 0 for l in _langs}
        for h in _dash_hist:
            l = h.get("lang")
            if l in _sum_by_lang:
                _sum_by_lang[l] += float(h.get("confidence", 0.0))
                _cnt_by_lang[l] += 1
        _avg_by_lang = {l: (_sum_by_lang[l] / _cnt_by_lang[l]) if _cnt_by_lang[l] else 0.0 for l in _langs}

        c_chart1, c_chart2 = st.columns(2, gap="large")
        with c_chart1:
            st.markdown('<div class="slbl">Verdict distribution</div>', unsafe_allow_html=True)
            if _PLOTLY_OK:
                fig_v = go.Figure(
                    data=[
                        go.Bar(
                            x=["REAL", "FAKE"],
                            y=[_real_n, _fake_n],
                            marker_color=["#10B981", "#EF4444"],
                            marker_line=dict(color="rgba(255,255,255,0.2)", width=1),
                            text=[_real_n, _fake_n],
                            textposition="outside",
                            textfont=dict(color="#F1F5F9", size=12),
                            hovertemplate="%{x}: %{y} predictions<extra></extra>",
                        )
                    ]
                )
                fig_v.update_layout(**_layout_bi, title=dict(text="Verdict count", font=dict(size=14)), xaxis_title="", yaxis_title="Count")
                st.plotly_chart(fig_v, use_container_width=True, config=dict(displayModeBar=False, displaylogo=False))
            else:
                st.bar_chart({"REAL": _real_n, "FAKE": _fake_n})
        with c_chart2:
            st.markdown('<div class="slbl">Avg confidence by language</div>', unsafe_allow_html=True)
            if _PLOTLY_OK:
                _lang_order = [l for l in _langs if _cnt_by_lang[l] > 0] or _langs
                fig_l = go.Figure(
                    data=[
                        go.Bar(
                            x=_lang_order,
                            y=[round(_avg_by_lang[l], 1) for l in _lang_order],
                            marker_color="#3B82F6",
                            marker_line=dict(color="#60A5FA", width=1),
                            hovertemplate="%{x}: %{y}% avg confidence<extra></extra>",
                        )
                    ]
                )
                fig_l.update_layout(
                    **_layout_bi,
                    title=dict(text="Avg confidence (%)", font=dict(size=14)),
                    xaxis_title="",
                    yaxis_title="Confidence %",
                )
                # Set y-range without passing `yaxis=` twice (it already exists inside `_layout_bi`).
                fig_l.update_yaxes(range=[0, 105])
                st.plotly_chart(fig_l, use_container_width=True, config=dict(displayModeBar=False, displaylogo=False))
            else:
                st.bar_chart(_avg_by_lang)

        st.markdown("<div style='height:.9rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="slbl">Prediction drill-down</div>', unsafe_allow_html=True)

        _pick_space = min(30, len(_dash_hist))
        _indices = list(range(_pick_space))
        _pick_idx = st.selectbox(
            "Choose a prediction (latest first)",
            _indices,
            format_func=lambda i: f'{i+1}. {(_dash_hist[i].get("lang","?"))} · {(_dash_hist[i].get("verdict","?"))} · {float(_dash_hist[i].get("confidence",0.0)):.1f}%',
            key="dash_pick",
        )
        _item = _dash_hist[_pick_idx]

        _lang = _item.get("lang", "?")
        _verdict = _item.get("verdict", "UNKNOWN")
        _conf = float(_item.get("confidence", 0.0))
        _fb_used = bool(_item.get("fallback"))
        _fb_reason = _item.get("fallback_reason")
        _model_name = str(_item.get("model") or "Signal-only")

        _accent = "#10B981" if _verdict == "REAL" else ("#EF4444" if _verdict == "FAKE" else "#3B82F6")
        _fb_badge_bg = "rgba(16,185,129,.12)" if not _fb_used else "rgba(239,68,68,.12)"
        _fb_badge_bd = "rgba(16,185,129,.35)" if not _fb_used else "rgba(239,68,68,.35)"
        _fb_badge_tx = "#34D399" if not _fb_used else "#FCA5A5"

        st.markdown(
            f"""
            <div style="display:flex;gap:.85rem;align-items:center;justify-content:space-between;
                        background:var(--bg-l);border:1px solid var(--border);border-radius:12px;
                        padding:.85rem 1rem;margin-bottom:.7rem">
              <div>
                <div class="slbl" style="margin-bottom:.25rem">Prediction</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:.7rem;color:var(--text-dd)">
                  {_lang} · {_verdict}
                </div>
              </div>
              <div style="text-align:right">
                <div class="slbl" style="margin-bottom:.25rem">Confidence</div>
                <div style="font-size:1.25rem;font-weight:800;color:{_accent}">{_conf:.1f}%</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        d_cols = st.columns(3, gap="medium")
        with d_cols[0]:
            st.markdown(
                f"""
                <div style="background:var(--bg-l);border:1px solid var(--border);border-radius:12px;padding:1rem .95rem;
                            min-height:82px">
                  <div class="slbl" style="margin-bottom:.35rem">Model</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--text-m);
                              white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                    {_model_name}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with d_cols[1]:
            st.markdown(
                f"""
                <div style="background:var(--bg-l);border:1px solid var(--border);border-radius:12px;padding:1rem .95rem;
                            min-height:82px">
                  <div class="slbl" style="margin-bottom:.35rem">Confidence</div>
                  <div style="font-size:1.15rem;font-weight:800;color:{_accent}">{_conf:.1f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with d_cols[2]:
            st.markdown(
                f"""
                <div style="background:var(--bg-l);border:1px solid var(--border);border-radius:12px;padding:1rem .95rem;
                            min-height:82px">
                  <div class="slbl" style="margin-bottom:.35rem">Fallback used</div>
                  <div style="display:inline-flex;align-items:center;gap:.55rem;padding:.45rem .75rem;border-radius:999px;
                              background:{_fb_badge_bg};border:1px solid {_fb_badge_bd};color:{_fb_badge_tx};
                              font-family:'JetBrains Mono',monospace;font-size:.62rem">
                    <span style="width:6px;height:6px;border-radius:50%;background:{_accent}"></span>
                    {"Yes" if _fb_used else "No"}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:.55rem'></div>", unsafe_allow_html=True)

        s1, s2 = st.columns(2, gap="medium")
        with s1:
            st.markdown(
                f"""
                <div style="background:var(--bg-l);border:1px solid var(--border);border-radius:12px;padding:1rem .95rem;
                            min-height:74px">
                  <div class="slbl" style="margin-bottom:.35rem">Signal Fake Matched</div>
                  <div style="font-size:1.2rem;font-weight:800;color:#F1F5F9">{int(_item.get("signal_fake_matches", 0))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f"""
                <div style="background:var(--bg-l);border:1px solid var(--border);border-radius:12px;padding:1rem .95rem;
                            min-height:74px">
                  <div class="slbl" style="margin-bottom:.35rem">Signal Real Matched</div>
                  <div style="font-size:1.2rem;font-weight:800;color:#F1F5F9">{int(_item.get("signal_real_matches", 0))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if _fb_used and _fb_reason:
            st.caption(f"Fallback reason: {_fb_reason}")

        with st.expander("Show raw prediction payload", expanded=False):
            st.json(_item)
    # Close the dashboard panel. We intentionally keep the Dashboard clean
    # and focused on the interactive session-based Command Center.
    st.markdown('</div></div>', unsafe_allow_html=True)

with tab_hist:
    st.markdown('<div class="panel"><div class="ph"><div class="ph-bar ph-cyan"></div><span class="ph-lbl">Prediction History</span></div><div class="pb">', unsafe_allow_html=True)
    if not st.session_state.history:
        st.caption("No predictions yet. Run an analysis in the Verify tab.")
    else:
        st.write(f"**Saved predictions:** {len(st.session_state.history)} (this session)")
        st.dataframe(st.session_state.history[:50], use_container_width=True, height=280)
        st.download_button(
            "⬇ Export history (JSON)",
            data=json.dumps(st.session_state.history, ensure_ascii=False, indent=2),
            file_name="crediAI_history.json",
            mime="application/json",
            use_container_width=True,
        )
        if st.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center;padding:2rem 0;font-family:\'JetBrains Mono\',monospace;font-size:.48rem;letter-spacing:.18em;text-transform:uppercase;color:var(--text-dd);">CrediAI · Verify Before You Believe</div>', unsafe_allow_html=True)