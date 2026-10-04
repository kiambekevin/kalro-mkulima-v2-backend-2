# apps/badges/renderers.py
"""
SVG + PNG rendering for badges.

The SVG mirrors the React `BadgeDesign.jsx` component so the client and
server produce visually identical badges. `cairosvg` handles SVG → PNG,
and `Pillow` writes the final file to storage.
"""
import io
from textwrap import wrap

from django.conf import settings
from django.core.files.base import ContentFile

from .constants import (
    BADGE_PNG_SIZE,
    BRAND_NAME,
    BRAND_SUB,
    BRAND_TAGLINE,
    DEFAULT_ICON,
    DEFAULT_ACCENT,
    DEFAULT_TINT,
)
from .qr import make_qr_png_bytes


def _subject_theme(badge):
    """Resolve a subject's badge theme, falling back to defaults."""
    template = getattr(badge.course.subject, "badge_template", None)
    if template:
        return {
            "tint": template.tint_hex,
            "accent": template.accent_hex,
            "icon": template.icon or DEFAULT_ICON,
            "label": template.display_label,
        }
    return {
        "tint": DEFAULT_TINT,
        "accent": DEFAULT_ACCENT,
        "icon": DEFAULT_ICON,
        "label": badge.course.subject.label,
    }


def _format_date(dt) -> str:
    return dt.strftime("%d %b %Y").upper()


def _wrap_title(title: str, max_chars: int = 42, max_lines: int = 2) -> list[str]:
    lines = wrap(title, width=max_chars)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max_chars - 1].rstrip() + "…"
    return lines


def render_badge_svg(badge) -> bytes:
    """
    Returns the SVG markup as UTF-8 bytes. Pure function — no DB writes.
    Sized to a 480x480 viewBox that cairosvg will scale up on render.
    """
    theme = _subject_theme(badge)
    earned = _format_date(badge.issued_at)
    title_lines = _wrap_title(badge.snapshot.get("course_title") or badge.course.title)
    subject_label = theme["label"].upper()
    level = (badge.snapshot.get("level") or badge.course.level).title()
    hours = badge.snapshot.get("hours") or badge.course.hours

    # SVG uses a fixed viewBox; cairosvg renders at BADGE_PNG_SIZE.
    title_svg_lines = "".join(
        f'<tspan x="240" dy="{0 if i == 0 else 22}">{escape(line)}</tspan>'
        for i, line in enumerate(title_lines)
    )

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="480" height="480" viewBox="0 0 480 480">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{theme['tint']}" />
      <stop offset="100%" stop-color="#0C2B1A" />
    </linearGradient>
    <linearGradient id="ribbon" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{theme['accent']}" />
      <stop offset="100%" stop-color="#B7801A" />
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="480" height="480" fill="#F5F7F2" />
  <circle cx="240" cy="220" r="180" fill="url(#bg)" />

  <!-- Inner rings -->
  <circle cx="240" cy="220" r="158" fill="none"
          stroke="#fff" stroke-opacity=".35" stroke-width="2"
          stroke-dasharray="4 6" />
  <circle cx="240" cy="220" r="146" fill="none"
          stroke="#fff" stroke-opacity=".18" stroke-width="1" />

  <!-- Subject label -->
  <text x="240" y="140" text-anchor="middle"
        font-family="Bricolage Grotesque, system-ui, sans-serif"
        font-size="14" font-weight="800" letter-spacing="3"
        fill="#ffffff" fill-opacity=".85">
    {escape(subject_label)}
  </text>

  <!-- Brand wordmark -->
  <text x="240" y="180" text-anchor="middle"
        font-family="Bricolage Grotesque, system-ui, sans-serif"
        font-size="34" font-weight="800" letter-spacing="-0.5"
        fill="#ffffff">
    {escape(BRAND_NAME)}
  </text>
  <text x="240" y="204" text-anchor="middle"
        font-family="Source Sans 3, system-ui, sans-serif"
        font-size="13" font-weight="600" letter-spacing="2"
        fill="{theme['accent']}">
    {escape(BRAND_SUB)}
  </text>

  <!-- Course title -->
  <text x="240" y="236" text-anchor="middle"
        font-family="Bricolage Grotesque, system-ui, sans-serif"
        font-size="17" font-weight="700"
        fill="#ffffff">
    {title_svg_lines}
  </text>

  <!-- Stats row -->
  <text x="240" y="318" text-anchor="middle"
        font-family="Source Sans 3, system-ui, sans-serif"
        font-size="12" font-weight="600" letter-spacing="1.5"
        fill="#ffffff" fill-opacity=".75">
    {escape(level.upper())} · {hours} HRS
  </text>

  <!-- Ribbon -->
  <g>
    <rect x="90" y="408" width="300" height="44" rx="22"
          fill="url(#ribbon)" />
    <text x="240" y="436" text-anchor="middle"
          font-family="Bricolage Grotesque, system-ui, sans-serif"
          font-size="14" font-weight="800" letter-spacing="2"
          fill="#123B26">
      VERIFIED · {escape(earned)}
    </text>
  </g>

  <!-- Badge ID -->
  <text x="240" y="470" text-anchor="middle"
        font-family="ui-monospace, Menlo, monospace"
        font-size="11" fill="#55655B" letter-spacing="0.5">
    {escape(badge.badge_id)}
  </text>
</svg>
"""
    return svg.encode("utf-8")


def svg_to_png(svg_bytes: bytes, size: int = BADGE_PNG_SIZE) -> bytes:
    """
    Rasterise an SVG into a PNG using cairosvg. Falls back to a plain
    PNG error image if cairosvg isn't installed.
    """
    try:
        import cairosvg
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "cairosvg is required for badge PNG rendering. "
            "Install it via `pip install cairosvg`."
        ) from exc

    return cairosvg.svg2png(
        bytestring=svg_bytes,
        output_width=size,
        output_height=size,
    )


def render_badge_png_bytes(badge) -> bytes:
    """Convenience: SVG → PNG in one call."""
    return svg_to_png(render_badge_svg(badge))


def save_badge_png(badge, *, overwrite: bool = False) -> str:
    """
    Render and store the PNG on the badge instance. Returns the storage
    name. Set `overwrite=True` to force regeneration.
    """
    if badge.png_file and not overwrite:
        return badge.png_file.name

    png_bytes = render_badge_png_bytes(badge)
    filename = f"{badge.badge_id}.png"
    badge.png_file.save(filename, ContentFile(png_bytes), save=True)
    return badge.png_file.name


def render_badge_with_qr_png_bytes(badge, qr_size: int = 180) -> bytes:
    """
    Composite render: badge PNG with a QR code in the bottom-right corner.
    Used for printable certificates and WhatsApp sharing.
    """
    from PIL import Image

    base_png = render_badge_png_bytes(badge)
    qr_png = make_qr_png_bytes(badge.badge_id, box_size=6)

    base = Image.open(io.BytesIO(base_png)).convert("RGBA")
    qr = Image.open(io.BytesIO(qr_png)).convert("RGBA")
    qr = qr.resize((qr_size, qr_size), Image.LANCZOS)

    # Paste QR in bottom-right with a small white frame
    padding = 20
    frame = Image.new("RGBA", (qr_size + padding, qr_size + padding), (255, 255, 255, 255))
    frame.paste(qr, (padding // 2, padding // 2), qr)
    base.alpha_composite(frame, (base.width - frame.width - 16, base.height - frame.height - 16))

    out = io.BytesIO()
    base.save(out, format="PNG", optimize=True)
    return out.getvalue()


def escape(text) -> str:
    """Minimal XML escaping for SVG text nodes."""
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )