"""Read the active Matugen palette and generate the website's theme.css.

The local Quickshell palette is the source of truth. If it is missing (for
example on a GitHub Actions runner), an existing generated theme is preserved,
and a bundled fallback is used only when no theme file exists yet.
"""

from __future__ import annotations

import colorsys
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COLORS_PATH = Path(
    os.environ.get("QUICKSHELL_COLORS", Path.home() / ".config" / "quickshell" / "Colors.qml")
)
THEME_PATH = ROOT / "docs" / "theme.css"

DEFAULT_COLORS = {
    "background": "#eff1f5",
    "surface": "#eff1f5",
    "surfaceContainer": "#e6e9ef",
    "surfaceContainerHigh": "#dce0e8",
    "foreground": "#4c4f69",
    "foregroundMuted": "#9ca0b0",
    "primary": "#8839ef",
    "primaryText": "#eff1f5",
    "primaryContainer": "#d2bdf3",
    "primaryContainerText": "#4c4f69",
    "tertiary": "#179299",
    "error": "#d20f39",
    "errorText": "#eff1f5",
    "outline": "#9ca0b0",
    "outlineVariant": "#acb0be",
}

ROLES = list(DEFAULT_COLORS)
HEX_RE = re.compile(r'readonly\s+property\s+color\s+(\w+)\s*:\s*"(#[0-9a-fA-F]{6})"')


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _rgb_to_hex(red: float, green: float, blue: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        *(max(0, min(255, round(channel * 255))) for channel in (red, green, blue))
    )


def _hls(value: str) -> tuple[float, float, float]:
    return colorsys.rgb_to_hls(*_hex_to_rgb(value))


def _hsl_hex(hue: float, lightness: float, saturation: float) -> str:
    return _rgb_to_hex(*colorsys.hls_to_rgb(hue % 1.0, max(0.0, min(1.0, lightness)), max(0.0, min(1.0, saturation))))


def _rgba(value: str, alpha: float) -> str:
    red, green, blue = _hex_to_rgb(value)
    return f"rgba({round(red * 255)}, {round(green * 255)}, {round(blue * 255)}, {alpha:.2f})"


def _is_light(colors: dict[str, str]) -> bool:
    # colorsys returns (hue, lightness, saturation).
    return _hls(colors["surface"])[1] > 0.55


def _derive_dark(base: dict[str, str]) -> dict[str, str]:
    surface_h, surface_l, surface_s = _hls(base["surface"])
    primary_h, primary_l, primary_s = _hls(base["primary"])
    tertiary_h, tertiary_l, tertiary_s = _hls(base["tertiary"])
    error_h, error_l, error_s = _hls(base["error"])
    tint_h = primary_h if primary_s > 0.04 else surface_h

    surface = _hsl_hex(tint_h, 0.08, 0.10)
    return {
        "background": _hsl_hex(tint_h, 0.06, 0.07),
        "surface": surface,
        "surfaceContainer": _hsl_hex(tint_h, 0.10, 0.12),
        "surfaceContainerHigh": _hsl_hex(tint_h, 0.11, 0.16),
        "foreground": _hsl_hex(surface_h, 0.90, 0.12),
        "foregroundMuted": _hsl_hex(surface_h, 0.64, 0.08),
        "primary": _hsl_hex(primary_h, max(primary_l, 0.70), max(primary_s, 0.45)),
        "primaryText": _hsl_hex(primary_h, 0.10, 0.25),
        "primaryContainer": _hsl_hex(primary_h, 0.24, min(max(primary_s * 0.8, 0.30), 0.45)),
        "primaryContainerText": _hsl_hex(primary_h, 0.91, 0.15),
        "tertiary": _hsl_hex(tertiary_h, max(tertiary_l, 0.66), max(tertiary_s, 0.45)),
        "error": _hsl_hex(error_h, max(error_l, 0.66), max(error_s, 0.55)),
        "errorText": _hsl_hex(error_h, 0.10, 0.25),
        "outline": _hsl_hex(surface_h, 0.46, 0.08),
        "outlineVariant": _hsl_hex(surface_h, 0.30, 0.08),
    }


