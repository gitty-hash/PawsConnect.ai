# PawsConnect - AI suite for a pet-adoption platform

MIS 552 - Homework 1. A Streamlit demo with five AI features, each built for a specific person on the platform and each with a human in the loop.

| Tab | Feature | Course source | Technique |
|---|---|---|---|
| Overview | Stakeholder map, feature-to-technique matrix, model note (Part A) | Ch. 1 | Customization roadmap |
| B | Photo-to-Profile listing generator | Ch. 2 (CampusMart + extras labs) | Vision model, structured JSON, fallback prompting |
| C1 | Adoption inquiry triage queue | Ch. 3 (StayScape Step 2) | Few-shot classification, defined labels, JSON |
| C2 | Counselor "Hazel" with a judge guardrail | Ch. 3 (Steps 4 and 6) | Role-playing system prompt, LLM-as-judge |
| C3 | Adopter-pet match explainer | Ch. 3 (Step 5) | Chain-of-thought + self-consistency vote |
| D | **PawStay** - post-adoption stability monitor | Ch. 3 + Ch. 1 | Few-shot JSON, judge guardrail, evaluation set + regression gate |

## Run it (no API key needed)

Python 3.10+ is required.

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

The app opens in **Cached demo** mode: every bundled sample replays a response recorded from a real `gpt-4o-mini` run (`cache/cached_responses.json`), so every feature can be demonstrated offline. The TA can grade entirely in this mode.

### Live mode (optional)

Live mode reads the key from an environment variable; no key is ever stored in the project.

```powershell
# Windows PowerShell (then restart the terminal)
setx OPENAI_API_KEY "sk-..."
```
```bash
# macOS / Linux
export OPENAI_API_KEY="sk-..."
```

Switch the sidebar to **Live (OpenAI API)** to upload your own photos, type your own messages, edit household profiles and add new check-ins. Whole-demo cost with `gpt-4o-mini` is well under two dollars.

## What to try (about 5 minutes)

1. **B. Photo to Profile** - pick `dog_01.jpg`, then the three hard cases (`hard_case_blurry.jpg`, `multiple_animals.jpg`, `no_animal.jpg`) and watch confidence labels and the review flag. Press *Run all sample photos* for the summary table.
2. **C1. Inquiry Triage** - *Triage all 12 sample messages*: queue sorted by urgency with badges, reasons and routes; two messages are deliberately ambiguous.
3. **C2. Counselor Hazel** - run the four test scenarios. Scenario 4 uses a deliberately weakened persona (red-team toggle) so the judge has a real problem to catch; open *Reviewer details* to see draft 1, the verdict and the regenerated draft.
4. **C3. Match Explainer** - pick *The Okafor family* with *Maple* and press *Explain the match*: five step-by-step runs, a vote, the top reasons and concern, and the reasoning in an expander.
5. **D. PawStay** - *Staff queue* shows every placement worst-first; *Case timeline* shows Rocky going Stable -> Needs Attention -> Improving; *Evaluation* scores PawStay against a labelled set and applies a release gate; *KPIs* shows the four business KPIs.

## Folder layout

```
app.py                      Streamlit entry point (sidebar mode toggle + tabs)
pawsconnect/
  llm.py                    single model gateway: cached replay or live OpenAI, JSON mode, image parts
  prompts.py                every prompt in one place (versions tracked)
  features/                 profile, triage, counselor, match, pawstay, pawstay_eval, events
  tabs/                     one Streamlit module per tab
  theme.py                  badges, cards, stylesheet
data/                       sample data (6 pets, 4 adopter profiles, 12 inquiries, 9 PawStay journeys, KPI seed events)
Testing_Images/             8 CC0 photos + credits.md (referenced by relative path)
cache/cached_responses.json recorded gpt-4o-mini responses for the cached demo
scripts/record_cache.py     re-record the cache (needs OPENAI_API_KEY)
scripts/export_prompts.py   regenerate prompts.md from the code
prompts.md                  final prompt for every feature + the iteration log
```

If you edit a prompt, the cache entries for it no longer match (the key includes the full prompt text); run `python scripts/record_cache.py` to re-record.

## Honest limits

- **All sample data is synthetic or CC0.** The PawStay answer key (`gold` labels in `data/pawstay_cases.json`) was written for this project; evaluation scores on 28 check-ins are indicative, not statistically precise.
- **The prompts were tuned on the same 28 check-ins they are scored on**, so the evaluation numbers (28/28 status, 26/28 trend, 4/4 urgent cases escalated, 0/12 false alarms) are optimistic. `docs/iteration_log.md` shows every version, including the failures; a real pilot needs fresh, real check-ins.
- **An LLM judge from the same small model is noisy.** Both guardrails therefore use a two-key design (the judge must quote the offending words *and* the quote must match a policy lexicon); see `prompts.md` section 2 for why.
- **The KPI board's seed events are synthetic** (labelled in the UI). KPIs 1-3 describe how impact will be measured in a pilot; KPI 4 comes from the evaluation harness.
- AI output is a *draft*: every uncertain, medical, safety or welfare-related result is flagged for a person. PawStay never diagnoses, gives care advice, or recommends returning a pet.
