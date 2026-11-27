"""
📈 Retention import (YouTube Studio exports) + 🖼️ Thumbnail analysis.
Both work on files already on your PC. Nothing is downloaded or uploaded.
Made by Harsh Rajput · MIT
"""
import csv, io, json, re, statistics, zipfile
from pathlib import Path

from . import engine, guard

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


# ------------------------------------------------------------------ retention
def _num(x):
    x = str(x).strip().replace("%", "").replace(",", "")
    if ":" in x:                                     # 1:05 or 0:01:05
        s = 0.0
        for part in x.split(":"):
            s = s * 60 + float(part)
        return s
    return float(x)


def _read_rows(path):
    """CSV rows from a YouTube Studio export: the .zip itself or the 'Chart data.csv' inside it."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            pick = next((n for n in names if "chart" in n.lower()), names[0] if names else None)
            if not pick:
                raise ValueError("no CSV inside the zip")
            text = z.read(pick).decode("utf-8-sig", "replace")
    else:
        text = path.read_text("utf-8-sig", errors="replace")
    return list(csv.reader(io.StringIO(text)))


def parse_retention(path, duration=None):
    """Returns [(seconds, retention_pct)] sorted by time. Accepts position in %, 0-1 ratio, seconds or m:ss."""
    rows = [r for r in _read_rows(path) if any(c.strip() for c in r)]
    head_i = next((i for i, r in enumerate(rows) if any(re.search(r"position|time|elapsed|second", c, re.I) for c in r)), None)
    if head_i is None:
        raise ValueError("couldn't find a 'Video position' column: export the Audience retention chart from YouTube Studio")
    head = [c.strip() for c in rows[head_i]]
    pos_c = next(i for i, c in enumerate(head) if re.search(r"position|time|elapsed|second", c, re.I))
    ret_cs = [i for i, c in enumerate(head) if re.search(r"retention|watching|audience", c, re.I) and i != pos_c]
    if not ret_cs:
        raise ValueError("couldn't find an 'Audience retention' column")
    ret_c = next((i for i in ret_cs if not re.search(r"relative", head[i], re.I)), ret_cs[0])
    pts = []
    for r in rows[head_i + 1:]:
        try:
            pts.append((_num(r[pos_c]), _num(r[ret_c])))
        except (ValueError, IndexError):
            continue
    if len(pts) < 3:
        raise ValueError("not enough data points in the export")
    pts.sort()
    if max(v for _, v in pts) <= 1.5:                # ratios -> %
        pts = [(t, v * 100) for t, v in pts]
    ph = head[pos_c].lower()
    is_pct = bool(re.search(r"%|percent|ratio", ph)) or (
        "position" in ph and not re.search(r"sec|time", ph) and max(t for t, _ in pts) <= 100
        and ":" not in str(rows[head_i + 1][pos_c]))
    if is_pct:
        top = max(t for t, _ in pts)
        scale = 1 / 100 if top > 1.5 else 1.0        # 0-100 % or 0-1 ratio
        if not duration:
            raise ValueError("this export uses % of the video: add --video FILE or --duration SECONDS")
        pts = [(round(t * scale * duration, 2), v) for t, v in pts]
    return pts


def _at(pts, t):
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            return v0 if t1 == t0 else v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return pts[-1][1] if t > pts[-1][0] else pts[0][1]


def _context(study, t):
    """What happens on screen / in the audio around second t (from the video's study)."""
    if not study:
        return {}
    words = " ".join(w["w"] for w in study.get("words", []) if t - 2 <= w["s"] <= t + 1)
    cuts = study.get("cut_times", [])
    last_cut = max([c for c in cuts if c <= t], default=0.0)
    silent = any(s["s"] - 0.3 <= t <= s["e"] + 0.3 for s in study.get("audio", {}).get("silences", []))
    text = [o["text"] for o in study.get("on_screen_text", []) if abs(o["t"] - t) <= 1.5]
    return {"said": words, "seconds_since_cut": round(t - last_cut, 1), "silence": silent, "on_screen": text[:2]}


def retention(path, duration=None, study=None):
    pts = parse_retention(path, duration)
    dur = duration or pts[-1][0]
    start = pts[0][1] or 100.0
    step = max(1.0, dur * 0.03)
    drops, spikes = [], []
    t = pts[0][0]
    while t + step <= dur:
        d = _at(pts, t + step) - _at(pts, t)
        (drops if d < 0 else spikes).append((round(t, 1), round(d, 1)))
        t += step / 2
    drops = sorted(drops, key=lambda x: x[1])[:6]
    top_drops = []
    for t, d in drops:                                # keep the 3 biggest, at least 2 s apart
        if all(abs(t - k["at_s"]) >= 2 for k in top_drops) and len(top_drops) < 3 and t >= 1:
            top_drops.append({"at_s": t, "lost_pct": -d, **_context(study, t)})
    rewatch = [{"at_s": t, "gain_pct": d, **_context(study, t)} for t, d in sorted(spikes, key=lambda x: -x[1])[:2] if d >= 1]
    hold3 = _at(pts, min(3, dur)) / start * 100
    s = {"source": Path(path).name, "duration_s": round(dur, 1), "points": len(pts),
         "hook_hold_3s_pct": round(hold3, 1), "at_25_pct": round(_at(pts, dur * .25), 1),
         "at_50_pct": round(_at(pts, dur * .5), 1), "end_pct": round(pts[-1][1], 1),
         "avg_pct": round(statistics.mean(v for _, v in pts), 1), "biggest_drops": top_drops, "rewatch": rewatch,
         "curve": [[round(t, 1), round(v, 1)] for t, v in pts][:400]}
    s["fixes"] = retention_fixes(s)
    return s


def retention_fixes(s):
    f = []
    if s["hook_hold_3s_pct"] < 75:
        f.append(f"Only {s['hook_hold_3s_pct']:.0f}% stay past 3 s: show the payoff or a bold visual in frame 0 and say the hook in the first second.")
    for d in s["biggest_drops"]:
        why = []
        if d.get("silence"):
            why.append("dead air")
        if (d.get("seconds_since_cut") or 0) >= 4:
            why.append(f"no cut for {d['seconds_since_cut']:.0f} s")
        if not d.get("said") and not d.get("silence") and d.get("seconds_since_cut") is not None:
            why.append("nothing said")
        f.append(f"{d['lost_pct']:.0f}% leave around {d['at_s']:.0f} s"
                 + (f" ({', '.join(why)})" if why else "") + (f": \"{d['said'][:60]}\"" if d.get("said") else "")
                 + ". Tighten or add a re-hook here.")
    for r in s["rewatch"]:
        f.append(f"Rewatch spike at {r['at_s']:.0f} s: viewers replay this moment; do more of it in the next video.")
    if s["end_pct"] >= 70:
        f.append("Strong finish: most viewers reach the end. Try a loop ending to push replays.")
    return f


def import_retention(out, csv_path, video=None, creator="me", duration=None):
    """Attach a YouTube Studio retention export to a video's study (if analysed) and save it."""
    out = Path(out)
    study, sid = None, None
    if video:
        sid = engine.vid_id(video, creator)
        sf = out / "study" / f"{sid}.json"
        if sf.exists():
            study = json.loads(sf.read_text("utf-8"))
            duration = duration or study.get("pacing", {}).get("duration_s")
        elif Path(video).exists() and not duration:
            duration = engine.duration(video)
    guard._log("import", Path(csv_path).name, True, "local YouTube Studio export (read only)")
    s = retention(csv_path, duration, study)
    (out / "retention").mkdir(parents=True, exist_ok=True)
    name = sid or re.sub(r"[^A-Za-z0-9_-]", "_", Path(csv_path).stem)[:60]
    (out / "retention" / f"{name}.json").write_text(json.dumps(s, ensure_ascii=False, indent=2), "utf-8")
    if study:
        study["retention"] = {k: v for k, v in s.items() if k != "curve"}
        (out / "study" / f"{sid}.json").write_text(json.dumps(study, ensure_ascii=False, indent=2), "utf-8")
    return s, name, study is not None


# ------------------------------------------------------------------ thumbnails
def _ocr_boxes(img_path):
    engine.ocr([])                                   # loads the OCR model once
    if engine._ocr is None:
        return []
    return [(b, t, c) for b, t, c in engine._ocr_run(img_path) if c > 0.6 and len(t.strip()) > 1]


def thumbnail(path, tmp_dir):
    """Local, rule-based look at one thumbnail (no AI needed)."""
    import numpy as np
    from PIL import Image, ImageFilter
    im = Image.open(path).convert("RGB")
    w, h = im.size
    a = np.asarray(im.resize((640, int(640 * h / w)))).astype(float)
    gray = a @ [0.299, 0.587, 0.114]
    hsv = np.asarray(Image.fromarray(a.astype("uint8")).convert("HSV")).astype(float)
    rg, yb = a[..., 0] - a[..., 1], (a[..., 0] + a[..., 1]) / 2 - a[..., 2]
    colorful = float(np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean()))
    edges = np.asarray(Image.fromarray(gray.astype("uint8")).filter(ImageFilter.FIND_EDGES)).astype(float)
    clutter = float((edges > 40).mean())
    ys, xs = np.nonzero(edges > 40)                  # where the detail is = where the eye goes
    fx, fy = (float(xs.mean() / edges.shape[1]), float(ys.mean() / edges.shape[0])) if len(xs) else (.5, .5)
    thirds = min(abs(fx - x) for x in (1 / 3, 2 / 3)) + min(abs(fy - y) for y in (1 / 3, 2 / 3))
    pal = im.resize((100, int(100 * h / w))).quantize(5).convert("RGB").getcolors(10000)
    palette = ["#%02x%02x%02x" % c for _, c in sorted(pal, reverse=True)[:5]]
    boxes = _ocr_boxes(path)
    words = sum(len(t.split()) for _, t, _ in boxes)
    area = sum((max(p[0] for p in b) - min(p[0] for p in b)) * (max(p[1] for p in b) - min(p[1] for p in b)) for b, _, _ in boxes)
    small = Path(tmp_dir) / ("_small_" + Path(path).stem + ".png")       # how it looks on a phone feed
    im.resize((246, 138)).resize((738, 414)).save(small)
    small_words = {t.strip().lower() for _, t, _ in _ocr_boxes(small)}
    small.unlink(missing_ok=True)
    big_words = {t.strip().lower() for _, t, _ in boxes}
    legible = (len(big_words & small_words) / len(big_words)) if big_words else None
    m = {"file": str(path), "size": f"{w}x{h}", "aspect_ok": abs(w / h - 16 / 9) < 0.05 or abs(w / h - 9 / 16) < 0.05,
         "hd": min(w, h) >= 720, "brightness": round(float(gray.mean()), 1), "contrast": round(float(gray.std()), 1),
         "saturation": round(float(hsv[..., 1].mean() / 255), 2), "colorfulness": round(colorful, 1),
         "clutter": round(clutter, 3), "focus_xy": [round(fx, 2), round(fy, 2)], "focus_on_thirds": thirds < 0.12,
         "palette": palette, "text": " ".join(t for _, t, _ in boxes)[:120], "words": words,
         "text_area_pct": round(area / (w * h) * 100, 1), "mobile_legible": None if legible is None else round(legible, 2)}
    m["score"], m["fixes"] = thumb_score(m)
    return m


