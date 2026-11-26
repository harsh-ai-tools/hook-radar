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


def summary(out, studies):
    """out/summary.json: one tiny row per video, the only study data Claude needs to read."""
    keys = {"creator": "creator", "x": "outlier_x", "views": "stats.views", "len": "pacing.duration_s",
            "cuts10": "pacing.cuts_per_10s", "wpm": "pacing.wpm", "hook": "hook.spoken_3s",
            "text_hook": "hook.on_screen_3s", "music": "audio.has_music_bed", "captions": "captions.present"}
    rows = [{"id": s["id"]} | {k: get(s, v) for k, v in keys.items() if get(s, v) not in (None, "", [])}
            for s in studies]
    (out / "summary.json").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", "utf-8")


def build(out):
    out = Path(out)
    (out / "study").mkdir(parents=True, exist_ok=True)
    studies = outliers(load_studies(out))
    table = creator_table(studies)
    vs = you_vs_them(table)
    summary(out, studies)
    e = lambda v: html.escape(", ".join(map(str, v)) if isinstance(v, list) else ("" if v is None else str(v)))
    vid_cols = [("creator", "creator"), ("outlier_x", "outlier ×"), ("stats.views", "views"),
                ("pacing.duration_s", "len"), ("pacing.cuts_per_10s", "cuts/10s"),
                ("pacing.wpm", "wpm"), ("pacing.first_word_at_s", "1st word"),
                ("hook.spoken_3s", "spoken hook"), ("hook.on_screen_3s", "text hook"),
                ("analysis.hook_type", "hook type"), ("audio.has_music_bed", "music"),
                ("retention.hook_hold_3s_pct", "3s hold %"), ("retention.avg_pct", "avg retention %"),
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
<h1><svg width="30" height="30" style="vertical-align:-6px;margin-right:8px" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" xmlns:c2pa="http://c2pa.org/manifest"><defs><linearGradient id="s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#34d399" stop-opacity=".9"/><stop offset="1" stop-color="#34d399" stop-opacity="0"/></linearGradient></defs><circle cx="32" cy="32" r="30" fill="#0b1220" stroke="#3b82f6" stroke-width="3"/><circle cx="32" cy="32" r="20" fill="none" stroke="#3b82f6" stroke-opacity=".45" stroke-width="2"/><circle cx="32" cy="32" r="10" fill="none" stroke="#3b82f6" stroke-opacity=".45" stroke-width="2"/><path d="M32 32 L32 2 A30 30 0 0 1 58 17 Z" fill="url(#s)"/><line x1="32" y1="32" x2="58" y2="17" stroke="#34d399" stroke-width="2.5" stroke-linecap="round"/><circle cx="44" cy="16" r="3.5" fill="#34d399"/><circle cx="18" cy="38" r="3" fill="#60a5fa"/><circle cx="40" cy="46" r="3" fill="#fbbf24"/><circle cx="32" cy="32" r="2.5" fill="#e5e7eb"/><metadata><c2pa:manifest>AAAWgmp1bWIAAAAeanVtZGMycGEAEQAQgAAAqgA4m3EDYzJwYQAAABZcanVtYgAAAEdqdW1kYzJtYQARABCAAACqADibcQN1cm46YzJwYTozYjgxOTZlNi1kNGYzLTQzNzYtOTM3My02ZTNlYTY4ODU2ZjQAAAADl2p1bWIAAAApanVtZGMyYXMAEQAQgAAAqgA4m3EDYzJwYS5hc3NlcnRpb25zAAAAALxqdW1iAAAARGp1bWRjYm9yABEAEIAAAKoAOJtxE2MycGEuaW5ncmVkaWVudC52MwAAAAAYYzJzaCyhP3Cr2QMeMIUAuqW+oGIAAABwY2JvcqNpZGM6Zm9ybWF0bWltYWdlL3N2Zyt4bWxqaW5zdGFuY2VJRHgseG1wOmlpZDowNmNiMTMzZS02YTE1LTQ5NWUtYjVlMS1iNTQwNWY3NTdhZTZscmVsYXRpb25zaGlwaHBhcmVudE9mAAAB4mp1bWIAAABBanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5hY3Rpb25zLnYyAAAAABhjMnNommjMglBYZZ+uRb9YWc5I5QAAAZljYm9yomdhY3Rpb25zgqJmYWN0aW9ua2MycGEub3BlbmVkanBhcmFtZXRlcnOha2luZ3JlZGllbnRzgaJjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFggZZPENNQTZPXAa2Bj6+ff7FpzqhLrOVIw8251vbvQfSGkZmFjdGlvbngdY29tLmFudGhyb3BpYy5jbGF1ZGUucHJvdmlkZWRqcGFyYW1ldGVyc6F4H2NvbS5hbnRocm9waWMub3JpZ2luLWNvbmZpZGVuY2VndW5rbm93bmtkZXNjcmlwdGlvbnhmQ2xhdWRlIHByb3ZpZGVkIHRoaXMgZmlsZSBhdCB0aGUgcmVxdWVzdCBvZiBhIHVzZXIgYW5kIG1heSBoYXZlIGNyZWF0ZWQgb3IgbW9kaWZpZWQgdGhlIGZpbGUgY29udGVudHMubXNvZnR3YXJlQWdlbnShZG5hbWVmQ2xhdWRlcmFsbEFjdGlvbnNJbmNsdWRlZPUAAADIanVtYgAAAEBqdW1kY2JvcgARABCAAACqADibcRNjMnBhLmhhc2guZGF0YQAAAAAYYzJzaF67IRcc1e5Ht77XjJ6ScTkAAACAY2JvcqVjYWxnZnNoYTI1NmNwYWRMAAAAAAAAAAAAAAAAZGhhc2hYIHGZFscqQnG/XLYNmvMoQfdPp0OW+LkN/ckM3UBz08pXZG5hbWVuanVtYmYgbWFuaWZlc3RqZXhjbHVzaW9uc4GiZXN0YXJ0GQOuZmxlbmd0aBkeBAAAAj5qdW1iAAAAJ2p1bWRjMmNsABEAEIAAAKoAOJtxA2MycGEuY2xhaW0udjIAAAACD2Nib3KlY2FsZ2ZzaGEyNTZpc2lnbmF0dXJleE1zZWxmI2p1bWJmPS9jMnBhL3VybjpjMnBhOjNiODE5NmU2LWQ0ZjMtNDM3Ni05MzczLTZlM2VhNjg4NTZmNC9jMnBhLnNpZ25hdHVyZWppbnN0YW5jZUlEeCx4bXA6aWlkOmM5Yjk4NDA1LTQ0ZjgtNDk1Yy1hZGRmLTRmODdkNDZmNTI3MHJjcmVhdGVkX2Fzc2VydGlvbnODomN1cmx4LXNlbGYjanVtYmY9YzJwYS5hc3NlcnRpb25zL2MycGEuaW5ncmVkaWVudC52M2RoYXNoWCBlk8Q01BNk9cBrYGPr59/sWnOqEus5UjDzbnW9u9B9IaJjdXJseCpzZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmFjdGlvbnMudjJkaGFzaFggeD+MUQviO4ljyo9G65+1WV34pffsavC3IFg+M5QHOVyiY3VybHgpc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5oYXNoLmRhdGFkaGFzaFgguJ/ukg/bS08tBamDcOxJya/03udMnbL0l9hmh0Lr2At0Y2xhaW1fZ2VuZXJhdG9yX2luZm+jZG5hbWVvQW50aHJvcGljIEZpbGVzZ3ZlcnNpb25lMS4wLjBrc3BlY1ZlcnNpb25lMi40LjAAABA4anVtYgAAAChqdW1kYzJjcwARABCAAACqADibcQNjMnBhLnNpZ25hdHVyZQAAABAIY2JvctKEWQISogEmGCFZAgowggIGMIIBjaADAgECAhRA5aAK7sI50L64g/oGQgU9Z1UTADAKBggqhkjOPQQDAzBJMRcwFQYDVQQKEw5BbnRocm9waWMsIFBCQzEuMCwGA1UEAxMlQW50aHJvcGljIENvbnRlbnQgQ3JlZGVudGlhbHMgUm9vdCBDQTAeFw0yNjA4MDcxODQzNTZaFw0yODA4MDYxOTQzNTZaMEQxFzAVBgNVBAoTDkFudGhyb3BpYywgUEJDMSkwJwYDVQQDEyBBbnRocm9waWMgQ2xhdWRlIENvbnRlbnQgU2lnbmluZzBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABJh6CmvLUBgFFNU0vUKlOVtE6djd17L5SuwX0LemFisBM3dkd/3cyjxFA3Qo5S46fX0/ihY0VZ7mfb9KF703t5OjWDBWMA4GA1UdDwEB/wQEAwIHgDAVBgNVHSUEDjAMBgorBgEEAYPoXgIBMAwGA1UdEwEB/wQCMAAwHwYDVR0jBBgwFoAUzlHiBIFOZFsj+OPEz5o+nMHXXMIwCgYIKoZIzj0EAwMDZwAwZAIwMXMdFJ4BetLLVY7ORuE9noqbbAZOZn/aArXyTwFAZfKrPzxF2vPoJNf1+UCdg1XGAjBwX1zd9WGqYkqmL5SFqw1QySjr1zJfpJM9+1rdDwSPLMOPOjKuiXjoU/pUUeG9RwmhY3BhZFkNngAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPZYQM1Vo8SllcX7Z1LWkRYZC/Q9ZTDbPT5+nMXZTQ1njI1xg1NopJiOtqqdzTRCTD+hfkpSN0ut9HV/0pm55vVZgaI=</c2pa:manifest></metadata></svg>
Reel Radar Playbook</h1>
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
