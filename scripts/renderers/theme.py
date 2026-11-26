import hashlib
import html

# Paleta pastel de contraste dual: calibrada para legibilidad simultánea
# sobre GitHub Light (#FFFFFF) y GitHub Dark (#0D1117) con hex directos.
PALETTE = {
    "blue": "#4A90D9",      # Azul pastel medio
    "mint": "#3DA372",      # Menta equilibrado
    "lavender": "#8B6BB7",  # Lavanda definido
    "peach": "#D97B54",     # Durazno terracota suave
    "coral": "#D95F69",     # Coral suave
    "yellow": "#C49A1A",    # Ámbar pastel / dorado suave
    "cyan": "#2E86AB",      # Cian océano suave
    "pink": "#C86490",      # Rosa pastel medio
    "neutral": "#768390",   # Gris neutro dual de GitHub
}

LANG_COLORS = [
    PALETTE["blue"],
    PALETTE["lavender"],
    PALETTE["mint"],
    PALETTE["peach"],
    PALETTE["yellow"],
    PALETTE["cyan"],
    PALETTE["pink"],
    PALETTE["coral"],
]

LANGUAGE_COLOR_MAP: dict[str, str] = {
    "typescript": PALETTE["blue"],
    "tsx": PALETTE["blue"],
    "javascript": PALETTE["yellow"],
    "jsx": PALETTE["yellow"],
    "python": PALETTE["mint"],
    "dart": PALETTE["cyan"],
    "c#": PALETTE["lavender"],
    "csharp": PALETTE["lavender"],
    "java": PALETTE["peach"],
    "c++": PALETTE["pink"],
    "cpp": PALETTE["pink"],
    "c": PALETTE["blue"],
    "html": PALETTE["coral"],
    "css": PALETTE["lavender"],
    "scss": PALETTE["pink"],
    "sql": PALETTE["cyan"],
    "shell": PALETTE["mint"],
    "bash": PALETTE["mint"],
    "powershell": PALETTE["blue"],
    "go": PALETTE["cyan"],
    "rust": PALETTE["peach"],
    "kotlin": PALETTE["lavender"],
    "swift": PALETTE["coral"],
    "php": PALETTE["lavender"],
    "ruby": PALETTE["coral"],
    "otros": PALETTE["neutral"],
    "other": PALETTE["neutral"],
}


def get_language_color(lang_name: str, fallback_idx: int = 0) -> str:
    """Devuelve siempre el mismo color pastel dual para un lenguaje dado."""
    key = (lang_name or "").strip().lower()
    if not key:
        return LANG_COLORS[fallback_idx % len(LANG_COLORS)]
    if key in LANGUAGE_COLOR_MAP:
        return LANGUAGE_COLOR_MAP[key]

    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    slot = int(digest[:8], 16) % len(LANG_COLORS)
    return LANG_COLORS[slot]


def format_compact_number(value: int | float | str) -> str:
    """Formatea enteros con separador de miles o sufijo k para mantener alineación."""
    if isinstance(value, (int, float)):
        num = int(value)
        if num >= 100_000:
            return f"{num / 1_000:.0f}k"
        if num >= 10_000:
            return f"{num / 1_000:.1f}k"
        return f"{num:,}"
    return str(value)


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)
