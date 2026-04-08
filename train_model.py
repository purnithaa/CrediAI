"""
train_model.py — Multilingual Fake News Detection Training Pipeline
Supports: English (articles + headlines), Tamil, Hindi, Telugu, Malayalam, Kannada.
Uses LIAR (English), in-code synthetic (Tamil), and optional CSV under dataset/
for Indic languages. See DATASETS.md for public datasets (TALLIP, DFND, MMIFND).
"""

import pandas as pd
import numpy as np
from datasets import load_dataset, Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)
import torch
import os
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

print("Bilingual Fake News Detection — Training Pipeline")
print("=" * 70)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — DATASET BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_english_article_dataset():
    """Full-article English dataset."""
    print("\nBuilding English article dataset...")
    datasets = []

    # LIAR dataset (politifact fact-checks)
    try:
        liar = load_dataset("liar", split="train")
        df   = pd.DataFrame(liar)
        df['label'] = df['label'].apply(lambda x: 0 if x in [0, 1, 2] else 1)
        df = df[['statement', 'label']].rename(columns={'statement': 'text'})
        datasets.append(df)
        print(f"  [OK] LIAR: {len(df)} samples")
    except Exception as e:
        print(f"  [ERR] LIAR: {e}")

    real_templates = [
        "The {} Ministry announced today that {} has increased by {}% this quarter, according to official data released by {}.",
        "A court in {} sentenced {} to {} years in prison after being convicted of {} charges under Section {} of the IPC.",
        "The {} government approved a Rs {} crore budget for {} infrastructure in {}. The project is expected to benefit {} citizens.",
        "{} officials confirmed that {} people were affected by {} in {}. Relief camps have been set up in {} locations.",
        "Scientists at {} published research showing {} can reduce {} by {}% in patients with {}. The study covered {} participants.",
        "The {} Election Commission announced polling dates for {} assembly elections. Voting will be held on {} across {} constituencies.",
        "The Reserve Bank of India kept the repo rate unchanged at {}% during its {} monetary policy committee meeting.",
        "{} arrested {} suspects in connection with the {} case. Police recovered {} worth of {} during the raid.",
        "India's GDP grew at {}% in Q{} of FY{}, driven by strong performance in {} and {} sectors, data showed.",
        "The Supreme Court of India ruled that {} must {} within {} days, citing violation of Article {} of the Constitution.",
        # Entertainment / Celebrity
        "Actor {} and singer {} have officially confirmed their separation after {} years of marriage, sources close to the couple said.",
        "Composer {} won the National Award for Best Music Direction for the film {}, presented at a ceremony in New Delhi.",
        "{} and {} announced their engagement on social media. The couple has been together for {} years.",
        "Director {} officially confirmed that the sequel to {} will begin production next month.",
        # Sports
        "India beat {} by {} wickets in the {} Test at {}. {} scored a century while {} took {} wickets.",
        "{} won the IPL title for the {} time, defeating {} by {} runs in the final at {}.",
        "{} became the first Indian to win a {} medal at the Olympics in {} at {}.",
        "Virat Kohli scored {} runs in the {} ODI series against {} making him the leading run-scorer.",
        # World news
        "The United Nations Security Council passed a resolution calling for an immediate ceasefire in {} amid escalating tensions.",
        "{} and {} signed a bilateral trade agreement worth ${} billion during the summit in {}.",
        "The US Federal Reserve raised interest rates by {} basis points, citing persistent inflation concerns.",
        "WHO declared the {} outbreak an international public health emergency after cases surged in {} countries.",
        # Economy
        "Sensex rallied {} points to close at {} after RBI held rates steady and {} sector posted strong quarterly results.",
        "India's foreign exchange reserves rose to ${} billion, the highest level in {} months, RBI data showed.",
        "{} IPO was oversubscribed {} times on the final day of bidding, with strong interest from institutional investors.",
    ]

    fake_templates = [
        "SHOCKING!!! {} is being HIDDEN from you! {} has been SUPPRESSING this for YEARS! Share before they DELETE this!!!",
        "BREAKING: Miracle cure discovered! {} can cure {} in just {} days! Big {} doesn't want you to know!!! URGENT!!!",
        "YOU WON'T BELIEVE what {} did! This EXPOSES the truth about {}! WAKE UP people!!! {} is LYING to you!!!",
        "ALERT: {} is planning to SECRETLY {}! The government is HIDING this! Share this VIRAL post NOW before banned!",
        "100% PROOF: {} causes {}! Scientists HATE this one trick! {} has been COVERING UP the truth for {} years!!!",
        "EXPOSED: {} is actually {}! The REAL truth they never told you! This is going VIRAL! Don't let them silence us!",
        "WARNING: {} in your {} is DANGEROUS! Doctors REFUSE to tell you this! Natural remedy cures ALL of this INSTANTLY!",
        "UNBELIEVABLE: {} caught on camera {}! The media is SILENT! Share this everywhere before {} removes it!!!",
        "SECRET PLAN REVEALED: {} government secretly planning to {}! They don't want you to know! Wake up!!!",
        "Is {} coming back? Hidden government plan to {} will SHOCK you — share before they delete this!!!",
        "BANNED VIDEO: {} admits the truth about {}! They tried to hide this for {} years! Must share!!!",
        "CONSPIRACY EXPOSED: {} and {} working together to secretly {}! The illuminati doesn't want you to see this!",
    ]

    import random
    random.seed(42)

    entities   = ["Health","Finance","Education","Defence","Agriculture","Technology"]
    names      = ["Ramesh Kumar","Priya Sharma","Ahmed Khan","Sita Devi","Mohan Lal","Rajiv Nair"]
    numbers    = ["15","23","47","8","102","500","1200","3","7","11"]
    places     = ["Delhi","Mumbai","Chennai","Kolkata","Bengaluru","Hyderabad","Pune","Jaipur"]
    topics     = ["inflation","vaccination","infrastructure","corruption","climate","education"]

    real_rows, fake_rows = [], []
    for _ in range(3000):
        t = random.choice(real_templates)
        try:
            filled = t.format(*random.choices(entities+names+numbers+places+topics, k=10))
        except Exception:
            filled = t
        real_rows.append({'text': filled, 'label': 1})

    for _ in range(3000):
        t = random.choice(fake_templates)
        try:
            filled = t.format(*random.choices(entities+names+numbers+places+topics, k=6))
        except Exception:
            filled = t
        fake_rows.append({'text': filled, 'label': 0})

    df = pd.concat([pd.DataFrame(real_rows), pd.DataFrame(fake_rows)], ignore_index=True)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"  [OK] Synthetic articles: {len(df)} samples")
    datasets.append(df)

    combined = pd.concat(datasets, ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"\n[OK] English article dataset: {len(combined)} total")
    return combined


