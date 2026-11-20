from .theme import LANG_COLORS, PALETTE, esc


def render_langs(data: dict) -> str:
    langs = data.get("languages", [])
    if not langs:
        langs = [{"name": "Code", "percent": 100.0}]

    bar_x = 14
    total_bar_w = 232
    gap = 2.5
    usable_w = max(10.0, total_bar_w - gap * (len(langs) - 1))

    total_pct = sum(float(item.get("percent", 0)) for item in langs) or 100.0

    bars_svg = []
    labels_svg = []

    curr_x = float(bar_x)
    for idx, item in enumerate(langs):
        color = LANG_COLORS[idx % len(LANG_COLORS)]
        pct = float(item.get("percent", 0))
        ratio = pct / total_pct

        w = max(4.0, round(ratio * usable_w, 1))
        if idx == len(langs) - 1:
            w = max(4.0, round((bar_x + total_bar_w) - curr_x, 1))

        bars_svg.append(
            f'  <rect x="{curr_x:.1f}" y="40" width="{w:.1f}" height="7" rx="3.5" fill="{color}" />'
        )
        curr_x += w + gap

        col = idx % 2
        row = idx // 2
        cx = 18 if col == 0 else 136
        cy = 68 + row * 22

        # Formato limpio: entero si termina en .0, o 1 decimal si tiene fracción
        pct_str = f"{pct:.1f}".rstrip("0").rstrip(".")
        label_text = f"{esc(item['name'])} {pct_str}%"

        labels_svg.append(
            f'  <circle cx="{cx}" cy="{cy}" r="3.5" fill="{color}" />\n'
            f'  <text x="{cx + 9}" y="{cy + 4}" font-family="monospace" font-size="10.5" fill="{PALETTE["neutral"]}">{label_text}</text>'
        )

    rows = (len(langs) + 1) // 2
    svg_height = max(116, 68 + rows * 22 + 8)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 {svg_height}" width="260" height="{svg_height}">
  <text x="14" y="22" font-family="sans-serif" font-size="11" font-weight="600" fill="{PALETTE['neutral']}" letter-spacing="1.2">LENGUAJES</text>
  <line x1="14" y1="30" x2="246" y2="30" stroke="{PALETTE['neutral']}" stroke-opacity="0.2" stroke-width="1" />

{chr(10).join(bars_svg)}

{chr(10).join(labels_svg)}
</svg>
"""
