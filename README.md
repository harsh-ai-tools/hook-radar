<h1 align="center">📡 Reel Radar</h1>
<p align="center"><b>Free, local AI that studies your competitors' Shorts, Reels & TikToks and shows you exactly what to improve.</b><br>
Runs 100% on your PC · never downloads videos · no paid APIs</p>
<p align="center"><i>Made by Harsh Rajput · MIT License</i></p>

---

## ✨ Features

**👁️ Eyes: what it sees**
- **Scene cuts**: finds every cut and measures cuts per 10 seconds
- **Key frames**: grabs the opening seconds plus one frame after every cut
- **Contact sheet**: the whole video on one image, with timestamps
- **On-screen text**: reads captions and titles, and where they sit on screen
- **Visual hook**: checks if the picture changes in the first second and if frame 0 has text

**👂 Ears: what it hears**
- **Transcript**: every word with its exact time (GPU or CPU)
- **Spoken hook**: exactly what's said in the first 3 seconds
- **Voice pace**: words per minute and when the first word starts
- **Music bed**: detects background music and its loudness
- **Voice vs music**: how much louder the voice is than the music
- **Silences & drops**: dead air, and sudden audio drops used as re-hooks
- **Voice energy**: how often the speaker's energy changes

**🧠 Brain: what it learns**
- **Fixed analysis format**: every video graded on the same fields, so results compare cleanly
- **AI verdict** *(optional, free & local via Ollama)*: hook type, format, story beats, re-hooks, ending, why it works, an idea to reuse
- **CTA finder**: spots "comment X", "link in bio", "part 2" and more
- **Outlier score**: shows which videos beat their creator's usual views (×2, ×10…)

**📊 Reports**
- **You vs Them**: your numbers next to your competitors', marked ahead, level or behind
- **Creator profiles**: each competitor's typical pacing, length, hook style
- **Playbook**: a searchable, sortable table of every video with hook thumbnails

**🖥️ Live dashboard**
- Watch the AI work in real time: the video, frames, live log, analysis and transcript side by side

**🔒 Safe by design**
- Never downloads or uploads videos; it only reads files already in your `library/` folder
- Dashboard runs only on your own PC (127.0.0.1) and can't open files outside your library
- No logins, passwords or cookies stored

---

## 📥 How to download
Pick any one way. **Way 1 is the easiest.**

**Way 1: Download ZIP (no GitHub account needed)**
1. On this page, click the green **`<> Code`** button
2. Click **Download ZIP**
3. Right-click the downloaded file → **Extract All**
4. Open the extracted folder → done ✅

**Way 2: GitHub Desktop (easy updates later)**
1. Install [GitHub Desktop](https://desktop.github.com)
2. Click the green **`<> Code`** button → **Open with GitHub Desktop**
3. Choose a folder → **Clone**. To update later, click **Fetch origin**

**Way 3: Command line (for developers)**
```bash
git clone https://github.com/harsh-ai-tools/reel-radar.git
cd reel-radar
```

---

## 🚀 Quick start (Windows)
1. Install **Python 3.10+** (tick "Add to PATH") and **ffmpeg** (`winget install Gyan.FFmpeg`)
2. In this folder: `pip install -r requirements.txt`
3. `python radar.py init`: tell it your niche, platforms and competitors
4. Put videos you already have into folders:
   - your own → `library/me/`
   - a competitor's → `library/<their name>/` (optional `stats.csv`: `file,views,likes,comments,posted`)
5. `python radar.py watch`: the live dashboard opens at `http://127.0.0.1:8765`
6. Open `out/playbook.html` for You vs Them

*Optional AI verdict:* install [Ollama](https://ollama.com), run `ollama pull qwen2.5vl:7b`, then `python radar.py watch --ollama qwen2.5vl:7b`

## 🗺️ Roadmap
- [x] Eyes, ears, fixed analysis, live dashboard, You vs Them
- [ ] AI team: Manager, Security Guard, Head of Security, Scout, Mastermind, Scriptwriter, Editor, YouTube & Instagram managers
- [ ] Live browser watching (view only, no downloads)
- [ ] Mastermind: learns creators' script & visual style and writes your next brief
- [ ] Pre-post check, trend radar, comment mining, weekly report
- [ ] One-click installer + Claude plugin

> ⚠️ For study only. Don't re-upload other creators' videos or copy their scripts word for word. AI output is a draft: verify before using.
