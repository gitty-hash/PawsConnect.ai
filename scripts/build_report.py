"""Build the design report PDF from docs/report/report_body.html + the appendix.

    python scripts/build_report.py --name "Your Name" --id "Your ID"

Output: docs/PawsConnect_Design_Report.pdf  (plus docs/report/report.html).
Needs `playwright` and Microsoft Edge (or Chrome): pip install playwright
The photo-results table in the appendix is computed from the recorded cache, so it
always matches what the app shows. The word count printed at the end covers the report
BODY only (sections 1-6); the appendix is excluded, as the assignment allows.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pawsconnect.features.profile import generate_profile  # noqa: E402
from pawsconnect.llm import LLMGateway  # noqa: E402

REPORT_DIR = ROOT / "docs" / "report"
SHOTS = "img"          # cropped copies are written to docs/report/img by prepare_images()

# bottom crop (pixels, original 2400-px-wide screenshots) removing sections that are not the point of the figure
CROPS = {"live_B_photo_to_profile_blurry.png": 2060, "live_D_pawstay_timeline_max.png": 2460}


def prepare_images() -> None:
    from PIL import Image
    out = REPORT_DIR / "img"
    out.mkdir(exist_ok=True)
    for f in (ROOT / "docs" / "screenshots").glob("*.png"):
        im = Image.open(f).convert("RGB")
        bottom = CROPS.get(f.name)
        if bottom:
            im = im.crop((0, 0, im.width, min(im.height, bottom)))
        im.save(out / f.name, optimize=True)
    banner = ROOT / "data" / "banners" / "cocoa_banner.png"
    if banner.exists():
        im = Image.open(banner).convert("RGB")
        im = im.resize((1600, int(im.height * 1600 / im.width)))
        im.save(out / "cocoa_banner.png", optimize=True)

CSS = """
@page { size: Letter; margin: 17mm 16mm 18mm 16mm; }
body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 10pt; line-height: 1.38; color: #222; }
h1 { font-size: 20pt; margin: 0 0 2pt 0; color: #3b2a1e; }
.sub { color: #6b5b4f; margin-bottom: 6pt; }
.meta { font-size: 9.5pt; margin: 6pt 0 10pt 0; padding: 6pt 9pt; background: #f6f1ea; border-radius: 6pt; }
.meta span.blank { display:inline-block; min-width: 105pt; border-bottom: 1px solid #555; }
h2 { font-size: 13.2pt; margin: 14pt 0 4pt 0; color: #7a3b17; border-bottom: 1px solid #e3d6c6; padding-bottom: 2pt; break-after: avoid; }
h3 { font-size: 11pt; margin: 10pt 0 3pt 0; color: #7a3b17; break-after: avoid; }
p { margin: 4pt 0 6pt 0; text-align: left; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 8pt 0; font-size: 8.8pt; break-inside: avoid; }
th { background: #f1e7da; text-align: left; padding: 3.5pt 5pt; border: 1px solid #ddcdb9; }
td { padding: 3.5pt 5pt; border: 1px solid #e5d9c9; vertical-align: top; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f4efe9; padding: 0 2pt; }
.appendix { margin-top: 10pt; }
figure { margin: 8pt 0 12pt 0; break-inside: avoid; text-align: center; }
figure img { max-width: 90%; max-height: 118mm; width: auto; height: auto; border: 1px solid #d9cdbd; }
figcaption { font-size: 8.8pt; color: #4b4037; text-align: left; margin: 4pt 6% 0 6%; }
.note { font-size: 9pt; color: #5a4c40; background: #fbf7f1; border-left: 3pt solid #d8b58c; padding: 4pt 8pt; margin: 6pt 0; }
.pb { break-before: page; }
"""


def photo_table() -> str:
    gw = LLMGateway("cached")
    rows = []
    for f in sorted((ROOT / "Testing_Images").glob("*.jpg")):
        p = generate_profile(gw, f.read_bytes())
        flag = "Yes" if p["human_review"] else "No"
        rows.append(
            f"<tr><td><code>{f.name}</code></td><td>{html.escape(p['species'])} x{p['animal_count']}</td>"
            f"<td>{html.escape(p['breed_guess'])} ({p['breed_confidence']})</td>"
            f"<td>{html.escape(p['age_range'])} ({p['age_confidence']})</td>"
            f"<td>{p['personality_confidence']}</td><td>{html.escape(p['fee_tier'].split(' - ')[0])}</td><td>{flag}</td></tr>")
    return ("<table><tr><th>Photo</th><th>Species</th><th>Breed guess (confidence)</th><th>Age (confidence)</th>"
            "<th>Personality conf.</th><th>Fee tier</th><th>Human review</th></tr>" + "".join(rows) + "</table>")


def _banner_meta() -> dict:
    import json
    p = ROOT / "data" / "banners" / "banner_meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def appendix(photo_rows: str) -> str:
    bm = _banner_meta()
    banner_tool = html.escape(bm.get("tool", "image model"))
    banner_prompt = html.escape(bm.get("prompt", ""))
    banner_date = html.escape(bm.get("generated", ""))
    return f"""
<div class="appendix">
<h2>7. Appendix (not counted in the word limit)</h2>

<h3>A. Live-mode evidence</h3>
<p>All three screenshots were taken on 2026-10-04 with the sidebar set to <b>Live (OpenAI API)</b> and the key read from the
<code>OPENAI_API_KEY</code> environment variable. The sidebar shows the live API call count and estimated cost for the session at the moment of capture.</p>

<figure><img src="{SHOTS}/live_B_photo_to_profile_blurry.png">
<figcaption><b>Figure A1 - Part B, live mode, hard case (blurry photo).</b> The vision model returns "not determinable" for breed and personality, no suggested names, low confidence on every field, Tier 0 ("staff to set") and five review reasons. Sidebar: 1 live call, est. $0.0007.</figcaption></figure>

<figure><img src="{SHOTS}/live_C2_counselor_judge_catch.png">
<figcaption><b>Figure A2 - Part C2, live mode, red-team scenario.</b> With the deliberately weakened persona, draft 1 says "yes, he is available for adoption!". The judge fails the honesty check, quotes the offending words, and the app regenerates once; draft 2 passes and is the reply the adopter would see. Sidebar: 5 live calls, est. $0.0012.</figcaption></figure>

<figure><img src="{SHOTS}/live_D_pawstay_timeline_max.png">
<figcaption><b>Figure A3 - Part D (PawStay), live mode, Max's four check-ins.</b> The timeline runs Needs Attention, Needs Attention (Worsening), Urgent, Urgent; the Day 14 card shows the adopter's words, the trend, quoted evidence from Day 14 and Day 7, the route (Welfare &amp; Safety Lead) and a staff-only action. The guardrail panel shows the judge's "no return recommendation" fail discarded because the quoted phrase was not in the text. Sidebar: 13 live calls, est. $0.0036.</figcaption></figure>

<figure><img src="{SHOTS}/cocoa_banner.png">
<figcaption><b>Figure A4 - Bonus: promotional banner for Cocoa</b>, generated with the OpenAI Images API (<code>gpt-image-1</code>, image edit of her CC0 photo) on 2026-10-04. Text is limited to the pet's name and one line, and the prompt forbids behaviour claims. In the app it is labelled "AI-generated" and needs staff approval before posting. Tool and prompt: Appendix B.</figcaption></figure>

<h3>B. Bonus banner: tool and prompt</h3>
<table>
<tr><th style="width:18%">Tool</th><td>{banner_tool}</td></tr>
<tr><th>Input</th><td>Testing_Images/dog_01.jpg (CC0 photo of the Labrador-type dog listed as Cocoa)</td></tr>
<tr><th>Settings</th><td>Size 1536x1024, quality medium, one image, generated {banner_date}</td></tr>
<tr><th>Prompt</th><td>{banner_prompt}</td></tr>
<tr><th>Note</th><td>Outside tool: the Chapter 2 labs use Stable Diffusion (SD-Turbo). OpenAI's image model was used instead because it renders short text reliably. The image is a draft; staff approve before posting.</td></tr>
</table>


</div>
"""


def count_words(body_html: str) -> int:
    s = re.sub(r"<!--.*?-->", "", body_html, flags=re.S)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'â€™\-\./%\$]*", s))


def build_html(name: str = "", sid: str = "") -> tuple[str, str]:
    """Return (full report HTML, body HTML). Used by the PDF and Word builders."""
    prepare_images()
    body = (REPORT_DIR / "report_body.html").read_text(encoding="utf-8")
    n = html.escape(name) if name else '<span class="blank"></span>'
    i = html.escape(sid) if sid else '<span class="blank"></span>'
    head = f"""
<h1>PawsConnect: an AI feature suite for a pet-adoption platform</h1>
<div class="sub">MIS 552 &middot; AI for Digital Platforms &middot; Homework 1 design report</div>
<div class="meta"><b>Student:</b> {n} &middot; <b>ID / section:</b> {i} &middot; <b>Date:</b> October 4, 2026</div>
"""
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><title>PawsConnect design report</title>"
           f"<style>{CSS}</style></head><body>{head}{body}{appendix(photo_table())}</body></html>")
    return doc, body


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="")
    ap.add_argument("--id", default="")
    args = ap.parse_args()
    doc, body = build_html(args.name, args.id)
    out_html = REPORT_DIR / "report.html"
    out_html.write_text(doc, encoding="utf-8")

    from playwright.sync_api import sync_playwright
    out_pdf = ROOT / "docs" / "PawsConnect_Design_Report.pdf"
    with sync_playwright() as p:
        browser = None
        for channel in ("msedge", "chrome"):
            try:
                browser = p.chromium.launch(channel=channel, headless=True)
                break
            except Exception:
                continue
        if browser is None:
            raise SystemExit("Install Microsoft Edge or Chrome (Playwright needs a Chromium browser).")
        page = browser.new_page()
        page.goto(out_html.as_uri())
        page.wait_for_timeout(1500)
        page.pdf(path=str(out_pdf), format="Letter", print_background=True, display_header_footer=True,
                 header_template="<div></div>",
                 footer_template="<div style='font-size:8px;width:100%;text-align:center;color:#777'>"
                                 "PawsConnect design report - page <span class='pageNumber'></span> of <span class='totalPages'></span></div>",
                 margin={"top": "17mm", "bottom": "18mm", "left": "16mm", "right": "16mm"})
        browser.close()
    print(f"Report body words (sections 1-6, tables included): {count_words(body)} (limit 1,200-1,800)")
    print(f"Wrote {out_pdf}")


if __name__ == "__main__":
    main()

