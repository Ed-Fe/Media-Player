import json
import os
import re
import time
from dataclasses import dataclass
from http.cookies import SimpleCookie
from urllib.parse import urlencode, urlparse

from .session import APP_STORAGE_DIR


YTMUSIC_BROWSER_AUTH_FILE_NAME = "ytmusic_browser.json"
YTMUSIC_SOURCE_PREFIX = "ytmusic://"


@dataclass(frozen=True)
class YouTubeMusicPlaylistSummary:
    playlist_id: str
    title: str
    track_count_text: str = ""
    source_badge: str = ""

    @property
    def choice_label(self):
        details = []
        if self.source_badge:
            details.append(self.source_badge)
        if self.track_count_text:
            details.append(self.track_count_text)
        if details:
            return f"{self.title} — {' · '.join(details)}"
        return self.title


@dataclass(frozen=True)
class YouTubeMusicPlaylistContent:
    playlist_id: str
    title: str
    item_urls: list[str]
    item_labels: list[str]


class YouTubeMusicService:
    def __init__(self):
        self._client = None
        self._account_info = None

    @property
    def browser_auth_file_path(self):
        return os.path.join(_get_storage_dir(), YTMUSIC_BROWSER_AUTH_FILE_NAME)

    @property
    def token_file_path(self):
        return self.browser_auth_file_path

    def has_saved_browser_auth(self):
        return os.path.isfile(self.browser_auth_file_path)

    def has_saved_auth(self):
        return self.has_saved_browser_auth()

    def is_authenticated(self):
        if not self.has_saved_browser_auth():
            return False

        try:
            self.get_account_info()
        except Exception:
            self.clear_client_cache()
            return False

        return True

    def clear_client_cache(self):
        self._client = None
        self._account_info = None

    def disconnect(self):
        self.clear_client_cache()
        try:
            os.remove(self.browser_auth_file_path)
        except FileNotFoundError:
            return False
        return True

    def save_browser_auth(self, headers_raw=None, source_file_path=None):
        target_path = self.browser_auth_file_path

        normalized_headers_raw = ""
        if source_file_path:
            normalized_source_file_path = os.path.abspath(os.path.normpath(str(source_file_path or "").strip()))
            if not normalized_source_file_path or not os.path.isfile(normalized_source_file_path):
                raise RuntimeError("Selecione um arquivo browser.json, JSON de cookies ou cookies.txt válido.")
            normalized_headers_raw = _prepare_browser_auth_input(
                _read_auth_file_text(normalized_source_file_path),
                source_name=os.path.basename(normalized_source_file_path),
            )
        else:
            normalized_headers_raw = _prepare_browser_auth_input(headers_raw, source_name="texto colado")

        if not normalized_headers_raw:
            raise RuntimeError(
                "Cole os cabeçalhos do navegador ou selecione um browser.json, JSON de cookies ou cookies.txt válido."
            )

        try:
            import ytmusicapi
        except ImportError as exc:
            raise RuntimeError(
                "A dependência ytmusicapi não está instalada. Atualize o ambiente com o requirements.txt."
            ) from exc

        ytmusicapi.setup(filepath=target_path, headers_raw=normalized_headers_raw)
        self.clear_client_cache()
        return target_path

    def get_account_info(self):
        if self._account_info is not None:
            return self._account_info

        client = self.get_client()
        try:
            account_info = client.get_account_info()
        except Exception as exc:
            self.clear_client_cache()
            raise RuntimeError("Não foi possível verificar se a conta do YouTube Music está conectada.") from exc

        if not isinstance(account_info, dict):
            raise RuntimeError("A resposta da conta do YouTube Music veio em formato inválido.")

        self._account_info = account_info
        return account_info

    def get_connected_account_name(self):
        account_info = self.get_account_info()
        return str(account_info.get("accountName") or account_info.get("channelHandle") or "Conta do YouTube Music").strip()

    def get_library_playlists(self):
        client = self.get_client()
        try:
            raw_playlists = client.get_library_playlists(limit=None)
        except TypeError:
            raw_playlists = client.get_library_playlists()

        playlists = []
        seen_playlist_ids = set()
        for item in raw_playlists or []:
            playlist_id = str(item.get("playlistId") or item.get("browseId") or "").strip()
            title = str(item.get("title") or "").strip()
            if not playlist_id or not title:
                continue
            if playlist_id in seen_playlist_ids:
                continue

            track_count_text = _playlist_track_count_text(item)
            playlists.append(
                YouTubeMusicPlaylistSummary(
                    playlist_id=playlist_id,
                    title=title,
                    track_count_text=track_count_text,
                )
            )
            seen_playlist_ids.add(playlist_id)

        try:
            home_rows = client.get_home(limit=20)
        except Exception:
            home_rows = []

        for item in _extract_personalized_mix_summaries(home_rows):
            if item.playlist_id in seen_playlist_ids:
                continue
            playlists.append(item)
            seen_playlist_ids.add(item.playlist_id)

        playlists.sort(key=lambda playlist: playlist.title.casefold())
        return playlists

    def get_playlist_content(self, playlist_id, fallback_title=""):
        client = self.get_client()
        normalized_playlist_id = str(playlist_id or "").strip()

        if _is_watch_playlist_id(normalized_playlist_id):
            playlist = client.get_watch_playlist(playlistId=normalized_playlist_id, limit=200)
            playlist_title = str(fallback_title or "Mix do YouTube Music").strip()
            tracks = playlist.get("tracks") or []
        else:
            playlist = client.get_playlist(normalized_playlist_id, limit=None)
            playlist_title = str(playlist.get("title") or fallback_title or "Playlist do YouTube Music").strip()
            tracks = playlist.get("tracks") or []

        item_urls = []
        item_labels = []

        for track in tracks:
            video_id = str(track.get("videoId") or "").strip()
            if not video_id:
                continue

            item_urls.append(self.build_watch_url(video_id, playlist_id=normalized_playlist_id))
            item_labels.append(_track_display_label(track))

        return YouTubeMusicPlaylistContent(
            playlist_id=normalized_playlist_id,
            title=playlist_title,
            item_urls=item_urls,
            item_labels=item_labels,
        )

    def get_client(self):
        if self._client is not None:
            return self._client

        from ytmusicapi import YTMusic

        if not self.has_saved_browser_auth():
            raise RuntimeError("Faça a autenticação do navegador antes de buscar playlists.")

        self._client = YTMusic(self.browser_auth_file_path)
        return self._client

    def resolve_stream_url(self, media_path):
        normalized_media_path = str(media_path or "").strip()
        if not self.is_youtube_music_media(normalized_media_path):
            return normalized_media_path

        try:
            import yt_dlp
        except ImportError as exc:
            raise RuntimeError(
                "A dependência yt-dlp não está instalada. Atualize o ambiente com o requirements.txt."
            ) from exc

        base_options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "extract_flat": False,
        }
        extractor_profiles = [
            {"extractor_args": {"youtube": {"player_client": ["web_music", "web"]}}},
            {"extractor_args": {"youtube": {"player_client": ["web", "android", "ios"]}}},
            {},
        ]

        info = None
        last_error = ""
        for profile in extractor_profiles:
            try:
                with yt_dlp.YoutubeDL({**base_options, **profile}) as ydl:
                    info = ydl.extract_info(normalized_media_path, download=False)
                if info:
                    break
            except Exception as exc:
                last_error = _clean_external_tool_error(exc)

        if not info:
            raise RuntimeError(last_error or "O yt-dlp não conseguiu abrir a faixa do YouTube Music.")

        resolved_url = _preferred_stream_url_from_info(info)
        if not resolved_url:
            raise RuntimeError("O yt-dlp não conseguiu determinar uma URL de reprodução compatível para esta faixa.")
        return resolved_url

    def build_watch_url(self, video_id, playlist_id=None):
        normalized_video_id = str(video_id or "").strip()
        if not normalized_video_id:
            raise RuntimeError("A faixa do YouTube Music não tem videoId válido.")

        query_items = [("v", normalized_video_id)]
        normalized_playlist_id = str(playlist_id or "").strip()
        if normalized_playlist_id:
            query_items.append(("list", normalized_playlist_id))
        return f"https://music.youtube.com/watch?{urlencode(query_items)}"

    def build_playlist_source(self, playlist_id):
        normalized_playlist_id = str(playlist_id or "").strip()
        source_kind = "mix" if _is_watch_playlist_id(normalized_playlist_id) else "playlist"
        return f"{YTMUSIC_SOURCE_PREFIX}{source_kind}/{normalized_playlist_id}"

    @staticmethod
    def is_youtube_music_media(media_path):
        normalized_media_path = str(media_path or "").strip()
        if not normalized_media_path:
            return False

        parsed_url = urlparse(normalized_media_path)
        host = (parsed_url.netloc or "").lower()
        if host in {"music.youtube.com", "www.youtube.com", "youtube.com", "youtu.be"}:
            return True

        return normalized_media_path.lower().startswith(YTMUSIC_SOURCE_PREFIX)


