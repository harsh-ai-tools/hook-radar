"""
🧠 Mastermind: learns how competitors write, show and hook, and turns it into YOUR plan.
  patterns()  - per-creator style + what winning (outlier) videos do differently
  brief()     - next-video brief from the winners' patterns
  precheck()  - grade a draft video before you post it
  trends()    - rising words/topics in your niche, weighted by performance
  comment_ideas() - viewer questions from pasted comments -> video ideas
  weekly()    - one report with everything
Made by Harsh Rajput · MIT
"""
import json, re, time
from collections import Counter
from pathlib import Path
from statistics import median

from . import guard, report

STOP = set("""a an the and or but so to of in on at for with from by is are was were be been it its this that these
those you your i we they he she them his her our my me us not no yes do does did have has had will would can could
just very really what which who whom how why when where there here than then as if about into over after before up
down out off again all any some more most such only own same too s t don now get got like one two three""".split())

HOOK_TEMPLATES = {
    "myth-bust": "Everyone thinks [common belief]. That's wrong: [surprising truth].",
    "shock-fact": "[Shocking number or fact] and almost nobody knows why.",
    "cold-open": "Start mid-action: [the most intense moment], then rewind.",
    "question": "What if [unexpected situation]? Here's what actually happened.",
    "numbered-promise": "[N] things about [topic] nobody told you. Number [best] is wild.",
    "contradiction": "[A] should have won. Instead, [B] did, because of [twist].",
    "visual-first": "Open on [striking visual] with no words for 0.5s, then one line of text.",
    "other": "Start with the payoff, then explain how it happened.",
}


def _studies(out):
    return report.outliers(report.load_studies(Path(out)))


def _winners(studies, me="me"):
    comp = [s for s in studies if s["creator"] != me]
    scored = [s for s in comp if s.get("outlier_x")]
    if len(scored) >= 4:
        cut = sorted(s["outlier_x"] for s in scored)[int(len(scored) * 0.75)]
        return [s for s in scored if s["outlier_x"] >= cut], comp
    return comp, comp          # no view data yet: learn from all competitors


def _med(ss, key):
    v = [report.get(s, key) for s in ss if isinstance(report.get(s, key), (int, float))]
    return round(median(v), 2) if v else None


