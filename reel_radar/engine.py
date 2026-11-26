"""
Reel Radar engine: watches LOCAL videos only (never downloads).
Eyes  = scene cuts, key frames, contact sheet, on-screen text (OCR)
Ears  = transcript with word timing, loudness curve, silences, music bed, energy drops
Brain = fixed-schema analysis (+ optional local AI verdict via Ollama)
Made by Harsh Rajput · MIT
"""
import base64, json, os, re, shutil, subprocess, urllib.request
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")   # privacy: no usage pings
os.environ.setdefault("DO_NOT_TRACK", "1")
from pathlib import Path
from statistics import median

from . import guard, live

HOOK_TIMES = [0.0, 0.5, 1.0, 2.0, 3.0]
MAX_FRAMES = 24
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
CTA_RE = re.compile(
    r"\b(?:comment|dm me|dm)\s+[\"'“]?[A-Za-z0-9]{2,20}[\"'”]?(?=\s+(?:and|to|for|below|if)\b|[\s.!,]*$)"
    r"|\blink in (?:my )?bio\b|\b(?:follow|subscribe) for (?:part \d+|more)\b|\bpart \d+ (?:is )?(?:coming|tomorrow|next)\b"
    r"|\bsave this\b|\bshare this with\b", re.I)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")


def duration(video):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(video)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def resolution(video):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height", "-of", "csv=p=0", str(video)])
    return r.stdout.strip().replace(",", "x")


def vid_id(path, creator=""):
    raw = f"{creator}__{Path(path).stem}" if creator else Path(path).stem
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", raw)[:70]
    if safe != raw:                                   # non-English names: add a short unique code
        import hashlib
        safe += "_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:6]
    return safe


def has_audio(video):
    r = run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=index", "-of", "csv=p=0", str(video)])
    return bool(r.stdout.strip())


# ------------------------------------------------------------------ EYES
def scene_cuts(video, thresh):
    r = run(["ffmpeg", "-hide_banner", "-i", str(video), "-filter:v",
             f"select='gt(scene,{thresh})',showinfo", "-f", "null", "-"])
    return [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def grab(video, t, dest):
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}",
         "-i", str(video), "-frames:v", "1", "-q:v", "3", "-vf", "scale=360:-2", str(dest)])
    return dest if dest.exists() else None


def key_frames(video, cuts, dur, folder):
    times = [t for t in HOOK_TIMES if t < dur] + [min(c + 0.3, dur - 0.1) for c in cuts]
    times = sorted(set(round(t, 1) for t in times))[:MAX_FRAMES]
    frames = []
    for i, t in enumerate(times):
        f = grab(video, t, folder / f"f{i:02d}.jpg")
        if f:
            frames.append((t, f))
            live.frame(t, f)
            live.log(f"[eyes] frame {i + 1}/{len(times)} t={t:.1f}s")
    return frames


def contact_sheet(frames, dest, cols=4, w=240):
    from PIL import Image, ImageDraw
    if not frames:
        return None
    ims = [Image.open(f).convert("RGB") for _, f in frames]
    h = int(w * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), "black")
    d = ImageDraw.Draw(sheet)
    for i, (im, (t, _)) in enumerate(zip(ims, frames)):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(im.resize((w, h)), (x, y))
        d.rectangle([x, y, x + 50, y + 16], fill="black")
        d.text((x + 4, y + 2), f"{t:.1f}s", fill="yellow")
    sheet.save(dest, quality=85)
    return dest


_ocr = None
def _ocr_run(path):
    """Returns [(box, text, score)] for both rapidocr 3.x and old rapidocr_onnxruntime."""
    r = _ocr(str(path))
    if isinstance(r, tuple):                      # old API: (result, elapse)
        return [(b, t, float(c)) for b, t, c in (r[0] or [])]
    if getattr(r, "txts", None) is None:          # new API, nothing found
        return []
    boxes = r.boxes.tolist() if hasattr(r.boxes, "tolist") else r.boxes
    return [(b, t, float(c)) for b, t, c in zip(boxes, r.txts, r.scores)]


def ocr(frames):
    global _ocr
    if _ocr is None:
        try:
            from rapidocr import RapidOCR
        except ImportError:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except ImportError:
                live.log("[eyes] OCR not installed, skipping on-screen text")
                return []
        import logging
        for name in ("RapidOCR", "rapidocr"):
            logging.getLogger(name).setLevel(logging.ERROR)
        guard.log_network("modelscope.cn", "one-time OCR model download/check")
        _ocr = RapidOCR()
        for name in ("RapidOCR", "rapidocr"):
            logging.getLogger(name).setLevel(logging.ERROR)
    from PIL import Image
    seen, out = set(), []
    for t, f in frames:
        h = Image.open(f).height or 1
        for box, text, conf in _ocr_run(f):
            key = text.strip().lower()
            if conf > 0.6 and len(key) > 1 and key not in seen:
                seen.add(key)
                ys = [pt[1] for pt in box]
                out.append({"t": t, "text": text.strip(),
                            "y_pct": round(sum(ys) / len(ys) / h * 100)})
    return out


