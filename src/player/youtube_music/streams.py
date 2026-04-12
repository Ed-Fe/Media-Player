import re

from .playlists import is_youtube_music_media


def resolve_stream_url(media_path):
    normalized_media_path = str(media_path or "").strip()
    if not is_youtube_music_media(normalized_media_path):
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


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clean_external_tool_error(error):
    message = re.sub(r"\x1b\[[0-9;]*m", "", str(error or "")).strip()
    if "ERROR:" in message:
        message = message.split("ERROR:", 1)[1].strip()
    return message
