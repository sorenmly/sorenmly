#!/usr/bin/env python3

import os
import sys
import html
import requests

TEMPLATE_PATH = os.environ.get("TEMPLATE_PATH", "profile-template.svg")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "profile.svg")

LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"
GITHUB_API_URL = "https://api.github.com"


def esc(text: str) -> str:
    """Escapa texto pra nao quebrar o XML do SVG."""
    return html.escape(str(text), quote=False)


def truncate(text: str, max_len: int = 46) -> str:
    text = text.strip()
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def get_lastfm_now_playing(api_key: str, username: str) -> str:
    """Retorna uma linha tipo 'Artista - Musica' (ou aviso se nao achar nada)."""
    params = {
        "method": "user.getrecenttracks",
        "user": username,
        "api_key": api_key,
        "format": "json",
        "limit": 1,
    }
    try:
        resp = requests.get(LASTFM_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        tracks = data.get("recenttracks", {}).get("track", [])
        if not tracks:
            return "nada tocado recentemente"

        track = tracks[0]
        artist = track.get("artist", {}).get("#text", "artista desconhecido")
        name = track.get("name", "faixa desconhecida")
        now_playing = track.get("@attr", {}).get("nowplaying") == "true"

        prefix = "tocando agora: " if now_playing else "ultima vez: "
        return truncate(f"{prefix}{artist} - {name}")
    except requests.RequestException as e:
        print(f"[lastfm] erro ao buscar dados: {e}", file=sys.stderr)
        return "last.fm indisponivel no momento"
    except (KeyError, IndexError, ValueError) as e:
        print(f"[lastfm] resposta inesperada: {e}", file=sys.stderr)
        return "sem dados do last.fm"


def get_recent_commits(username: str, token: str | None = None, limit: int = 3) -> list[str]:
    """Retorna uma lista de strings 'repo: mensagem do commit' com os commits mais recentes."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{GITHUB_API_URL}/users/{username}/events/public"
    commits: list[str] = []

    try:
        resp = requests.get(url, headers=headers, params={"per_page": 30}, timeout=10)
        resp.raise_for_status()
        events = resp.json()

        for event in events:
            if event.get("type") != "PushEvent":
                continue
            repo_name = event.get("repo", {}).get("name", "repo").split("/")[-1]
            for c in event.get("payload", {}).get("commits", []):
                msg = c.get("message", "").splitlines()[0]  # so a primeira linha
                commits.append(truncate(f"{repo_name}: {msg}", 44))
                if len(commits) >= limit:
                    return commits
        return commits
    except requests.RequestException as e:
        print(f"[github] erro ao buscar commits: {e}", file=sys.stderr)
        return []
    except (KeyError, IndexError, ValueError) as e:
        print(f"[github] resposta inesperada: {e}", file=sys.stderr)
        return []


def build_svg(replacements: dict[str, str]) -> str:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        svg = f.read()

    for placeholder, value in replacements.items():
        svg = svg.replace(placeholder, esc(value))

    return svg


def main() -> None:
    lastfm_api_key = os.environ.get("LASTFM_API_KEY")
    lastfm_username = os.environ.get("LASTFM_USERNAME")
    github_username = os.environ.get("GITHUB_USERNAME")
    github_token = os.environ.get("GITHUB_TOKEN")

    # dados que voce pode trocar por variaveis de ambiente tambem, se quiser
    name = os.environ.get("PROFILE_NAME", "Seu Nome Aqui")
    role = os.environ.get("PROFILE_ROLE", "Desenvolvedor(a) Full Stack")
    links = os.environ.get(
        "PROFILE_LINKS",
        f"github.com/{github_username or 'seu-usuario'} - seusite.dev",
    )

    if lastfm_api_key and lastfm_username:
        lastfm_line = get_lastfm_now_playing(lastfm_api_key, lastfm_username)
    else:
        print("[lastfm] LASTFM_API_KEY ou LASTFM_USERNAME nao definidos, pulando.", file=sys.stderr)
        lastfm_line = "last.fm nao configurado"

    if github_username:
        commits = get_recent_commits(github_username, github_token)
    else:
        print("[github] GITHUB_USERNAME nao definido, pulando.", file=sys.stderr)
        commits = []

    # garante sempre 3 linhas, mesmo sem commits suficientes
    while len(commits) < 3:
        commits.append("sem commits recentes")

    replacements = {
        "__USERNAME__": github_username or "seu-usuario",
        "__NAME__": name,
        "__ROLE__": role,
        "__LASTFM_LINE__": lastfm_line,
        "__COMMIT_1__": commits[0],
        "__COMMIT_2__": commits[1],
        "__COMMIT_3__": commits[2],
        "__LINKS__": links,
    }

    svg = build_svg(replacements)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"SVG gerado em: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
