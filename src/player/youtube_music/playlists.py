import re
from urllib.parse import parse_qs, urlencode, urlparse

from .models import YouTubeMusicPlaylistSummary


YTMUSIC_SOURCE_PREFIX = "ytmusic://"
PLAYLIST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,}$")


def playlist_track_count_text(item):
    track_count = item.get("trackCount")
    if isinstance(track_count, int) and track_count > 0:
        suffix = "faixa" if track_count == 1 else "faixas"
        return f"{track_count} {suffix}"

    count_text = str(item.get("count") or item.get("description") or "").strip()
    return count_text


def extract_personalized_mix_summaries(home_rows):
    playlists = []
    for row in home_rows or []:
        if not isinstance(row, dict):
            continue

        row_title = str(row.get("title") or "").strip()
        for item in row.get("contents") or []:
            if not isinstance(item, dict):
                continue

            playlist_id = str(item.get("playlistId") or "").strip()
            title = str(item.get("title") or "").strip()
            if not playlist_id or not title:
                continue
            if not _looks_like_personalized_mix(title, item, row_title):
                continue

            track_count_text = playlist_track_count_text(item)
            playlists.append(
                YouTubeMusicPlaylistSummary(
                    playlist_id=playlist_id,
                    title=title,
                    track_count_text=track_count_text,
                    source_badge="mix personalizada",
                )
            )

    return playlists


def _looks_like_personalized_mix(title, item, row_title=""):
    normalized_title = str(title or "").casefold()
    normalized_description = str(item.get("description") or "").casefold()
    normalized_row_title = str(row_title or "").casefold()
    playlist_id = str(item.get("playlistId") or "").strip()

    title_keywords = (
        "mix",
        "supermix",
        "super mix",
    )
    row_keywords = (
        "for you",
        "para você",
        "made for you",
        "mixes",
        "mixed for you",
    )

    if any(keyword in normalized_title for keyword in title_keywords):
        return True
    if playlist_id.startswith("RD") and any(keyword in normalized_description for keyword in title_keywords):
        return True
    if playlist_id.startswith("RD") and any(keyword in normalized_row_title for keyword in row_keywords):
        return True

    return False


def is_watch_playlist_id(playlist_id):
    normalized_playlist_id = str(playlist_id or "").strip().upper()
    return normalized_playlist_id.startswith("RD")


def build_watch_url(video_id, playlist_id=None):
    normalized_video_id = str(video_id or "").strip()
    if not normalized_video_id:
        raise RuntimeError("A faixa do YouTube Music não tem videoId válido.")

    query_items = [("v", normalized_video_id)]
    normalized_playlist_id = str(playlist_id or "").strip()
    if normalized_playlist_id:
        query_items.append(("list", normalized_playlist_id))
    return f"https://music.youtube.com/watch?{urlencode(query_items)}"


def build_playlist_source(playlist_id):
    normalized_playlist_id = str(playlist_id or "").strip()
    source_kind = "mix" if is_watch_playlist_id(normalized_playlist_id) else "playlist"
    return f"{YTMUSIC_SOURCE_PREFIX}{source_kind}/{normalized_playlist_id}"


def extract_playlist_id_from_source(source_path):
    normalized_source_path = str(source_path or "").strip()
    if not normalized_source_path.lower().startswith(YTMUSIC_SOURCE_PREFIX):
        return None

    parsed_source = urlparse(normalized_source_path)
    source_kind = str(parsed_source.netloc or "").strip().lower()
    if source_kind not in {"playlist", "mix"}:
        return None

    playlist_id = str(parsed_source.path or "").strip("/")
    return playlist_id or None


def extract_playlist_id_from_text(source_text):
    normalized_source_text = str(source_text or "").strip()
    if not normalized_source_text:
        return None

    playlist_id = extract_playlist_id_from_source(normalized_source_text)
    if playlist_id:
        return playlist_id

    parsed_source = urlparse(normalized_source_text)
    if parsed_source.scheme or parsed_source.netloc:
        query_playlist_ids = parse_qs(parsed_source.query).get("list") or []
        for candidate in query_playlist_ids:
            normalized_candidate = str(candidate or "").strip()
            if normalized_candidate:
                return normalized_candidate
        return None

    if any(character.isspace() for character in normalized_source_text):
        return None

    if PLAYLIST_ID_PATTERN.match(normalized_source_text):
        return normalized_source_text

    return None


def is_youtube_music_media(media_path):
    normalized_media_path = str(media_path or "").strip()
    if not normalized_media_path:
        return False

    parsed_url = urlparse(normalized_media_path)
    host = (parsed_url.netloc or "").lower()
    if host in {"music.youtube.com", "www.youtube.com", "youtube.com", "youtu.be"}:
        return True

    return normalized_media_path.lower().startswith(YTMUSIC_SOURCE_PREFIX)


def track_display_label(track):
    title = str(track.get("title") or "Faixa sem título").strip()
    artist_names = []
    for artist in track.get("artists") or []:
        artist_name = str(artist.get("name") or "").strip()
        if artist_name:
            artist_names.append(artist_name)

    if artist_names:
        return f"{', '.join(artist_names)} — {title}"

    return title
