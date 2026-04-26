import ast
import re
import uuid
from dataclasses import dataclass, field


EQUALIZER_SCREEN_ID = "equalizer"
EQUALIZER_GAIN_MIN_DB = -20.0
EQUALIZER_GAIN_MAX_DB = 20.0
DEFAULT_EQUALIZER_PRESET_KEY = "flat"
DEFAULT_EQUALIZER_PRESET_ID = f"builtin:{DEFAULT_EQUALIZER_PRESET_KEY}"
DEFAULT_EQUALIZER_PREAMP_DB = 0.0
FALLBACK_EQUALIZER_FREQUENCIES_HZ = [60.0, 170.0, 310.0, 600.0, 1000.0, 3000.0, 6000.0, 12000.0, 14000.0, 16000.0]
PRESET_SOURCE_BUILTIN = "builtin"
PRESET_SOURCE_CUSTOM = "custom"


BUILTIN_PRESET_LABELS = {
    "flat": "Padrão",
    "classical": "Clássico",
    "club": "Club",
    "dance": "Dance",
    "fullbass": "Graves profundos",
    "fullbasstreble": "Graves e agudos",
    "fulltreble": "Agudos realçados",
    "headphones": "Fones de ouvido",
    "largehall": "Sala ampla",
    "live": "Ao vivo",
    "party": "Festa",
    "pop": "Pop",
    "reggae": "Reggae",
    "rock": "Rock",
    "ska": "Ska",
    "soft": "Suave",
    "softrock": "Rock suave",
    "techno": "Techno",
}

BUILTIN_PRESET_DESCRIPTIONS = {
    "flat": "Curva neutra, útil para manter o som original da mídia.",
    "classical": "Realça definição e brilho sem exagerar nos graves.",
    "club": "Empurra graves e agudos para uma escuta mais animada.",
    "dance": "Dá mais impacto ao grave e mais brilho ao topo.",
    "fullbass": "Prioriza subgraves e graves para dar mais peso à batida.",
    "fullbasstreble": "Curva em V com graves fortes e agudos brilhantes.",
    "fulltreble": "Destaca detalhes, pratos, vozes e brilho geral.",
    "headphones": "Equilíbrio pensado para fones com sensação de clareza.",
    "largehall": "Cria uma sensação mais aberta e ampla no som.",
    "live": "Tenta trazer presença de palco e mais ambiência.",
    "party": "Curva divertida para volumes casuais e músicas animadas.",
    "pop": "Favorece voz, brilho e graves limpos para pop moderno.",
    "reggae": "Dá mais corpo aos graves com médios mais relaxados.",
    "rock": "Realça ataque de guitarras, caixa e presença geral.",
    "ska": "Mantém baixo firme com médios e agudos vivos.",
    "soft": "Escuta suave para reduzir agressividade em faixas brilhantes.",
    "softrock": "Mistura equilíbrio com leve presença de voz e brilho.",
    "techno": "Enfatiza batida, subgrave e brilho eletrônico.",
}