def build_english_headline_dataset():
    """Short-headline dataset — massively expanded with all news categories."""
    print("\nBuilding English HEADLINE dataset...")

    real_headlines = [
        # ── Court / Legal ──────────────────────────────────────────────────
        "DMK Leader Jailed For 3 Years Over Controversial Remark Targeting Tamil Nadu Governor",
        "Supreme Court dismisses petition challenging electoral bond scheme",
        "Delhi High Court grants bail to accused in 2020 riots case",
        "Bombay HC orders state to pay Rs 50,000 compensation to wrongful arrest victim",
        "Madras HC stays government order on Tamil medium school closures",
        "Byrathi Basavaraj remanded to CID custody in murder case for seven days",
        "CBI files chargesheet against former minister in coal scam case",
        "ED arrests businessman in Rs 500 crore money laundering case in Mumbai",
        "Supreme Court upholds OBC quota in local body elections in Maharashtra",
        "POCSO court sentences teacher to 10 years for sexual assault of minor",

        # ── Politics ───────────────────────────────────────────────────────
        "PM Modi inaugurates new parliament building in New Delhi",
        "Congress wins Karnataka assembly elections with 136 seats",
        "AIADMK expels 11 members for anti-party activities",
        "Rajya Sabha passes Telecom Bill after heated debate",
        "Tamil Nadu CM announces Rs 2,000 crore drought relief package",
        "Siddaramaiah takes oath as Karnataka Chief Minister",
        "BJP wins Madhya Pradesh assembly elections retaining power",
        "Rahul Gandhi disqualified from Lok Sabha after conviction in defamation case",
        "AAP wins Delhi MCD elections ending 15 years of BJP rule",
        "Nitish Kumar resigns as Bihar CM, joins NDA again",

        # ── Economy ────────────────────────────────────────────────────────
        "India GDP grows 7.2% in Q3, beats analyst estimates",
        "RBI holds repo rate at 6.5% for fourth consecutive meeting",
        "Sensex falls 500 points amid global sell-off on rate fears",
        "Rupee hits all-time low of 84.50 against US dollar",
        "India's retail inflation eases to 4.8% in October",
        "Adani Group stocks recover after Hindenburg report triggers sell-off",
        "SEBI orders forensic audit of Byju's amid financial irregularities probe",
        "India's forex reserves rise to record $650 billion, RBI data shows",
        "Zomato acquires Blinkit for Rs 4,447 crore in all-stock deal",
        "PhonePe files for IPO at $12 billion valuation on Indian exchanges",

        # ── Crime ──────────────────────────────────────────────────────────
        "Hyderabad police arrest 5 in connection with online fraud worth Rs 2 crore",
        "Chennai man sentenced to life imprisonment for murder of wife",
        "CBI arrests former telecom official in bribery case",
        "Three held for smuggling gold worth Rs 1.2 crore at Chennai airport",
        "Delhi police bust fake call centre duping US citizens, 24 arrested",
        "Pune hit-and-run case: Teen arrested after Porsche kills 2 techies",
        "Kolkata doctor rape murder case: RG Kar Medical College principal arrested",

        # ── Science / Health ───────────────────────────────────────────────
        "ISRO successfully launches PSLV-C57 carrying Aditya-L1 solar mission",
        "AIIMS study finds new drug reduces heart attack risk by 30%",
        "WHO declares mpox outbreak over in affected African nations",
        "India reports 200 new dengue cases in Tamil Nadu this week",
        "Chandrayaan-3 successfully lands on Moon's south pole",
        "ICMR approves first indigenously developed mRNA vaccine for COVID-19",

        # ── International ──────────────────────────────────────────────────
        "Russia and Ukraine exchange 200 prisoners in latest swap deal",
        "US Federal Reserve raises interest rates by 25 basis points",
        "China imposes new restrictions on rare earth mineral exports",
        "Israel ceasefire talks resume in Qatar mediated negotiations",
        "G20 summit concludes with joint declaration on climate finance",
        "Bangladesh PM Sheikh Hasina resigns, flees to India amid protests",
        "Pakistan IMF bailout approved at $3 billion to avert default",
        "Donald Trump wins 2024 US Presidential election defeating Kamala Harris",
        "Iran launches missile attack on Israel, Middle East tensions escalate",

        # ── Entertainment / Celebrity ─────────────────────────────────────
        "G.V. Prakash Kumar and Saindhavi officially confirm separation after 11 years",
        "Virat Kohli and Anushka Sharma welcome second child, a baby boy",
        "Dhanush and Aishwaryaa Rajinikanth finalise divorce after 18 years of marriage",
        "Samantha Ruth Prabhu diagnosed with myositis, takes break from work",
        "Nayanthara and Vignesh Shivan get married in a private ceremony in Chennai",
        "Shah Rukh Khan's Jawan crosses Rs 1000 crore at box office in 10 days",
        "Rajinikanth awarded Dadasaheb Phalke Award at 68th National Film Awards",
        "AR Rahman wins Grammy nomination for Best Global Music Album",
        "Priyanka Chopra and Nick Jonas welcome daughter via surrogate",
        "Ranbir Kapoor and Alia Bhatt get married in intimate ceremony in Mumbai",
        "Vijay announces retirement from acting to focus on politics",
        "Suriya wins National Award for Best Actor for Jai Bhim",
        "Deepika Padukone gives birth to first child with Ranveer Singh",

        # ── Sports ────────────────────────────────────────────────────────
        "India beat Australia by 6 wickets to win World Test Championship final",
        "Rohit Sharma scores century in final Test, India wins series 3-1",
        "Mumbai Indians win IPL 2024 title defeating Sunrisers Hyderabad",
        "Neeraj Chopra wins gold at Paris Olympics with 89.45m throw",
        "PV Sindhu wins silver at Paris Olympics in women's badminton",
        "Chess grandmaster D Gukesh becomes World Chess Champion at age 18",
        "Indian football team qualifies for AFC Asian Cup after 8 years",
        "Virat Kohli retires from T20 internationals after World Cup win",
        "Novak Djokovic wins record 24th Grand Slam title at US Open",
        "Real Madrid wins Champions League 2024 defeating Borussia Dortmund",

        # ── Additional Real Headlines (diverse topics) ─────────────────────
        "Kerala government launches free bus travel scheme for women students",
        "TRAI mandates telcos to provide free broadband to gram panchayats",
        "Supreme Court asks Centre to respond on electoral roll discrepancies",
        "India signs defence deal with France for 26 Rafale Marine jets",
        "CBSE class 12 results announced: 87.98% students pass nationwide",
        "RBI issues new guidelines on digital lending platforms",
        "PM Modi launches PM Vishwakarma scheme for traditional artisans",
        "India's unemployment rate drops to 7.8% in October: CMIE data",
        "Uttarakhand tunnel rescue: All 41 workers safely evacuated after 17 days",
        "Air India merges with Vistara to form India's second largest airline",
        "SEBI approves new framework for index funds and ETFs",
        "India Post Payments Bank adds 1 crore new accounts in six months",
        "Manipur violence: Centre deploys additional CRPF battalions",
        "Tamil Nadu gets UNESCO recognition for Kanchipuram silk weaving",
        "ISRO signs agreement with NASA for joint lunar mission",
    ]

    fake_headlines = [
        # ── Sensationalist English ─────────────────────────────────────────
        "BREAKING: Scientists discover MIRACLE CURE doctors don't want you to know!!!",
        "SHOCKING: Government SECRETLY planning to ban WhatsApp from India!!!",
        "EXPOSED: Famous actor reveals TRUTH about Bollywood drug mafia!!!",
        "WARNING: This common food is KILLING you and media is HIDING it!!!",
        "VIRAL: PM Modi caught on camera doing THIS will leave you speechless!!!",
        "ALERT: Banks to FREEZE all accounts this Friday — share before deleted!!!",
        "YOU WON'T BELIEVE what they found in packaged milk brands in India!!!",
        "UNBELIEVABLE: Alien spacecraft spotted over New Delhi caught on camera!!!",
        "URGENT: COVID new variant 100x more dangerous spreading fast in India!!!",
        "SHOCKING TRUTH: Onions cause cancer — doctors finally admit what they hid!!!",
        "BREAKING: India to become part of China by 2025 secret treaty revealed!!!",
        "100% PROOF: Moon landing was FAKE — NASA admits in leaked document!!!",
        "MUST SHARE: This one juice cures diabetes in 3 days permanently!!!",
        "EXPOSED: WHO is planning to microchip all humans through vaccines!!!",
        "ALERT: RBI to ban all old currency notes by midnight tonight!!!",
        "SHOCKING: Famous celebrity dies — media hiding truth about vaccine death!!!",
        "VIRAL: Petrol price to drop to Rs 20 per litre from next month!!!",
        "WARNING: 5G towers causing mass bird deaths across India — proof inside!!!",
        "BREAKING: India declares war on Pakistan — army deployed at border!!!",
        "URGENT: Withdraw your bank deposits NOW before government seizes accounts!!!",
        "EXPOSED: This politician secretly converted — proof here!!!",
        "SHOCKING: Eating this fruit daily causes INSTANT death — share to save lives!!!",
        "ALERT: New law allows police to arrest anyone without warrant from Monday!!!",
        "MIRACLE: Blind man regains sight after applying this home remedy!!!",
        "BREAKING: Earth to stop rotating for 24 hours next week, NASA confirms!!!",

        # ── Conspiracy / Rumour framing ────────────────────────────────────
        "Is ₹2000 note coming back? Government's SECRET plan revealed — share now!!!",
        "Hidden truth about COVID vaccines — what they don't want you to know!!!",
        "Secret treaty exposed: India surrendering Kashmir by 2026 — viral proof!!!",
        "BANNED: This video proves 5G towers are microchipping people in India!!!",
        "SHOCKING: Drinking this water cures cancer in 7 days — doctors SILENT!!!",
        "Government secretly adding chemicals to tap water — proof inside!!!",
        "EXPOSED: Illuminati controls Indian politics — leaked document confirms!!!",
        "Is India going bankrupt? Secret RBI report hidden from public!!!",
        "PM secretly planning to ban gold ownership — share before they delete!!!",
        "URGENT: New law will take away your property rights from next month!!!",

        # ── Additional Fake Headlines ──────────────────────────────────────
        "SHOCKING: Eating onions at night causes instant liver damage — doctors silent!!!",
        "BREAKING: India to demonetise Rs 500 notes again — RBI secret circular leaked!!!",
        "MUST WATCH: This politician's son caught doing this — media hiding the truth!!!",
        "VIRAL PROOF: Moon is actually a hologram — NASA scientist admits!!!",
        "WARNING: New WhatsApp update STEALS your bank passwords — delete immediately!!!",
        "EXPOSED: Turmeric milk kills COVID in 2 hours — government hiding this!!!",
        "SECRET REVEALED: Drinking this kills cancer cells — big pharma doesn't want you to know!!!",
        "BREAKING NEWS: India-Pakistan war started — army on full alert — share NOW!!!",
        "ALERT: All ATMs to shut down from midnight — withdraw cash immediately!!!",
        "100% REAL: This temple water cures blindness — doctors furious!!!",
    ]

    rows = []
    for h in real_headlines:
        rows.append({'text': h, 'label': 1})
    for h in fake_headlines:
        rows.append({'text': h, 'label': 0})

    import random
    random.seed(42)
    augmented = []
    for _ in range(500):
        h = random.choice(real_headlines)
        augmented.append({'text': h + " — officials confirm", 'label': 1})
        augmented.append({'text': h + ", report says", 'label': 1})
        augmented.append({'text': h + ", sources told PTI", 'label': 1})
    for _ in range(500):
        h = random.choice(fake_headlines)
        augmented.append({'text': h + " SHARE NOW!!!", 'label': 0})

    df = pd.DataFrame(rows + augmented)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"  [OK] Headlines: {len(df)} samples (real={sum(df.label==1)}, fake={sum(df.label==0)})")
    return df


