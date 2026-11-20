from .theme import PALETTE

LANG_PALETTE = [
    PALETTE["blue"],      # #A2D2FF
    PALETTE["mint"],      # #B7E4C7
    PALETTE["lavender"],  # #CDB4DB
    PALETTE["peach"],     # #FBC4AB
    PALETTE["yellow"],    # #FFF3B0
    PALETTE["pink"],      # #FFAFCC
    PALETTE["cyan"],      # #8ECAE6
]


def _shade_hex(hex_color: str, factor: float) -> str:
    """Oscurece o aclara un color hexadecimal para generar las caras lateral izquierda y derecha."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r = max(0, min(255, int(int(h[0:2], 16) * factor)))
    g = max(0, min(255, int(int(h[2:4], 16) * factor)))
    b = max(0, min(255, int(int(h[4:6], 16) * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _extract_language_slots(data: dict) -> list[dict]:
    """Obtiene los lenguajes reales desde metrics.json y les asigna un color pastel y glifo geométrico."""
    raw_langs = data.get("languages") or data.get("top_languages") or []
    slots = []

    if isinstance(raw_langs, dict):
        items = [{"name": k, "size": v} for k, v in raw_langs.items()]
    else:
        items = list(raw_langs)

    for idx, item in enumerate(items[:6]):
        base_color = LANG_PALETTE[idx % len(LANG_PALETTE)]
        slots.append(
            {
                "idx": idx,
                "top": base_color,
                "left": _shade_hex(base_color, 0.84),
                "right": _shade_hex(base_color, 0.68),
                "glyph": idx % 5,
            }
        )

    if not slots:
        for idx in range(4):
            base_color = LANG_PALETTE[idx]
            slots.append(
                {
                    "idx": idx,
                    "top": base_color,
                    "left": _shade_hex(base_color, 0.84),
                    "right": _shade_hex(base_color, 0.68),
                    "glyph": idx % 5,
                }
            )
    return slots


def _render_top_glyph(cx: float, cy: float, glyph_id: int) -> str:
    """Dibuja un identificador geométrico minimalista sobre la cara superior del prisma (sin texto)."""
    stroke = "#1e293b"
    if glyph_id == 0:
        # Rombo isométrico hueco
        return (
            f'<polygon points="{cx},{cy - 3.0} {cx + 5.2},{cy} {cx},{cy + 3.0} {cx - 5.2},{cy}" '
            f'fill="none" stroke="{stroke}" stroke-opacity="0.45" stroke-width="1.1" />'
        )
    if glyph_id == 1:
        # Anillo isométrico
        return (
            f'<ellipse cx="{cx}" cy="{cy}" rx="4.2" ry="2.3" '
            f'fill="none" stroke="{stroke}" stroke-opacity="0.45" stroke-width="1.1" />'
        )
    if glyph_id == 2:
        # Cruz isométrica
        return (
            f'<path d="M {cx - 3.6} {cy - 1.8} L {cx + 3.6} {cy + 1.8} '
            f'M {cx - 3.6} {cy + 1.8} L {cx + 3.6} {cy - 1.8}" '
            f'stroke="{stroke}" stroke-opacity="0.45" stroke-width="1.15" stroke-linecap="round" />'
        )
    if glyph_id == 3:
        # Núcleo sólido
        return f'<ellipse cx="{cx}" cy="{cy}" rx="2.6" ry="1.4" fill="{stroke}" fill-opacity="0.45" />'
    # Doble trazo diagonal
    return (
        f'<path d="M {cx - 2.8} {cy + 1.6} L {cx + 1.2} {cy - 2.2} '
        f'M {cx - 0.6} {cy + 2.2} L {cx + 3.4} {cy - 1.6}" '
        f'stroke="{stroke}" stroke-opacity="0.45" stroke-width="1.1" stroke-linecap="round" />'
    )


def render_isometric(data: dict) -> str:
    days = data.get("recent_25_days", [])
    while len(days) < 25:
        days.insert(0, {"contributionCount": 0})
    days = days[-25:]

    lang_slots = _extract_language_slots(data)
    num_langs = len(lang_slots)
    max_count = max((d.get("contributionCount", 0) for d in days), default=1) or 1

    # Paso de rejilla ligeramente mayor al tamaño del prisma (18x9) para dejar espacio limpio entre bloques
    step_x = 20.5
    step_y = 10.25
    bw = 17.5
    bh = 8.75

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
                f'fill="{PALETTE["neutral"]}" fill-opacity="0.14" />'
            )
            continue

        # Asignar lenguaje de forma determinista según día/actividad para reflejar el stack real
        lang = lang_slots[(idx + count) % num_langs]
        top_c, left_c, right_c = lang["top"], lang["left"], lang["right"]

        h = 6 + round((count / max_count) * 20)
        dur = 3.2 + (idx % 5) * 0.28
        begin = (idx % 7) * 0.25
        lift = 4 + (idx % 3)

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

    # Mini leyenda icónica sin palabras en la esquina superior derecha
    legend_items = []
    legend_start_x = 406.0 - (num_langs * 18.0)
    for idx, slot in enumerate(lang_slots):
        lx = round(legend_start_x + idx * 18.0 + 6.0, 1)
        ly = 16.0
        legend_items.append(
            f'    <rect x="{lx - 6:.1f}" y="{ly - 6:.1f}" width="12" height="12" rx="3" fill="{slot["top"]}" />'
            f'    {_render_top_glyph(lx, ly, slot["glyph"])}'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 182" width="420" height="182">
  <text x="14" y="20" font-family="sans-serif" font-size="11" font-weight="600" fill="{PALETTE['neutral']}" letter-spacing="1.2">MATRIZ ISOMÉTRICA (25D)</text>
{chr(10).join(legend_items)}
  <line x1="14" y1="28" x2="406" y2="28" stroke="{PALETTE['neutral']}" stroke-opacity="0.2" stroke-width="1" />

  <g transform="translate(192.5, 68)">
{chr(10).join(blocks)}
  </g>
</svg>
"""
