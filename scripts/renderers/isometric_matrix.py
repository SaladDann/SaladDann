from .theme import PALETTE, get_language_color


def _shade_hex(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r = max(0, min(255, int(int(h[0:2], 16) * factor)))
    g = max(0, min(255, int(int(h[2:4], 16) * factor)))
    b = max(0, min(255, int(int(h[4:6], 16) * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _extract_language_slots(data: dict) -> list[dict]:
    raw_langs = data.get("languages") or data.get("top_languages") or []
    slots = []

    if isinstance(raw_langs, dict):
        items = [{"name": k, "size": v} for k, v in raw_langs.items()]
    else:
        items = list(raw_langs)

    for idx, item in enumerate(items[:5]):
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("language") or f"Lang {idx}")
        else:
            name = str(item)

        base_color = get_language_color(name, fallback_idx=idx)
        slots.append({
            "idx": idx,
            "name": name,
            "top": base_color,
            "left": _shade_hex(base_color, 0.84),
            "right": _shade_hex(base_color, 0.68),
            "glyph": idx % 5,
        })

    if not slots:
        default_names = ["TypeScript", "Python", "Dart", "JavaScript"]
        for idx, name in enumerate(default_names):
            base_color = get_language_color(name, fallback_idx=idx)
            slots.append({
                "idx": idx,
                "name": name,
                "top": base_color,
                "left": _shade_hex(base_color, 0.84),
                "right": _shade_hex(base_color, 0.68),
                "glyph": idx % 5,
            })
    return slots


def _render_top_glyph(cx: float, cy: float, glyph_id: int) -> str:
    stroke = "#1e293b"
    opacity = "0.55"
    if glyph_id == 0:
        return (
            f'<polygon points="{cx},{cy - 2.6} {cx + 4.4},{cy} {cx},{cy + 2.6} {cx - 4.4},{cy}" '
            f'fill="none" stroke="{stroke}" stroke-opacity="{opacity}" stroke-width="1.15" />'
        )
    if glyph_id == 1:
        return (
            f'<ellipse cx="{cx}" cy="{cy}" rx="3.6" ry="2.0" '
            f'fill="none" stroke="{stroke}" stroke-opacity="{opacity}" stroke-width="1.15" />'
        )
    if glyph_id == 2:
        return (
            f'<path d="M {cx - 3.0} {cy - 1.5} L {cx + 3.0} {cy + 1.5} '
            f'M {cx - 3.0} {cy + 1.5} L {cx + 3.0} {cy - 1.5}" '
            f'stroke="{stroke}" stroke-opacity="{opacity}" stroke-width="1.2" stroke-linecap="round" />'
        )
    if glyph_id == 3:
        return f'<ellipse cx="{cx}" cy="{cy}" rx="2.4" ry="1.3" fill="{stroke}" fill-opacity="{opacity}" />'
    return (
        f'<path d="M {cx - 2.4} {cy + 1.4} L {cx + 1.0} {cy - 1.9} '
        f'M {cx - 0.5} {cy + 1.9} L {cx + 2.9} {cy - 1.4}" '
        f'stroke="{stroke}" stroke-opacity="{opacity}" stroke-width="1.15" stroke-linecap="round" />'
    )


def render_isometric(data: dict) -> str:
    days = data.get("recent_25_days", [])
    while len(days) < 25:
        days.insert(0, {"contributionCount": 0})
    days = days[-25:]

    lang_slots = _extract_language_slots(data)
    num_langs = len(lang_slots)
    max_count = max((d.get("contributionCount", 0) for d in days), default=1) or 1

    # Geometría calibrada para lienzo 250x155
    step_x = 18.0
    step_y = 9.0
    bw = 15.2
    bh = 7.6

    blocks = []

    for idx, day in enumerate(days):
        row = idx // 5
        col = idx % 5
        count = day.get("contributionCount", 0)

        ix = round((col - row) * step_x, 2)
        iy = round((col + row) * step_y, 2)

        if count == 0:
            blocks.append(
                f'    <polygon points="{ix},{iy} {ix + bw},{iy - bh} {ix + bw * 2},{iy} {ix + bw},{iy + bh}" '
                f'fill="{PALETTE["neutral"]}" fill-opacity="0.16" />'
            )
            continue

        lang = lang_slots[(idx + count) % num_langs]
        top_c, left_c, right_c = lang["top"], lang["left"], lang["right"]

        h = 5 + round((count / max_count) * 18)
        dur = 3.2 + (idx % 5) * 0.28
        begin = (idx % 7) * 0.25
        lift = 3.5 + (idx % 3)

        cx = round(ix + bw, 2)
        cy = round(iy - h, 2)
        glyph_svg = _render_top_glyph(cx, cy, lang["glyph"])

        blocks.append(
            f'    <g>\n'
            f'      <animateTransform attributeName="transform" type="translate" values="0,0; 0,-{lift}; 0,0" dur="{dur:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1; 0.45 0 0.55 1" />\n'
            f'      <polygon points="{ix},{iy - h} {ix + bw},{iy - bh - h} {ix + bw * 2},{iy - h} {ix + bw},{iy + bh - h}" fill="{top_c}" />\n'
            f'      <polygon points="{ix},{iy - h} {ix + bw},{iy + bh - h} {ix + bw},{iy + bh} {ix},{iy}" fill="{left_c}" />\n'
            f'      <polygon points="{ix + bw},{iy + bh - h} {ix + bw * 2},{iy - h} {ix + bw * 2},{iy} {ix + bw},{iy + bh}" fill="{right_c}" />\n'
            f'      {glyph_svg}\n'
            f'    </g>'
        )

    legend_items = []
    legend_start_x = 240.0 - (num_langs * 16.0)
    for idx, slot in enumerate(lang_slots):
        lx = round(legend_start_x + idx * 16.0 + 6.0, 1)
        ly = 16.0
        legend_items.append(
            f'    <rect x="{lx - 6:.1f}" y="{ly - 6:.1f}" width="12" height="12" rx="3" fill="{slot["top"]}" />'
            f'    {_render_top_glyph(lx, ly, slot["glyph"])}'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 250 155"
     width="250"
     height="155"
     direction="ltr"
     role="img"
     aria-label="25-Day Isometric Activity Matrix">

  <text x="10" y="20"
    font-family="sans-serif"
    font-size="11"
    font-weight="600"
    fill="{PALETTE['neutral']}"
    letter-spacing="1.1">
    ACTIVITY (25D)
  </text>

{chr(10).join(legend_items)}

  <line x1="10" y1="29" x2="240" y2="29"
    stroke="{PALETTE['neutral']}"
    stroke-opacity="0.2"
    stroke-width="1" />

  <g transform="translate(109.8, 56)">
{chr(10).join(blocks)}
  </g>
</svg>
"""
