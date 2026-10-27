from pathlib import Path
from typing import List

IMAGE_FORMATS = {
    "png", "jpg", "jpeg", "webp", "bmp", "ico", "tiff", "gif",
    "heic", "heif", "avif", "svg",
}
DOCUMENT_FORMATS = {"pdf", "docx", "doc", "rtf", "odt", "txt", "md", "html"}
SLIDE_FORMATS = {"ppt", "pptx", "odp"}
SUBTITLE_FORMATS = {"srt", "vtt"}
EBOOK_FORMATS = {"epub", "fb2", "xps", "cbz"}
DATA_FORMATS = {"json", "yaml", "yml", "toml", "xml", "csv", "tsv", "xlsx", "xls", "ods"}
VIDEO_FORMATS = {"mp4", "mkv", "webm", "avi", "mov", "wmv"}
AUDIO_FORMATS = {"mp3", "wav", "flac", "ogg", "m4a", "opus", "aiff", "wma"}
MEDIA_FORMATS = VIDEO_FORMATS | AUDIO_FORMATS

SUPPORTED_TARGETS = {
    "png": ["JPG", "WEBP", "SVG", "AVIF", "PDF", "ICO", "TXT", "DOCX"],
    "jpg": ["PNG", "WEBP", "SVG", "AVIF", "PDF", "ICO", "TXT", "DOCX"],
    "jpeg": ["PNG", "WEBP", "SVG", "AVIF", "PDF", "ICO", "TXT", "DOCX"],
    "webp": ["PNG", "JPG", "SVG", "AVIF", "PDF", "ICO", "TXT", "DOCX"],
    "avif": ["PNG", "JPG", "WEBP", "SVG", "PDF", "TXT", "DOCX"],
    "heic": ["JPG", "PNG", "WEBP", "SVG", "PDF", "TXT", "DOCX"],
    "heif": ["JPG", "PNG", "WEBP", "SVG", "PDF", "TXT", "DOCX"],
    "bmp": ["PNG", "JPG", "WEBP", "SVG", "PDF", "TXT", "DOCX"],
    "tiff": ["PNG", "JPG", "WEBP", "SVG", "PDF", "TXT", "DOCX"],
    "gif": ["MP4", "WEBP", "PNG", "JPG", "PDF"],
    "ico": ["PNG", "SVG", "JPG", "WEBP"],
    "svg": ["PDF", "PNG", "JPG", "WEBP", "ICO"],
    "pdf": ["DOCX", "PPTX", "XLSX", "CSV", "SVG", "JPG", "PNG", "TXT", "MD", "HTML"],
    "docx": ["PDF", "TXT", "MD", "HTML"],
    "doc": ["PDF", "DOCX", "TXT", "HTML"],
    "rtf": ["PDF", "DOCX", "TXT", "MD", "HTML"],
    "odt": ["PDF", "DOCX", "TXT", "HTML"],
    "txt": ["PDF", "DOCX", "MD", "HTML"],
    "md": ["PDF", "DOCX", "HTML", "TXT"],
    "html": ["PDF", "DOCX", "MD", "TXT"],
    "ppt": ["PDF", "PNG", "JPG"],
    "pptx": ["PDF", "PNG", "JPG"],
    "odp": ["PDF", "PPTX", "PNG", "JPG"],
    "xlsx": ["PDF", "CSV", "TSV", "ODS", "JSON", "YAML"],
    "xls": ["XLSX", "PDF", "CSV", "TSV", "JSON"],
    "ods": ["XLSX", "PDF", "CSV", "TSV", "JSON"],
    "csv": ["XLSX", "TSV", "PDF", "JSON", "YAML", "XML"],
    "tsv": ["XLSX", "CSV", "PDF", "JSON", "YAML"],
    "json": ["XLSX", "CSV", "YAML", "TOML", "XML"],
    "yaml": ["JSON", "TOML", "XLSX", "CSV", "XML"],
    "yml": ["JSON", "TOML", "XLSX", "CSV", "XML"],
    "toml": ["JSON", "YAML", "XLSX", "CSV", "XML"],
    "xml": ["JSON", "YAML", "XLSX", "CSV"],
    "srt": ["TXT", "VTT"],
    "vtt": ["TXT", "SRT"],
    "epub": ["PDF", "DOCX", "TXT", "MD", "HTML"],
    "fb2": ["PDF", "DOCX", "TXT", "HTML"],
    "xps": ["PDF", "DOCX", "TXT", "PNG"],
    "cbz": ["PDF", "PNG"],
    "mp4": ["MOV", "MKV", "WEBM", "GIF", "MP3", "WAV"],
    "mov": ["MP4", "MKV", "WEBM", "GIF", "MP3", "WAV"],
    "mkv": ["MP4", "MOV", "WEBM", "GIF", "MP3", "WAV"],
    "webm": ["MP4", "MKV", "GIF", "MP3", "WAV"],
    "avi": ["MP4", "WEBM", "GIF", "MP3", "WAV"],
    "wmv": ["MP4", "WEBM", "GIF", "MP3", "WAV"],
    "mp3": ["M4A", "WAV", "FLAC", "OGG", "OPUS", "AIFF"],
    "m4a": ["MP3", "WAV", "FLAC", "OGG", "OPUS"],
    "wav": ["MP3", "M4A", "FLAC", "OGG", "OPUS", "AIFF"],
    "flac": ["MP3", "M4A", "WAV", "OGG", "OPUS"],
    "ogg": ["MP3", "M4A", "WAV", "FLAC", "OPUS"],
    "opus": ["MP3", "M4A", "WAV", "FLAC", "OGG"],
    "aiff": ["MP3", "M4A", "WAV", "FLAC"],
    "wma": ["MP3", "M4A", "WAV", "FLAC"],
}


def get_extension(file_path: Path) -> str:
    return file_path.suffix.lower().lstrip(".")


def is_supported(file_path: Path) -> bool:
    return get_extension(file_path) in SUPPORTED_TARGETS


def get_available_targets(file_path: Path, mode: str = "convert") -> List[str]:
    ext = get_extension(file_path)
    if mode == "tools":
        tools = ["COMPRESS", "NO-META", "ZIP"]
        if ext == "pdf":
            tools = ["EDIT-PDF", "COMPRESS", "REDACT", "LOCK-PDF", "NO-META", "ALL-PNG", "ZIP"]
        elif ext in DOCUMENT_FORMATS:
            tools = ["EDIT-PDF", "COMPRESS", "NO-META", "ZIP"]
        elif ext in IMAGE_FORMATS:
            tools = ["NO-BG", "COMPRESS", "NO-META", "OCR-TXT", "SVG", "PDF", "ZIP"]
        return tools
    return SUPPORTED_TARGETS.get(ext, [])


def resolve_output_path(source_path: Path, target_ext: str, suffix_tag: str = "") -> Path:
    clean_ext = target_ext.lower().lstrip(".")
    stem = f"{source_path.stem}{suffix_tag}"
    base_output = source_path.with_name(f"{stem}.{clean_ext}")
    if not base_output.exists() or base_output.resolve() == source_path.resolve():
        if base_output.resolve() == source_path.resolve():
            return source_path.with_name(f"{stem}_optimized.{clean_ext}")
        return base_output

    counter = 1
    while True:
        candidate = source_path.with_name(f"{stem}_{counter}.{clean_ext}")
        if not candidate.exists():
            return candidate
        counter += 1
