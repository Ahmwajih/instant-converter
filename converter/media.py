import shutil
import subprocess
from pathlib import Path


def convert_media(source_path: Path, output_path: Path, target_format: str) -> Path:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError(
            "FFmpeg is not installed. Install it with: sudo apt install ffmpeg"
        )

    tgt = target_format.lower().lstrip(".")
    cmd = [ffmpeg_bin, "-y", "-i", str(source_path)]

    if tgt == "gif":
        cmd.extend(["-vf", "fps=12,scale=480:-1:flags=lanczos", str(output_path)])
    elif tgt == "mp3":
        cmd.extend(["-vn", "-ab", "192k", str(output_path)])
    elif tgt in {"wav", "flac", "ogg"}:
        cmd.extend(["-vn", str(output_path)])
    else:
        cmd.append(str(output_path))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"FFmpeg conversion failed: {result.stderr[-200:]}")

    return output_path
