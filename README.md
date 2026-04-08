# CrediAI-V2

**CrediAI** is a fake-news detection app that analyzes text in **6 languages** (English, Tamil, Hindi, Telugu, Malayalam, Kannada) using hybrid AI + signal scoring. This repo contains the web app, cloud configs, and an Android WebView app.

---

## Table of contents

1. [What is CrediAI?](#what-is-crediai)
2. [Repository structure](#repository-structure)
3. [Definitions: files and folders](#definitions-files-and-folders)
4. [Definitions: deployments](#definitions-deployments)
5. [How to run locally](#how-to-run-locally)
6. [How to deploy](#how-to-deploy)
7. [How to build the Android APK](#how-to-build-the-android-apk)
8. [Glossary](#glossary)

---

## What is CrediAI?

- **Web app:** A **Streamlit** (Python) app that lets users paste headlines or articles and get a **Likely Fake / Likely Real** verdict with confidence, plus signal-based indicators (word count, numbers, quotes, caps, etc.).
- **Models:** Uses Hugging Face transformers (RoBERTa, mBERT, XLM-RoBERTa) for English, Tamil, and four Indic languages. Models are **lazy-loaded** (only when the user runs analysis) to avoid high memory use on startup.
- **Extra features:** Live headlines (RSS), optional Twitter/X and Instagram feeds, dashboard with model metrics, prediction history.
- **Deployments:** The app runs as a **web service** on **Render**. An **Android APK** is a WebView that opens the Render URL.

---

## Repository structure

```
credi_ai/
├── app.py                 # Main Streamlit app (fake-news UI + logic)
├── train_model.py         # Optional: train custom models per language
├── requirements.txt       # Python deps for the web app
├── runtime.txt            # Python version for Render
├── render.yaml            # Render.com web service definition
├── .streamlit/            # Streamlit config + optional secrets
├── android-app/           # Android WebView app (builds to APK)
├── dataset/               # Optional CSV data for training
├── DATASETS.md            # Docs for datasets and training
├── DEPLOY_RENDER.md       # Step-by-step Render deploy
├── SETUP.md               # Local setup (e.g. UV_LINK_MODE)
└── README.md              # This file
```

---

## Definitions: files and folders

| Item | Purpose |
|------|--------|
| **app.py** | Streamlit app: UI, language detection, model loading (`@st.cache_resource`), inference, RSS, optional Twitter/Instagram, dashboard, history. Entrypoint for `streamlit run app.py`. |
| **train_model.py** | Script to train or fine-tune models (English/Tamil/Indic) and write `models/<lang>/` and `metrics.json`. Not required to run the app. |
| **requirements.txt** | Python dependencies: `streamlit`, `torch`, `transformers`, `feedparser`, `plotly`. Used by Render and local runs. |
| **runtime.txt** | Pins Python version (e.g. `python-3.11.7`) for Render. |
| **render.yaml** | Render Blueprint: defines one **web** service that runs `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`, installs deps from `requirements.txt`, and ensures `.streamlit/secrets.toml` exists from example. |
| **.streamlit/config.toml** | Streamlit server config (headless, CORS, etc.) for local and cloud. |
| **.streamlit/secrets.toml.example** | Template for secrets (e.g. `TW_BEARER`, `IG_USERNAME`, `IG_PASSWORD`). Copied to `secrets.toml` on Render if missing. |
| **.streamlit/secrets.toml** | Actual secrets (gitignored). Optional for Twitter/Instagram; app works without them. |
| **android-app/** | Android project: single-activity WebView app that loads `credi_app_url` (Render URL). Shows a loading screen until the page loads. |
| **android-app/app/src/main/res/values/strings.xml** | Defines `app_name`, `credi_app_url` (e.g. `https://crediai.onrender.com`), and loading screen text. |
| **android-app/app/build.gradle.kts** | App-level Gradle: SDK 34, Kotlin, dependencies (AndroidX, WebKit). |
| **android-app/gradle/wrapper/gradle-wrapper.properties** | Pins Gradle 8.7 for the Android build. |
| **dataset/** | Optional CSVs (`*_train.csv`, etc.) for training; see **DATASETS.md**. |
| **.gitignore** | Ignores `.env`, `venv/`, `.streamlit/secrets.toml`, build artifacts, etc. |
| **.env.example** | Example env vars (e.g. `UV_LINK_MODE=copy` for uv on Windows/OneDrive). |
| **SETUP.md** | Local setup notes (UV hardlink warning, env vars). |
| **DEPLOY_RENDER.md** | How to deploy the Streamlit app on Render (Web Service, env, URL). |
| **DATASETS.md** | Datasets and training instructions for each language. |

---

## Definitions: deployments

| Term | Meaning |
|------|--------|
| **Render** | Host for the **live Streamlit app**. Build: install deps, optional copy of `secrets.toml`. Start: `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`. Free tier can spin down after inactivity (cold start ~30–60 s). Live URL example: `https://crediai.onrender.com`. |
| **Android APK** | App that opens the **Render URL** in a full-screen WebView. Built in Android Studio from `android-app/`. All logic stays on the server (Render). |

---

## How to run locally

1. **Python 3.11**, optional **uv** (or plain pip).
2. From repo root:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Open `http://localhost:8501`. Optional: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add Twitter/Instagram keys if needed.
4. If you see uv hardlink warnings (e.g. on OneDrive), set `UV_LINK_MODE=copy` or see **SETUP.md**.

---

## How to deploy

- **Render:** Connect this repo to Render, use `render.yaml` (Blueprint) or create a Web Service with build command `pip install -r requirements.txt` and start command `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`. See **DEPLOY_RENDER.md**.
- **Android:** After Render is live, set `credi_app_url` in `android-app/.../strings.xml` to your Render URL, then build the APK (see below).

---

## How to build the Android APK

1. Open **android-app** in Android Studio.
2. Wait for Gradle sync (Gradle 8.7, AGP 8.5.2).
3. **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
4. Debug APK: `android-app/app/build/outputs/apk/debug/app-debug.apk`.
5. For release/signed APK: **Build → Generate Signed Bundle / APK** and follow the wizard. See **android-app/README.md**.

---

## Troubleshooting: site keeps loading

If the Render site never finishes loading:

1. **Render free tier** spins down after ~15 min of no traffic; the first request can take **30–60+ seconds**. Wait once; later loads are faster until it sleeps again.
2. **Check Render logs** (Dashboard → your service → Logs) for **out-of-memory (OOM)** or Python errors. Free tier has limited RAM; if the app crashes on startup, the page will hang.
3. **RSS timeouts:** The app fetches headlines from several RSS feeds with a **4 s timeout per feed**. Slow feeds no longer block the page indefinitely.
4. **For reliably fast load:** Deploy the same app on **Streamlit Community Cloud** ([share.streamlit.io](https://share.streamlit.io)) or **Hugging Face Spaces**, then point the APK or browser to that URL. These free tiers often keep the app warm so it loads in a few seconds.

---

## Glossary

| Term | Definition |
|------|------------|
| **Streamlit** | Python framework for data apps. Runs as a single process. |
| **WebView** | Android component that displays a web page inside the app; this project uses it to show the CrediAI Streamlit UI. |
| **APK** | Android application package; the installable file for Android. |
| **Lazy loading** | In this repo: `torch` and `transformers` are imported only when the user runs analysis (inside `load_model()` / `infer()`), so the first page render is light and avoids OOM on Render free tier. |
| **Blueprint (Render)** | `render.yaml` in the repo; Render can create/update the web service from it. |
| **credi_app_url** | String resource in the Android app that holds the URL the WebView loads (Render). |
| **secrets.toml** | Streamlit secrets (API keys, etc.); optional. On Render, `.streamlit/secrets.toml.example` is copied to `secrets.toml` during build if the file is missing. |

---

For dataset and training details, see **DATASETS.md**. For Render-only steps, see **DEPLOY_RENDER.md**. For local env/setup, see **SETUP.md**.
