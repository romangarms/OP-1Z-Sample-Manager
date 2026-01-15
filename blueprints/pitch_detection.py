"""Pitch detection and correction utilities for sample conversion.

Uses YIN algorithm implemented in pure NumPy for lightweight pitch detection.
Based on: de Cheveigné, A., & Kawahara, H. (2002). YIN, a fundamental frequency estimator.
"""
import logging
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# Frequency constants
FMIN = 110.0   # A2
FMAX = 1760.0  # A6


def _difference_function(signal, max_tau):
    """Compute the YIN difference function using FFT-based autocorrelation."""
    n = len(signal)
    # Pad signal for FFT
    padded = np.zeros(2 * n)
    padded[:n] = signal

    # FFT-based autocorrelation (Wiener-Khinchin theorem)
    fft_signal = np.fft.rfft(padded)
    acf = np.fft.irfft(fft_signal * np.conj(fft_signal))[:n]

    # Energy at zero lag
    energy = acf[0]

    # Compute difference function: d(tau) = r(0) - 2*r(tau) + energy_shifted
    # Using cumulative sum for efficiency
    cumsum = np.cumsum(signal ** 2)

    diff = np.zeros(max_tau)
    diff[0] = 0
    for tau in range(1, max_tau):
        # Energy of shifted signal segment
        energy_shifted = cumsum[n - 1] - cumsum[tau - 1] if tau > 0 else cumsum[n - 1]
        energy_orig = cumsum[n - tau - 1] if n - tau - 1 >= 0 else 0
        diff[tau] = energy_orig + energy_shifted - 2 * acf[tau]

    return diff


def _cumulative_mean_normalized_difference(diff):
    """Compute cumulative mean normalized difference function (CMNDF)."""
    cmndf = np.zeros(len(diff))
    cmndf[0] = 1.0

    running_sum = 0.0
    for tau in range(1, len(diff)):
        running_sum += diff[tau]
        cmndf[tau] = diff[tau] / (running_sum / tau) if running_sum > 0 else 1.0

    return cmndf


def _get_pitch(cmndf, sr, fmin, fmax, threshold=0.1):
    """Extract pitch from CMNDF using absolute threshold."""
    min_tau = int(sr / fmax)
    max_tau = min(int(sr / fmin), len(cmndf) - 1)

    # Find first tau below threshold
    for tau in range(min_tau, max_tau):
        if cmndf[tau] < threshold:
            # Parabolic interpolation for sub-sample accuracy
            if tau > 0 and tau < len(cmndf) - 1:
                alpha = cmndf[tau - 1]
                beta = cmndf[tau]
                gamma = cmndf[tau + 1]
                peak = tau + 0.5 * (alpha - gamma) / (alpha - 2 * beta + gamma + 1e-10)
            else:
                peak = tau
            return sr / peak if peak > 0 else None

    # Fallback: find minimum in valid range
    valid_range = cmndf[min_tau:max_tau + 1]
    if len(valid_range) > 0:
        min_idx = np.argmin(valid_range) + min_tau
        if cmndf[min_idx] < 0.5:  # Only return if reasonably confident
            return sr / min_idx

    return None


def detect_pitch(audio_path, max_duration=None):
    """
    Detect the fundamental frequency of an audio file using YIN algorithm.

    Args:
        audio_path: Path to the audio file to analyze
        max_duration: Maximum duration in seconds to analyze (None = entire file)

    Returns:
        float: Median fundamental frequency in Hz, or None if detection fails
    """
    try:
        # Load audio with soundfile
        y, sr = sf.read(audio_path, dtype='float32')

        # Convert stereo to mono if needed
        if len(y.shape) > 1:
            y = np.mean(y, axis=1)

        # Limit duration if specified
        if max_duration is not None:
            max_samples = int(max_duration * sr)
            y = y[:max_samples]

        # YIN parameters
        frame_size = 2048
        hop_size = 512
        max_tau = int(sr / FMIN) + 1

        # Collect pitch estimates from each frame
        pitches = []

        for start in range(0, len(y) - frame_size, hop_size):
            frame = y[start:start + frame_size]

            # Skip silent frames
            if np.max(np.abs(frame)) < 0.01:
                continue

            # Compute YIN
            diff = _difference_function(frame, min(max_tau, frame_size // 2))
            cmndf = _cumulative_mean_normalized_difference(diff)
            pitch = _get_pitch(cmndf, sr, FMIN, FMAX)

            if pitch is not None and FMIN <= pitch <= FMAX:
                pitches.append(pitch)

        if len(pitches) == 0:
            return None

        return float(np.median(pitches))
    except Exception as e:
        logger.error(f"Pitch detection exception: {e}")
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