def _get_storage_dir():
    if os.name == "nt":
        base_dir = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")

    storage_dir = os.path.join(base_dir, APP_STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)
    return storage_dir


def _playlist_track_count_text(item):
    track_count = item.get("trackCount")
    if isinstance(track_count, int) and track_count > 0:
        suffix = "faixa" if track_count == 1 else "faixas"
        return f"{track_count} {suffix}"

    count_text = str(item.get("count") or item.get("description") or "").strip()
    return count_text


def _extract_personalized_mix_summaries(home_rows):
    playlists = []
    for row in home_rows or []:
        row_title = str(getattr(row, "get", lambda *_args, **_kwargs: "")("title") or "").strip()
        for item in row.get("contents") or []:
            if not isinstance(item, dict):
                continue

            playlist_id = str(item.get("playlistId") or "").strip()
            title = str(item.get("title") or "").strip()
            if not playlist_id or not title:
                continue
            if not _looks_like_personalized_mix(title, item, row_title):
                continue

            track_count_text = _playlist_track_count_text(item)
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


def _is_watch_playlist_id(playlist_id):
    normalized_playlist_id = str(playlist_id or "").strip().upper()
    return normalized_playlist_id.startswith("RD")


def _track_display_label(track):
    title = str(track.get("title") or "Faixa sem título").strip()
    artist_names = []
    for artist in track.get("artists") or []:
        artist_name = str(artist.get("name") or "").strip()
        if artist_name:
            artist_names.append(artist_name)

    if artist_names:
        return f"{', '.join(artist_names)} — {title}"

    return title


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_auth_file_text(file_path):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as auth_file:
                return auth_file.read()
        except UnicodeDecodeError:
            continue

    raise RuntimeError("Não foi possível ler o arquivo de autenticação selecionado.")


