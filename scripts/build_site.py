"""T3.2 — Build the static site into docs/ (GitHub Pages).

Reads data/aggregates/*.json and emits self-contained, theme-aware HTML:
  docs/index.html        dashboard (stat tiles + SVG charts)
  docs/bills.html        client-side searchable/filterable bill table
  docs/methodology.html  rubric verbatim + models + disclaimer (REQUIRED)

Charts are server-rendered inline SVG (no JS chart library, no external requests),
using the validated dataviz palette: a diverging blue<->red scale for the -2..+2
axes and categorical hues for the derived buckets. All Hebrew is UTF-8 / RTL.

Usage:
    python scripts/build_site.py [--out docs]
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from _common import AGG_DIR, REPO_ROOT

RUBRIC_MD = REPO_ROOT / "skills" / "classification-rubric.md"
AXES = ("citizen_welfare", "corporate_benefit", "executive_power")
AXIS_LABELS = {
    "citizen_welfare": "Citizen welfare",
    "corporate_benefit": "Business &amp; regulation",
    "executive_power": "Executive power",
}
AXIS_MEANING = {
    "citizen_welfare": "+2 helps citizens · −2 harms",
    "corporate_benefit": "+2 helps business · −2 adds burdens",
    "executive_power": "+2 grows exec power · −2 grows checks",
}
BUCKET_ORDER = ["Citizen-oriented", "Corporate-oriented",
                "Power-concentrating", "Neutral/technical"]
BUCKET_COLOR = {  # categorical slots (identity), neutral is muted gray
    "Citizen-oriented": "var(--c-blue)",
    "Corporate-oriented": "var(--c-orange)",
    "Power-concentrating": "var(--c-violet)",
    "Neutral/technical": "var(--muted)",
}
# diverging blue<->red, gray midpoint; keys are axis scores -2..+2
SCORE_COLOR = {
    -2: "var(--d-neg2)", -1: "var(--d-neg1)", 0: "var(--d-zero)",
    1: "var(--d-pos1)", 2: "var(--d-pos2)",
}
SCORE_LABEL = {-2: "−2", -1: "−1", 0: "0", 1: "+1", 2: "+2"}

# ---- design tokens (validated dataviz palette; light + dark) ----------------
CSS = """
:root{
  --plane:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e;
  --muted:#898781; --grid:#e1e0d9; --border:rgba(11,11,11,.10);
  --c-blue:#2a78d6; --c-orange:#eb6834; --c-violet:#4a3aa7; --c-aqua:#1baf7a;
  --d-neg2:#a5211f; --d-neg1:#e34948; --d-zero:#c9c7c0; --d-pos1:#5598e7; --d-pos2:#184f95;
  --warn-bg:#fff6e6; --warn-bd:#fab219;
}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])){
  --plane:#0d0d0d; --surface:#1a1a19; --ink:#fff; --ink2:#c3c2b7;
  --muted:#898781; --grid:#2c2c2a; --border:rgba(255,255,255,.10);
  --c-blue:#3987e5; --c-orange:#d95926; --c-violet:#9085e9; --c-aqua:#199e70;
  --d-neg2:#e66767; --d-neg1:#d03b3b; --d-zero:#4b4b48; --d-pos1:#3987e5; --d-pos2:#86b6ef;
  --warn-bg:#2a2213; --warn-bd:#fab219;
}}
:root[data-theme=dark]{
  --plane:#0d0d0d; --surface:#1a1a19; --ink:#fff; --ink2:#c3c2b7;
  --muted:#898781; --grid:#2c2c2a; --border:rgba(255,255,255,.10);
  --c-blue:#3987e5; --c-orange:#d95926; --c-violet:#9085e9; --c-aqua:#199e70;
  --d-neg2:#e66767; --d-neg1:#d03b3b; --d-zero:#4b4b48; --d-pos1:#3987e5; --d-pos2:#86b6ef;
  --warn-bg:#2a2213; --warn-bd:#fab219;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.5}
a{color:var(--c-blue)}
.wrap{max-width:960px;margin:0 auto;padding:0 20px 64px}
header.site{border-bottom:1px solid var(--border);background:var(--surface)}
header.site .wrap{padding-top:18px;padding-bottom:14px}
h1{font-size:1.5rem;margin:.2rem 0}
nav a{margin-right:16px;text-decoration:none;font-weight:600}
nav a.active{color:var(--ink);border-bottom:2px solid var(--c-blue)}
.disclaimer{background:var(--warn-bg);border:1px solid var(--warn-bd);
  border-radius:8px;padding:12px 14px;margin:20px 0;font-size:.92rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:22px 0}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px}