def thumb_score(m):
    pts, fixes = 100, []
    def miss(n, fix):
        nonlocal pts; pts -= n; fixes.append(fix)
    if not m["aspect_ok"]: miss(10, "Use 16:9 (1280x720) for long-form or 9:16 for Shorts.")
    if not m["hd"]: miss(5, "Export at least 1280x720 so it stays sharp.")
    if m["contrast"] < 45: miss(15, f"Low contrast ({m['contrast']}): darken the background or add a rim light on the subject.")
    if m["saturation"] < 0.3: miss(10, "Colours look flat: push saturation or add one bold accent colour.")
    if m["brightness"] < 60: miss(8, "Too dark for a phone feed: lift the exposure.")
    if m["clutter"] > 0.22: miss(12, "Busy image: cut to one subject + one idea, blur or simplify the background.")
    if m["words"] > 5: miss(12, f"{m['words']} words is a lot: keep thumbnail text to 1-4 words.")
    if m["mobile_legible"] is not None and m["mobile_legible"] < 0.6:
        miss(15, "Text is hard to read at phone size: bigger, bolder letters with an outline.")
    if not m["focus_on_thirds"] and m["clutter"] > 0.05:
        miss(5, "Main detail sits off the rule-of-thirds lines: move the subject or the text onto them.")
    return max(pts, 0), fixes or ["Looks strong. A/B test a variant with a different emotion or text."]


