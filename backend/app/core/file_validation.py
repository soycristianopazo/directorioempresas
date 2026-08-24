"""Valida que el contenido real de un archivo subido coincida con el
Content-Type declarado, por firma de bytes (magic numbers) — el header
Content-Type de un multipart lo pone el cliente y no es una garantía sobre
el contenido real, solo una afirmación. Sin esto, alguien puede subir un
HTML/SVG con script embebido declarándolo image/png y servirlo luego desde
el bucket público org-media.
"""

from __future__ import annotations

_IMAGE_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
}


def matches_declared_image_type(content: bytes, content_type: str) -> bool:
    if content_type == "image/webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    signatures = _IMAGE_SIGNATURES.get(content_type)
    if not signatures:
        return False
    return any(content.startswith(sig) for sig in signatures)


def matches_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-"
