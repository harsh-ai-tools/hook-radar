"""
Reel Radar engine: watches LOCAL videos only (never downloads).
Eyes  = scene cuts, key frames, contact sheet, on-screen text (OCR)
Ears  = transcript with word timing, loudness curve, silences, music bed, energy drops
Brain = fixed-schema analysis (+ optional local AI verdict via Ollama)
Made by Harsh Rajput · MIT
"""
import base64, json, os, re, shutil, subprocess, unicodedata, urllib.request
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")   # privacy: no usage pings
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")      # harmless Windows notice, hide it
os.environ.setdefault("HF_HUB_VERBOSITY", "error")
import warnings
warnings.filterwarnings("ignore", module="huggingface_hub")
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


def file_hash(path, chunk=1 << 20):
    """Fast content fingerprint (size + first/last 1 MB): unchanged videos are never re-analysed."""
    import hashlib
    p = Path(path); n = p.stat().st_size; h = hashlib.sha1(str(n).encode())
    with open(p, "rb") as f:
        h.update(f.read(chunk))
        if n > chunk:
            f.seek(max(n - chunk, chunk)); h.update(f.read(chunk))
    return h.hexdigest()[:16]


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
    if _ocr is False:
        return []
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
        import socket
        old_to = socket.getdefaulttimeout(); socket.setdefaulttimeout(20)   # offline? don't hang
        try:
            _ocr = RapidOCR()
        except Exception as e:
            _ocr = False
            live.log(f"[eyes] OCR unavailable ({type(e).__name__}), skipping on-screen text; Claude can read the contact sheet")
        finally:
            socket.setdefaulttimeout(old_to)
        for name in ("RapidOCR", "rapidocr"):
            logging.getLogger(name).setLevel(logging.ERROR)
    from PIL import Image
    seen, out = set(), []
    for t, f in frames:
        h = Image.open(f).height or 1
        try:
            found = _ocr_run(f)
        except Exception as e:
            live.log(f"[eyes] OCR failed on a frame ({type(e).__name__}), skipped")
            continue
        for box, text, conf in found:
            key = text.strip().lower()
            if conf > 0.6 and len(key) > 1 and key not in seen:
                seen.add(key)
                ys = [pt[1] for pt in box]
                out.append({"t": t, "text": text.strip(),
                            "y_pct": round(sum(ys) / len(ys) / h * 100)})
    return out