BUILTIN_PRESET_TABLE = {
    "flat": {
        "preamp_db": 12.0,
        "band_gains_db": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    },
    "classical": {
        "preamp_db": 12.0,
        "band_gains_db": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -7.2, -7.2, -7.2, -9.6],
    },
    "club": {
        "preamp_db": 6.0,
        "band_gains_db": [0.0, 0.0, 8.0, 5.6, 5.6, 5.6, 3.2, 0.0, 0.0, 0.0],
    },
    "dance": {
        "preamp_db": 5.0,
        "band_gains_db": [9.6, 7.2, 2.4, 0.0, 0.0, -5.6, -7.2, -7.2, 0.0, 0.0],
    },
    "fullbass": {
        "preamp_db": 5.0,
        "band_gains_db": [-8.0, 9.6, 9.6, 5.6, 1.6, -4.0, -8.0, -10.4, -11.2, -11.2],
    },
    "fullbasstreble": {
        "preamp_db": 4.0,
        "band_gains_db": [7.2, 5.6, 0.0, -7.2, -4.8, 1.6, 8.0, 11.2, 12.0, 12.0],
    },
    "fulltreble": {
        "preamp_db": 3.0,
        "band_gains_db": [-9.6, -9.6, -9.6, -4.0, 2.4, 11.2, 16.0, 16.0, 16.0, 16.8],
    },
    "headphones": {
        "preamp_db": 4.0,
        "band_gains_db": [4.8, 11.2, 5.6, -3.2, -2.4, 1.6, 4.8, 9.6, 12.8, 14.4],
    },
    "largehall": {
        "preamp_db": 5.0,
        "band_gains_db": [10.4, 10.4, 5.6, 5.6, 0.0, -4.8, -4.8, -4.8, 0.0, 0.0],
    },
    "live": {
        "preamp_db": 7.0,
        "band_gains_db": [-4.8, 0.0, 4.0, 5.6, 5.6, 5.6, 4.0, 2.4, 2.4, 2.4],
    },
    "party": {
        "preamp_db": 6.0,
        "band_gains_db": [7.2, 7.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 7.2, 7.2],
    },
    "pop": {
        "preamp_db": 6.0,
        "band_gains_db": [-1.6, 4.8, 7.2, 8.0, 5.6, 0.0, -2.4, -2.4, -1.6, -1.6],
    },
    "reggae": {
        "preamp_db": 8.0,
        "band_gains_db": [0.0, 0.0, 0.0, -5.6, 0.0, 6.4, 6.4, 0.0, 0.0, 0.0],
    },
    "rock": {
        "preamp_db": 5.0,
        "band_gains_db": [8.0, 4.8, -5.6, -8.0, -3.2, 4.0, 8.8, 11.2, 11.2, 11.2],
    },
    "ska": {
        "preamp_db": 6.0,
        "band_gains_db": [-2.4, -4.8, -4.0, 0.0, 4.0, 5.6, 8.8, 9.6, 11.2, 9.6],
    },
    "soft": {
        "preamp_db": 5.0,
        "band_gains_db": [4.8, 1.6, 0.0, -2.4, 0.0, 4.0, 8.0, 9.6, 11.2, 12.0],
    },
    "softrock": {
        "preamp_db": 7.0,
        "band_gains_db": [4.0, 4.0, 2.4, 0.0, -4.0, -5.6, -3.2, 0.0, 2.4, 8.8],
    },
    "techno": {
        "preamp_db": 5.0,
        "band_gains_db": [8.0, 5.6, 0.0, -5.6, -4.8, 0.0, 8.0, 9.6, 9.6, 8.8],
    },
}


@dataclass
class EqualizerPreset:
    preset_id: str
    name: str
    preamp_db: float = DEFAULT_EQUALIZER_PREAMP_DB
    band_gains_db: list[float] = field(default_factory=list)
    source: str = PRESET_SOURCE_CUSTOM
    builtin_key: str | None = None
    description: str = ""

    @property
    def is_builtin(self):
        return self.source == PRESET_SOURCE_BUILTIN

    def to_dict(self):
        return {
            "id": self.preset_id,
            "name": self.name,
            "preamp_db": self.preamp_db,
            "band_gains_db": list(self.band_gains_db),
        }

    @classmethod
    def from_dict(cls, data, *, fallback_band_count=None):
        preset_name = str(data.get("name") or "Preset personalizado").strip() or "Preset personalizado"
        preset_id = str(data.get("id") or "").strip()
        if not preset_id.startswith(f"{PRESET_SOURCE_CUSTOM}:"):
            preset_id = generate_custom_preset_id()

        raw_bands = data.get("band_gains_db")
        if not isinstance(raw_bands, list):
            raw_bands = []

        band_count = len(raw_bands)
        if fallback_band_count is not None and fallback_band_count > 0:
            band_count = fallback_band_count
        elif band_count <= 0:
            band_count = len(FALLBACK_EQUALIZER_FREQUENCIES_HZ)

        return cls(
            preset_id=preset_id,
            name=preset_name,
            preamp_db=clamp_gain_db(data.get("preamp_db", DEFAULT_EQUALIZER_PREAMP_DB)),
            band_gains_db=normalize_band_gains(raw_bands, expected_count=band_count),
            source=PRESET_SOURCE_CUSTOM,
        )


