from dataclasses import dataclass


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