def build_tamil_dataset():
    """Tamil fake/real news dataset — expanded with all categories."""
    print("\nBuilding Tamil dataset...")

    real_samples = [
        # ── Legal / Court ──────────────────────────────────────────────────
        "தமிழ்நாடு அரசு புதிய மருத்துவமனை கட்டிடத்தை இன்று திறந்து வைத்தது",
        "சுகாதாரத்துறை அமைச்சர் 200 படுக்கை வசதி கொண்ட மருத்துவமனையை திறந்து வைத்தார்.",
        "மத்திய அரசு புதிய வேலைவாய்ப்புக் கொள்கையை வெளியிட்டது",
        "நீதிமன்றம் குற்றவாளிக்கு 3 ஆண்டு சிறைத்தண்டனை விதித்தது.",
        "திமுக தலைவர் கவர்னர் பற்றிய கருத்துக்காக 3 ஆண்டு சிறை தண்டனை பெற்றார்",
        "எக்மூர் நீதிமன்றம் குற்றவாளிக்கு 5 ஆண்டு சிறைத்தண்டனை விதித்தது",
        "சென்னை நீதிமன்றம் ஜாமீன் மனுவை நிராகரித்தது",
        "உச்ச நீதிமன்றம் தமிழ்நாடு அரசின் மேல்முறையீட்டை ஏற்றுக்கொண்டது",
        "மாஜிஸ்திரேட் நீதிமன்றம் குற்றவாளியை காவல் துறை காவலில் ஒப்படைத்தது",

        # ── Politics ───────────────────────────────────────────────────────
        "இந்திய பொருளாதார வளர்ச்சியில் முன்னேற்றம் காணப்படுகிறது என்று பொருளாதார நிபுணர்கள் தெரிவித்தனர்",
        "உள்ளாட்சி தேர்தல் அமைதியாக நடைபெற்றது என்று தேர்தல் ஆணையம் அறிவித்தது",
        "கல்வி வாரியம் புதிய பாடத்திட்டத்தை அறிமுகப்படுத்தியது",
        "திமுக தலைவர் சிவாஜி கிருஷ்ணமூர்த்தி 3 ஆண்டு சிறைத்தண்டனை பெற்றார்",
        "அதிமுக பொதுக்குழு கூட்டம் அறிவிக்கப்பட்டது",
        "முதலமைச்சர் தமிழிசை 500 கோடி ரூபாய் திட்டம் அறிவித்தார்",
        "ஆளுநர் புதிய நியமனம் குறித்து அரசு உத்தரவு பிறப்பிக்கப்பட்டது",

        # ── Economy ────────────────────────────────────────────────────────
        "சதவீதம் உயர்வு கோடி ரூபாய் திட்டம் அறிவிக்கப்பட்டது",
        "இந்திய பங்குச்சந்தை 500 புள்ளிகள் உயர்வு பதிவு செய்தது",
        "ரிசர்வ் வங்கி வட்டி விகிதத்தை மாற்றாமல் தக்கவைத்தது",
        "தமிழ்நாடு அரசின் வருவாய் கடந்த ஆண்டை விட 15 சதவீதம் உயர்ந்துள்ளது",

        # ── Entertainment / Celebrity ─────────────────────────────────────
        "ஜி.வி. பிரகாஷ் - சைந்தவி விவாகரத்து பெற்றதை அதிகாரப்பூர்வமாக உறுதிப்படுத்தினர்",
        "11 ஆண்டுகள் திருமண வாழ்க்கையின் பின் இருவரும் பிரிந்தனர் என்று குடும்பத்தினர் தெரிவித்தனர்",
        "நயன்தாரா - விக்னேஷ் சிவன் திருமணம் சென்னையில் நடைபெற்றது",
        "தனுஷ் - ஐஸ்வர்யா விவாகரத்து முடிவுக்கு வந்தது",
        "சமந்தா நோய்வாய்ப்பட்டதால் படப்பிடிப்பிலிருந்து விலகினார்",
        "விஜய் அரசியலில் ஈடுபட நடிப்பிலிருந்து விலகுவதாக அறிவித்தார்",
        "சூர்யா தேசிய திரைப்பட விருது பெற்றார்",
        "ஏ.ஆர். ரஹ்மான் கிராமி விருதுக்கு நாமினேஷன் பெற்றார்",
        "ரஜினிகாந்த் தாதாசாஹேப் பால்கே விருது பெற்றார்",

        # ── Sports ────────────────────────────────────────────────────────
        "இந்தியா ஆஸ்திரேலியாவை 6 விக்கெட்டுகளால் தோற்கடித்து உலக சாம்பியன்ஷிப் வென்றது",
        "நீரஜ் சோப்ரா பாரிஸ் ஒலிம்பிக்ஸில் தங்க பதக்கம் வென்றார்",
        "மும்பை இந்தியன்ஸ் ஐபிஎல் 2024 கோப்பையை வென்றது",
        "விராட் கோஹ்லி டி20 சர்வதேச கிரிக்கெட்டிலிருந்து ஓய்வு பெற்றார்",

        # ── World news ────────────────────────────────────────────────────
        "ஐக்கிய நாடுகள் சபை போர் நிறுத்த தீர்மானம் நிறைவேற்றியது",
        "அமெரிக்க மத்திய வங்கி வட்டி விகிதத்தை உயர்த்தியது",
        "உலக சுகாதார நிறுவனம் புதிய தொற்றுநோய் அவசர நிலை அறிவித்தது",
    ]

    fake_samples = [
        # ── Sensationalist / Viral ─────────────────────────────────────────
        "அதிர்ச்சி! இந்த செய்தியை பகிரவும் உடனே மறைக்கும் முன்!!!",
        "வைரல் ஆகும் வீடியோ! நம்ப முடியாத உண்மை அம்பலம்!!!",
        "அவசரம்! எல்லா நோய்களும் குணமாகும் அதிசய மூலிகை கண்டுபிடிப்பு!!!",
        "நீக்கப்படும் முன் பாருங்கள்! ரகசியம் வெளியாகிறது!!!",
        "விரைவில் நீக்கப்படும்! உடனே பகிரவும்! மறைக்கும் உண்மை!!!",
        "மருத்துவர்கள் மறைக்கும் இரகசியம்! எல்லா நோய் குணமாகும்!!!",
        "வைரலாகும் வீடியோ! நம்ப முடியாத அதிசய தகவல் பகிரவும்!!!",
        "உடனே பகிரவும்! அரசு மறைக்கும் தகவல் இதோ!!!",
        "அதிர்ச்சி தகவல்! நம்ப முடியவில்லை! அனைவருக்கும் அனுப்புங்கள்!!!",

        # ── Conspiracy / Rumour framing ────────────────────────────────────
        "இந்தியாவில் ₹2000 நோட்டுகள் மீண்டும் அறிமுகம் செய்யப்படுகிறதா? மத்திய அரசு ரகசிய திட்டம்?",
        "ரகசிய திட்டம்! அரசு மக்களிடமிருந்து இதை மறைக்கிறது! உண்மை வெளியானது!!!",
        "மீண்டும் வருகிறதா ₹1000 நோட்டு? ரகசிய சதி அம்பலம்! உடனே பகிருங்கள்!!!",
        "அதிர்ச்சி! தடுப்பூசி ஆபத்தானது என்று மருத்துவர்கள் மறைக்கும் உண்மை!!!",
        "5ஜி கோபுரம் ஆபத்தானது! மக்களை கொல்லும் திட்டம் அம்பலம்!!!",
        "நம்ப முடியாத உண்மை! இந்த மூலிகை எல்லா நோயையும் குணப்படுத்தும்!!!",
        "ரகசியம் அம்பலம்! அரசு மக்களை ஏமாற்றுகிறது! மறைத்த உண்மை வெளியானது!!!",
        "அவசர செய்தி! வங்கி கணக்குகள் நாளை முடக்கப்படும்! உடனே பணம் எடுங்கள்!!!",
        "மறைக்கப்படுகிறது! இந்த இயற்கை மருந்து புற்றுநோயை குணப்படுத்தும்!!!",
        "அதிர்ச்சியான செய்தி! இந்தியா சீனாவுடன் ரகசிய ஒப்பந்தம் செய்தது!!!",
        "நம்ப முடியாத செய்தி! பெட்ரோல் விலை நாளை ரூ.20க்கு குறையும்!!!",
        "உடனே பகிருங்கள்! அரசு புதிய சட்டம் உங்கள் சொத்தை பறிக்கும்!!!",
        "வைரல் செய்தி! இந்த பழம் சாப்பிட்டால் உடனே இறந்துவிடுவீர்கள்!!!",
    ]

    rows = []
    for s in real_samples * 450:
        rows.append({'text': s, 'label': 1})
    for s in fake_samples * 450:
        rows.append({'text': s, 'label': 0})

    import random
    random.seed(42)
    augmented = []
    for _ in range(300):
        s = random.choice(real_samples)
        augmented.append({'text': s + " என்று அதிகாரிகள் தெரிவித்தனர்.", 'label': 1})
        augmented.append({'text': s + " என்று செய்திகள் தெரிவிக்கின்றன.", 'label': 1})
    for _ in range(300):
        s = random.choice(fake_samples)
        augmented.append({'text': s + " உடனே பகிர்ந்துகொள்ளுங்கள்!!!", 'label': 0})

    df = pd.DataFrame(rows + augmented).sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"  [OK] Tamil: {len(df)} samples (real={sum(df.label==1)}, fake={sum(df.label==0)})")
    return df