.tile .n{font-size:2rem;font-weight:700}
.tile .l{color:var(--ink2);font-size:.85rem}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:18px;margin:18px 0}
.card h2{font-size:1.05rem;margin:.1rem 0 .3rem}
.card .sub{color:var(--ink2);font-size:.85rem;margin-bottom:14px}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:.82rem;color:var(--ink2);margin-top:10px}
.legend .sw{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:-1px}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--grid);vertical-align:top}
th{color:var(--ink2);font-weight:600;cursor:default}
td.he{direction:rtl;text-align:right;font-size:.95rem}
.chip{display:inline-block;min-width:26px;text-align:center;border-radius:6px;
  padding:1px 6px;font-variant-numeric:tabular-nums;color:#fff;font-size:.8rem;font-weight:600}
.bkt{display:inline-block;border-radius:6px;padding:1px 7px;font-size:.76rem;
  border:1px solid var(--border);margin:1px 2px}
.controls{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}
.controls input,.controls select{padding:8px 10px;border:1px solid var(--border);
  border-radius:8px;background:var(--surface);color:var(--ink);font:inherit}
.muted{color:var(--muted)}
footer{color:var(--ink2);font-size:.82rem;margin-top:30px;border-top:1px solid var(--border);padding-top:14px}
svg .bar:hover{opacity:.82}
pre.rubric{white-space:pre-wrap;background:var(--surface);border:1px solid var(--border);
  border-radius:8px;padding:16px;direction:ltr;overflow-x:auto;font-size:.85rem}
"""

THEME_JS = """
(function(){var k='knesset-theme';try{var t=localStorage.getItem(k);
if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}
window.toggleTheme=function(){var d=document.documentElement;
var cur=d.getAttribute('data-theme');var next=cur==='dark'?'light':'dark';
d.setAttribute('data-theme',next);try{localStorage.setItem(k,next);}catch(e){}};})();
"""


def esc(s: object) -> str:
    return html.escape(str(s if s is not None else ""))


def page(title: str, active: str, body: str) -> str:
    def nav(href, label, key):
        cls = ' class="active"' if key == active else ""
        return f'<a href="{href}"{cls}>{label}</a>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style>
<script>{THEME_JS}</script>
</head>
<body>
<header class="site"><div class="wrap">
<div style="display:flex;justify-content:space-between;align-items:center">
<h1>Knesset Legislation Analyzer</h1>
<button onclick="toggleTheme()" style="background:var(--surface);color:var(--ink);
 border:1px solid var(--border);border-radius:8px;padding:6px 10px;cursor:pointer">◐ theme</button>
</div>
<nav>{nav('index.html','Dashboard','index')}{nav('bills.html','Browse bills','bills')}{nav('methodology.html','Methodology','methodology')}</nav>
</div></header>
<div class="wrap">
{body}
</div>
</body></html>"""


DISCLAIMER = (
    '<div class="disclaimer"><strong>These scores are model-generated opinions,'
    ' not facts.</strong> Each bill is scored by an automated classifier against a'
    ' published rubric. Scores may be wrong or biased. See the '
    '<a href="methodology.html">methodology</a> for the model, the rubric, and'
    ' known limitations.</div>'
)


# ---- SVG chart helpers ------------------------------------------------------
def hbar_chart(pairs: list[tuple[str, int]], colors: list[str], *, width=620,
               row_h=30, pad_l=150) -> str:
    """Horizontal bar chart with direct value labels and hover titles."""
    maxv = max((v for _, v in pairs), default=1) or 1
    inner = width - pad_l - 60
    h = row_h * len(pairs) + 10
    out = [f'<svg viewBox="0 0 {width} {h}" width="100%" role="img" '
           f'style="max-width:{width}px">']
    for i, ((label, val), color) in enumerate(zip(pairs, colors)):
        y = i * row_h + 6
        bw = max(2, int(inner * val / maxv))
        out.append(f'<text x="{pad_l-8}" y="{y+13}" text-anchor="end" '
                   f'font-size="12" fill="var(--ink2)">{esc(label)}</text>')
        out.append(f'<rect class="bar" x="{pad_l}" y="{y}" width="{bw}" height="18" '
                   f'rx="4" fill="{color}"><title>{esc(label)}: {val}</title></rect>')
        out.append(f'<text x="{pad_l+bw+6}" y="{y+13}" font-size="12" '
                   f'fill="var(--ink)" font-weight="600">{val}</text>')
    out.append('</svg>')
    return "".join(out)


def stacked_axis_chart(dist: dict[str, dict[str, int]], *, width=640) -> str:
    """One 100%-stacked horizontal bar per axis, split by score -2..+2."""
    pad_l, row_h, gap = 215, 40, 2
    inner = width - pad_l - 20
    h = row_h * len(AXES) + 6
    out = [f'<svg viewBox="0 0 {width} {h}" width="100%" role="img" '
           f'style="max-width:{width}px">']
    for i, axis in enumerate(AXES):
        counts = dist[axis]
        total = sum(counts.values()) or 1
        y = i * row_h + 6
        out.append(f'<text x="4" y="{y+11}" font-size="12" '
                   f'fill="var(--ink2)">{AXIS_LABELS[axis]}</text>')
        out.append(f'<text x="4" y="{y+25}" font-size="10" '
                   f'fill="var(--muted)">{AXIS_MEANING[axis]}</text>')
        x = pad_l
        for score in range(-2, 3):
            v = counts.get(str(score), 0)
            if v == 0:
                continue
            seg = max(2, int(inner * v / total))
            out.append(
                f'<rect class="bar" x="{x}" y="{y}" width="{max(1,seg-gap)}" height="20" '
                f'rx="3" fill="{SCORE_COLOR[score]}">'
                f'<title>{AXIS_LABELS[axis]} score {SCORE_LABEL[score]}: {v} bills</title></rect>')
            if seg > 22:
                out.append(f'<text x="{x+ (seg-gap)/2}" y="{y+14}" text-anchor="middle" '
                           f'font-size="11" fill="#fff" font-weight="600">{v}</text>')
            x += seg
    out.append('</svg>')
    legend = '<div class="legend">' + "".join(
        f'<span><span class="sw" style="background:{SCORE_COLOR[s]}"></span>'
        f'score {SCORE_LABEL[s]}</span>' for s in range(-2, 3)) + '</div>'
    return "".join(out) + legend


# ---- pages ------------------------------------------------------------------
def load(name: str) -> dict:
    return json.loads((AGG_DIR / name).read_text(encoding="utf-8"))


def build_index() -> str:
    summary = load("summary.json")
    buckets = load("buckets.json")
    axis = load("axis_distributions.json")
    byk = load("by_knesset.json")

    lowpct = (100 * summary["low_confidence"] // summary["n_classified"]
              if summary["n_classified"] else 0)
    tiles = [
        (summary["n_bills"], "bills fetched"),
        (summary["n_classified"], "classified"),
        (summary["n_with_text"], "with full text"),
        (f"{lowpct}%", "low confidence (&lt;0.5)"),
    ]
    tiles_html = "".join(
        f'<div class="tile"><div class="n">{esc(n)}</div><div class="l">{l}</div></div>'
        for n, l in tiles)

    bucket_pairs = [(b, buckets.get(b, 0)) for b in BUCKET_ORDER]
    bucket_colors = [BUCKET_COLOR[b] for b in BUCKET_ORDER]
    bucket_legend = '<div class="legend">' + "".join(
        f'<span><span class="sw" style="background:{BUCKET_COLOR[b]}"></span>{esc(b)}</span>'
        for b in BUCKET_ORDER) + '</div>'

    kn_pairs = [(f"Knesset {k}", v) for k, v in
                sorted(byk.items(), key=lambda kv: int(kv[0]))]
    kn_colors = ["var(--c-blue)"] * len(kn_pairs)

    body = f"""{DISCLAIMER}
<div class="tiles">{tiles_html}</div>
<div class="card"><h2>Where bills land</h2>
<div class="sub">Derived buckets from the 3-axis scores. A bill can appear in more than one bucket.</div>
{hbar_chart(bucket_pairs, bucket_colors)}{bucket_legend}</div>
<div class="card"><h2>Score distribution per axis</h2>
<div class="sub">Share of classified bills at each score, −2 to +2.</div>
{stacked_axis_chart(axis)}</div>
<div class="card"><h2>Bills by Knesset term</h2>
<div class="sub">Coverage of the current dataset (a bounded sample; scale by re-running the sync).</div>
{hbar_chart(kn_pairs, kn_colors)}</div>
<footer>Generated {esc(summary['generated_utc'])} · model(s): {esc(', '.join(summary['models']) or 'none')}
· <a href="https://knesset.gov.il/Odata/ParliamentInfo.svc/">source: Knesset OData</a></footer>"""
    return page("Knesset Legislation Analyzer", "index", body)


def build_bills() -> str:
    bills = load("bills.json")
    data_json = json.dumps(bills, ensure_ascii=False)
    body = f"""{DISCLAIMER}
<div class="card"><h2>Browse bills</h2>
<div class="sub">{len(bills)} bills. Filter by text, Knesset term, or bucket. Scores are model opinions.</div>
<div class="controls">
<input id="q" type="search" placeholder="search Hebrew title…" oninput="render()">
<select id="knesset" onchange="render()"><option value="">All Knessets</option></select>
<select id="bucket" onchange="render()"><option value="">All buckets</option></select>
</div>
<div id="count" class="muted"></div>
<table><thead><tr>
<th>ID</th><th>Title</th><th>Knesset</th>
<th title="citizen welfare">CW</th><th title="business/regulation">BR</th>
<th title="executive power">EP</th><th>Conf.</th><th>Buckets</th></tr></thead>
<tbody id="rows"></tbody></table></div>
<footer><a href="methodology.html">How these scores are produced →</a></footer>
<script id="data" type="application/json">{data_json}</script>
<script>{BILLS_JS}</script>"""
    return page("Browse bills — Knesset Analyzer", "bills", body)


BILLS_JS = r"""
var BILLS = JSON.parse(document.getElementById('data').textContent);
var SC = {'-2':'var(--d-neg2)','-1':'var(--d-neg1)','0':'var(--d-zero)','1':'var(--d-pos1)','2':'var(--d-pos2)'};
var BC = {'Citizen-oriented':'var(--c-blue)','Corporate-oriented':'var(--c-orange)',
'Power-concentrating':'var(--c-violet)','Neutral/technical':'var(--muted)'};
function esc(s){var d=document.createElement('div');d.textContent=(s==null?'':s);return d.innerHTML;}
function chip(v){if(v==null)return '<span class="muted">–</span>';
return '<span class="chip" style="background:'+SC[String(v)]+'">'+(v>0?'+':'')+v+'</span>';}
function initFilters(){
 var ks=[...new Set(BILLS.map(b=>b.knesset_num).filter(x=>x!=null))].sort((a,b)=>a-b);
 var ksel=document.getElementById('knesset');
 ks.forEach(k=>ksel.insertAdjacentHTML('beforeend','<option>'+k+'</option>'));
 var bsel=document.getElementById('bucket');
 ['Citizen-oriented','Corporate-oriented','Power-concentrating','Neutral/technical']
  .forEach(b=>bsel.insertAdjacentHTML('beforeend','<option>'+b+'</option>'));
}
function render(){
 var q=document.getElementById('q').value.trim();
 var k=document.getElementById('knesset').value;
 var bk=document.getElementById('bucket').value;
 var rows=BILLS.filter(function(b){
  if(q && (b.title||'').indexOf(q)<0) return false;
  if(k && String(b.knesset_num)!==k) return false;
  if(bk && (b.buckets||[]).indexOf(bk)<0) return false;
  return true;});
 document.getElementById('count').textContent=rows.length+' of '+BILLS.length+' bills';
 document.getElementById('rows').innerHTML=rows.map(function(b){
  var a=b.axes||{};
  var conf=(b.confidence==null)?'<span class="muted">–</span>':b.confidence.toFixed(2);
  var bkts=(b.buckets||[]).map(function(x){return '<span class="bkt" style="border-color:'+BC[x]+'">'+esc(x)+'</span>';}).join('');
  var title=esc(b.title);
  if(b.rationale) title+='<br><span class="muted" style="font-size:.8rem">'+esc(b.rationale)+'</span>';
  return '<tr><td>'+b.bill_id+'</td><td class="he">'+title+'</td><td>'+esc(b.knesset_num)+
   '</td><td>'+chip(a.citizen_welfare)+'</td><td>'+chip(a.corporate_benefit)+
   '</td><td>'+chip(a.executive_power)+'</td><td>'+conf+'</td><td>'+bkts+'</td></tr>';}).join('');
}
initFilters();render();
"""


def build_methodology() -> str:
    summary = load("summary.json")
    rubric = RUBRIC_MD.read_text(encoding="utf-8") if RUBRIC_MD.exists() else "(rubric missing)"
    body = f"""{DISCLAIMER}
<div class="card"><h2>What this is</h2>
<p>An automated pipeline fetches bills from the official
<a href="https://knesset.gov.il/Odata/ParliamentInfo.svc/">Knesset OData API</a>,
extracts each bill's Hebrew text, and asks a classifier to score it on three
independent axes. <strong>Every score is a model-generated opinion</strong> and may
be wrong. Nothing here is legal advice or an official position.</p></div>

<div class="card"><h2>Models used</h2>
<p>Current scores were produced by: <strong>{esc(', '.join(summary['models']) or 'none')}</strong>.
The <code>heuristic-v0</code> backend is a deterministic keyword placeholder used to
validate the pipeline end-to-end; its scores are intentionally low-confidence and are
<em>not</em> a substitute for a real language-model pass (pending the Jetson/Haiku
quality gate). Rubric version and per-bill rationale are shown on each bill.</p></div>

<div class="card"><h2>Coverage</h2>
<p>{summary['n_classified']} of {summary['n_bills']} fetched bills classified;
{summary['n_with_text']} had extractable full text; {summary['low_confidence']} are
low-confidence (&lt;0.5). Knesset terms in this dataset:
{esc(', '.join(map(str, summary['knesset_terms'])))}. This is a bounded sample —
re-running the sync without a limit backfills more bills.</p></div>

<div class="card"><h2>Limitations</h2>
<ul>
<li>Legacy <code>.doc</code> bills (older Knessets) are not text-extracted yet, so they
are scored from title only (confidence capped at 0.4).</li>
<li>Hebrew PDF text is de-mojibaked from visual to logical order heuristically;
extraction can be imperfect.</li>
<li>The classifier scores the <em>text</em>, never the proposing party — but it can
still misread nuance, sarcasm, or cross-references to other laws.</li>
</ul></div>

<div class="card"><h2>Classification rubric (verbatim)</h2>
<pre class="rubric">{esc(rubric)}</pre></div>
<footer>Generated {esc(summary['generated_utc'])}.</footer>"""
    return page("Methodology — Knesset Analyzer", "methodology", body)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the static site into docs/.")
    ap.add_argument("--out", default=str(REPO_ROOT / "docs"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    (out / "index.html").write_text(build_index(), encoding="utf-8")
    (out / "bills.html").write_text(build_bills(), encoding="utf-8")
    (out / "methodology.html").write_text(build_methodology(), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")  # serve _-prefixed files as-is
    print(f"[build_site] wrote index.html, bills.html, methodology.html -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
