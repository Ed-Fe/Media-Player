import os

from .auth import (
    YTMUSIC_BROWSER_AUTH_FILE_NAME,
    get_browser_auth_file_path,
    prepare_browser_auth_input,
    read_auth_file_text,
)
from .models import YouTubeMusicPlaylistContent, YouTubeMusicPlaylistSummary
from .playlists import (
    build_playlist_source as build_playlist_source_fn,
    build_watch_url as build_watch_url_fn,
    extract_personalized_mix_summaries,
    is_watch_playlist_id,
    is_youtube_music_media as is_youtube_music_media_fn,
    playlist_track_count_text,
    track_display_label,
)
from .streams import resolve_stream_url as resolve_music_stream_url


class YouTubeMusicService:
    def __init__(self):
        self._client = None
        self._account_info = None

    @property
    def browser_auth_file_path(self):
        return get_browser_auth_file_path()

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
            normalized_headers_raw = prepare_browser_auth_input(
                read_auth_file_text(normalized_source_file_path),
                source_name=os.path.basename(normalized_source_file_path),
            )
        else:
            normalized_headers_raw = prepare_browser_auth_input(headers_raw, source_name="texto colado")

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

            track_count_text = playlist_track_count_text(item)
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

        for item in extract_personalized_mix_summaries(home_rows):
            if item.playlist_id in seen_playlist_ids:
                continue
            playlists.append(item)
            seen_playlist_ids.add(item.playlist_id)

        playlists.sort(key=lambda playlist: playlist.title.casefold())
        return playlists

    def get_playlist_content(self, playlist_id, fallback_title=""):
        client = self.get_client()
        normalized_playlist_id = str(playlist_id or "").strip()

        if is_watch_playlist_id(normalized_playlist_id):
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
            item_labels.append(track_display_label(track))

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
        return resolve_music_stream_url(media_path)

    def build_watch_url(self, video_id, playlist_id=None):
        return build_watch_url_fn(video_id, playlist_id=playlist_id)

    def build_playlist_source(self, playlist_id):
        return build_playlist_source_fn(playlist_id)

    @staticmethod
    def is_youtube_music_media(media_path):
        return is_youtube_music_media_fn(media_path)