@dataclass
class EqualizerCatalog:
    band_frequencies_hz: list[float] = field(default_factory=list)
    builtin_presets: list[EqualizerPreset] = field(default_factory=list)

    @property
    def supported(self):
        return bool(self.band_frequencies_hz and self.builtin_presets)


def generate_custom_preset_id():
    return f"{PRESET_SOURCE_CUSTOM}:{uuid.uuid4()}"


def normalize_equalizer_text(value):
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")

    text = str(value or "")
    if len(text) >= 3 and text[0] in ("b", "B") and text[1] in ("'", '"') and text[-1] == text[1]:
        try:
            literal_value = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            literal_value = None

        if isinstance(literal_value, (bytes, bytearray)):
            return bytes(literal_value).decode("utf-8", errors="replace")

    return text


def normalize_builtin_preset_key(preset_key):
    normalized_key = normalize_equalizer_text(preset_key).strip().lower()
    return re.sub(r"[^a-z0-9]+", "", normalized_key)


def build_builtin_preset_id(preset_key):
    normalized_key = normalize_builtin_preset_key(preset_key)
    return f"{PRESET_SOURCE_BUILTIN}:{normalized_key}"


def normalize_equalizer_preset_id(preset_id):
    normalized_preset_id = str(preset_id or "").strip()
    if not normalized_preset_id.startswith(f"{PRESET_SOURCE_BUILTIN}:"):
        return normalized_preset_id

    _source, raw_key = normalized_preset_id.split(":", 1)
    return build_builtin_preset_id(raw_key)


def clamp_gain_db(value):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        numeric_value = DEFAULT_EQUALIZER_PREAMP_DB

    return max(EQUALIZER_GAIN_MIN_DB, min(EQUALIZER_GAIN_MAX_DB, round(numeric_value, 1)))


def normalize_band_gains(values, *, expected_count):
    normalized_values = []
    if isinstance(values, list):
        normalized_values = [clamp_gain_db(value) for value in values]

    if expected_count <= 0:
        return normalized_values

    if len(normalized_values) < expected_count:
        normalized_values.extend([0.0] * (expected_count - len(normalized_values)))
    elif len(normalized_values) > expected_count:
        normalized_values = normalized_values[:expected_count]

    return normalized_values


def normalize_custom_presets(custom_presets, *, expected_band_count):
    normalized_presets = []
    for preset in custom_presets or []:
        if not isinstance(preset, EqualizerPreset):
            continue

        normalized_presets.append(
            EqualizerPreset(
                preset_id=preset.preset_id if preset.preset_id.startswith(f"{PRESET_SOURCE_CUSTOM}:") else generate_custom_preset_id(),
                name=preset.name,
                preamp_db=clamp_gain_db(preset.preamp_db),
                band_gains_db=normalize_band_gains(preset.band_gains_db, expected_count=expected_band_count),
                source=PRESET_SOURCE_CUSTOM,
                description=preset.description,
            )
        )

    return normalized_presets


def create_custom_preset(name, preamp_db, band_gains_db, *, preset_id=None):
    normalized_name = str(name or "").strip() or "Preset personalizado"
    normalized_bands = normalize_band_gains(
        list(band_gains_db or []),
        expected_count=len(list(band_gains_db or [])) or len(FALLBACK_EQUALIZER_FREQUENCIES_HZ),
    )
    return EqualizerPreset(
        preset_id=preset_id or generate_custom_preset_id(),
        name=normalized_name,
        preamp_db=clamp_gain_db(preamp_db),
        band_gains_db=normalized_bands,
        source=PRESET_SOURCE_CUSTOM,
    )


def format_frequency_label(frequency_hz):
    try:
        numeric_frequency = float(frequency_hz)
    except (TypeError, ValueError):
        return "Frequência"

    if numeric_frequency >= 1000:
        rounded_khz = numeric_frequency / 1000
        if rounded_khz.is_integer():
            return f"{int(rounded_khz)} kHz"
        return f"{rounded_khz:.1f} kHz"

    if numeric_frequency.is_integer():
        return f"{int(numeric_frequency)} Hz"
    return f"{numeric_frequency:.0f} Hz"