# ------------------------------------------------------------------ EARS
def load_audio(video, sr=16000):
    """Mono 16 kHz float32 audio via ffmpeg (what Whisper expects)."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(video),
                        "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg could not read the audio: " + r.stderr.decode("utf-8", "ignore")[-200:])
    return np.frombuffer(r.stdout, np.float32).copy()


_wm, _wm_gpu = None, False


def _cuda_ready():
    """True if the CUDA libraries faster-whisper needs (cuBLAS 12 + cuDNN 9) can be loaded.
    Checked BEFORE using the GPU: a missing DLL otherwise crashes Python mid-transcript."""
    import ctypes, glob, sys, sysconfig
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() < 1:
            return False, "no NVIDIA GPU found"
    except Exception as e:
        return False, f"ctranslate2: {e}"
    site = Path(sysconfig.get_paths()["purelib"]) / "nvidia"          # pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
    if sys.platform == "win32":
        for d in glob.glob(str(site / "*" / "bin")):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        libs = ["cublas64_12.dll", "cudnn_ops64_9.dll"]
        load = ctypes.WinDLL
    else:
        for d in glob.glob(str(site / "*" / "lib")):
            os.environ["LD_LIBRARY_PATH"] = d + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        libs = [str(next(iter(glob.glob(str(site / "cublas/lib/libcublas.so.12"))), "libcublas.so.12")),
                str(next(iter(glob.glob(str(site / "cudnn/lib/libcudnn_ops.so.9"))), "libcudnn_ops.so.9"))]
        load = lambda n: ctypes.CDLL(n, mode=ctypes.RTLD_GLOBAL)
    for lib in libs:
        try:
            load(lib)
        except OSError:
            return False, f"{Path(lib).name} missing (install GPU support: INSTALL_WINDOWS.bat --gpu)"
    return True, "ok"


# Whisper often writes Punjabi in Devanagari. Gurmukhi sits exactly 0x100 above Devanagari in Unicode,
# so map letter by letter; the few signs Gurmukhi lacks get their nearest Gurmukhi sign.
_DEV2GUR_FIX = {"\u0943": "\u0a3f\u0a30", "\u090b": "\u0a30\u0a3f", "\u0937": "\u0a38\u0a3c", "\u0911": "\u0a13",
                "\u0949": "\u0a4b", "\u0945": "\u0a47", "\u0946": "\u0a47", "\u094a": "\u0a4b", "\u0912": "\u0a13",
                "\u090e": "\u0a0f", "\u090d": "\u0a0f", "\u0903": "", "\u0950": "\u0a74", "\u0964": "\u0964"}


def to_gurmukhi(text):
    out = []
    for ch in text:
        if ch in _DEV2GUR_FIX:
            out.append(_DEV2GUR_FIX[ch]); continue
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:
            g = chr(o + 0x100)
            out.append(g if unicodedata.name(g, "") else ch)   # unassigned in Gurmukhi: keep as is
        else:
            out.append(ch)
    return "".join(out)


# A short prompt in the right script helps Hindi punctuation/spelling. (Tested: a Gurmukhi prompt makes
# whisper small hallucinate on Punjabi, so Punjabi relies on to_gurmukhi() instead.)
_SCRIPT_PROMPT = {"hi": "नमस्ते। यह हिंदी में है।"}


def transcribe(video, size, gpu=False, language=None):
    global _wm, _wm_gpu
    from faster_whisper import WhisperModel
    if _wm is None:
        guard.log_network("huggingface.co", f"one-time speech model download/check (whisper {size})")
        if gpu:
            ok, why = _cuda_ready()
            if ok:
                try:
                    _wm, _wm_gpu = WhisperModel(size, device="cuda", compute_type="float16"), True
                    live.log("[ears] whisper on GPU")
                except Exception as e:
                    live.log(f"[ears] GPU not available ({e}); using CPU")
            else:
                live.log(f"[ears] GPU not available ({why}); using CPU")
        if _wm is None:
            _wm = WhisperModel(size, device="cpu", compute_type="int8")
            live.log("[ears] whisper on CPU")
    lang = language if language and language not in ("auto", "") else None
    audio = load_audio(video)                        # decode with ffmpeg: no PyAV version problems

    def run(model):
        segs, info = model.transcribe(audio, word_timestamps=True, vad_filter=True, language=lang,
                                      initial_prompt=_SCRIPT_PROMPT.get(lang))
        return list(segs), info                      # decode now so GPU errors surface here
    try:
        segs, info = run(_wm)
    except RuntimeError as e:                        # GPU failed mid-run: finish this video on CPU
        if not _wm_gpu:
            raise
        live.log(f"[ears] GPU error ({e}); switching to CPU")
        _wm, _wm_gpu = WhisperModel(size, device="cpu", compute_type="int8"), False
        segs, info = run(_wm)
    fix = to_gurmukhi if info.language == "pa" else (lambda t: t)
    words, text = [], []
    for s in segs:
        text.append(fix(s.text.strip()))
        for w in s.words or []:
            words.append({"w": fix(w.word.strip()), "s": round(w.start, 2), "e": round(w.end, 2)})
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


def _frames_db(audio, sr=16000, frame=0.02):
    import numpy as np
    n = int(sr * frame)
    k = len(audio) // n
    if k == 0:
        return np.array([]), frame
    rms = np.sqrt((audio[: k * n].reshape(k, n) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-9), frame


def ears(video, words, dur):
    """Sound design: music bed, voice level, silences, drops, energy changes."""
    import numpy as np
    curve = loudness_curve(video)
    sil = silences(video)
    db, step = _frames_db(load_audio(video))
    t = np.arange(len(db)) * step
    bed_db = voice_db = None
    if len(db):
        if words:
            span = (t >= words[0]["s"]) & (t <= words[-1]["e"])
            speech = np.zeros(len(db), bool)
            for w in words:
                speech |= (t >= w["s"]) & (t <= w["e"])
            # 2nd percentile of 20 ms frames = the tiny gaps between words (silent without a music bed)
            floor = np.percentile(db[span], 2) if span.any() else np.percentile(db, 2)
            voice_db = float(np.median(db[speech])) if speech.any() else None
        else:
            floor = float(np.percentile(db, 2))
        bed_db = float(floor)
    # music bed = a sound floor that never drops to silence under/between the words
    has_bed = bed_db is not None and bed_db > -45 and (voice_db is None or voice_db - bed_db < 30)
    drops = []
    for i in range(2, len(curve)):
        prev = (curve[i - 1][1] + curve[i - 2][1]) / 2
        if prev - curve[i][1] >= 10 and curve[i][1] > -70:
            drops.append(curve[i][0])
    voice = [m for tt, m in curve if any(w["s"] <= tt <= w["e"] for w in words) and m > -60]
    energy_shifts = sum(1 for i in range(2, len(voice)) if abs(voice[i] - voice[i - 2]) >= 4)
    out = {
        "has_music_bed": bool(has_bed),
        "music_bed_db": round(bed_db, 1) if has_bed else None,
        "voice_db": round(voice_db, 1) if voice_db is not None else None,
        "voice_vs_music_db": round(voice_db - bed_db, 1) if has_bed and voice_db is not None else None,
        "silences": sil,
        "silences_over_0_3s": sum(1 for x in sil if x["e"] - x["s"] > 0.3),
        "energy_drops_s": drops[:20],
        "voice_energy_shifts_per_10s": round(energy_shifts / dur * 10, 1) if dur else 0,
        "curve": curve,
    }
    live.log(f"[ears] music bed: {'yes, ' + str(out['music_bed_db']) + ' dB' if has_bed else 'none'} · "
             f"{len(sil)} silences · {len(drops)} drops")
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


def join_words(ws):
    text = " ".join(ws)
    text = re.sub(r"\s+([,.!?%:;)\]'’])", r"\1", text)       # no space before punctuation
    text = re.sub(r"(\d) ([,.]\d)", r"\1\2", text)
    return re.sub(r"([(\[]) ", r"\1", text).strip()


def hook(words, ocr_lines, cuts):
    spoken = join_words([w["w"] for w in words if w["s"] < 3.0])
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
        raw = json.loads(r.read()).get("response", "")
    return parse_ai_json(raw)


def parse_ai_json(raw):
    """Small local models sometimes wrap JSON in ```fences``` or add a sentence: take the {...} part."""
    try:
        return json.loads(raw)
    except ValueError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise ValueError(f"AI reply was not JSON: {raw[:120]!r}")
        return json.loads(m.group(0))


def watch_item(study):
    """Short card for the dashboard's 'Watched so far' list."""
    a, m = study.get("audio", {}), study.get("pacing", {})
    tags = [("talking" if study.get("words") else "no speech"), ("music" if a.get("has_music_bed") else "no music"),
            ("captions" if study.get("captions", {}).get("present") else "no captions"),
            ("fast cuts" if (m.get("cuts_per_10s") or 0) >= 3 else "slow cuts")]
    if study.get("analysis", {}).get("format"):
        tags.insert(0, study["analysis"]["format"])
    h = study.get("hook", {})
    return {"id": study["id"], "creator": study["creator"], "platform": study.get("platform", ""),
            "file": study["file"], "hook": h.get("spoken_3s") or h.get("on_screen_3s") or "",
            "duration": m.get("duration_s"), "tags": tags}


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
        try:
            tr = transcribe(video, opts.whisper, getattr(opts, "gpu", False), getattr(opts, "language", None))
            live.log(f"[ears] transcript: {len(tr['words'])} words · lang={tr['language']}")
        except Exception as e:                # offline first run / broken model: keep going without words
            live.log(f"[ears] speech-to-text skipped ({type(e).__name__}). First run needs internet once to fetch the Whisper model.")
            tr = {"language": None, "text": "", "words": []}
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
                  {"audio": {k: v for k, v in a.items() if k != "curve"}, "curve": a.get("curve", [])[:400]} |
                  ({"analysis": study["analysis"]} if "analysis" in study else {}))
    live.watched(watch_item(study))
    live.log(f"[done] wrote study/{vid}.json")
    return study
