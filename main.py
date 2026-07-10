import os
import base64
import html
import requests

LASTFM_API_KEY = os.environ["LASTFM_API_KEY"]
LASTFM_USERNAME = os.environ["LASTFM_USERNAME"]

url = (
    "https://ws.audioscrobbler.com/2.0/"
    f"?method=user.getrecenttracks"
    f"&user={LASTFM_USERNAME}"
    f"&api_key={LASTFM_API_KEY}"
    "&limit=1"
    "&format=json"
)

data = requests.get(url, timeout=10).json()
track = data["recenttracks"]["track"][0]

artist = track["artist"]["#text"]
title = track["name"]
album = track["album"]["#text"]
playing = track.get("@attr", {}).get("nowplaying") == "true"


def truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def esc(text: str) -> str:
    # evita quebrar o SVG se vier & < > " no nome da música/artista
    return html.escape(text, quote=True)


title = truncate(title, 34)
artist = truncate(artist, 38)
album = truncate(album, 42)

# pega a maior capa disponível; cai pro placeholder se não tiver
cover_url = ""
for img in reversed(track["image"]):
    if img["#text"]:
        cover_url = img["#text"]
        break

cover_data = ""
if cover_url:
    try:
        img_bytes = requests.get(cover_url, timeout=10).content
        cover_data = base64.b64encode(img_bytes).decode("utf-8")
    except requests.RequestException:
        cover_data = ""

accent = (
    "#1DB954" if playing else "#6b7280"
)  # verde estilo Spotify / cinza quando parado
status_label = "NOW PLAYING" if playing else "LAST PLAYED"


# barras de equalizer só animam quando tá tocando de verdade
def eq_bars():
    if not playing:
        return f'<rect x="0" y="6" width="3" height="4" rx="1.5" fill="{accent}"/>'
    bars = ""
    heights = [(0, "6;14;6", "0.9s"), (6, "14;5;14", "1.1s"), (12, "8;16;8", "0.8s")]
    for x, vals, dur in heights:
        bars += (
            f'<rect x="{x}" width="3" rx="1.5" fill="{accent}">'
            f'<animate attributeName="height" values="{vals}" dur="{dur}" '
            f'repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{",".join(str(16 - int(v)) for v in vals.split(";"))}" '
            f'dur="{dur}" repeatCount="indefinite"/>'
            f"</rect>"
        )
    return bars


svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="560" height="160" viewBox="0 0 560 160">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#15151f"/>
      <stop offset="100%" stop-color="#0b0b12"/>
    </linearGradient>
    <linearGradient id="border" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="artClip">
      <rect x="20" y="20" width="120" height="120" rx="14"/>
    </clipPath>
    <filter id="artShadow" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="#000" flood-opacity="0.45"/>
    </filter>
    <style>
      .status {{
        font: 600 11px -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
        letter-spacing: 2px;
        fill: {accent};
      }}
      .title {{
        font: 700 20px -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
        fill: #f5f5f7;
      }}
      .artist {{
        font: 500 15px -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
        fill: #c7c7cf;
      }}
      .album {{
        font: 400 13px -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
        fill: #83838d;
      }}
    </style>
  </defs>

  <rect width="560" height="160" rx="16" fill="url(#bg)"/>
  <rect x="0.5" y="0.5" width="559" height="159" rx="15.5" fill="none" stroke="url(#border)" stroke-width="1"/>

  <g filter="url(#artShadow)">
    <rect x="20" y="20" width="120" height="120" rx="14" fill="#222"/>
    {f'<image x="20" y="20" width="120" height="120" href="data:image/jpeg;base64,{cover_data}" preserveAspectRatio="xMidYMid slice" clip-path="url(#artClip)"/>' if cover_data else ""}
  </g>
  <rect x="20" y="20" width="120" height="120" rx="14" fill="none" stroke="#ffffff" stroke-opacity="0.08" stroke-width="1"/>

  <g transform="translate(160, 34)">
    <g transform="translate(0, -8)">{eq_bars()}</g>
    <text x="24" y="4" class="status">{status_label}</text>
  </g>

  <text x="160" y="70" class="title">{esc(title)}</text>
  <text x="160" y="96" class="artist">{esc(artist)}</text>
  <text x="160" y="118" class="album">{esc(album)}</text>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/now-playing.svg", "w", encoding="utf-8") as f:
    f.write(svg)