# ------------------------------------------------------------------ EARS
_wm = None
def transcribe(video, size, gpu=False, language=None):
    global _wm
    from faster_whisper import WhisperModel
    if _wm is None:
        guard.log_network("huggingface.co", f"one-time speech model download/check (whisper {size})")
        if gpu:
            try:
                _wm = WhisperModel(size, device="cuda", compute_type="float16")
                live.log("[ears] whisper on GPU")
            except Exception as e:
                live.log(f"[ears] GPU not available ({e}); using CPU")
        if _wm is None:
            _wm = WhisperModel(size, device="cpu", compute_type="int8")
            live.log("[ears] whisper on CPU")
    lang = language if language and language not in ("auto", "") else None
    segs, info = _wm.transcribe(str(video), word_timestamps=True, vad_filter=True, language=lang)
    words, text = [], []
    for s in segs:
        text.append(s.text.strip())
        for w in s.words or []:
            words.append({"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)})
    live.transcript(words)
    return {"language": info.language, "text": " ".join(text), "words": words}


def loudness_curve(video, step=0.5):
    """Momentary loudness (LUFS) every `step` seconds, via ffmpeg ebur128."""
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn",
             "-af", "ebur128=peak=none", "-f", "null", "-"])
    pts = [(float(t), float(m)) for t, m in re.findall(r"t:\s*([\d.]+)\s+TARGET.*?M:\s*(-?[\d.]+)", r.stderr)]
    curve, nxt = [], 0.0
    for t, m in pts:
        if t >= nxt:
            curve.append((round(t, 1), max(m, -70.0)))
            nxt += step
    return curve


def silences(video, noise="-35dB", d=0.25):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn",
             "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [{"s": round(max(a, 0), 2), "e": round(b, 2)} for a, b in zip(starts, ends)]


def ears(video, words, dur):
    curve = loudness_curve(video)
    sil = silences(video)
    speaking = lambda t: any(w["s"] - 0.1 <= t <= w["e"] + 0.1 for w in words)
    bed = [m for t, m in curve if not speaking(t) and m > -60]
    voice = [m for t, m in curve if speaking(t) and m > -60]
    drops = []
    for i in range(2, len(curve)):
        prev = (curve[i - 1][1] + curve[i - 2][1]) / 2
        if prev - curve[i][1] >= 10 and curve[i][1] > -70:
            drops.append(curve[i][0])
    energy_shifts = 0
    for i in range(2, len(voice)):
        if abs(voice[i] - voice[i - 2]) >= 4:
            energy_shifts += 1
    out = {
        "music_bed_lufs": round(median(bed), 1) if bed else None,
        "has_music_bed": bool(bed) and bool(voice) and median(bed) > -45,
        "voice_lufs": round(median(voice), 1) if voice else None,
        "voice_vs_music_db": round(median(voice) - median(bed), 1) if bed and voice else None,
        "silences": sil,
        "silences_over_0_3s": sum(1 for s in sil if s["e"] - s["s"] > 0.3),
        "energy_drops_s": drops[:20],
        "voice_energy_shifts_per_10s": round(energy_shifts / dur * 10, 1) if dur else 0,
        "curve": curve,
    }
    live.log(f"[ears] music bed {out['music_bed_lufs']} LUFS · {len(sil)} silences · {len(drops)} drops")
    return out


# ------------------------------------------------------------------ BRAIN
def pacing(dur, cuts, words):
    shots = [b - a for a, b in zip([0.0] + cuts, cuts + [dur])] if dur else []
    speech = (words[-1]["e"] - words[0]["s"]) if words else 0
    return {
        "duration_s": round(dur, 1),
        "cuts": len(cuts),
        "cuts_per_10s": round(len(cuts) / dur * 10, 1) if dur else 0,
        "cuts_first_3s": sum(1 for c in cuts if c < 3),
        "avg_shot_s": round(sum(shots) / len(shots), 2) if shots else None,
        "longest_shot_s": round(max(shots), 2) if shots else None,
        "words": len(words),
        "wpm": round(len(words) / speech * 60) if speech > 0 else 0,
        "first_word_at_s": words[0]["s"] if words else None,
    }


def hook(words, ocr_lines, cuts):
    spoken = " ".join(w["w"] for w in words if w["s"] < 3.0)
    on_screen = " / ".join(o["text"] for o in ocr_lines if o["t"] <= 3.0)
    return {"spoken_3s": spoken, "on_screen_3s": on_screen,
            "visual_change_in_first_1s": any(c <= 1.05 for c in cuts),
            "text_on_frame_0": any(o["t"] == 0.0 for o in ocr_lines)}


def captions(ocr_lines):
    if not ocr_lines:
        return {"present": False}
    lens = [len(o["text"].split()) for o in ocr_lines]
    ys = [o["y_pct"] for o in ocr_lines]
    return {"present": True, "avg_words": round(sum(lens) / len(lens), 1),
            "median_y_pct": median(ys), "lines_seen": len(ocr_lines)}


