from .theme import PALETTE, esc, get_language_color


def render_langs(data: dict) -> str:
    langs = data.get("languages", [])
    if not langs:
        langs = [{"name": "Code", "percent": 100.0}]

    bar_x = 14
    total_bar_w = 392
    gap = 3
    usable_w = max(10.0, total_bar_w - gap * (len(langs) - 1))

    total_pct = sum(float(item.get("percent", 0)) for item in langs) or 100.0
    neutral_color = PALETTE["neutral"]

    bars_svg = []
    labels_svg = []

    curr_x = float(bar_x)
    for idx, item in enumerate(langs):
        name = str(item.get("name", "Code"))
        color = get_language_color(name, fallback_idx=idx)
        pct = float(item.get("percent", 0))
        ratio = pct / total_pct

        w = max(4.0, round(ratio * usable_w, 1))
        if idx == len(langs) - 1:
            w = max(4.0, round((bar_x + total_bar_w) - curr_x, 1))

        bars_svg.append(
            f'  <rect x="{curr_x:.1f}" y="40" width="{w:.1f}" height="8" rx="4" fill="{color}" />'
        )
        curr_x += w + gap

        col = idx % 2
        row = idx // 2
        cx = 24 if col == 0 else 220
        cy = 76 + row * 26

        pct_str = f"{pct:.1f}".rstrip("0").rstrip(".")
        label_text = f"{esc(name)} {pct_str}%"

        labels_svg.append(
            f'  <circle cx="{cx}" cy="{cy}" r="4" fill="{color}" />\n'
            f'  <text x="{cx + 10}" y="{cy + 4}" font-family="monospace" font-size="11.5" fill="{neutral_color}">{label_text}</text>'
        )

    bars_block = "\n".join(bars_svg)
    labels_block = "\n".join(labels_svg)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 150" width="420" height="150">\n'
        f'  <text x="14" y="20" font-family="sans-serif" font-size="11" font-weight="600" fill="{neutral_color}" letter-spacing="1.2">LENGUAJES</text>\n'
        f'  <line x1="14" y1="28" x2="406" y2="28" stroke="{neutral_color}" stroke-opacity="0.2" stroke-width="1" />\n\n'
        f'{bars_block}\n\n'
        f'{labels_block}\n'
        f'</svg>\n'
    )
