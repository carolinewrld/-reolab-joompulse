"""Video frame sampling via ffmpeg.

Strategy (README §stack): sample at configured FPS, cap at
`video_frames_per_request`, and hand back JPEGs so downstream code can base64
them into Claude Vision content blocks.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class FfmpegMissing(RuntimeError):
    pass


class FfmpegFailed(RuntimeError):
    pass


@dataclass(slots=True)
class SampledFrame:
    index: int
    timestamp_s: float
    jpeg: bytes


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise FfmpegMissing("ffmpeg binary not found in PATH")
    return path


def sample_frames_from_bytes(
    video: bytes,
    *,
    fps: int = 1,
    max_frames: int = 15,
    quality: int = 3,
) -> list[SampledFrame]:
    ffmpeg = _require_ffmpeg()

    with tempfile.TemporaryDirectory(prefix="joompulse-video-") as tmp:
        tmp_path = Path(tmp)
        in_path = tmp_path / "input.mp4"
        in_path.write_bytes(video)
        out_pattern = tmp_path / "frame_%03d.jpg"

        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(in_path),
            "-vf", f"fps={fps}",
            "-frames:v", str(max_frames),
            "-q:v", str(quality),
            str(out_pattern),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise FfmpegFailed(result.stderr.decode(errors="replace"))

        frames: list[SampledFrame] = []
        for i, f in enumerate(sorted(tmp_path.glob("frame_*.jpg"))):
            frames.append(
                SampledFrame(
                    index=i,
                    timestamp_s=i / fps if fps > 0 else 0.0,
                    jpeg=f.read_bytes(),
                )
            )
        return frames