def thumbnails(out, files=None, library=None, me="me"):
    out = Path(out)
    lib = Path(library or guard.LIBRARY)
    if not files:
        files = sorted(p for p in lib.glob("*/thumbnails/*") if p.suffix.lower() in IMG_EXT)
    res, tmp = [], out / "thumbnails"
    tmp.mkdir(parents=True, exist_ok=True)
    for f in files:
        ok, why = guard.check_image(f)
        if not ok:
            print(f"[guard] skipped {f}: {why}"); continue
        m = thumbnail(f, tmp)
        rel = Path(f).resolve().relative_to(lib.resolve()) if guard._inside(f, lib) else Path(f)
        m["creator"] = rel.parts[0] if len(rel.parts) > 1 else "?"
        res.append(m)
    keys = ("contrast", "saturation", "colorfulness", "clutter", "words", "text_area_pct", "score")
    med = lambda rs, k: round(statistics.median(r[k] for r in rs), 2) if rs else None
    mine, theirs = [r for r in res if r["creator"] == me], [r for r in res if r["creator"] != me]
    vs = [{"metric": k, "you": med(mine, k), "competitors": med(theirs, k)} for k in keys]
    (out / "thumbnails.json").write_text(json.dumps({"thumbnails": res, "you_vs_them": vs}, ensure_ascii=False, indent=2), "utf-8")
    _thumb_page(out, res, vs, lib)
    return res, vs


