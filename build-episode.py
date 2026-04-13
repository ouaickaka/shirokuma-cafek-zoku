#!/usr/bin/env python3
"""
build-episode.py — Build a Shirokuma Cafe learning site episode from subtitle + MKV.

Parses a Japanese subtitle file (ASS or SRT), groups lines into scenes,
clips audio from the MKV, and writes an episode JSON data file.

Usage:
    python3 build-episode.py <episode_number> <subtitle_file> <mkv_file>

Example:
    python3 build-episode.py 43 \
        "[Fixed Timing - Kamigami] Shirokuma Cafe - 43 [1280x720 x264 AAC][JPN].ass" \
        "/mnt/media/tvshows/Polar Bear's Café/Season 01/Shirokuma Cafe - S01E43.mkv"

Outputs (relative to this script's directory):
    episodes/43.json
    audio/43/0.mp3, 1.mp3, ...
"""

import os
import re
import sys
import json
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

# Skip OP and ED — timecodes in seconds
SKIP_BEFORE = 90   # skip first 90s (opening song)
SKIP_AFTER  = 90   # skip last 90s (ending song)

# Group lines into scenes — gap larger than this = new scene
SCENE_GAP = 1.5  # seconds

# Maximum dialogue lines per scene before forcing a split
MAX_SCENE_LINES = 5

# Padding around each audio clip
CLIP_PAD = 0.3   # seconds


# --- Subtitle parsing ---

def ass_time_to_s(t):
    """Convert ASS timestamp H:MM:SS.xx to seconds."""
    h, m, rest = t.split(":")
    s, cs = rest.split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100

def srt_time_to_s(t):
    """Convert SRT timestamp HH:MM:SS,mmm to seconds."""
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

def strip_ass_tags(text):
    """Remove inline ASS formatting codes like {\\fad(...)}, {\\pos(...)} etc."""
    text = re.sub(r"\{[^}]*\}", "", text)
    text = text.replace("\\N", " ").replace("\\n", " ")
    return text.strip()

def is_noise(text):
    """Return True for lines that are not spoken dialogue."""
    if not text:
        return True
    # Sound effects: （玄関チャイム）, （SE）, etc.
    if re.fullmatch(r"[（(][^）)]+[）)]", text):
        return True
    # Signs/title cards: ＜ダジャレカフェ＞
    if re.fullmatch(r"[＜<][^＞>]+[＞>]", text):
        return True
    # Fansub credits (Chinese subtitle group watermarks)
    if "------" in text or re.search(r"[诸神字幕组翻译校对时间轴压制]", text):
        return True
    return False

def extract_title(text):
    """Pull title from a ＜...＞ marker."""
    m = re.match(r"[＜<]([^＞>]+)[＞>]", text)
    return m.group(1).strip() if m else None

def parse_ass(path):
    """Return (title, lines) where lines = [(start_s, end_s, text), ...]."""
    title = None
    lines = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            if not raw.startswith("Dialogue:"):
                continue
            parts = raw.split(",", 9)
            if len(parts) < 10:
                continue
            start = ass_time_to_s(parts[1].strip())
            end   = ass_time_to_s(parts[2].strip())
            text  = strip_ass_tags(parts[9].strip())
            if not title:
                t = extract_title(text)
                if t:
                    title = t
                    continue
            if is_noise(text):
                continue
            lines.append((start, end, text))
    return title, lines

def parse_srt(path):
    """Return (title, lines) where lines = [(start_s, end_s, text), ...]."""
    title = None
    lines = []
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    blocks = re.split(r"\n\n+", content.strip())
    for block in blocks:
        parts = block.strip().splitlines()
        if len(parts) < 3:
            continue
        times = parts[1]
        if "-->" not in times:
            continue
        start_s, end_s = times.split("-->")
        start = srt_time_to_s(start_s.strip())
        end   = srt_time_to_s(end_s.strip())
        # Join multi-line subtitle text, strip speaker labels (グリズリー）
        raw_text = " ".join(parts[2:])
        raw_text = re.sub(r"^[（(][^）)]+[）)]\s*", "", raw_text).strip()
        if not title:
            t = extract_title(raw_text)
            if t:
                title = t
                continue
        if is_noise(raw_text):
            continue
        if raw_text:
            lines.append((start, end, raw_text))
    return title, lines

