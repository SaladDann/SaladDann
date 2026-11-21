import hashlib
import html

PALETTE = {
    "blue": "#A2D2FF",
    "mint": "#B7E4C7",
    "lavender": "#CDB4DB",
    "peach": "#FBC4AB",
    "coral": "#FFADAD",
    "yellow": "#FFF3B0",
    "cyan": "#8ECAE6",
    "pink": "#FFAFCC",
    "neutral": "#808080",
}

LANG_COLORS = [
    PALETTE["blue"],      # #A2D2FF
    PALETTE["lavender"],  # #CDB4DB
    PALETTE["mint"],      # #B7E4C7
    PALETTE["peach"],     # #FBC4AB
    PALETTE["yellow"],    # #FFF3B0
    PALETTE["cyan"],      # #8ECAE6
    PALETTE["pink"],      # #FFAFCC
    PALETTE["coral"],     # #FFADAD
]

# Colores pastel acordes a la identidad de cada lenguaje (basados en PALETTE)
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
}


def get_language_color(lang_name: str, fallback_idx: int = 0) -> str:
    """Devuelve siempre el mismo color pastel para un lenguaje dado."""
    key = (lang_name or "").strip().lower()
    if not key:
        return LANG_COLORS[fallback_idx % len(LANG_COLORS)]
    if key in LANGUAGE_COLOR_MAP:
        return LANGUAGE_COLOR_MAP[key]

    # Hash estable (MD5 no criptográfico, determinista entre ejecuciones y procesos)
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    slot = int(digest[:8], 16) % len(LANG_COLORS)
    return LANG_COLORS[slot]


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)
