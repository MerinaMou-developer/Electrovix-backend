from django.conf import settings


def absolute_media_url(image_field, request=None):
    """Return a browser-ready image URL (Cloudinary HTTPS or backend absolute path)."""
    if not image_field:
        return _fallback_url(request)

    try:
        url = image_field.url
    except (ValueError, AttributeError):
        return _fallback_url(request)

    if url.startswith("http://") or url.startswith("https://"):
        return url

    path = url if url.startswith("/") else f"/{url}"
    if request is not None:
        return request.build_absolute_uri(path)

    base = getattr(settings, "BACKEND_BASE_URL", "").rstrip("/")
    if base:
        return f"{base}{path}"
    return path


def _fallback_url(request=None):
    path = "/images/placeholder.png"
    if request is not None:
        return request.build_absolute_uri(path)
    base = getattr(settings, "BACKEND_BASE_URL", "").rstrip("/")
    return f"{base}{path}" if base else path
