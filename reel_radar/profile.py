"""Creator profile: niche, platforms, own handles, approved competitors (radar.json)."""
import json
from pathlib import Path

PROFILE = Path("radar.json")
LIBRARY = Path("library")

DEFAULT = {"niche": "", "language": "en", "platforms": ["youtube_shorts", "instagram_reels"],
           "me": {"name": "me", "handles": {}},
           "competitors": [],          # [{"name","platform","handle","why","approved":true}]
           "suggested": []}            # Scout suggestions waiting for approval


def load():
    if PROFILE.exists():
        return json.loads(PROFILE.read_text("utf-8"))
    return json.loads(json.dumps(DEFAULT))


def save(p):
    PROFILE.write_text(json.dumps(p, ensure_ascii=False, indent=2), "utf-8")


def ask(q, default=""):
    a = input(f"{q}{f' [{default}]' if default else ''}: ").strip()
    return a or default


def init(niche=None, language=None, platforms=None):
    p = load()
    if niche:                                     # non-interactive (used by the Claude setup wizard)
        p["niche"], p["language"] = niche, language or p["language"]
        if platforms:
            p["platforms"] = [x.strip() for x in platforms.split(",") if x.strip()]
        save(p)
        (LIBRARY / p["me"]["name"]).mkdir(parents=True, exist_ok=True)
        print(f"Saved radar.json (niche: {niche}). Put your videos in library/me/")
        return p
    print("\n=== Reel Radar setup ===  (press Enter to keep the value in brackets)\n")
    p["niche"] = ask("Your niche in a few words (e.g. 'animated history shorts')", p["niche"])
    p["language"] = ask("Main language of your videos (en, hi, pa, ...)", p["language"])
    plats = ask("Platforms (comma list: youtube_shorts, instagram_reels, tiktok, youtube_long)",
                ",".join(p["platforms"]))
    p["platforms"] = [x.strip() for x in plats.split(",") if x.strip()]
    for pl in p["platforms"]:
        h = ask(f"Your handle on {pl} (optional)", p["me"]["handles"].get(pl, ""))
        if h:
            p["me"]["handles"][pl] = h
    print("\nCompetitors you already know (one per line, 'platform handle', empty line to finish).")
    print("Example: instagram_reels @somecreator")
    while True:
        line = input("> ").strip()
        if not line:
            break
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            p["competitors"].append({"name": parts[1].lstrip("@"), "platform": parts[0],
                                     "handle": parts[1], "why": "added by you", "approved": True})
    save(p)
    for c in [p["me"]["name"]] + [c["name"] for c in p["competitors"]]:
        (LIBRARY / c).mkdir(parents=True, exist_ok=True)
    print("\nSaved radar.json. Put videos you already have on your PC into library/<creator>/")
    print("  your own videos  -> library/me/")
    print("  a competitor's   -> library/<their name>/   (optional stats.csv: file,views,likes,comments,posted)")
    print("Tip: ask Claude 'scout competitors for my niche' to get suggestions you can approve.\n")
    return p
