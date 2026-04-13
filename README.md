# shirokuma-cafek-zoku 続

A Japanese language learning site built around the anime **Shirokuma Cafe (しろくまカフェ)**.
Each episode presents the original Japanese dialogue scene by scene with audio clips and optional English translations.

> **続** (zoku) — continuation, sequel.
> This is a rebuilt and extended version of the original [Shirokuma Cafe](https://github.com/gwmatthews/Shirokuma-Cafe) project by [George Matthews](https://github.com/gwmatthews). All episode content, transcripts, and the learning concept are his work.

---

## A foundation for more

This project is built as a reusable pipeline — not just for Shirokuma Cafe, but for any anime or Japanese-language show. Given a video file and Japanese subtitles, the tooling here can automatically parse dialogue, clip audio, and generate translations, producing a complete interactive learning site ready to deploy.

The goal is to make this kind of immersive, audio-first learning accessible for more shows beyond this one.

---

## Quick start

```bash
git clone https://github.com/ouaickaka/shirokuma-cafek-zoku
cd shirokuma-cafek-zoku
docker compose up -d
# open http://localhost:8080
```

---

## Adding a new show

You'll need the video files and Japanese subtitle files (.ass or .srt).

```bash
# 1. Set up
cp env.template .env        # add your ANTHROPIC_API_KEY
pip install -r requirements.txt

# 2. Build an episode
python3 build-episode.py 1 \
  "subtitles/show-01.ja.ass" \
  "/media/show/S01E01.mkv"

# 3. Translate
python3 translate.py episodes/01.json en

# 4. Rebuild index
python3 convert-to-json.py 0 0

# 5. Deploy
docker compose up -d
```

---

## Project structure

```
episodes/          # JSON episode data + index.json
audio/             # MP3 clips per episode (Git LFS)
includes/          # style.css
episode.html       # single episode template
index.html         # episode list
build-episode.py   # subtitle → audio + JSON pipeline
translate.py       # Claude Haiku translation (in-place, resumable)
docker-compose.yml # nginx static file server
```

---

## Credits

Original project: [gwmatthews/Shirokuma-Cafe](https://github.com/gwmatthews/Shirokuma-Cafe) by George Matthews.
Anime: *Shirokuma Cafe* © Aloha Higa / Shogakukan.