def _derive_light(base: dict[str, str]) -> dict[str, str]:
    surface_h, surface_l, surface_s = _hls(base["surface"])
    primary_h, primary_l, primary_s = _hls(base["primary"])
    tertiary_h, tertiary_l, tertiary_s = _hls(base["tertiary"])
    error_h, error_l, error_s = _hls(base["error"])
    tint_h = primary_h if primary_s > 0.04 else surface_h

    return {
        "background": _hsl_hex(tint_h, 0.97, 0.04),
        "surface": _hsl_hex(tint_h, 0.96, 0.04),
        "surfaceContainer": _hsl_hex(tint_h, 0.93, 0.05),
        "surfaceContainerHigh": _hsl_hex(tint_h, 0.88, 0.06),
        "foreground": _hsl_hex(surface_h, 0.20, 0.14),
        "foregroundMuted": _hsl_hex(surface_h, 0.47, 0.08),
        "primary": _hsl_hex(primary_h, max(0.28, min(primary_l, 0.40)), max(primary_s, 0.55)),
        "primaryText": _hsl_hex(primary_h, 0.98, 0.10),
        "primaryContainer": _hsl_hex(primary_h, 0.88, min(max(primary_s * 0.7, 0.25), 0.40)),
        "primaryContainerText": _hsl_hex(primary_h, 0.20, 0.18),
        "tertiary": _hsl_hex(tertiary_h, max(0.30, min(tertiary_l, 0.42)), max(tertiary_s, 0.45)),
        "error": _hsl_hex(error_h, max(0.30, min(error_l, 0.44)), max(error_s, 0.55)),
        "errorText": _hsl_hex(error_h, 0.98, 0.10),
        "outline": _hsl_hex(surface_h, 0.54, 0.08),
        "outlineVariant": _hsl_hex(surface_h, 0.72, 0.06),
    }


def _block(selector: str, colors: dict[str, str]) -> str:
    lines = [f"{selector} {{"]
    for role in ROLES:
        lines.append(f"    --{role}: {colors[role]};")
    lines.append(f"    --secondary-text: {_rgba(colors['foreground'], 0.80)};")
    lines.append("}")
    return "\n".join(lines)


def _read_palette() -> dict[str, str] | None:
    try:
        text = COLORS_PATH.read_text(encoding="utf-8")
    except OSError:
        return None

    found = dict(HEX_RE.findall(text))
    if not found:
        return None

    colors = dict(DEFAULT_COLORS)
    colors.update({key: value for key, value in found.items() if key in DEFAULT_COLORS})
    return colors


def write_theme_css(force: bool = False) -> bool:
    palette = _read_palette()
    if palette is None and THEME_PATH.exists() and not force:
        return False
    if palette is None:
        palette = dict(DEFAULT_COLORS)

    if _is_light(palette):
        light, dark = palette, _derive_dark(palette)
    else:
        light, dark = _derive_light(palette), palette

    header = (
        "/* Generated by theme.py from ~/.config/quickshell/Colors.qml.\n"
        "   Do not edit by hand; edit the Matugen palette instead. */\n\n"
    )
    css = (
        header
        + _block(":root", palette)
        + "\n\n"
        + _block('[data-theme="light"]', light)
        + "\n\n"
        + _block('[data-theme="dark"]', dark)
        + "\n"
    )

    if THEME_PATH.exists():
        try:
            if THEME_PATH.read_text(encoding="utf-8") == css:
                return False
        except OSError:
            pass

    THEME_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = THEME_PATH.with_suffix(".css.tmp")
    temporary.write_text(css, encoding="utf-8")
    temporary.replace(THEME_PATH)
    return True


if __name__ == "__main__":
    changed = write_theme_css(force=True)
    print(f"Wrote {THEME_PATH}" + ("" if changed else " (unchanged)"))