def _load_indic_csv_if_exists(lang, filename=None):
    """Load dataset/<lang>_train.csv if present. Expects columns: text, label (0=FAKE, 1=REAL)."""
    path = filename or os.path.join("dataset", f"{lang.lower()}_train.csv")
    if os.path.isfile(path):
        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
        if "text" in df.columns and "label" in df.columns:
            df = df[["text", "label"]].dropna()
            df["label"] = df["label"].astype(int)
            return df
    return None


def build_hindi_dataset():
    """Hindi: load dataset/hindi_train.csv if present, else minimal synthetic (Devanagari + Roman)."""
    print("\nBuilding Hindi dataset...")
    df = _load_indic_csv_if_exists("hindi")
    if df is not None:
        print(f"  [OK] Loaded from CSV: {len(df)} samples")
        return df
    # Minimal synthetic for demo; add more or use TALLIP/MMIFND (see DATASETS.md)
    real = ["सरकार ने आज घोषणा की", "पुलिस ने बताया कि", "अदालत ने फैसला सुनाया", "मंत्री ने कहा कि", "पीटीआई की रिपोर्ट के मुताबिक"]
    fake = ["तुरंत शेयर करें!!!", "वायरल खबर!!! झूठ मत समझो", "सच्चाई सामने!!! शेयर करें", "अफवाह नहीं सच्चाई"]
    rows = [{"text": s, "label": 1} for s in real * 200] + [{"text": s, "label": 0} for s in fake * 200]
    df = pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"  [OK] Synthetic Hindi: {len(df)} samples (add dataset/hindi_train.csv for real data)")
    return df


