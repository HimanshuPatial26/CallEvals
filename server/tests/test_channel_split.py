import numpy as np
import pytest
import soundfile as sf

from app.audio.channel_split import NotDualChannelError, is_dual_channel, split_channels
from app.config import settings


def _write_wav(path, channels: int, sample_rate: int = 16000, duration_s: float = 0.1):
    samples = int(sample_rate * duration_s)
    if channels == 1:
        data = np.zeros(samples, dtype="float32")
    else:
        data = np.zeros((samples, channels), dtype="float32")
        data[:, 0] = 0.1  # rep track distinguishable from customer track
    sf.write(str(path), data, sample_rate)


def test_is_dual_channel_true_for_stereo(tmp_path):
    path = tmp_path / "stereo.wav"
    _write_wav(path, channels=2)
    assert is_dual_channel(path) is True


def test_is_dual_channel_false_for_mono(tmp_path):
    path = tmp_path / "mono.wav"
    _write_wav(path, channels=1)
    assert is_dual_channel(path) is False


def test_split_channels_separates_tracks(tmp_path):
    path = tmp_path / "stereo.wav"
    _write_wav(path, channels=2)

    rep, customer, sample_rate = split_channels(path)

    assert sample_rate == 16000
    assert rep.mean() == pytest.approx(0.1, abs=1e-3)
    assert customer.mean() == pytest.approx(0.0, abs=1e-3)


def test_split_channels_rejects_mono(tmp_path):
    path = tmp_path / "mono.wav"
    _write_wav(path, channels=1)

    with pytest.raises(NotDualChannelError):
        split_channels(path)


def test_split_channels_respects_rep_channel_index_override(tmp_path, monkeypatch):
    """Reproduces the reported bug: a dialer that exports the rep on channel 1
    instead of the assumed channel 0. REP_CHANNEL_INDEX=1 should flip which
    physical channel comes back as the rep track."""
    path = tmp_path / "stereo.wav"
    _write_wav(path, channels=2)  # channel 0 is the loud track, channel 1 is silent

    monkeypatch.setattr(settings, "rep_channel_index", 1)
    rep, customer, _ = split_channels(path)

    assert rep.mean() == pytest.approx(0.0, abs=1e-3)  # now the silent (customer) track
    assert customer.mean() == pytest.approx(0.1, abs=1e-3)  # now the loud (rep) track
