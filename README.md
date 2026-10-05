# PawsConnect - an AI feature suite for a pet-adoption platform

PawsConnect connects animal shelters with people who want to adopt. This project is a working demo of **five AI features**, each built for one specific person on the platform (a shelter volunteer, the intake team, an adopter, a post-adoption coordinator). It was built for **MIS 552 (AI for Digital Platforms), Homework 1**.

> **One rule runs through the whole app: the AI drafts and flags, people decide.** Anything uncertain, medical, safety-related or welfare-related is marked "Human review". No feature diagnoses an animal, gives medical or training advice, or recommends returning a pet.

**You can run everything without an API key.** The app ships with 207 recorded answers from a real model run, so every feature works offline in "Cached demo" mode.

---

## Contents
1. [Quick start](#1-quick-start-5-minutes-no-api-key)
2. [The two modes: Cached and Live](#2-the-two-modes-cached-demo-and-live)
3. [A 5-minute guided tour](#3-a-5-minute-guided-tour)
4. [What each feature does](#4-what-each-feature-does)
5. [Tools and technologies: what is used where](#5-tools-and-technologies-what-is-used-where)
6. [How it works under the hood](#6-how-it-works-under-the-hood)
7. [Project layout](#7-project-layout)
8. [Common tasks](#8-common-tasks)
9. [Troubleshooting](#9-troubleshooting)
10. [Data, licensing and privacy](#10-data-licensing-and-privacy)
11. [Honest limits](#11-honest-limits)

---

## 1. Quick start (5 minutes, no API key)

**You need:** Python 3.10 or newer ([python.org](https://www.python.org/downloads/)). Tested on Windows 11 with Python 3.13 and two library sets: the versions it was built with (Streamlit 1.59, OpenAI SDK 2.45) and a fresh `pip install -r requirements.txt` (Streamlit 1.65, OpenAI SDK 3.24). The smoke test and live text/vision calls passed on both.

**Step 1 - get the code.** Download the ZIP (or `git clone` the repository) and open a terminal inside the `Pawsconnect` folder.

**Step 2 - (recommended) create a virtual environment and install the requirements.**

| Windows (PowerShell) | macOS / Linux |
|---|---|
| `python -m venv .venv` | `python3 -m venv .venv` |
| `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| `pip install -r requirements.txt` | `pip install -r requirements.txt` |

**Step 3 - start the app.**

```bash
python -m streamlit run app.py
```

Your browser opens at `http://localhost:8501`. If it does not, open that address yourself.

**Step 4 (optional) - check that everything works on your computer.**

```bash
python scripts/smoke_test.py
```

This presses every feature button in the background and prints `PASS` or `FAIL` for each (11 checks). It needs no API key.

---

## 2. The two modes: Cached demo and Live

Choose the mode with the radio button at the top of the sidebar.

| | **Cached demo** (default) | **Live (OpenAI API)** |
|---|---|---|
| Needs an API key? | **No** | Yes |
| What it does | Replays answers recorded from real `gpt-4o-mini` runs | Calls the OpenAI API for every action |
| What you can try | The bundled samples: 8 photos, 12 messages, 4 counselor scenarios, 4 households x 6 pets, 9 adopter journeys | Everything above **plus** your own photo uploads, your own messages, edited household profiles, free chat with Hazel, new check-ins |
| Cost | Free | Fractions of a cent per action (whole demo well under $2) |
| If you try something new | Shows "This input was not recorded..." instead of crashing | Works |

Switching modes clears all displayed results, so a cached answer is never shown on a "Live" screen. The sidebar shows how many cached answers were replayed, or (in Live mode) how many real API calls were made and the estimated cost.

### Setting up an API key for Live mode

The app reads the key from the environment variable **`OPENAI_API_KEY`**. It never stores or asks for the key in the app itself, and the repository contains no key.

1. Create an account at [platform.openai.com](https://platform.openai.com) and add a few dollars of credit (Settings -> Billing). Without credit every call fails with a `429 insufficient_quota` error even if the key is valid.
2. Create a key (Settings -> API keys) and set it:

| Windows (PowerShell) | macOS / Linux |
|---|---|
| `setx OPENAI_API_KEY "sk-..."` then **close and reopen the terminal** | `export OPENAI_API_KEY="sk-..."` (add it to `~/.zshrc` or `~/.bashrc` to keep it) |

3. Restart the app, then pick **Live (OpenAI API)** in the sidebar. A green "API key found in the environment" box confirms it.

> Never paste your key into chat, code or a commit. If a key is ever exposed, delete it in the OpenAI dashboard and create a new one.

---

## 3. A 5-minute guided tour

Open the app (Cached mode is fine) and visit the tabs in order.

| Tab | Try this | What you should see |
|---|---|---|
| **Overview** | Read the two tables | Who each feature serves, and which technique was used and why |
| **B. Photo to Profile** | Pick `dog_01.jpg` -> *Generate adoption profile*; then try `hard_case_blurry.jpg`, `multiple_animals.jpg`, `no_animal.jpg`; press *Run all sample photos*; scroll to the banner | A profile card with confidence badges and a fee tier. On the hard cases: "not determinable", low confidence, an orange **Needs human review** box. At the bottom: an AI-generated promo banner for Cocoa and the exact prompt used |
| **C1. Inquiry Triage** | *Triage all 12 sample messages* | A queue sorted by urgency with coloured badges, the model's reason for each label, the team to route to, and review flags (two messages are deliberately ambiguous) |
| **C2. Counselor Hazel** | Click the four test scenarios, then open *Reviewer details* | A named counselor persona. Scenario 4 uses a deliberately weakened persona: the judge **catches** "yes, he is available for adoption!", the reply is regenerated once, then passes |
| **C3. Match Explainer** | Household *The Okafor family* + pet *Maple* -> *Explain the match* | Five step-by-step runs vote on a fit rating, with the vote split shown, the top three reasons, the top concern, and the reasoning inside an expander |
| **D. PawStay** | *Staff queue* -> *Load staff queue*; then *Case timeline* (pick Rocky); then *Evaluation* -> *Run evaluation*; then *KPIs* | Every adopted pet, most urgent first; how a placement changes over time (Rocky: Stable -> Needs Attention -> Improving); a scored test set with a pass/fail release gate; and the four business KPIs |

---

## 4. What each feature does

| Feature | Who it helps | What it does | Course technique |
|---|---|---|---|
| **B. Photo to Profile** | Shelter volunteers | One photo in, a draft adoption profile out (names, breed guess with confidence, age range, personality, care needs, fee tier). When the model cannot tell, it must say "not determinable" instead of inventing. A person reviews every draft | Ch. 2: vision model, structured JSON, fallback prompting |
| **B bonus. Promo banner** | Shelter marketing | An image model turns Cocoa's photo into a banner. Labelled "AI-generated", needs staff approval | Ch. 2: Shopify Magic (image generation) |
| **C1. Inquiry Triage** | Intake / front desk | Turns free-text messages into records: category, urgency, who should handle it, a one-line summary, the reason, and a review flag | Ch. 3: few-shot classification, JSON output |
| **C2. Counselor Hazel** | Adopters | A chat persona that answers adoption questions only, never promises availability, never gives vet advice, and escalates emergencies. A second AI call (the "judge") checks every reply before it is shown | Ch. 3: role-playing system prompt, LLM-as-judge |
| **C3. Match Explainer** | Adopters and counselors | Explains how well a household fits a pet, by reasoning step by step five times and taking a majority vote. A split vote is shown, not hidden | Ch. 3: chain-of-thought, self-consistency |
| **D. PawStay** *(innovation)* | Post-adoption coordinators | Reads adopters' Day 1/3/7/14/30 check-ins **together with the earlier ones**, labels each placement Stable / Needs Attention / Urgent Human Follow-up, notes whether it is improving or worsening, quotes the adopter's words as evidence and routes it to the right team. Includes a labelled test set, a release gate and a KPI board | Ch. 3: few-shot JSON + judge; Ch. 1: evaluation set and regression gate |

---

## 5. Tools and technologies: what is used where

| Tool | What it is used for | Where in the project |
|---|---|---|
| **Python 3.10+** | The whole application | everywhere |
| **Streamlit** | The web interface (tabs, buttons, badges, tables, chat) | `app.py`, `pawsconnect/tabs/*`, `pawsconnect/theme.py` |
| **OpenAI API, model `gpt-4o-mini`** | The language and vision model behind every feature (reads photos, classifies, chats, reasons, judges). Called in "JSON mode" when code needs structured output | `pawsconnect/llm.py` (the only file that talks to the API) |
| **OpenAI Python SDK (`openai`)** | Python client for the API above | `pawsconnect/llm.py`, `scripts/generate_banner.py` |
| **OpenAI Images API, model `gpt-image-1`** | Creates the promo banner from a photo (an outside tool; the course labs use Stable Diffusion) | `scripts/generate_banner.py`, shown in `pawsconnect/tabs/profile_tab.py` |
| **Pillow (`PIL`)** | Resizes photos and encodes them for the vision model; crops report images | `pawsconnect/llm.py`, `scripts/build_report*.py` |
| **pandas** | Displays the PawStay evaluation table | `pawsconnect/tabs/pawstay_tab.py` |
| **httpx** (installed with `openai`) | Network layer; asks for uncompressed replies to avoid a decoding bug seen in the course labs | `pawsconnect/llm.py` |
| **JSON files + SHA-256 hashing** | The *cache*: each prompt is hashed and its recorded answer stored, so Cached mode replays real answers offline | `cache/cached_responses.json`, `pawsconnect/llm.py` |
| **Plain Python rules + regular expressions** | Safety net and guardrail checks that do not depend on the AI: review-flag rules, routing rules, quote verification, risk-phrase detection, the policy word lists that confirm a judge's objection | `pawsconnect/features/*.py` |
| **Streamlit `AppTest`** | Headless self-check of the whole UI | `scripts/smoke_test.py` |
| **Playwright + Microsoft Edge/Chrome** | Takes the report screenshots and prints the report to PDF *(only needed to rebuild the report)* | `scripts/build_report.py` |
| **python-docx + BeautifulSoup** | Builds the editable Word version of the report *(only needed to rebuild the report)* | `scripts/build_report_docx.py` |
| **Wikimedia Commons** | Source of the 8 CC0 (public-domain) test photos | `Testing_Images/credits.md` |
| **Git / GitHub** | Version control and hosting | `.gitignore` keeps keys and build files out |

Packages for the app itself are in `requirements.txt`. Extra packages for rebuilding the report are in `requirements-report.txt`.

---

## 6. How it works under the hood

```
 You (browser)
     |
     v
 Streamlit tab  (pawsconnect/tabs/*)        <- shows cards, badges, tables
     |
     v
 Feature logic  (pawsconnect/features/*)    <- builds the prompt, applies the rules in plain Python
     |
     v
 LLMGateway.chat()  (pawsconnect/llm.py)    <- ONE place every model call goes through
     |
     +--- Cached mode --> looks up cache/cached_responses.json (no network)
     |
     +--- Live mode ----> OpenAI API (gpt-4o-mini)
```

- **One gateway.** Every model call passes through `LLMGateway.chat()`. It handles JSON mode, image encoding, retries, the usage/cost meter and the cache. The cache key is a hash of the *whole* prompt, so if you edit a prompt the old recorded answer is no longer used (you will see "not recorded" until you re-record - see [Common tasks](#8-common-tasks)).
- **All prompts live in one file** (`pawsconnect/prompts.py`), each with a version number. `prompts.md` shows the final text of every prompt plus the log of what went wrong in each version and what was changed.
- **The AI is never the last line of defence.** Plain Python code sets the review flags, forces the right team for health/safety/return-intent cases, checks that quoted evidence really appears in the adopter's message, and blocks risky phrases from being marked "Stable".
- **Two-key guardrails.** Both judges (Hazel's replies and PawStay's assessments) work like this: the AI judge must quote the exact offending words, *and* those words must match a short policy word list. Testing showed the small model, used alone as a judge, invented violations.
- **Draft -> judge -> send / regenerate once / escalate to a human.** This is the flow for Hazel's chat and for PawStay.

---

## 7. Project layout

```
Pawsconnect/
|-- app.py                          Streamlit entry point: sidebar (mode switch) + the six tabs
|-- requirements.txt                Packages needed to run the app
|-- requirements-report.txt         Extra packages only for rebuilding the report
|-- README.md                       This file
|-- prompts.md                      Final prompt for every feature + iteration log (generated)
|-- PawsConnect_Design_Report.pdf   The design report (also as .docx)
|
|-- pawsconnect/                    The application code
|   |-- llm.py                      The single model gateway: cached replay or live OpenAI
|   |-- prompts.py                  Every prompt, with version numbers
|   |-- theme.py                    Colours, badges, cards
|   |-- features/                   Logic, one file per feature (no Streamlit code in here)
|   |   |-- profile.py              Part B  - photo -> profile + review rules
|   |   |-- triage.py               Part C1 - inquiry triage
|   |   |-- counselor.py            Part C2 - Hazel + judge
|   |   |-- match.py                Part C3 - chain-of-thought + voting
|   |   |-- pawstay.py              Part D  - PawStay pipeline (assess -> rules -> judge)
|   |   |-- pawstay_eval.py         Part D  - labelled test set, metrics, release gate
|   |   |-- events.py               Part D  - KPI event log
|   |   `-- common.py               Shared helpers (data loading, evidence gate)
|   `-- tabs/                       One Streamlit screen per tab
|
|-- data/                           Sample data (all synthetic)
|   |-- pet_listings.json           6 pets with shelter facts
|   |-- adopter_profiles.json       4 household descriptions
|   |-- inquiries.json              12 messages (2 ambiguous)
|   |-- pawstay_cases.json          9 adopter journeys with answer-key labels
|   |-- pawstay_events_seed.jsonl   Synthetic KPI events so the KPI board is not empty
|   `-- banners/                    Promo banner image + banner_meta.json (tool, prompt, date)
|
|-- Testing_Images/                 8 CC0 photos (5 clear pets + 3 hard cases) + credits.md
|-- cache/cached_responses.json     207 recorded model answers for Cached mode
|
|-- scripts/
|   |-- smoke_test.py               Check the app works on your machine (no key needed)
|   |-- record_cache.py             Re-record the cached answers (needs a key)
|   |-- generate_banner.py          Regenerate the promo banner (needs a key)
|   |-- export_prompts.py           Rebuild prompts.md from the code
|   |-- build_report.py             Rebuild the report PDF
|   `-- build_report_docx.py        Rebuild the report as Word
`-- docs/
    |-- iteration_log.md            What was observed in every prompt version
    |-- screenshots/                Live-mode and cached-mode screenshots used in the report
    `-- report/report_body.html     Source text of the report body
```

---

## 8. Common tasks

| I want to... | Run this | Needs a key? |
|---|---|---|
| Start the app | `python -m streamlit run app.py` | No |
| Check my setup works | `python scripts/smoke_test.py` | No |
| Use a different port | `python -m streamlit run app.py --server.port 8600` | No |
| Re-record the cached answers after editing a prompt | `python scripts/record_cache.py` (add `--only triage` to re-record one feature; takes about 3 minutes, costs about $0.07) | **Yes** |
| Regenerate the promo banner | `python scripts/generate_banner.py` (about $0.07 per image) | **Yes** |
| Refresh `prompts.md` from the code | `python scripts/export_prompts.py` | No |
| Rebuild the report PDF | `pip install -r requirements-report.txt` then `python scripts/build_report.py --name "Your Name" --id "Your ID"` (needs Edge or Chrome installed) | No |
| Rebuild the Word report | `python scripts/build_report_docx.py --name "Your Name" --id "Your ID"` | No |

On Windows, set the key for a single terminal session with `$env:OPENAI_API_KEY="sk-..."` (PowerShell) before running a script that needs it.

---

## 9. Troubleshooting

| Problem | Cause and fix |
|---|---|
| PowerShell says "running scripts is disabled" when activating `.venv` | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that same window (it lasts only for that window), then activate again. Or skip the virtual environment and run `pip install -r requirements.txt` directly |
| `streamlit` is not recognised | Use `python -m streamlit run app.py` (it works even when the command is not on your PATH), and make sure the virtual environment is activated |
| "This input was not recorded in the cached demo" | You are in Cached mode and tried something new (own photo, edited text). Use a bundled sample, or switch to Live mode |
| The Live option says "No OPENAI_API_KEY in the environment" | Set the variable (see section 2), then **fully close and reopen the terminal**, then restart the app. `setx` only affects terminals opened afterwards |
| `429 insufficient_quota` in Live mode | The OpenAI account has no credit. Add credit at platform.openai.com -> Billing (the key itself is fine) |
| `401 Incorrect API key` | The key is mistyped, truncated or revoked. Create a new one |
| After editing a prompt, Cached mode says "not recorded" | Expected: the cache key includes the prompt text. Run `python scripts/record_cache.py` (needs a key) |
| Port 8501 is already in use | Another Streamlit app is running. Close it or use `--server.port 8600` |
| Report build fails with a Playwright/browser error | Install Microsoft Edge or Google Chrome, and run `pip install -r requirements-report.txt` |
| Photos or the banner do not appear | Run the app from the project folder (`cd Pawsconnect`); images are found by relative paths like `Testing_Images/dog_01.jpg` |

---

## 10. Data, licensing and privacy

- **Photos:** the 8 test photos are **CC0** (public-domain dedication) from Wikimedia Commons. `Testing_Images/credits.md` lists each file's source page, creator, license and the date it was accessed. The app reads them from disk and never downloads anything.
- **Everything else is synthetic:** the pets' stories, adopter households, messages and check-ins were written for this project. No real personal data is used.
- **Photos sent to OpenAI:** in Live mode (and when the cache was recorded) a photo and prompt are sent to the OpenAI API. In Cached mode nothing leaves your computer.
- **Secrets:** the API key is read only from an environment variable. `.gitignore` excludes `.env` files and the runtime event log.
- **Promo banner:** AI-generated from a CC0 photo; the app labels it as AI-generated and as a draft that needs staff approval.

---

## 11. Honest limits

- **The PawStay answer key is synthetic** (labels in `data/pawstay_cases.json` were written for this project); evaluation scores on 28 check-ins are indicative, not statistically precise.
- **Prompts were tuned on the same 28 check-ins they are scored on**, so the evaluation numbers (status 28/28, trend 26/28, 4/4 urgent cases escalated, 0/12 false alarms) are optimistic. `docs/iteration_log.md` shows every version, including the failures. A real pilot needs fresh, real check-ins.
- **A judge built on the same small model is noisy**, which is why both guardrails use the two-key design described in section 6.
- **The KPI board's seed events are synthetic** and labelled as such in the app. KPIs 1-3 (return rate, time to contact, share stabilised) describe how impact would be measured in a pilot; KPI 4 (urgent cases escalated) comes from the evaluation harness.
- **Breed labels are guesses.** The model's breed call is shown as e.g. "Collie-type mix (medium confidence)" with its evidence, and fee tiers depend on age only, never on breed.
