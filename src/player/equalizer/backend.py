import vlc

from .models import (
    FALLBACK_EQUALIZER_FREQUENCIES_HZ,
    VLC_PRESET_DESCRIPTIONS,
    VLC_PRESET_LABELS,
    EqualizerCatalog,
    EqualizerPreset,
    build_builtin_preset_id,
    clamp_gain_db,
    normalize_band_gains,
    normalize_builtin_preset_key,
    normalize_vlc_text,
)


def load_equalizer_catalog():
    try:
        band_count = int(vlc.libvlc_audio_equalizer_get_band_count())
    except Exception:
        return EqualizerCatalog()

    if band_count <= 0:
        return EqualizerCatalog()

    frequencies = []
    for index in range(band_count):
        try:
            frequency = float(vlc.libvlc_audio_equalizer_get_band_frequency(index))
        except Exception:
            frequency = -1.0

        if frequency <= 0 and index < len(FALLBACK_EQUALIZER_FREQUENCIES_HZ):
            frequency = FALLBACK_EQUALIZER_FREQUENCIES_HZ[index]

        frequencies.append(frequency)

    builtin_presets = []
    try:
        preset_count = int(vlc.libvlc_audio_equalizer_get_preset_count())
    except Exception:
        preset_count = 0

    for preset_index in range(max(0, preset_count)):
        preset_name = normalize_vlc_text(vlc.libvlc_audio_equalizer_get_preset_name(preset_index)).strip()
        if not preset_name:
            continue

        preset_key = normalize_builtin_preset_key(preset_name)
        equalizer = None
        try:
            equalizer = vlc.libvlc_audio_equalizer_new_from_preset(preset_index)
            if equalizer is None:
                continue

            preamp_db = clamp_gain_db(vlc.libvlc_audio_equalizer_get_preamp(equalizer))
            band_gains_db = [
                clamp_gain_db(vlc.libvlc_audio_equalizer_get_amp_at_index(equalizer, band_index))
                for band_index in range(band_count)
            ]
        except Exception:
            continue
        finally:
            if equalizer is not None:
                try:
                    equalizer.release()
                except Exception:
                    pass

        builtin_presets.append(
            EqualizerPreset(
                preset_id=build_builtin_preset_id(preset_key),
                name=VLC_PRESET_LABELS.get(preset_key, preset_name.title()),
                preamp_db=preamp_db,
                band_gains_db=band_gains_db,
                source="builtin",
                builtin_key=preset_key,
                description=VLC_PRESET_DESCRIPTIONS.get(preset_key, f"Preset nativo do VLC: {preset_name}."),
            )
        )

    return EqualizerCatalog(band_frequencies_hz=frequencies, builtin_presets=builtin_presets)


def build_vlc_equalizer(preset, *, band_count):
    if preset is None:
        return None

    try:
        equalizer = vlc.AudioEqualizer()
    except Exception:
        return None

    if equalizer is None:
        return None

    vlc.libvlc_audio_equalizer_set_preamp(equalizer, clamp_gain_db(preset.preamp_db))
    normalized_band_gains = normalize_band_gains(preset.band_gains_db, expected_count=band_count)
    for band_index, gain_db in enumerate(normalized_band_gains):
        vlc.libvlc_audio_equalizer_set_amp_at_index(equalizer, clamp_gain_db(gain_db), band_index)

    return equalizer
