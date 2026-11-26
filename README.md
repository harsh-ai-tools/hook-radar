<p align="center"><img src="docs/banner.png" alt="Reel Radar" width="100%"></p>

<h1 align="center">📡 Reel Radar</h1>
<p align="center"><b>A free, local AI team that studies your competitors' Shorts, Reels & TikToks and tells you exactly what to make next.</b><br>
Runs 100% on your PC · never downloads videos · no paid APIs · works with Claude</p>
<p align="center"><i>Made by Harsh Rajput · MIT License</i></p>

---

## ⚙️ How it works
<p align="center"><img src="docs/how-it-works.png" alt="How Reel Radar works" width="100%"></p>

## 📸 See it in action
**Live dashboard**: watch the AI see, hear and grade each video in real time
<p align="center"><img src="docs/dashboard.png" alt="Live dashboard" width="100%"></p>

**Playbook**: You vs Them, creator profiles and every video in one page
<p align="center"><img src="docs/playbook.png" alt="Playbook report" width="100%"></p>

<sub>Screenshots use demo videos generated for testing.</sub>

---

## ✨ Features

**👁️ Eyes: what it sees**
- **Scene cuts**: every cut, cuts per 10 seconds, shot length
- **Key frames & contact sheet**: the opening seconds plus a frame after every cut
- **On-screen text**: reads captions and titles, and where they sit
- **Visual hook**: does the picture change in the first second? Is there text on frame 0?

**👂 Ears: what it hears**
- **Transcript**: every word with its exact time, in your language
- **Spoken hook**: exactly what's said in the first 3 seconds
- **Voice pace**: words per minute, time to first word, energy changes
- **Sound design**: music bed, voice-over-music level, silences, audio drops (re-hooks)

**🧠 Mastermind: what it learns**
- **Winning traits**: what outlier videos do differently from the rest
- **Creator style**: each competitor's hook types, length, pacing, captions, music, CTAs
- **Outlier score**: which videos beat their creator's usual views (×2, ×10…)
- **Trend radar**: rising words and topics in your niche, weighted by performance
- **Comment ideas**: viewer questions turned into video ideas
- **Next-video brief**: targets, hook formulas, structure and sound plan

**✅ Create better**
- **Pre-post check**: grade your draft 0–100 against winning videos, with exact fixes
- **Originality check**: stops scripts that copy a competitor word for word
- **You vs Them**: your numbers next to theirs, marked ahead, level or behind
- **Weekly report**: outliers, gaps, trends, ideas and security in one page

**🤖 AI team (for Claude)**
| Member | Job |
|---|---|
| 🧭 Manager | Splits your request and hands work to the right member |
| 🛡️ Security Guard | Checks every file, page and action *before* it happens |
| 👮 Head of Security | Audits the Guard after every job: PASS or FAIL |
| 🔭 Scout | Finds the right competitors for your niche (you approve) |
| 👀 Live Watcher | Watches Reels/Shorts in your browser, view-only, Guard-approved pages |
| 🧠 Mastermind | Learns why competitors grow and writes your brief |
| 🎬 Executive Producer | Rates ideas and rejects weak ones |
| ✍️ Scriptwriter | Writes hooks and scripts in your voice |
| ✂️ Video Editor | Timecoded edit plan: cuts, captions, sound |
| ▶️ YouTube Manager | Titles, descriptions, hashtags, thumbnails |
| 📸 Instagram Manager | Captions, hashtags, covers, collabs |
| 📈 Coach | Learns from your real results after posting |

**🔒 Safety & privacy**
- **View-only:** never downloads, uploads, likes, follows, comments or DMs
- **Your files:** only reads videos already in your `library/` folder, and never deletes them
- **Live watching:** the Guard approves every page *before* it opens: only YouTube, Instagram and TikTok, never login or account pages, at human pace (100 videos/hour, 4 s apart; adjustable)
- **Your data stays on your PC:** no accounts, no cloud, no tracking. The AI verdict runs on a local Ollama only, unless you add `--allow-remote-ai`
- **Private dashboard:** a new secret link each time; other websites and other devices can't read it
- **No secrets saved:** detects 10+ key/password/token formats; the Head of Security audits every run
- **Other people's privacy:** emails, phone numbers, @usernames and links in pasted comments are hidden
- **Delete anytime:** `python radar.py forget "creator"` or `python radar.py forget --all`

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

**Way 4: Claude Code plugin**
```
/plugin marketplace add harsh-ai-tools/reel-radar
/plugin install reel-radar@harsh-ai-tools
```

---

## 🚀 Install & start (one click)
**Windows:** double-click **`install.bat`**. It installs Python and ffmpeg if missing (it asks first), sets everything up, and connects the AI team to Claude. Then double-click **`Reel Radar.bat`**.

**Mac / Linux:** run `./install.sh`, then `./reel-radar.sh`.

The first start asks for your niche, platforms and competitors. Then put videos **you already have** into:
- your own → `library/me/`
- each competitor's → `library/<their name>/`

## 🧰 Commands
| Command | What it does |
|---|---|
| `python radar.py init` | Set niche, language, platforms, competitors |
| `python radar.py watch` | Analyse new videos with the live dashboard |
| `python radar.py brief "topic"` | Next-video brief from winning videos |
| `python radar.py precheck draft.mp4` | Grade a draft before posting |
| `python radar.py originality script.txt` | Check a script isn't copied |
| `python radar.py trends` / `ideas` / `patterns` | Trends, comment ideas, what winners do |
| `python radar.py weekly` | Everything in one weekly report |
| `python radar.py scout` / `approve "name"` | Find & approve competitors |
| `python radar.py stats-template` | Create `stats.csv` to add views (for outlier scores) |
| `python radar.py audit` | Head of Security check |
| `python radar.py forget "name"` / `--all` | Delete analysis data (your videos stay) |
| `python radar.py connect` | Connect the AI team to Claude |

**Options:** `--gpu` (NVIDIA, faster speech-to-text) · `--ollama qwen2.5vl:7b` (free local AI verdict via [Ollama](https://ollama.com)) · `--whisper medium` (more accurate transcripts)

## 💬 Use it with Claude
After install, just ask Claude:
- *"Reel Radar, find my competitors"*
- *"Watch my library and tell me why history_hub is growing"*
- *"Watch @creator's Reels live in my browser"*
- *"Write my next video about the fall of Rome"*
- *"Precheck my draft before I post"*

## 🗺️ Roadmap
- [x] Eyes, ears, live dashboard, You vs Them
- [x] AI team with Security Guard + Head of Security
- [x] Mastermind: patterns, briefs, trends, comment ideas, weekly report
- [x] Pre-post check and originality check
- [x] One-click installer + Claude plugin
- [ ] Retention-curve import from YouTube Studio exports
- [ ] Thumbnail analysis for long-form videos

> ⚠️ For study only. Don't re-upload other creators' videos or copy their scripts. AI output is a draft: verify facts before posting.