def _prepare_browser_auth_input(raw_input, *, source_name="entrada"):
    normalized_input = str(raw_input or "").strip()
    if not normalized_input:
        return ""

    json_payload = _try_parse_json(normalized_input)
    if json_payload is not None:
        browser_headers = _extract_browser_auth_headers(json_payload)
        if browser_headers:
            return _headers_dict_to_raw(browser_headers)

        cookie_header = _cookie_header_from_json_payload(json_payload)
        if cookie_header:
            return _build_headers_raw_from_cookie(cookie_header)

        raise RuntimeError(
            f"O {source_name} não contém um browser.json válido nem um export JSON de cookies compatível."
        )

    cookie_header = _cookie_header_from_netscape_text(normalized_input)
    if cookie_header:
        return _build_headers_raw_from_cookie(cookie_header)

    return normalized_input


def _try_parse_json(raw_text):
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return None


def _extract_browser_auth_headers(payload):
    candidate = payload
    if isinstance(payload, dict) and isinstance(payload.get("headers"), dict):
        candidate = payload.get("headers")

    if not isinstance(candidate, dict):
        return None

    normalized_headers = {}
    for key, value in candidate.items():
        if not isinstance(key, str) or isinstance(value, (dict, list)):
            continue

        normalized_value = str(value).strip()
        if not normalized_value:
            continue
        normalized_headers[key] = normalized_value

    lowered_keys = {str(key).lower() for key in normalized_headers.keys()}
    if "cookie" not in lowered_keys:
        return None

    if "x-goog-authuser" not in lowered_keys:
        normalized_headers["X-Goog-AuthUser"] = "0"
    if "x-origin" not in lowered_keys:
        normalized_headers["x-origin"] = "https://music.youtube.com"

    return normalized_headers


def _cookie_header_from_json_payload(payload):
    cookie_entries = []
    _collect_cookie_entries(payload, cookie_entries)
    if not cookie_entries:
        return ""

    cookie_pairs = []
    seen_names = set()
    for cookie in cookie_entries:
        name = str(cookie.get("name") or "").strip()
        value = str(cookie.get("value") or "").strip()
        if not name or name in seen_names:
            continue
        if not _cookie_entry_matches_music_youtube(cookie):
            continue
        if _cookie_entry_is_expired(cookie):
            continue
        seen_names.add(name)
        cookie_pairs.append(f"{name}={value}")

    return "; ".join(cookie_pairs)


def _collect_cookie_entries(node, cookie_entries):
    if isinstance(node, dict):
        if _looks_like_cookie_entry(node):
            cookie_entries.append(node)
            return
        for value in node.values():
            _collect_cookie_entries(value, cookie_entries)
        return

    if isinstance(node, list):
        for item in node:
            _collect_cookie_entries(item, cookie_entries)


def _looks_like_cookie_entry(value):
    return isinstance(value, dict) and "name" in value and "value" in value


def _cookie_entry_matches_music_youtube(cookie):
    domain = str(cookie.get("domain") or cookie.get("host") or "").strip().lstrip(".").lower()
    if not domain:
        return True
    return domain.endswith("youtube.com") or domain.endswith("music.youtube.com")


