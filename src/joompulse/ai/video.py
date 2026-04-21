"""ffmpeg frame sampling for video creatives. Implementation in §2 roadmap."""

from __future__ import annotations

from pathlib import Path


def sample_frames(video_path: Path, out_dir: Path, fps: int = 1) -> list[Path]:
    raise NotImplementedError
