"""Pitch detection and correction utilities for sample conversion."""
import numpy as np
import librosa
from flask import current_app


def detect_pitch(audio_path):
    """
    Detect the fundamental frequency of an audio file.

    Args:
        audio_path: Path to the audio file to analyze

    Returns:
        float: Median fundamental frequency in Hz, or None if detection fails
    """
    try:
        # Load audio file (librosa resamples to 22050 Hz by default, but we'll use native rate)
        y, sr = librosa.load(audio_path, sr=None, mono=True)

        # Use pYIN algorithm for pitch detection
        # Range: A2 (110 Hz) to A6 (1760 Hz) covers typical synth samples
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('A2'),  # 110 Hz
            fmax=librosa.note_to_hz('A6'),   # 1760 Hz
            sr=sr  # Pass the actual sample rate
        )

        # Get median of voiced frames only
        voiced_freqs = f0[voiced_flag]
        if len(voiced_freqs) == 0:
            return None

        return float(np.median(voiced_freqs))
    except Exception as e:
        # Log the exception for debugging but return None gracefully
        if current_app:
            current_app.logger.error(f"Pitch detection exception: {e}")
        return None


def find_nearest_a(frequency_hz):
    """
    Find the nearest A note (110, 220, 440, 880, 1760 Hz) to a given frequency.

    Args:
        frequency_hz: Detected fundamental frequency in Hz

    Returns:
        tuple: (target_freq_hz, semitone_shift)
            - target_freq_hz: The closest A note frequency
            - semitone_shift: Number of semitones to shift (positive = up, negative = down)
    """
    # A notes in Hz
    a_notes = [110, 220, 440, 880, 1760]

    # Find closest A
    closest_a = min(a_notes, key=lambda a: abs(frequency_hz - a))

    # Calculate semitone shift: 12 * log2(target / detected)
    semitone_shift = 12 * np.log2(closest_a / frequency_hz)

    return closest_a, semitone_shift


def calculate_pitch_shift_params(semitones):
    """
    Calculate FFmpeg filter parameters for pitch shifting.

    Args:
        semitones: Number of semitones to shift (positive = up, negative = down)

    Returns:
        tuple: (asetrate_ratio, atempo_ratio) for FFmpeg filters
    """
    # Pitch shift formula: ratio = 2^(semitones/12)
    pitch_ratio = 2 ** (semitones / 12)

    # asetrate changes both pitch AND tempo
    # atempo corrects the tempo back to normal
    asetrate_ratio = pitch_ratio
    atempo_ratio = 1.0 / pitch_ratio

    # Clamp atempo to FFmpeg's valid range [0.5, 100.0]
    atempo_ratio = max(0.5, min(100.0, atempo_ratio))

    return asetrate_ratio, atempo_ratio