def _cookie_entry_is_expired(cookie):
    expiration_value = cookie.get("expirationDate")
    if expiration_value in (None, "", 0, "0"):
        return False

    try:
        return float(expiration_value) <= time.time()
    except (TypeError, ValueError):
        return False


def _cookie_header_from_netscape_text(raw_text):
    cookie_pairs = []
    seen_names = set()

    for raw_line in str(raw_text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = raw_line.split("\t")
        if len(parts) < 7:
            continue

        domain, _include_subdomains, _path, _secure, expiry, name, value = parts[:7]
        normalized_domain = str(domain or "").strip().lstrip(".").lower()
        normalized_name = str(name or "").strip()
        normalized_value = str(value or "").strip()
        if not normalized_name or not normalized_value:
            continue
        if normalized_name in seen_names:
            continue
        if normalized_domain and not (
            normalized_domain.endswith("youtube.com") or normalized_domain.endswith("music.youtube.com")
        ):
            continue

        try:
            if expiry and expiry != "0" and float(expiry) <= time.time():
                continue
        except ValueError:
            pass

        seen_names.add(normalized_name)
        cookie_pairs.append(f"{normalized_name}={normalized_value}")

    return "; ".join(cookie_pairs)


def _build_headers_raw_from_cookie(cookie_header):
    normalized_cookie_header = str(cookie_header or "").strip()
    if not normalized_cookie_header:
        return ""

    origin = "https://music.youtube.com"
    authorization = _authorization_from_cookie(normalized_cookie_header, origin)
    if not authorization:
        raise RuntimeError(
            "O export de cookies não contém um cookie de autenticação compatível do YouTube Music. "
            "Faça login em music.youtube.com e exporte novamente os cookies da sessão ativa."
        )

    return "\n".join(
        [
            "Accept: */*",
            f"Authorization: {authorization}",
            "Content-Type: application/json",
            f"Cookie: {normalized_cookie_header}",
            "X-Goog-AuthUser: 0",
            f"x-origin: {origin}",
        ]
    )


def _headers_dict_to_raw(headers):
    header_lines = []
    for key, value in headers.items():
        normalized_key = str(key or "").strip()
        normalized_value = str(value or "").strip()
        if not normalized_key or not normalized_value:
            continue
        header_lines.append(f"{normalized_key}: {normalized_value}")

    return "\n".join(header_lines)


def _authorization_from_cookie(cookie_header, origin):
    cookie = SimpleCookie()
    try:
        cookie.load(str(cookie_header or "").replace('"', ""))
    except Exception:
        return ""

    sapisid = ""
    for cookie_name in ("__Secure-3PAPISID", "SAPISID", "__Secure-1PAPISID"):
        morsel = cookie.get(cookie_name)
        if morsel is not None:
            sapisid = str(morsel.value or "").strip()
            if sapisid:
                break

    if not sapisid:
        return ""

    try:
        from ytmusicapi.helpers import get_authorization
    except ImportError:
        return ""

    return get_authorization(f"{sapisid} {origin}")


def _preferred_stream_url_from_info(info):
    direct_url = str(info.get("url") or "").strip()

    formats = [fmt for fmt in info.get("formats", []) if fmt.get("url")]
    if not formats:
        return direct_url

    audio_only_formats = [
        fmt
        for fmt in formats
        if str(fmt.get("vcodec") or "").lower() == "none"
        and str(fmt.get("acodec") or "").lower() not in {"", "none"}
    ]
    audio_capable_formats = [fmt for fmt in formats if str(fmt.get("acodec") or "").lower() not in {"", "none"}]
    preferred_formats = audio_only_formats or audio_capable_formats or formats

    best_format = max(preferred_formats, key=_stream_format_score)
    return str(best_format.get("url") or direct_url).strip()


def _stream_format_score(fmt):
    protocol = str(fmt.get("protocol") or "").lower()
    vcodec = str(fmt.get("vcodec") or "").lower()
    acodec = str(fmt.get("acodec") or "").lower()
    return (
        1 if vcodec == "none" else 0,
        1 if acodec not in {"", "none"} else 0,
        1 if protocol in {"https", "http"} else 0,
        _safe_float(fmt.get("abr")),
        _safe_float(fmt.get("tbr")),
        _safe_float(fmt.get("asr")),
    )


def _clean_external_tool_error(error):
    message = re.sub(r"\x1b\[[0-9;]*m", "", str(error or "")).strip()
    if "ERROR:" in message:
        message = message.split("ERROR:", 1)[1].strip()
    return message