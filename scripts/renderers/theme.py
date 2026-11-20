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


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)
