"""Part B - Photo-to-Profile listing generator.

Chapter 2 (02b_multi_modal.ipynb, Part 2 "Photo -> Listing", eBay Magical Listing):
base64 image + text prompt -> vision model -> JSON that platform code can use.
Chapter 2 (02a notebook, Part 3 "chart extraction"): the prompt carries a FALLBACK
instruction for fields the model cannot extract ("If you can't extract the chart
data, summarize the image...") - here: "not determinable", never an invented breed.
"""
from __future__ import annotations

from ..llm import LLMGateway, image_part, parse_json
from ..prompts import FEE_TIERS, PROFILE_PROMPT
from .common import as_bool, as_list, pick

CONF = ["high", "medium", "low"]
AGES = ["under 1 year", "1 to 3 years", "3 to 7 years", "8+ years", "unknown"]
QUALITY = ["clear", "acceptable", "poor"]
SPECIES = ["dog", "cat", "other", "none"]
TIER_UNKNOWN = "Tier 0 - Staff to set (age unknown)"
NOT_DETERMINABLE = "not determinable"
CONTENT_FIELDS = {"breed_guess", "age_range", "personality", "care_requirements"}


def generate_profile(gw: LLMGateway, raw_image_bytes: bytes) -> dict:
    """Photo bytes -> normalised profile dict (with human_review computed in code)."""
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": PROFILE_PROMPT},
            # detail="low" is cheaper and plenty for a pet photo (Chapter 2 lab).
            image_part(raw_image_bytes, detail="low"),
        ],
    }]
    raw = gw.chat(messages, tag="profile", temperature=0, json_mode=True)
    return normalise_profile(parse_json(raw))


def normalise_profile(d: dict) -> dict:
    """Validate the model's JSON and apply the human-review rules in code.

    The model also reports ``model_human_review``; we never rely on it alone - the
    platform sets ``human_review`` itself whenever any confidence is low, any field
    is uncertain, the photo is poor, or there is not exactly one animal.
    """
    # The model's own reasons are shown as context only; the flag comes from the rules below
    # (v2 testing: the model asked for review on photos where every confidence was medium).
    model_reasons: list[str] = [str(r) for r in as_list(d.get("review_reasons")) if r]
    reasons: list[str] = []
    p = {
        "image_quality": pick(d.get("image_quality"), QUALITY, "poor"),
        "animal_count": d.get("animal_count") if isinstance(d.get("animal_count"), int) else 1,
        "species": pick(d.get("species"), SPECIES, "other"),
        "suggested_names": [str(n) for n in as_list(d.get("suggested_names"))][:3],
        "breed_guess": str(d.get("breed_guess") or NOT_DETERMINABLE),
        "breed_confidence": pick(d.get("breed_confidence"), CONF, "low"),
        "breed_evidence": str(d.get("breed_evidence") or ""),
        "age_range": pick(d.get("age_range"), AGES, "unknown"),
        "age_confidence": pick(d.get("age_confidence"), CONF, "low"),
        "personality": str(d.get("personality") or NOT_DETERMINABLE),
        "personality_confidence": pick(d.get("personality_confidence"), CONF, "low"),
        "care_requirements": [str(c) for c in as_list(d.get("care_requirements"))],
        "fee_tier": pick(d.get("fee_tier"), list(FEE_TIERS), TIER_UNKNOWN),
        "fee_tier_reason": str(d.get("fee_tier_reason") or ""),
        # The model's own list is kept for reference only: v1/v2 testing showed it lists
        # medium-confidence fields as "uncertain", which flagged every photo. The platform
        # derives the real list from the confidence labels (see below).
        "model_uncertain_fields": [str(f) for f in as_list(d.get("uncertain_fields")) if str(f) in CONTENT_FIELDS],
        "model_human_review": as_bool(d.get("model_human_review")),
    }

    # --- rules the platform enforces regardless of what the model said -------
    if p["species"] == "none" or p["animal_count"] == 0:
        reasons.append("No animal visible in the photo.")
    if p["animal_count"] > 1:
        reasons.append(f"{p['animal_count']} animals in one photo - a profile must describe one animal.")
    if p["image_quality"] == "poor":
        reasons.append("Photo quality is poor.")
    for field, conf in (("Breed", p["breed_confidence"]), ("Age", p["age_confidence"]),
                        ("Personality", p["personality_confidence"])):
        if conf == "low":
            reasons.append(f"{field} confidence is low.")
    # Uncertain fields = the ones the model itself rated "low" (or said it cannot determine).
    p["uncertain_fields"] = [f for f, c, v in (
        ("breed_guess", p["breed_confidence"], p["breed_guess"]),
        ("age_range", p["age_confidence"], p["age_range"]),
        ("personality", p["personality_confidence"], p["personality"])) if c == "low" or v == NOT_DETERMINABLE]

    # Never let a high breed confidence stand on a photo we cannot trust.
    if p["breed_confidence"] == "high" and (p["image_quality"] == "poor" or p["animal_count"] != 1):
        p["breed_confidence"] = "low"
        reasons.append("Breed confidence lowered by rule (photo unsuitable for a breed call).")

    # Age unknown or only a low-confidence guess -> staff must set the fee; never guess a tier.
    if p["age_range"] == "unknown" or p["age_confidence"] == "low":
        if p["fee_tier"] != TIER_UNKNOWN:
            reasons.append("Fee tier left for staff: the age estimate is not reliable.")
        p["fee_tier"] = TIER_UNKNOWN
        p["fee_tier_reason"] = "Age could not be estimated reliably from the photo, so staff must set the tier."

    p["fee_amount"] = FEE_TIERS.get(p["fee_tier"])
    p["human_review"] = bool(reasons)
    # de-duplicate, keep order; add the model's own wording as supporting context when flagged
    p["review_reasons"] = list(dict.fromkeys(reasons + (model_reasons if reasons else [])))
    p["model_note"] = "" if reasons else "; ".join(model_reasons)
    return p