def ctas(*texts):
    found = set()
    for t in texts:
        for m in CTA_RE.finditer(t or ""):
            found.add(m.group(0).strip())
    return sorted(found)


PROMPT = """You analyse short-form videos (Shorts/Reels/TikToks) for a creator.
The image is a contact sheet of key frames (timestamps in yellow).
Transcript: {tr}
On-screen text: {ocr}
Pacing: {m}
Audio: {a}
Reply ONLY with JSON with exactly these keys:
hook_type (one of: question, shock-fact, cold-open, myth-bust, numbered-promise, contradiction, visual-first, other),
hook_summary, visual_hook (what moves/appears in frame 0), format (talking-head, animation, b-roll-montage, map, slideshow, screen-record, other),
visual_style, editing_techniques (list), caption_style, story_beats (list of short beats in order),
re_hooks (list of seconds where attention is re-grabbed), ending (loop, cliffhanger, cta, payoff, fade),
cta, why_it_works (one line), steal_this (one line idea to reuse WITHOUT copying words)."""


def ai_verdict(model, sheet, tr, ocr_lines, m, a, host):
    img = base64.b64encode(Path(sheet).read_bytes()).decode()
    body = {"model": model, "stream": False, "format": "json", "images": [img],
            "prompt": PROMPT.format(tr=tr["text"][:3000],
                                    ocr="; ".join(o["text"] for o in ocr_lines)[:1500],
                                    m=json.dumps(m), a=json.dumps({k: v for k, v in a.items() if k != "curve"}))}
    req = urllib.request.Request(f"{host}/api/generate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    live.log(f"[brain] asking {model} for verdict…")
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(json.loads(r.read())["response"])


def analyse(video, creator, platform, out, opts):
    """Analyse one local video file. Returns the full study dict."""
    video = Path(video)
    vid = vid_id(video, creator)
    folder = out / "study" / vid
    folder.mkdir(parents=True, exist_ok=True)
    live.start_video(vid, creator, platform, str(video))
    dur = duration(video)
    res = resolution(video)
    live.log(f"[probe] {video.name} · {dur:.1f}s · {res}")
    cuts = scene_cuts(video, opts.scene)
    live.log(f"[eyes] scene detect: {len(cuts)} cuts ({len(cuts) / dur * 10 if dur else 0:.1f}/10s)")
    frames = key_frames(video, cuts, dur, folder)
    sheet = contact_sheet(frames, folder / "contact_sheet.jpg")
    if frames:
        shutil.copy(frames[0][1], folder / "hook.jpg")
    ocr_lines = [] if opts.no_ocr else ocr(frames)
    live.log(f"[eyes] on-screen text: {len(ocr_lines)} lines")
    if has_audio(video):
        tr = transcribe(video, opts.whisper, getattr(opts, "gpu", False), getattr(opts, "language", None))
        live.log(f"[ears] transcript: {len(tr['words'])} words · lang={tr['language']}")
        a = ears(video, tr["words"], dur)
    else:
        live.log("[ears] no audio track: skipping transcript and audio analysis")
        tr = {"language": None, "text": "", "words": []}
        a = {"has_music_bed": False, "silences": [], "energy_drops_s": [], "curve": []}
    m = pacing(dur, cuts, tr["words"])
    study = {
        "id": vid, "creator": creator, "platform": platform, "file": str(video),
        "resolution": res, "hook": hook(tr["words"], ocr_lines, cuts), "pacing": m,
        "audio": a, "captions": captions(ocr_lines), "cut_times": cuts,
        "on_screen_text": ocr_lines, "transcript": tr["text"], "language": tr["language"],
        "words": tr["words"],
        "ctas": ctas(tr["text"], " ".join(o["text"] for o in ocr_lines)),
        "stats": opts.stats.get(video.name, {}),
    }
    if opts.ollama and sheet and not guard.check_ai_host(opts.ollama_host, getattr(opts, "allow_remote_ai", False))[0]:
        live.log("[guard] AI verdict skipped: AI host is not this PC (use --allow-remote-ai to override)")
    elif opts.ollama and sheet:
        try:
            study["analysis"] = ai_verdict(opts.ollama, sheet, tr, ocr_lines, m, a, opts.ollama_host)
            study["analysis_note"] = "AI draft: verify names/quotes before using."
        except Exception as e:
            study["analysis_error"] = str(e)
            live.log(f"[brain] AI verdict failed: {e}")
    (out / "study" / f"{vid}.json").write_text(json.dumps(study, ensure_ascii=False, indent=2), "utf-8")
    live.analysis({k: study[k] for k in ("hook", "pacing", "captions", "ctas")} |
                  {"audio": {k: v for k, v in a.items() if k != "curve"}} |
                  ({"analysis": study["analysis"]} if "analysis" in study else {}))
    live.log(f"[done] wrote study/{vid}.json")
    return study
