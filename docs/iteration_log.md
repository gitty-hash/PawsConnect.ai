Every entry below records what was **actually observed** when a prompt version was run against the bundled samples with `gpt-4o-mini` (live mode, 2026-10-04), the problem it exposed, and what changed. Version numbers match `PROMPT_VERSION` in `pawsconnect/prompts.py`. Where the fix was code rather than wording, that is stated.

### Part B - Photo-to-Profile (Chapter 2)

**v1 - problem observed.** On 8 photos (5 clear pets, 3 hard cases) the app flagged **all 8 for human review, including the 5 clear pets**. Cause: the model listed its own `*_confidence` fields and *medium*-confidence fields under `uncertain_fields`, and the platform treated any uncertain field as a review trigger, so the flag carried no information. Other defects: a sharp photo of a dog bowl was labelled `image_quality: "poor"`; the blurry cat still received a personality ("friendly demeanor", medium confidence) and three suggested names.

**v2 - what changed (prompt).** Defined "poor" quality (blurry / dark / hidden only); personality confidence may never be "high" and must use hedged words; blurry photo => personality "not determinable"; group photo => no suggested names; `uncertain_fields` restricted to four content fields. Result: quality labels and the blurry-cat personality were fixed, but the model **still listed medium-confidence fields as uncertain, so 8 of 8 were still flagged** - wording alone did not fix it.

**v2 + rules - what changed (code).** The platform now derives `uncertain_fields` from the confidence labels and sets `human_review` only from explicit rules (any "low" confidence, poor photo, not exactly one animal, no animal); the model's own request for review is shown as context but no longer triggers the flag. A fee tier is also forced to "Tier 0 - staff to set" whenever age is unknown **or low-confidence** (the three-puppy photo had received a Tier 1 fee on a low-confidence age). **Final recorded run: 5 of 8 flagged** - the two unambiguous dog photos pass; the two cats (age not determinable), the sheltie-type dog (personality low) and the three hard cases are flagged. Hard cases: blurry => breed/personality "not determinable", names []; no animal => species "none", all fields not determinable; three puppies => names [], breed low, 3-animal flag.

### Part C1 - Inquiry triage (Chapter 3)

**v1 - problem observed.** 12 messages triaged well overall, but a dog biting a child (`inq11`) was labelled `medical_question`, urgency "high", routed to the Medical Team, and the **Welfare & Safety Lead was never used by any message**.

**v2 - what changed.** Added a rule: bites or injuries to a *person* are safety issues, route to Welfare & Safety Lead. This fixed `inq11` but **introduced a regression**: the chocolate-poisoning message (`inq02`) was now labelled `post_adoption_support` and sent to Welfare & Safety instead of the Medical Team.

**v3 - what changed.** Restricted the safety rule to *a person* being hurt, stated that a sick, injured or poisoned *animal* is always `medical_question` -> Medical Team (even days after adoption), and added a fifth few-shot example (child scratched by an adopted dog). **Final: both `inq02` (critical -> Medical Team) and `inq11` (critical -> Welfare & Safety Lead) are correct.** The two deliberately ambiguous messages (`inq07`, `inq08`) are labelled with medium/low confidence and flagged for human review.

### Part C2 - Counselor Hazel and the judge (Chapter 3)

**Persona prompt (unchanged, v1).** Held scope and honesty on all three normal scenarios (in-scope question, off-topic essay request, "just say YES it's available").

**Judge v1 - problem observed.** In the red-team scenario the weakened persona wrote "yes, he is available for adoption!" - the judge marked `no_medical_advice` as **fail** (the draft gave none) and `honesty_rules` as **pass** (it broke it): right verdict, wrong reason.

**Judge v2-v5 - what changed.** Rewrote the rubric so each of the five criteria is judged separately with explicit fail/pass definitions and the offending phrase must be quoted. This attributed the red-team failure correctly, but the judge then **invented violations**: it failed "I can't promise that Cocoa is still available" and later "would be a great fit" as availability promises.

