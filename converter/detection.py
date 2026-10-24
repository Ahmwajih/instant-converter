from pathlib import Path
from typing import List

IMAGE_FORMATS = {"png", "jpg", "jpeg", "webp", "bmp", "ico", "tiff", "gif"}
DOCUMENT_FORMATS = {"pdf", "docx", "txt", "md", "html"}
VIDEO_FORMATS = {"mp4", "mkv", "webm", "avi", "mov"}
AUDIO_FORMATS = {"mp3", "wav", "flac", "ogg", "m4a"}
MEDIA_FORMATS = VIDEO_FORMATS | AUDIO_FORMATS

SUPPORTED_TARGETS = {
    # Images
    "png": ["JPG", "WEBP", "BMP", "ICO", "PDF"],
    "jpg": ["PNG", "WEBP", "BMP", "ICO", "PDF"],
    "jpeg": ["PNG", "WEBP", "BMP", "ICO", "PDF"],
    "webp": ["PNG", "JPG", "BMP", "ICO", "PDF"],
    "bmp": ["PNG", "JPG", "WEBP", "ICO", "PDF"],
    "gif": ["PNG", "JPG", "WEBP", "MP4", "PDF"],
    "tiff": ["PNG", "JPG", "WEBP", "PDF"],
    "ico": ["PNG", "JPG", "WEBP"],
    # Documents & Text
    "pdf": ["DOCX", "TXT", "MD", "HTML", "PNG"],
    "docx": ["PDF", "TXT", "MD", "HTML"],
    "txt": ["PDF", "DOCX", "MD", "HTML"],
    "md": ["PDF", "DOCX", "HTML", "TXT"],
    "html": ["PDF", "DOCX", "MD", "TXT"],
    # Video
    "mp4": ["WEBM", "MKV", "MP3", "WAV", "GIF"],
    "mkv": ["MP4", "WEBM", "MP3", "WAV", "GIF"],
    "webm": ["MP4", "MKV", "MP3", "WAV", "GIF"],
    "avi": ["MP4", "WEBM", "MP3", "WAV", "GIF"],
    "mov": ["MP4", "WEBM", "MP3", "WAV", "GIF"],
    # Audio
    "mp3": ["WAV", "FLAC", "OGG"],
    "wav": ["MP3", "FLAC", "OGG"],
    "flac": ["MP3", "WAV", "OGG"],
    "ogg": ["MP3", "WAV", "FLAC"],
    "m4a": ["MP3", "WAV", "FLAC", "OGG"],
}


def get_extension(file_path: Path) -> str:
    return file_path.suffix.lower().lstrip(".")


def is_supported(file_path: Path) -> bool:
    return get_extension(file_path) in SUPPORTED_TARGETS


def get_available_targets(file_path: Path) -> List[str]:
    ext = get_extension(file_path)
    return SUPPORTED_TARGETS.get(ext, [])


def resolve_output_path(source_path: Path, target_ext: str) -> Path:
    clean_ext = target_ext.lower().lstrip(".")
    base_output = source_path.with_suffix(f".{clean_ext}")
    if not base_output.exists() or base_output.resolve() == source_path.resolve():
        if base_output.resolve() == source_path.resolve():
            return source_path.with_name(f"{source_path.stem}_converted.{clean_ext}")
        return base_output

    counter = 1
    while True:
        candidate = source_path.with_name(f"{source_path.stem}_{counter}.{clean_ext}")
        if not candidate.exists():
            return candidate
        counter += 1
