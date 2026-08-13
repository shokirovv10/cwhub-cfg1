"""
Fayl yuklash xizmati: kengaytma + MIME tekshiruvi, xavfsiz random nomlash,
va uploads papkasidan tashqariga chiqib ketmasligini kafolatlaydi (path traversal himoyasi).
"""
import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename
from flask import current_app


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _guess_mime(file_storage) -> str:
    mime = file_storage.mimetype
    if not mime or mime == "application/octet-stream":
        guessed, _ = mimetypes.guess_type(file_storage.filename)
        mime = guessed or mime
    return mime or ""


def validate_file(file_storage, allowed_extensions: set, allowed_mimes: set, max_size_bytes: int):
    """Fayl kengaytmasi, MIME turi va hajmini tekshiradi. Xato bo'lsa ValueError ko'taradi."""
    if not file_storage or not file_storage.filename:
        raise ValueError("Fayl tanlanmagan.")

    filename = secure_filename(file_storage.filename)
    ext = _ext(filename)
    if ext not in allowed_extensions:
        raise ValueError(f"Ruxsat etilmagan fayl turi: .{ext}")

    mime = _guess_mime(file_storage)
    if allowed_mimes and mime not in allowed_mimes:
        raise ValueError(f"Ruxsat etilmagan fayl formati (MIME: {mime}).")

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_size_bytes:
        raise ValueError("Fayl hajmi ruxsat etilgan chegaradan katta.")
    if size == 0:
        raise ValueError("Fayl bo'sh.")

    return filename, ext


def save_uploaded_file(file_storage, subdir: str, allowed_extensions: set, allowed_mimes: set) -> str:
    """Faylni tekshirib, random unique nom bilan uploads/<subdir>/ ichiga saqlaydi.
    Qaytaradi: serverda saqlangan fayl nomi (public URL orqali ochilmaydi)."""
    max_size = current_app.config["MAX_CONTENT_LENGTH"]
    _orig_name, ext = validate_file(file_storage, allowed_extensions, allowed_mimes, max_size)

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    os.makedirs(folder, exist_ok=True)

    dest_path = os.path.join(folder, unique_name)
    file_storage.save(dest_path)
    return unique_name


def safe_upload_path(subdir: str, filename: str) -> str:
    """Path traversal'dan himoyalangan holda to'liq faylga yo'lni qaytaradi."""
    filename = secure_filename(filename)
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    full_path = os.path.abspath(os.path.join(folder, filename))
    if not full_path.startswith(os.path.abspath(folder)):
        raise ValueError("Noto'g'ri fayl yo'li.")
    return full_path