def _thumb_page(out, res, vs, lib):
    import html, os
    e = lambda v: html.escape("" if v is None else str(v))
    rows = "".join(
        f"<tr><td><img src='{e(os.path.relpath(r['file'], out).replace(os.sep, '/'))}' width=180></td><td>{e(r['creator'])}</td>"
        f"<td><b>{r['score']}</b></td><td>{e(r['text'])} ({r['words']} words)</td><td>{r['contrast']} / {r['saturation']}</td>"
        f"<td>{r['clutter']}</td><td>{e(r['mobile_legible'])}</td>"
        f"<td>{''.join(f'<span style=background:{c}>&nbsp;&nbsp;&nbsp;</span>' for c in r['palette'])}</td>"
        f"<td>{'<br>'.join(e(x) for x in r['fixes'])}</td></tr>" for r in sorted(res, key=lambda r: -r["score"]))
    vrows = "".join(f"<tr><td>{e(v['metric'])}</td><td>{e(v['you'])}</td><td>{e(v['competitors'])}</td></tr>" for v in vs)
    (out / "thumbnails.html").write_text(f"""<!doctype html><meta charset=utf-8><title>HookRadar Thumbnails</title>
<style>body{{font:14px system-ui;margin:20px;background:#0d1117;color:#e6edf3}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #30363d;padding:6px;vertical-align:top}}th{{background:#161b22}}</style>
<h1>🖼️ Thumbnail check</h1><h2>🆚 You vs Them (medians)</h2>
<table><tr><th>metric</th><th>you</th><th>competitors</th></tr>{vrows}</table>
<h2>All thumbnails</h2><table><tr><th></th><th>creator</th><th>score</th><th>text</th><th>contrast / saturation</th>
<th>clutter</th><th>phone-size legible</th><th>palette</th><th>fixes</th></tr>{rows}</table>""", "utf-8")
