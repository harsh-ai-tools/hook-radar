"""Live state shared with the dashboard (written to out/live.json)."""
import json, time
from pathlib import Path

_path = Path("out/live.json")
_state = {"status": "idle", "progress": [0, 0], "video": None, "frames": [], "log": [],
          "analysis": None, "transcript": [], "settings": {}, "updated": 0}


def set_out(out):
    global _path
    _path = Path(out) / "live.json"


def _save():
    _state["updated"] = time.time()
    _path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_state, ensure_ascii=False), "utf-8")
    tmp.replace(_path)


def settings(**kw):
    _state["settings"].update(kw); _save()


def progress(done, total, status="running"):
    _state["progress"] = [done, total]; _state["status"] = status; _save()


def start_video(vid, creator, platform, file):
    _state.update(video={"id": vid, "creator": creator, "platform": platform, "file": file,
                         "started": time.time()}, frames=[], analysis=None, transcript=[])
    _save()


def frame(t, f):
    _state["frames"].append({"t": t, "src": Path(f).as_posix()}); _save()


def log(line):
    stamp = time.strftime("%H:%M:%S")
    _state["log"] = (_state["log"] + [f"{stamp} {line}"])[-80:]
    print(f"{stamp} {line}", flush=True)
    _save()


def transcript(words):
    _state["transcript"] = words[:400]; _save()


def analysis(a):
    _state["analysis"] = a; _save()
