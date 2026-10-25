from pathlib import Path
from typing import List

IMAGE_FORMATS = {
    "png", "jpg", "jpeg", "webp", "bmp", "ico", "tiff", "gif",
    "heic", "heif", "avif", "svg",
}
DOCUMENT_FORMATS = {"pdf", "docx", "txt", "md", "html"}
EBOOK_FORMATS = {"epub", "fb2", "xps", "cbz"}
DATA_FORMATS = {"json", "yaml", "yml", "toml", "xml", "csv", "xlsx"}
VIDEO_FORMATS = {"mp4", "mkv", "webm", "avi", "mov"}
AUDIO_FORMATS = {"mp3", "wav", "flac", "ogg", "m4a"}
MEDIA_FORMATS = VIDEO_FORMATS | AUDIO_FORMATS

SUPPORTED_TARGETS = {
    # Standard & Next-Gen Images (including OCR to TXT/DOCX)
    "png": ["JPG", "WEBP", "PDF", "ICO", "TXT", "DOCX"],
    "jpg": ["PNG", "WEBP", "PDF", "ICO", "TXT", "DOCX"],
    "jpeg": ["PNG", "WEBP", "PDF", "ICO", "TXT", "DOCX"],
    "webp": ["PNG", "JPG", "PDF", "ICO", "TXT", "DOCX"],
    "bmp": ["PNG", "JPG", "WEBP", "PDF", "TXT", "DOCX"],
    "gif": ["PNG", "JPG", "WEBP", "MP4", "PDF"],
    "tiff": ["PNG", "JPG", "WEBP", "PDF", "TXT", "DOCX"],
    "ico": ["PNG", "JPG", "WEBP"],
    "heic": ["JPG", "PNG", "WEBP", "PDF", "TXT", "DOCX"],
    "heif": ["JPG", "PNG", "WEBP", "PDF", "TXT", "DOCX"],
    "avif": ["PNG", "JPG", "WEBP", "PDF", "TXT", "DOCX"],
    "svg": ["PNG", "PDF", "JPG", "WEBP", "ICO"],
    # PDF (Layout DOCX, Excel/CSV Table Extraction, HTML, PNG, OCR TXT)
    "pdf": ["DOCX", "XLSX", "CSV", "TXT", "HTML", "PNG"],
    # Office & Markup Documents
    "docx": ["PDF", "TXT", "MD", "HTML"],
    "txt": ["PDF", "DOCX", "MD", "HTML"],
    "md": ["PDF", "DOCX", "HTML", "TXT"],
    "html": ["PDF", "DOCX", "MD", "TXT"],
    # E-Books & Comic Archives
    "epub": ["PDF", "DOCX", "TXT", "HTML", "PNG"],
    "fb2": ["PDF", "DOCX", "TXT", "HTML", "PNG"],
    "xps": ["PDF", "DOCX", "TXT", "HTML", "PNG"],
    "cbz": ["PDF", "PNG"],
    # Developer Data & Spreadsheets
    "json": ["XLSX", "CSV", "YAML", "TOML", "XML"],
    "yaml": ["JSON", "TOML", "XLSX", "CSV", "XML"],
    "yml": ["JSON", "TOML", "XLSX", "CSV", "XML"],
    "toml": ["JSON", "YAML", "XLSX", "CSV", "XML"],
    "xml": ["JSON", "YAML", "XLSX", "CSV"],
    "csv": ["XLSX", "JSON", "YAML", "XML"],
    "xlsx": ["CSV", "JSON", "YAML", "XML"],
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
