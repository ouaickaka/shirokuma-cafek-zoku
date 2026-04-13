# shirokuma-cafek-zoku 続

A Japanese language learning site built around the anime **Shirokuma Cafe (しろくまカフェ)**.
Each episode presents the original Japanese dialogue scene by scene with audio clips and optional English translations.

> **続** (zoku) — continuation, sequel.
> This is a rebuilt and extended version of the original [Shirokuma Cafe](https://github.com/gwmatthews/Shirokuma-Cafe) project by [George Matthews](https://github.com/gwmatthews). All episode content, transcripts, and the learning concept are his work.

---

## What's new in this version

- All **50 episodes** (original covered ~20)
- **Data-driven architecture** — 51 JSON files + a single `episode.html` template, replacing ~200 static HTML files
- **No dependencies** — vanilla JS and CSS, no Bootstrap or jQuery
- **JP/EN toggle** — English translations hidden by default, revealed on hover or with one button
- **Automated pipeline** — subtitle parsing → audio clipping → translation via Claude API
- **One-command deploy** via Docker

---

## Quick start

```bash
git clone https://github.com/ouaickaka/shirokuma-cafek-zoku
cd shirokuma-cafek-zoku
docker compose up -d
# open http://localhost:8080
```

---

## Adding new episodes

You'll need the MKV video file and a Japanese subtitle file (.ass or .srt).

```bash
# 1. Install dependencies
cp env.template .env        # add your ANTHROPIC_API_KEY
pip install -r requirements.txt

# 2. Build episode (parses subtitles, clips audio, writes episodes/XX.json)
python3 build-episode.py 51 \
  "subtitles/MyShow-51.ja.ass" \
  "/media/MyShow/S01E51.mkv"

# 3. Translate to English
python3 translate.py episodes/51.json en

# 4. Rebuild episode index
python3 convert-to-json.py 0 0

# 5. Redeploy
docker compose up -d
```

---

## Project structure

```
episodes/          # JSON episode data (51 files + index.json)
audio/             # MP3 clips per episode (Git LFS)
includes/          # style.css
episode.html       # single episode template
index.html         # episode list
build-episode.py   # subtitle → audio + JSON pipeline
translate.py       # Claude Haiku translation (in-place, resumable)
convert-to-json.py # converts old HTML episodes + rebuilds index.json
docker-compose.yml # nginx static file server
```

---

## Credits

Original project: [gwmatthews/Shirokuma-Cafe](https://github.com/gwmatthews/Shirokuma-Cafe) by George Matthews.
Anime: *Shirokuma Cafe* © Aloha Higa / Shogakukan.
