from __future__ import annotations

import io
import math
import struct
import wave

from pathlib import Path

import pytest

from meowdb.similarity import MeowSimilarity


def _make_sine_wav(freq_hz: float, duration_s: float = 1.0, sr: int = 44100) -> bytes:
    n_samples = int(sr * duration_s)
    samples = [int(32767 * math.sin(2 * math.pi * freq_hz * i / sr)) for i in range(n_samples)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack(f"<{n_samples}h", *samples))
    return buf.getvalue()


def test_fingerprint_dimension(tmp_path: Path) -> None:
    wav_path = tmp_path / "test.wav"
    wav_path.write_bytes(_make_sine_wav(500.0))
    sim = MeowSimilarity()
    fingerprint = sim.extract_fingerprint(wav_path)
    assert len(fingerprint) == 120


def test_fingerprint_deterministic(tmp_path: Path) -> None:
    wav_path = tmp_path / "test.wav"
    wav_path.write_bytes(_make_sine_wav(500.0))
    sim = MeowSimilarity()
    fp1 = sim.extract_fingerprint(wav_path)
    fp2 = sim.extract_fingerprint(wav_path)
    assert fp1 == fp2


def test_fingerprint_short_audio(tmp_path: Path) -> None:
    # 0.02s ≈ 880 samples — fewer than n_fft=2048, so delta features fall back to zeros
    wav_path = tmp_path / "short.wav"
    wav_path.write_bytes(_make_sine_wav(500.0, duration_s=0.02))
    sim = MeowSimilarity()
    fingerprint = sim.extract_fingerprint(wav_path)
    assert len(fingerprint) == 120


def test_scores_empty() -> None:
    sim = MeowSimilarity()
    assert sim.compute_uniqueness_scores({}) == {}


def test_scores_single() -> None:
    sim = MeowSimilarity()
    result = sim.compute_uniqueness_scores({"a": [0.0] * 120})
    assert result == {"a": None}


def test_scores_two_identical() -> None:
    sim = MeowSimilarity()
    fingerprints = {
        "a": [0.0] * 120,
        "b": [0.0] * 120,
    }
    result = sim.compute_uniqueness_scores(fingerprints)
    assert result["a"] == pytest.approx(0.0)
    assert result["b"] == pytest.approx(0.0)


def test_scores_percentile_range() -> None:
    sim = MeowSimilarity()
    # 4 identical cluster vectors + 1 antiparallel outlier guarantees the outlier
    # scores 100.0 (most unique) and the cluster members score 0.0 (least unique),
    # covering the full range. Constant-magnitude vectors like [5]*120 vs [10]*120
    # must NOT be used — they're colinear after z-score and all get cos_sim=1.0.
    fingerprints = {
        "a": [1.0, 0.0] * 60,
        "b": [1.0, 0.0] * 60,
        "c": [1.0, 0.0] * 60,
        "d": [1.0, 0.0] * 60,
        "e": [0.0, 1.0] * 60,
    }
    result = sim.compute_uniqueness_scores(fingerprints)
    assert all(s is not None for s in result.values())
    scores = [s for s in result.values() if s is not None]
    assert all(0.0 <= s <= 100.0 for s in scores)
    assert min(scores) == pytest.approx(0.0)
    assert max(scores) == pytest.approx(100.0)


def test_scores_knn_degrades_gracefully() -> None:
    sim = MeowSimilarity(k_neighbors=5)
    fingerprints = {
        "a": [0.0] * 120,
        "b": [1.0] * 120,
    }
    result = sim.compute_uniqueness_scores(fingerprints)
    assert all(s is not None for s in result.values())
    for score in (s for s in result.values() if s is not None):
        assert 0.0 <= score <= 100.0


def test_fingerprint_different_audio(tmp_path: Path) -> None:
    low_path = tmp_path / "low.wav"
    high_path = tmp_path / "high.wav"
    low_path.write_bytes(_make_sine_wav(500.0))
    high_path.write_bytes(_make_sine_wav(3000.0))
    sim = MeowSimilarity()
    fp_low = sim.extract_fingerprint(low_path)
    fp_high = sim.extract_fingerprint(high_path)
    assert fp_low != fp_high
