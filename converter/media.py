import shutil
import subprocess
from pathlib import Path


def convert_media(
    source_path: Path,
    output_path: Path,
    target_format: str,
    settings: dict | None = None,
) -> Path:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("FFmpeg is not installed. Install it with: sudo apt install ffmpeg")

    settings = settings or {}
    tgt = target_format.lower().lstrip(".")
    crf = int(settings.get("crf", 24))
    scale = float(settings.get("scale", 1.0))
    strip_meta = bool(settings.get("strip_meta", False))

    cmd = [ffmpeg_bin, "-y", "-i", str(source_path)]
    if strip_meta:
        cmd.extend(["-map_metadata", "-1"])

    if tgt == "gif":
        fps = 12
        width = int(480 * scale)
        cmd.extend(["-vf", f"fps={fps},scale={width}:-1:flags=lanczos", str(output_path)])
    elif tgt == "mp3":
        cmd.extend(["-vn", "-ab", "192k", str(output_path)])
    elif tgt == "m4a":
        cmd.extend(["-vn", "-c:a", "aac", "-b:a", "192k", str(output_path)])
    elif tgt == "opus":
        cmd.extend(["-vn", "-c:a", "libopus", "-b:a", "128k", str(output_path)])
    elif tgt == "aiff":
        cmd.extend(["-vn", "-c:a", "pcm_s16be", str(output_path)])
    elif tgt == "wma":
        cmd.extend(["-vn", "-c:a", "wmav2", "-b:a", "192k", str(output_path)])
    elif tgt in {"wav", "flac", "ogg"}:
        cmd.extend(["-vn", str(output_path)])
    elif tgt in {"mp4", "mov", "mkv", "webm", "avi", "wmv"}:
        if scale < 1.0:
            cmd.extend(["-vf", f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"])
        if tgt in {"mp4", "mov", "mkv"}:
            cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-c:a", "aac", str(output_path)])
        else:
            cmd.append(str(output_path))
    else:
        cmd.append(str(output_path))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"FFmpeg conversion failed: {result.stderr[-200:]}")

    return output_path
