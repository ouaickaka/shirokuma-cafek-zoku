#!/usr/bin/env python3
"""
convert-to-json.py — Convert existing Shirokuma Cafe HTML episodes to the new
data-driven JSON format used by episode.html.

Reads:  Shirokuma-Cafe-XX.html  (Japanese dialogue, scene structure)
        Shirokuma-Cafe-XX-en.json  (flat [[ja, en], ...] translation pairs)
Writes: episodes/XX.json  { ep, title, scenes: [{audio, lines: [{ja, en}]}] }

Usage:
    python3 convert-to-json.py          # convert all episodes
    python3 convert-to-json.py 01 42    # convert specific range
"""

import os
import sys
import json
import re
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "episodes")
os.makedirs(OUT_DIR, exist_ok=True)


def parse_episode_html(path):
    """
    Parse episode HTML into (title, scenes).
    scenes = list of lists of dialogue strings.
    Scene boundaries are marked by <audio> + <hr> pairs.
    """
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    title_el = soup.find(id="episode-title")
    title = title_el.get_text(strip=True) if title_el else ""

    scenes = []
    current_scene = []

    for el in soup.find_all(["p", "audio", "hr"]):
        if el.name == "p":
            # Skip the episode title paragraph
            if el.find(id="episode-title"):
                continue
            text = el.get_text(strip=True)
            if text:
                current_scene.append(text)
        elif el.name == "audio":
            if current_scene:
                scenes.append(current_scene)
                current_scene = []

    if current_scene:
        scenes.append(current_scene)

    return title, scenes


def load_translations(path):
    """Load flat [[ja, en], ...] translation pairs."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        pairs = json.load(f)
    return {ja: en for ja, en in pairs if ja}


def convert_episode(ep_str):
    html_path = os.path.join(BASE, f"Shirokuma-Cafe-{ep_str}.html")
    json_path = os.path.join(BASE, f"Shirokuma-Cafe-{ep_str}-en.json")
    out_path  = os.path.join(OUT_DIR, f"{ep_str}.json")

    if not os.path.exists(html_path):
        print(f"  {ep_str}: no HTML, skipping")
        return False

    title, scenes = parse_episode_html(html_path)
    translations  = load_translations(json_path)

    scene_data = []
    audio_idx  = 0
    for scene_lines in scenes:
        lines = []
        for ja in scene_lines:
            en = translations.get(ja, "")
            lines.append({"ja": ja, "en": en})
        scene_data.append({"audio": audio_idx, "lines": lines})
        audio_idx += 1

    episode = {
        "ep":     ep_str,
        "title":  title,
        "scenes": scene_data,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(episode, f, ensure_ascii=False, indent=2)

    en_count = sum(1 for s in scene_data for l in s["lines"] if l["en"])
    ja_count = sum(len(s["lines"]) for s in scene_data)
    print(f"  {ep_str}: '{title}' — {len(scene_data)} scenes, {ja_count} lines, {en_count} translated")
    return True


def build_index():
    """Generate episodes/index.json with metadata for all available episodes."""
    index = []
    for ep_str in [f"{i:02d}" for i in range(0, 51)]:
        path = os.path.join(OUT_DIR, f"{ep_str}.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        has_en = any(l.get("en") for s in data["scenes"] for l in s["lines"])
        index.append({"ep": ep_str, "title": data.get("title", ""), "hasEn": has_en})
    out = os.path.join(OUT_DIR, "index.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"Index written: {out} ({len(index)} episodes)")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        eps = [f"{i:02d}" for i in range(int(sys.argv[1]), int(sys.argv[2]) + 1)]
    else:
        eps = [f"{i:02d}" for i in range(0, 51)]

    print(f"Converting {len(eps)} episodes → episodes/XX.json")
    ok = sum(convert_episode(ep) for ep in eps)
    print(f"Done: {ok} episodes written to {OUT_DIR}/")
    build_index()
