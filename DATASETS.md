# CrediAI — Datasets for Training

This document lists datasets used or recommended for training CrediAI models (English + **Hindi, Telugu, Malayalam, Kannada**).

---

## Pre-trained models (default, no training)

**The app now uses pre-trained Hugging Face models for all 6 languages.** No local training or dataset is required to run Verify:

| Language | Model | Reported accuracy |
|----------|--------|-------------------|
| English | `hamzab/roberta-fake-news-classification` | — |
| Tamil | `mdosama39/bert-base-multilingual-cased-FakeNews-Dravidian-mBert` | ~83% |
| Hindi, Telugu, Malayalam, Kannada | `Sajib-006/fake_news_detection_xlmRoberta` (multilingual) | — |

You can still train your own models and place them under `./models/<lang>`; the app will prefer local models when present.

---

## Do I need to download or add anything?

**No.** You can use the app without putting any files in the `dataset/` folder. Training is optional.

| What you do | Need to download? | Need to add files in `dataset/`? |
|-------------|-------------------|-----------------------------------|
| **Run the app (Verify)** | No | No |
| **Train English / Tamil** | No (LIAR is auto-downloaded when you run `train_model.py`; Tamil is built from code) | No |
| **Train Hindi / Telugu / Malayalam / Kannada** | Optional | Optional |
| **Train Indic with *good* accuracy** | Yes — use TALLIP or DFND (see below) | Yes — add `dataset/hindi_train.csv` etc. (see “How to add data”) |

If you run `py train_model.py --indic` and do **not** add any CSV, the script still runs and trains on a small in-code synthetic set (useful only to test the pipeline). To get useful models for Hindi/Te/ML/KN, download one of the public datasets, convert to CSV (`text`, `label`), and place them in `dataset/` as described below.

---

## English

| Dataset | Source | Notes |
|--------|--------|--------|
| **LIAR** | Hugging Face `liar` | ~12.8K Politifact statements; 6-way labels. We map to binary: `pants-fire, false, barely-true` → FAKE (0); `half-true, mostly-true, true` → REAL (1). |
| Synthetic headlines/articles | `train_model.py` | Built-in templates for real/fake to augment LIAR. |

---

## Tamil

- **In-code synthetic** — `train_model.py` includes `build_tamil_dataset()` with real/fake Tamil samples (court, politics, entertainment, sports, sensational/viral phrases).
- For more data: **DFND (Dravidian Fake News Data)** and **TALLIP-FakeNews-Dataset** (see below) include Tamil.

---

## Hindi, Telugu, Malayalam, Kannada — Public Datasets

### 1. **TALLIP-FakeNews-Dataset** (Multilingual, low-resource)
- **Link:** [GitHub - Arko98/TALLIP-FakeNews-Dataset](https://github.com/Arko98/TALLIP-FakeNews-Dataset)
- **Paper:** "A Transformer Based Approach to Multilingual Fake News Detection in Low Resource Languages" (ACM TALLIP).
- Use for: Hindi, Telugu, Malayalam, Kannada (and others) with a single multilingual or per-language split.

### 2. **DFND — Dravidian Fake News Data**
- **Link:** [IEEE DataPort - DFND](https://ieee-dataport.org/documents/dfnd-dravidianfake-news-data)
- **Languages:** Telugu, Kannada, Tamil, Malayalam.
- **Size:** 27K+ preprocessed articles (50% fake, 50% real), Jan 2021–Dec 2022.
- **Format:** CSV by language; separate files for fake/real. Ideal for training `./models/telugu`, `./models/malayalam`, `./models/kannada` (and Tamil if you want more than in-code data).

### 3. **MMIFND / MMCFND** (Multimodal Multilingual Indic)
- **Paper:** "MMCFND: Multimodal Multilingual Caption-aware Fake News Detection for Low-resource Indic Languages" (arXiv 2410.10407).
- **Languages:** Hindi, Bengali, Marathi, Malayalam, Tamil, Gujarati, Punjabi.
- **Size:** 28,085 instances; text + image captions. Good for Hindi and Malayalam if you use their data or pipeline.

### 4. **Hindi-specific**
- **Fake news article detection datasets for Hindi** (Springer, 2024): large-scale hybrid (real + synthetic) with linguistic annotation. Search: "Fake news article detection datasets for Hindi language".

---

## How to add data in this repo

1. **Option A — CSV in `dataset/`**
   - Place train CSVs with columns `text` and `label` (0 = FAKE, 1 = REAL), e.g.:
     - `dataset/hindi_train.csv`
     - `dataset/telugu_train.csv`
     - `dataset/malayalam_train.csv`
     - `dataset/kannada_train.csv`
   - `train_model.py` can load them via `build_hindi_dataset()` etc. if the path exists; otherwise it uses minimal in-code synthetic data.

2. **Option B — Download TALLIP / DFND**
   - Clone or download the dataset, convert to `text,label` CSV, then save under `dataset/<lang>_train.csv` and run:
     ```bash
     py train_model.py
     ```
   - Training will produce `./models/hindi`, `./models/telugu`, etc., and `metrics.json` for the Dashboard.

3. **Base model**
   - For all Indic languages we use **XLM-RoBERTa** (`xlm-roberta-base`) so one script can train any of Tamil, Hindi, Telugu, Malayalam, Kannada.

---

## Summary

| Language   | Suggested data source                          | Model path        |
|-----------|-------------------------------------------------|-------------------|
| English   | LIAR + in-code synthetic                        | `english_article`, `english_headline` |
| Tamil     | In-code synthetic; optionally DFND/TALLIP     | `tamil`           |
| Hindi     | TALLIP, MMIFND, or Hindi-specific papers; CSV  | `hindi`           |
| Telugu    | DFND, TALLIP; CSV                              | `telugu`          |
| Malayalam | DFND, TALLIP, MMIFND; CSV                      | `malayalam`       |
| Kannada   | DFND, TALLIP; CSV                              | `kannada`         |

Once a model folder exists (e.g. `./models/hindi`) with trained weights and `metrics.json`, the app uses the transformer; otherwise it uses **signal-only fallback** for that language (no crash, clear “Fallback” in UI).
