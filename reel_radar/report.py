"""Playbook: every video, every creator, outliers, and You vs Them."""
import html, json
from pathlib import Path
from statistics import median

METRICS = [  # key, label, better ("high"/"low"/None)
    ("pacing.cuts_per_10s", "Cuts / 10s", "high"),
    ("pacing.cuts_first_3s", "Cuts in first 3s", "high"),
    ("pacing.avg_shot_s", "Avg shot (s)", "low"),
    ("pacing.wpm", "Words / min", "high"),
    ("pacing.first_word_at_s", "First word at (s)", "low"),
    ("pacing.duration_s", "Length (s)", None),
    ("audio.voice_vs_music_db", "Voice over music (dB)", None),
    ("audio.silences_over_0_3s", "Silences > 0.3s", "low"),
    ("audio.voice_energy_shifts_per_10s", "Voice energy shifts / 10s", "high"),
    ("captions.avg_words", "Caption words / line", "low"),
]


def get(d, path):
    for k in path.split("."):
        d = (d or {}).get(k) if isinstance(d, dict) else None
    return d


def load_studies(out, include_drafts=False):
    ss = [json.loads(p.read_text("utf-8")) for p in sorted((Path(out) / "study").glob("*.json"))]
    return ss if include_drafts else [s for s in ss if not s.get("creator", "").startswith("_")]


def outliers(studies):
    by = {}
    for s in studies:
        v = (s.get("stats") or {}).get("views")
        if v:
            by.setdefault(s["creator"], []).append(float(v))
    for s in studies:
        v = (s.get("stats") or {}).get("views")
        base = by.get(s["creator"])
        s["outlier_x"] = round(float(v) / median(base), 1) if v and base and median(base) else None
    return studies


def creator_table(studies):
    rows = {}
    for s in studies:
        rows.setdefault(s["creator"], []).append(s)
    table = {}
    for c, ss in rows.items():
        agg = {"videos": len(ss)}
        for key, label, _ in METRICS:
            vals = [get(s, key) for s in ss if isinstance(get(s, key), (int, float))]
            agg[key] = round(median(vals), 2) if vals else None
        hooks = [get(s, "analysis.hook_type") for s in ss if get(s, "analysis.hook_type")]
        agg["top_hook"] = max(set(hooks), key=hooks.count) if hooks else None
        table[c] = agg
    return table


def you_vs_them(table, me="me"):
    if me not in table:
        return []
    them = {k: v for k, v in table.items() if k != me}
    out = []
    for key, label, better in METRICS:
        vals = [v[key] for v in them.values() if v.get(key) is not None]
        mine = table[me].get(key)
        if not vals or mine is None:
            continue
        theirs = round(median(vals), 2)
        verdict = "—"
        if better and theirs:
            gap = (mine - theirs) / abs(theirs) if theirs else 0
            behind = gap < -0.15 if better == "high" else gap > 0.15
            ahead = gap > 0.15 if better == "high" else gap < -0.15
            verdict = "⚠ behind" if behind else ("✅ ahead" if ahead else "≈ level")
        out.append({"metric": label, "you": mine, "competitors": theirs, "verdict": verdict})
    return out


def build(out):
    out = Path(out)
    (out / "study").mkdir(parents=True, exist_ok=True)
    studies = outliers(load_studies(out))
    table = creator_table(studies)
    vs = you_vs_them(table)
    e = lambda v: html.escape(", ".join(map(str, v)) if isinstance(v, list) else ("" if v is None else str(v)))
    vid_cols = [("creator", "creator"), ("outlier_x", "outlier ×"), ("stats.views", "views"),
                ("pacing.duration_s", "len"), ("pacing.cuts_per_10s", "cuts/10s"),
                ("pacing.wpm", "wpm"), ("pacing.first_word_at_s", "1st word"),
                ("hook.spoken_3s", "spoken hook"), ("hook.on_screen_3s", "text hook"),
                ("analysis.hook_type", "hook type"), ("audio.has_music_bed", "music"),
                ("analysis.why_it_works", "why it works"), ("analysis.steal_this", "idea"), ("ctas", "CTAs")]
    vrows = "".join(
        f"<tr><td><img src='study/{s['id']}/hook.jpg' width=70 loading=lazy></td>"
        + "".join(f"<td>{e(get(s, k) if '.' in k else s.get(k))}</td>" for k, _ in vid_cols) + "</tr>"
        for s in studies)
    crow = "".join(f"<tr><td><b>{e(c)}</b></td><td>{a['videos']}</td>"
                   + "".join(f"<td>{e(a.get(k))}</td>" for k, _, _ in METRICS)
                   + f"<td>{e(a.get('top_hook'))}</td></tr>" for c, a in table.items())
    vsrow = "".join(f"<tr><td>{e(r['metric'])}</td><td>{e(r['you'])}</td><td>{e(r['competitors'])}</td>"
                    f"<td>{e(r['verdict'])}</td></tr>" for r in vs) or \
        "<tr><td colspan=4>Add your own videos to library/me/ to compare.</td></tr>"
    page = f"""<!doctype html><meta charset=utf-8><title>Reel Radar Playbook</title>
<style>body{{font:14px system-ui;margin:20px;background:#0d1117;color:#e6edf3}}h2{{margin-top:28px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #30363d;padding:6px;vertical-align:top}}
th{{background:#161b22;cursor:pointer;position:sticky;top:0}}input{{padding:6px;width:320px;background:#161b22;color:#eee;border:1px solid #30363d}}</style>
<h1>📡 Reel Radar Playbook</h1>
<h2>🆚 You vs Them (medians)</h2><table><tr><th>metric</th><th>you</th><th>competitors</th><th>verdict</th></tr>{vsrow}</table>
<h2>👥 Creators</h2><table><tr><th>creator</th><th>videos</th>{''.join(f'<th>{l}</th>' for _, l, _ in METRICS)}<th>top hook</th></tr>{crow}</table>
<h2>🎬 Videos ({len(studies)})</h2>
<input placeholder="search…" oninput="for(r of document.querySelectorAll('#v tbody tr'))r.hidden=!r.innerText.toLowerCase().includes(this.value.toLowerCase())">
<table id=v><thead><tr><th>hook</th>{''.join(f'<th onclick="s({i+1})">{l}</th>' for i, (_, l) in enumerate(vid_cols))}</tr></thead><tbody>{vrows}</tbody></table>
<script>function s(c){{const b=document.querySelector('#v tbody'),r=[...b.rows],d=b.dataset.d=b.dataset.d=='1'?'0':'1';
r.sort((x,y)=>{{let a=x.cells[c].innerText,z=y.cells[c].innerText,n=parseFloat(a)-parseFloat(z);
return (isNaN(n)?a.localeCompare(z):n)*(d=='1'?-1:1)}});r.forEach(x=>b.appendChild(x))}}</script>"""
    (out / "playbook.html").write_text(page, "utf-8")
    (out / "creators.json").write_text(json.dumps({"creators": table, "you_vs_them": vs}, indent=2), "utf-8")
    return out / "playbook.html"