def parse_subtitle(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".ass":
        return parse_ass(path)
    elif ext == ".srt":
        return parse_srt(path)
    else:
        raise ValueError(f"Unsupported subtitle format: {ext}")


# --- Scene grouping ---

def group_into_scenes(lines, episode_duration):
    """
    Filter lines by OP/ED, then group into visual scenes (paragraph breaks).
    Audio is per-line; scenes are just visual groupings with an <hr> between them.
    A new scene starts when there is a gap > SCENE_GAP between lines.
    """
    kept = []
    for start, end, text in lines:
        if start < SKIP_BEFORE:
            continue
        if episode_duration and start > (episode_duration - SKIP_AFTER):
            continue
        kept.append((start, end, text))

    scenes = []
    current = []
    for line in kept:
        start = line[0]
        gap_break  = current and (start - current[-1][1]) > SCENE_GAP
        size_break = len(current) >= MAX_SCENE_LINES
        if gap_break or size_break:
            scenes.append(current)
            current = []
        current.append(line)
    if current:
        scenes.append(current)
    return scenes


# --- Audio clipping ---

def get_duration(mkv_path):
    """Get video duration in seconds using ffprobe via docker."""
    result = subprocess.run(
        ["docker", "run", "--rm",
         "-v", f"{os.path.dirname(mkv_path)}:/media",
         "linuxserver/ffmpeg",
         "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         f"/media/{os.path.basename(mkv_path)}"],
        capture_output=True, text=True
    )
    # ffprobe not available via linuxserver/ffmpeg, use ffmpeg duration approach
    return None

def clip_audio(mkv_path, start_s, end_s, output_path):
    """Extract an audio clip from MKV using docker ffmpeg."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pad_start = max(0, start_s - CLIP_PAD)
    duration  = (end_s + CLIP_PAD) - pad_start
    media_dir = os.path.dirname(mkv_path)
    mkv_name  = os.path.basename(mkv_path)
    out_name  = os.path.basename(output_path)
    out_dir   = os.path.dirname(output_path)

    subprocess.run(
        ["docker", "run", "--rm",
         "-v", f"{media_dir}:/media",
         "-v", f"{out_dir}:/out",
         "linuxserver/ffmpeg",
         "-hide_banner", "-loglevel", "error", "-y",
         "-ss", str(pad_start), "-t", str(duration),
         "-i", f"/media/{mkv_name}",
         "-vn", "-ar", "22050", "-ac", "1", "-q:a", "4",
         f"/out/{out_name}"],
        check=True
    )


# --- JSON generation ---

def build_json(ep, title, scenes):
    """Build episode data dict for JSON output."""
    ep_str = str(ep).zfill(2)
    scene_data = []
    for i, scene in enumerate(scenes):
        lines = [{"ja": text, "en": ""} for _, _, text in scene]
        scene_data.append({"audio": i, "lines": lines})
    return {"ep": ep_str, "title": title, "scenes": scene_data}


# --- Main ---

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 build-episode.py <ep_num> <subtitle_file> <mkv_file>")
        sys.exit(1)

    ep_num   = int(sys.argv[1])
    sub_path = sys.argv[2]
    mkv_path = sys.argv[3]
    ep_str   = str(ep_num).zfill(2)

    print(f"Parsing subtitles: {sub_path}")
    title, lines = parse_subtitle(sub_path)
    title = title or f"Episode {ep_num}"
    print(f"  Title: {title}  |  Lines: {len(lines)}")

    # Get episode duration for ED skip — use max end time (last entry may be credits)
    ep_duration = max(l[1] for l in lines) + 30 if lines else None

    print("Grouping into scenes...")
    scenes = group_into_scenes(lines, ep_duration)
    print(f"  {len(scenes)} scenes, {sum(len(s) for s in scenes)} dialogue lines")

    print("Clipping audio...")
    audio_dir = os.path.join(BASE, "audio", ep_str)
    os.makedirs(audio_dir, exist_ok=True)
    for i, scene in enumerate(scenes):
        start_s = scene[0][0]
        end_s   = scene[-1][1]
        out_path = os.path.join(audio_dir, f"{i}.mp3")
        if os.path.exists(out_path):
            print(f"  Scene {i}: already exists, skipping")
            continue
        print(f"  Scene {i}: {start_s:.1f}s - {end_s:.1f}s ({len(scene)} lines)")
        clip_audio(mkv_path, start_s, end_s, out_path)

    print("Writing JSON...")
    os.makedirs(os.path.join(BASE, "episodes"), exist_ok=True)
    data = build_json(ep_num, title, scenes)
    out_json = os.path.join(BASE, "episodes", f"{ep_str}.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Written: {out_json}")

    print(f"\nDone! To add English translations:")
    print(f"  python3 translate.py episodes/{ep_str}.json en")


if __name__ == "__main__":
    main()