def build_telugu_dataset():
    """Telugu: load dataset/telugu_train.csv if present, else minimal synthetic."""
    print("\nBuilding Telugu dataset...")
    df = _load_indic_csv_if_exists("telugu")
    if df is not None:
        print(f"  [OK] Loaded from CSV: {len(df)} samples")
        return df
    # Placeholder; use DFND/TALLIP CSV (see DATASETS.md)
    real = ["పోలీసులు చెప్పారు", "సర్కారు ప్రకటన", "కోర్టు తీర్పు"]
    fake = ["వెంటనే షేర్ చేయండి!!!", "వైరల్ వార్త!!"]
    rows = [{"text": s, "label": 1} for s in real * 150] + [{"text": s, "label": 0} for s in fake * 150]
    df = pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"  [OK] Synthetic Telugu: {len(df)} samples (add dataset/telugu_train.csv, e.g. from DFND)")
    return df


def build_malayalam_dataset():
    """Malayalam: load dataset/malayalam_train.csv if present, else minimal synthetic."""
    print("\nBuilding Malayalam dataset...")
    df = _load_indic_csv_if_exists("malayalam")
    if df is not None:
        print(f"  [OK] Loaded from CSV: {len(df)} samples")
        return df
    real = ["പോലീസ് പറഞ്ഞു", "സർക്കാർ പ്രഖ്യാപനം", "കോടതി വിധി"]
    fake = ["ഉടൻ ഷെയർ ചെയ്യുക!!!", "വൈറല് വാർത്ത!!"]
    rows = [{"text": s, "label": 1} for s in real * 150] + [{"text": s, "label": 0} for s in fake * 150]
    df = pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"  [OK] Synthetic Malayalam: {len(df)} samples (add dataset/malayalam_train.csv, e.g. from DFND)")
    return df