def patterns(out, me="me"):
    studies = _studies(out)
    by = {}
    for s in studies:
        by.setdefault(s["creator"], []).append(s)
    creators = {}
    for c, ss in by.items():
        hooks = Counter(report.get(s, "analysis.hook_type") or "unknown" for s in ss)
        first = Counter((s["words"][0]["w"].lower().strip(".,!?") if s.get("words") else "") for s in ss)
        creators[c] = {
            "videos": len(ss),
            "hook_types": dict(hooks.most_common()),
            "opens_with_question": sum(1 for s in ss if "?" in (report.get(s, "hook.spoken_3s") or "")) ,
            "text_on_frame_0_pct": round(100 * sum(1 for s in ss if report.get(s, "hook.text_on_frame_0")) / len(ss)),
            "music_pct": round(100 * sum(1 for s in ss if report.get(s, "audio.has_music_bed")) / len(ss)),
            "median_length_s": _med(ss, "pacing.duration_s"),
            "median_wpm": _med(ss, "pacing.wpm"),
            "median_cuts_per_10s": _med(ss, "pacing.cuts_per_10s"),
            "caption_y_pct": _med(ss, "captions.median_y_pct"),
            "common_first_words": [w for w, _ in first.most_common(3) if w],
            "ctas": dict(Counter(c for s in ss for c in s.get("ctas", [])).most_common(5)),
        }
    win, comp = _winners(studies, me)
    rest = [s for s in comp if s not in win]
    traits = []
    for key, label, better in report.METRICS:
        w, r = _med(win, key), _med(rest, key)
        if w is not None and r is not None and r and abs(w - r) / abs(r) >= 0.2:
            traits.append(f"{label}: winners {w} vs others {r}")
    wh = Counter(report.get(s, "analysis.hook_type") for s in win if report.get(s, "analysis.hook_type"))
    result = {"creators": creators, "winning_traits": traits,
              "winning_hook_types": dict(wh.most_common()),
              "winners": [{"id": s["id"], "creator": s["creator"], "outlier_x": s.get("outlier_x"),
                           "hook": report.get(s, "hook.spoken_3s")} for s in win[:15]]}
    (Path(out) / "patterns.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    return result


def targets(out, me="me"):
    win, _ = _winners(_studies(out), me)
    return {key: _med(win, key) for key, _, _ in report.METRICS}, win


def brief(out, topic, me="me"):
    t, win = targets(out, me)
    pat = patterns(out, me)
    hooks = list(pat["winning_hook_types"]) or ["myth-bust", "shock-fact", "numbered-promise"]
    length = t.get("pacing.duration_s") or 40
    wpm = t.get("pacing.wpm") or 160
    words = int(length * wpm / 60)
    lines = [f"# 🎬 Brief: {topic}", "",
             f"_Built from {len(win)} winning competitor videos. Ideas only: write it in your own words._", "",
             "## Targets", f"- Length: **~{length:.0f}s** (~{words} words at {wpm:.0f} wpm)",
             f"- Cuts: **{t.get('pacing.cuts_per_10s') or 3} per 10s** · first cut within **1s**",
             f"- First word by **{t.get('pacing.first_word_at_s') or 0.3}s** · no intro, no 'hey guys'",
             f"- Captions: **{t.get('captions.avg_words') or 3} words per line**",
             "", "## Hook options (pick one, then make it yours)"]
    for h in hooks[:4]:
        lines.append(f"- **{h}**: {HOOK_TEMPLATES.get(h, HOOK_TEMPLATES['other']).replace('[topic]', topic)}")
    lines += ["", "## Structure",
              "1. **0–1s** visual hook: something moves or changes in frame 0",
              "2. **0–3s** spoken + on-screen hook (same idea, different words)",
              "3. **3–8s** raise the stakes: why this matters",
              f"4. **~{length * 0.4:.0f}s** re-hook: music drop / new visual / 'but here's the twist'",
              "5. **body**: one fact per shot, visual reset every 2–3s",
              "6. **end**: payoff that loops back to the first line",
              "", "## Sound", "- Voice clearly above music (~10 dB)",
              "- Short silence or music drop right before each re-hook", "- Sound effect on every big visual change"]
    if pat["winning_traits"]:
        lines += ["", "## What winners do differently"] + [f"- {x}" for x in pat["winning_traits"]]
    if pat["winners"]:
        lines += ["", "## Study these winners"] + [f"- {w['creator']} · ×{w['outlier_x']} · \"{w['hook']}\"" for w in pat["winners"][:5]]
    d = Path(out) / "briefs"
    d.mkdir(parents=True, exist_ok=True)
    f = d / (re.sub(r"[^A-Za-z0-9]+", "-", topic.lower()).strip("-")[:50] + ".md")
    f.write_text("\n".join(lines) + "\n", "utf-8")
    return f


def precheck(study, out, me="me"):
    """Score a draft video (already analysed study dict) vs what winners do."""
    t, win = targets(out, me)
    fixes, score, n = [], 0, 0
    for key, label, better in report.METRICS:
        mine, goal = report.get(study, key), t.get(key)
        if better is None or mine is None or goal is None:
            continue
        n += 1
        good = mine >= goal * 0.85 if better == "high" else mine <= goal * 1.15 + 0.05
        score += good
        if not good:
            fixes.append(f"{label}: yours {mine}, winners {goal}. "
                         + ("Go higher." if better == "high" else "Go lower."))
    h = study.get("hook", {})
    checks = [(h.get("visual_change_in_first_1s"), "Add a visual change inside the first second"),
              (h.get("text_on_frame_0"), "Put hook text on frame 0"),
              (bool(h.get("spoken_3s")), "Say your hook in the first 3 seconds")]
    for ok, fix in checks:
        n += 1
        score += bool(ok)
        if not ok:
            fixes.append(fix)
    pct = round(100 * score / n) if n else 0
    res = {"score": pct, "fixes": fixes, "compared_with": len(win)}
    lines = [f"# ✅ Pre-post check: {study['id']}", f"**Score: {pct}/100** (vs {len(win)} winning videos)", ""]
    lines += [f"- 🔧 {x}" for x in fixes] or ["- Looks ready. Post it! 🚀"]
    d = Path(out) / "precheck"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{study['id']}.md").write_text("\n".join(lines) + "\n", "utf-8")
    return res


def trends(out, me="me", top=25):
    studies = _studies(out)
    score = Counter()
    now = time.time()
    for s in studies:
        if s["creator"] == me:
            continue
        w = s.get("outlier_x") or 1.0
        posted = (s.get("stats") or {}).get("posted")
        if posted:
            try:
                age_days = (now - time.mktime(time.strptime(posted[:10], "%Y-%m-%d"))) / 86400
                w *= 2.0 if age_days <= 30 else 1.0
            except ValueError:
                pass
        text = s.get("transcript", "") + " " + " ".join(o["text"] for o in s.get("on_screen_text", []))
        words = [x for x in re.findall(r"[a-zA-Zऀ-෿']{3,}", text.lower()) if x not in STOP]
        for x in set(words):
            score[x] += w
        for a, b in zip(words, words[1:]):
            score[f"{a} {b}"] += w * 1.5
    res = [{"term": k, "score": round(v, 1)} for k, v in score.most_common(top)]
    (Path(out) / "trends.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), "utf-8")
    return res


REQ_RE = re.compile(r"(make (?:a )?(?:video|part)|part \d|do one on|please (?:make|cover)|what about|can you)", re.I)


def comment_ideas(library, out):
    """Reads comments you pasted into library/<creator>/comments.txt (one per line)."""
    ideas = Counter()
    for f in Path(library).glob("*/comments*.txt"):
        for line in f.read_text("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if len(line) < 8:
                continue
            if line.endswith("?") or REQ_RE.search(line):
                ideas[line[:160]] += 1
    res = [{"idea": k, "times": v} for k, v in ideas.most_common(40)]
    (Path(out) / "comment_ideas.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), "utf-8")
    return res


def weekly(out, library, me="me"):
    out = Path(out)
    week_ago = time.time() - 7 * 86400
    studies = _studies(out)
    new = [s for s in studies if (out / "study" / f"{s['id']}.json").stat().st_mtime >= week_ago]
    pat = patterns(out, me)
    tr = trends(out, me, 10)
    ideas = comment_ideas(library, out)[:10]
    vs = json.loads((out / "creators.json").read_text("utf-8")).get("you_vs_them", []) if (out / "creators.json").exists() else []
    passed, findings = guard.head_audit(week_ago)
    L = [f"# 📅 Weekly Radar: {time.strftime('%d %b %Y')}", "",
         f"**{len(new)}** new videos analysed this week · **{len(studies)}** total", "",
         "## 🏆 Top outliers"]
    top = sorted([s for s in studies if s.get("outlier_x")], key=lambda s: -s["outlier_x"])[:5]
    L += [f"- ×{s['outlier_x']} · {s['creator']} · \"{report.get(s, 'hook.spoken_3s')}\"" for s in top] or ["- Add views to stats.csv to see outliers"]
    L += ["", "## 🆚 Where you're behind"]
    L += [f"- {r['metric']}: you {r['you']} vs {r['competitors']}" for r in vs if "behind" in r["verdict"]] or ["- Nothing major 🎉"]
    L += ["", "## 🧠 What winners do differently"] + ([f"- {x}" for x in pat["winning_traits"]] or ["- Need more videos to tell"])
    L += ["", "## 📈 Trending words in your niche", ", ".join(t["term"] for t in tr) or "-"]
    L += ["", "## 💬 Viewer questions → video ideas"] + ([f"- {i['idea']}" for i in ideas] or ["- Paste comments into library/<creator>/comments.txt"])
    L += ["", f"## 🔒 Security: {'PASS ✅' if passed else 'FAIL ❌'}"] + [f"- {f}" for f in findings]
    f = out / f"weekly_{time.strftime('%Y-%m-%d')}.md"
    f.write_text("\n".join(L) + "\n", "utf-8")
    return f
