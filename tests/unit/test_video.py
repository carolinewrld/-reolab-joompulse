from __future__ import annotations

import shutil
import subprocess

import pytest

from joompulse.ai.video import FfmpegMissing, sample_frames_from_bytes

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def test_raises_when_ffmpeg_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(FfmpegMissing):
        sample_frames_from_bytes(b"not-a-video")


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_samples_frames_from_synthetic_video(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # Generate a 2-second 30fps test clip with ffmpeg itself.
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=64x64:rate=30",
            "-pix_fmt", "yuv420p",
            str(clip),
        ],
        check=True,
    )
    frames = sample_frames_from_bytes(clip.read_bytes(), fps=2, max_frames=5)
    assert 1 <= len(frames) <= 5
    assert all(f.jpeg[:3] == b"\xff\xd8\xff" for f in frames)  # JPEG SOI marker