def build_kannada_dataset():
    """Kannada: load dataset/kannada_train.csv if present, else minimal synthetic."""
    print("\nBuilding Kannada dataset...")
    df = _load_indic_csv_if_exists("kannada")
    if df is not None:
        print(f"  [OK] Loaded from CSV: {len(df)} samples")
        return df
    real = ["ಪೋಲೀಸ್ ತಿಳಿಸಿದರು", "ಸರ್ಕಾರ ಘೋಷಣೆ", "ನ್ಯಾಯಾಲಯ ತೀರ್ಪು"]
    fake = ["ತಕ್ಷಣ ಷೇರ್ ಮಾಡಿ!!!", "ವೈರಲ್ ಸುದ್ದಿ!!"]
    rows = [{"text": s, "label": 1} for s in real * 150] + [{"text": s, "label": 0} for s in fake * 150]
    df = pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"  [OK] Synthetic Kannada: {len(df)} samples (add dataset/kannada_train.csv, e.g. from DFND)")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — MODEL TRAINING
# ══════════════════════════════════════════════════════════════════════════════

def train_model(df, language, model_name, output_dir, num_epochs=5):
    print(f"\nTraining {language} model -> {output_dir}")
    print(f"   Base model : {model_name}")
    print(f"   Samples    : {len(df)}  (real={sum(df.label==1)}, fake={sum(df.label==0)})")

    train_df, val_df = train_test_split(df, test_size=0.20, random_state=42, stratify=df['label'])

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Class-weight balancing — helps when fake/real counts aren't perfectly equal
    from sklearn.utils.class_weight import compute_class_weight
    import numpy as np
    classes      = np.array([0, 1])
    class_weights = compute_class_weight('balanced', classes=classes, y=train_df['label'].values)
    class_weights_tensor = torch.tensor(class_weights, dtype=torch.float)

    model     = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2,
        id2label={0: "FAKE", 1: "REAL"},
        label2id={"FAKE": 0, "REAL": 1},
        ignore_mismatched_sizes=True
    )

    # Use 256 for articles, 64 for headlines (faster + better fit)
    max_len = 64 if "headline" in output_dir.lower() else 256

    def tokenize(examples):
        return tokenizer(examples['text'], padding='max_length',
                         truncation=True, max_length=max_len)

    train_ds = Dataset.from_pandas(train_df).map(tokenize, batched=True)
    val_ds   = Dataset.from_pandas(val_df).map(tokenize, batched=True)

    def compute_metrics(eval_pred):
        preds, labels = eval_pred
        preds = np.argmax(preds, axis=1)
        p, r, f1, _ = precision_recall_fscore_support(labels, preds, average='binary')
        return {'accuracy': accuracy_score(labels, preds), 'f1': f1,
                'precision': p, 'recall': r}

    # Weighted Trainer so minority class gets fair treatment
    from transformers import Trainer as BaseTrainer
    import torch.nn as nn
    class WeightedTrainer(BaseTrainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits  = outputs.logits
            loss_fn = nn.CrossEntropyLoss(weight=class_weights_tensor.to(logits.device))
            loss    = loss_fn(logits, labels)
            return (loss, outputs) if return_outputs else loss

    args = TrainingArguments(
        output_dir                  = output_dir,
        evaluation_strategy         = "epoch",
        save_strategy               = "epoch",
        learning_rate               = 1.5e-5,       # ↓ slower LR = more stable fine-tuning
        per_device_train_batch_size = 16,
        per_device_eval_batch_size  = 16,
        num_train_epochs            = num_epochs,
        weight_decay                = 0.02,          # ↑ slightly stronger regularisation
        load_best_model_at_end      = True,
        metric_for_best_model       = "f1",
        logging_steps               = 50,
        save_total_limit            = 2,
        push_to_hub                 = False,
        warmup_ratio                = 0.12,          # ↑ longer warmup prevents early spikes
        lr_scheduler_type           = "cosine",      # cosine decay = smoother convergence
        label_smoothing_factor      = 0.05,          # smoothing reduces overconfidence
        fp16                        = torch.cuda.is_available(),  # faster on GPU
    )

    trainer = WeightedTrainer(
        model           = model,
        args            = args,
        train_dataset   = train_ds,
        eval_dataset    = val_ds,
        tokenizer       = tokenizer,
        data_collator   = DataCollatorWithPadding(tokenizer),
        compute_metrics = compute_metrics,
    )

    print("Training started...")
    trainer.train()
    results = trainer.evaluate()

    print(f"\n[OK] {language} model done!")
    print(f"   Accuracy  : {results['eval_accuracy']:.4f}")
    print(f"   F1        : {results['eval_f1']:.4f}")
    print(f"   Precision : {results['eval_precision']:.4f}")
    print(f"   Recall    : {results['eval_recall']:.4f}")

    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # ── Save evaluation artifacts for UI dashboards ─────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    preds = trainer.predict(val_ds)
    y_true = preds.label_ids
    y_pred = np.argmax(preds.predictions, axis=1)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()  # [[TN, FP],[FN, TP]] for (FAKE=0, REAL=1)

    metrics_artifact = {
        "task": "fake_news_binary_classification",
        "language": language,
        "base_model": model_name,
        "output_dir": output_dir,
        "label_schema": {
            "id2label": { "0": "FAKE", "1": "REAL" },
            "liar_mapping_note": (
                "LIAR has 6 labels. In this project we map to binary: "
                "[pants-fire, false, barely-true] → FAKE (0) and "
                "[half-true, mostly-true, true] → REAL (1)."
            ),
        },
        "dataset_stats": {
            "train_size": int(len(train_df)),
            "val_size": int(len(val_df)),
            "train_counts": {
                "fake": int((train_df["label"] == 0).sum()),
                "real": int((train_df["label"] == 1).sum()),
            },
            "val_counts": {
                "fake": int((val_df["label"] == 0).sum()),
                "real": int((val_df["label"] == 1).sum()),
            },
            "max_len": int(max_len),
        },
        "metrics": {
            "accuracy": float(results["eval_accuracy"]),
            "precision": float(results["eval_precision"]),
            "recall": float(results["eval_recall"]),
            "f1": float(results["eval_f1"]),
        },
        "confusion_matrix": {
            "labels": ["FAKE", "REAL"],
            "matrix": cm,
            "note": "Rows are true labels, columns are predicted labels.",
        },
    }

    with open(os.path.join(output_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_artifact, f, ensure_ascii=False, indent=2)

    return results


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    import sys
    train_indic = "--indic" in sys.argv or os.getenv("TRAIN_INDIC", "").strip().lower() in ("1", "true", "yes")
    # Hackathon-friendly controls:
    #   --epochs 1
    #   --langs hindi,tamil  (supported tokens: en_article,en_headline,tamil,hindi,telugu,malayalam,kannada,all,indic)
    epochs = 5
    if "--epochs" in sys.argv:
        try:
            epochs = int(sys.argv[sys.argv.index("--epochs") + 1])
        except Exception:
            epochs = 1
    elif os.getenv("EPOCHS", "").strip().isdigit():
        epochs = int(os.getenv("EPOCHS").strip())

    langs_arg = None
    if "--langs" in sys.argv:
        try:
            langs_arg = sys.argv[sys.argv.index("--langs") + 1]
        except Exception:
            langs_arg = None

    langs = None
    if langs_arg:
        toks = [t.strip().lower() for t in langs_arg.split(",") if t.strip()]
        if "all" in toks:
            langs = {"en_article", "en_headline", "tamil", "hindi", "telugu", "malayalam", "kannada"}
        else:
            langs = set(toks)
        if "indic" in langs:
            langs |= {"hindi", "telugu", "malayalam", "kannada"}
            langs.discard("indic")
    else:
        # Default behavior preserved
        langs = {"en_article", "en_headline", "tamil"} | ({"hindi", "telugu", "malayalam", "kannada"} if train_indic else set())

    print("\n" + "="*70)
    print(f"TRAINING MODELS (epochs={epochs})")
    print("="*70)

    r_article = r_headline = r_tamil = None

    if "en_article" in langs:
        en_art_df  = build_english_article_dataset()
        r_article  = train_model(
            en_art_df, "English Articles",
            model_name="roberta-base",
            output_dir="./models/english_article",
            num_epochs=epochs,
        )

    if "en_headline" in langs:
        en_hl_df   = build_english_headline_dataset()
        r_headline = train_model(
            en_hl_df, "English Headlines",
            model_name="distilroberta-base",
            output_dir="./models/english_headline",
            num_epochs=epochs,
        )

    if "tamil" in langs:
        ta_df    = build_tamil_dataset()
        r_tamil  = train_model(
            ta_df, "Tamil",
            model_name="xlm-roberta-base",
            output_dir="./models/tamil",
            num_epochs=epochs,
        )

    indic_results = {}
    for lang, builder, out_dir, key in [
        ("Hindi", build_hindi_dataset, "./models/hindi", "hindi"),
        ("Telugu", build_telugu_dataset, "./models/telugu", "telugu"),
        ("Malayalam", build_malayalam_dataset, "./models/malayalam", "malayalam"),
        ("Kannada", build_kannada_dataset, "./models/kannada", "kannada"),
    ]:
        if key in langs:
            df = builder()
            indic_results[lang] = train_model(df, lang, model_name="xlm-roberta-base", output_dir=out_dir, num_epochs=epochs)

    print("\n\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    if r_article:
        print(f"  English Article Model  — Acc: {r_article['eval_accuracy']:.2%}  F1: {r_article['eval_f1']:.2%}")
    if r_headline:
        print(f"  English Headline Model — Acc: {r_headline['eval_accuracy']:.2%}  F1: {r_headline['eval_f1']:.2%}")
    if r_tamil:
        print(f"  Tamil Model            — Acc: {r_tamil['eval_accuracy']:.2%}  F1: {r_tamil['eval_f1']:.2%}")
    for lang, res in indic_results.items():
        print(f"  {lang} Model              — Acc: {res['eval_accuracy']:.2%}  F1: {res['eval_f1']:.2%}")
    print("\n[OK] All models saved. Run:  py -m streamlit run app.py")
    print("   Quick train (Hindi only): py train_model.py --langs hindi --epochs 1")
    print("   Quick train (Indic only): py train_model.py --langs indic --epochs 1")
    print("   Full train: py train_model.py --langs all --epochs 5")
    print("   See DATASETS.md for CSV paths and public datasets.")
    print("="*70)


if __name__ == "__main__":
    main()