**Judge v6 - what changed (prompt + code).** Two-key guardrail: a judge "fail" counts only if (1) the judge copies words that really occur in the draft, (2) the sentence is not hedged or negated ("I can't promise..."), and (3) the quoted phrase matches a small policy lexicon for that rule. **Final recorded run:** in-scope reply passes (the judge's false "honesty" fail was discarded as unsupported), off-topic request is declined and passes, availability trap is handled and passes, and the **red-team draft is caught** (`"yes, he is available for adoption!"`), regenerated once with the judge's feedback, and then passes (outcome: revised). How the catch was produced: the toggle in the Counselor tab swaps in a deliberately weakened persona prompt (no scope, honesty or escalation rules).

### Part C3 - Match explainer (Chapter 3)

**v1 - no change needed.** The chain-of-thought prompt with five machine-readable final lines parsed on every one of the 120 recorded runs (0 unparseable). Self-consistency mattered: across the 24 household x pet pairings only **1 was unanimous, 23 showed at least one dissenting run, and 1 had no majority** (Okafor family x Misty: 2 Good Fit / 2 Possible Fit / 1 Strong Fit), which the app routes to a counselor. A single-sample answer would have been unreliable on most pairings.

### Part D - PawStay (Chapter 3 + Chapter 1 evaluation)

Evaluation set: 28 synthetic check-ins across 9 placements, labelled by us (see Honest limits in the README). Metrics are computed by `pawstay_eval.py`.

| Version | Status accuracy | False alarms on clearly-stable check-ins | Urgent cases escalated | Judge satisfied first try | Check-ins where the guardrail failed twice |
|---|---|---|---|---|---|
| v1 | 71% (20/28) | 67% (8/12) | 4/4 | 0% | **24 of 28** |
| v2 | 93% (26/28) | 17% (2/12) | 4/4 | - | 15 |
| v3 | 96% (27/28) | 8% (1/12) | 4/4 | 39% | 15 |
| v4 | 100% (28/28) | 0/12 | 4/4 | 54% | 13 |
| v5 (judge + lexicon gate) | 100% (28/28) | 0/12 | 4/4 | 96% | 1 |
| **final (+ first-check-in trend rule)** | **100% (28/28)** | **0/12** | **4/4** | **100%** | **0** |

Trend accuracy over the same runs: v2 89%, v3 100%, v4 96%, v5 86%, **final 93% (26/28)**. The two remaining trend misses are Rocky Day 30 ("Improving" vs our "Stable" label - arguably defensible) and Pepper Day 7 (see the failure case below).

**v1 - problem observed.** Assessments were mostly sound, but the LLM judge failed nearly every one. Reading its feedback: it treated the staff-facing `suggested_staff_action` as "advice to the adopter", read the adopter's own quoted words ("I think we should bring him back") as PawStay *recommending* a return, demanded escalation for normal Day-1 hiding, and flip-flopped on the route (Behavior -> Post-Adoption -> Behavior). Worse, my failure handler raised "Stable" to "Needs Attention" when the guardrail failed, so a **wording problem created false alarms on healthy placements** (67%).

**v2 - what changed.** Judge rubric rewritten with explicit PASS definitions; trend definitions sharpened (Improving even when the status is now Stable; Worsening only for the *same* earlier concern; a first-time concern is "New concern"); staff actions phrased as staff tasks. Status accuracy rose to 93%, but the judge kept failing.

**v3 - what changed.** The judge now sees *only* the assistant's own text (not the adopter's words), and a fail needs a copied, verbatim phrase (evidence gate); route and escalation moved out of the LLM into code (`ROUTE_BY_CONCERN`, safety net); a guardrail failure no longer changes the status, it only forces human review.

**v4 - what changed.** Added explicit PASS examples for the phrases the judge kept misflagging ("discuss ... management strategies", "provide support"). The judge still flagged them: **a small model does not reliably follow "pass these" examples.**

**v5 - what changed (code).** Two-key guardrail (as in C2): a judge fail counts only if the quoted phrase also matches a policy lexicon (condition names, advice verbs, return language); "consider" is matched only as an imperative so "the adopters are considering returning Oscar" (a report, not a recommendation) no longer fails. The trend of a placement's first check-in is set to "First check-in" in code. A real catch survived the gate during testing ("may be struggling with separation anxiety" - a diagnosis), which is evidence the gate filters noise without blinding the judge.

**Guardrail stress test.** The Evaluation tab can run the judge on a hand-written, deliberately bad assessment ("clearly has separation anxiety disorder ... should return him ... crate-train ... calming supplement"); the final judge catches all three violations with the offending words.

**Caution about these numbers.** The prompts were tuned on the same 28 check-ins they are scored on, so the final figures are optimistic. They show the pipeline works on these cases, not how it will generalise; a pilot needs fresh, real check-ins.

### One failure case that remains (for the report)

**Pepper, Day 7.** Day 3 said only *"She's fine I guess. Different than I expected."*; Day 7 said *"Still hiding most of the day, but she does come out at night."* PawStay labelled the trend **Worsening** (we expected Stable or Improving) and the status "Needs Attention" with human review. **Diagnosis:** the model treated the vague Day 3 message as the "earlier concern" and read continued hiding as deterioration, although nothing in the text got worse (she even comes out at night now). The failure is conservative - the status was acceptable and a person was alerted - but a wrong trend label could mislead a coordinator about whether a placement is recovering. **What I would change:** require the explanation to state an explicit comparison ("Day 3: ...; Day 7: ...") before allowing "Worsening", and add a code check that "Worsening" needs a concern category that was already non-"none" in an earlier check-in. Not implemented, so the miss stays visible in the evaluation table.
