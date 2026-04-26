from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AudioOutputDevice:
	device_id: str
	name: str
	description: str = ""

	@property
	def menu_label(self) -> str:
		normalized_name = str(self.name or "").strip()
		normalized_description = str(self.description or "").strip()
		if normalized_description:
			return normalized_description
		if normalized_name:
			return normalized_name
		return self.device_id or "Dispositivo desconhecido"


def normalize_audio_output_device_id(value) -> str:
	normalized_value = str(value or "").strip()
	if normalized_value.casefold() in {"", "auto", "default"}:
		return ""
	return normalized_value


def audio_output_device_from_mpv_entry(entry) -> AudioOutputDevice | None:
	if not isinstance(entry, dict):
		return None

	raw_device_id = entry.get("name")
	device_id = normalize_audio_output_device_id(raw_device_id)
	normalized_name = str(raw_device_id or "").strip()
	normalized_description = str(entry.get("description") or "").strip()
	if not device_id and not normalized_name and not normalized_description:
		return None

	return AudioOutputDevice(
		device_id=device_id,
		name=normalized_name,
		description=normalized_description,
	)
