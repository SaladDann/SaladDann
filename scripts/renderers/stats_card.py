from .theme import PALETTE, esc, format_compact_number


def _render_stat_icon(name: str, x: float, y: float, color: str) -> str:
    """Iconos SVG geométricos de 14x14 estilo GitHub Octicons, sin rellenos."""
    icons = {
        "commits": (
            f'<path d="M{x+1.5} {y+7} H{x+4.2} M{x+9.8} {y+7} H{x+12.5}" />'
            f'<circle cx="{x+7}" cy="{y+7}" r="2.8" />'
        ),
        "repositories": (
            f'<path d="M{x+3} {y+2} H{x+11} V{y+12} H{x+3} '
            f'A1.2 1.2 0 0 1 {x+1.8} {y+10.8} V{y+3.2} '
            f'A1.2 1.2 0 0 1 {x+3} {y+2} Z" />'
            f'<path d="M{x+1.8} {y+9.8} H{x+11} M{x+5.5} {y+5} H{x+8.5}" />'
        ),
        "prs": (
            f'<circle cx="{x+4}" cy="{y+3.2}" r="1.8" />'
            f'<circle cx="{x+4}" cy="{y+10.8}" r="1.8" />'
            f'<circle cx="{x+10.2}" cy="{y+10.8}" r="1.8" />'
            f'<path d="M{x+4} {y+5} V{y+9} '
            f'M{x+5.8} {y+3.2} H{x+8.2} A2 2 0 0 1 {x+10.2} {y+5.2} V{y+9}" />'
        ),
        "issues": (
            f'<circle cx="{x+7}" cy="{y+7}" r="5.2" />'
            f'<path d="M{x+7} {y+4.2} V{y+7.3}" />'
            f'<circle cx="{x+7}" cy="{y+9.6}" r="0.6" fill="{color}" stroke="none" />'
        ),
        "stars_given": (
            f'<path d="M{x+7} {y+1.4} L{x+8.7} {y+5.0} '
            f'L{x+12.6} {y+5.5} L{x+9.8} {y+8.2} '
            f'L{x+10.5} {y+12.1} L{x+7} {y+10.2} '
            f'L{x+3.5} {y+12.1} L{x+4.2} {y+8.2} '
            f'L{x+1.4} {y+5.5} L{x+5.3} {y+5.0} Z" />'
        ),
        "stars_received": (
            f'<path d="M{x+6.4} {y+2.2} L{x+7.9} {y+5.4} '
            f'L{x+11.4} {y+5.9} L{x+8.9} {y+8.3} '
            f'L{x+9.5} {y+11.8} L{x+6.4} {y+10.1} '
            f'L{x+3.3} {y+11.8} L{x+3.9} {y+8.3} '
            f'L{x+1.4} {y+5.9} L{x+4.9} {y+5.4} Z" />'
            f'<path d="M{x+11.2} {y+1.2} V{y+3.2} M{x+10.2} {y+2.2} H{x+12.2}" />'
        ),
    }

    shape = icons.get(name, "")

    return (
        f'<g fill="none" stroke="{color}" '
        f'stroke-width="1.3" stroke-linecap="round" '
        f'stroke-linejoin="round" opacity="0.92">'
        f'{shape}'
        f'</g>'
    )


def render_stats(data: dict) -> str:
    st = data.get("stats", {})
    year = esc(str(data.get("generated_at", "2026"))[:4])

    metrics = [
        ("commits", "Commits", st.get("commits_year", 0), PALETTE["blue"]),
        ("repositories", "Repositories", st.get("repos", 0), PALETTE["mint"]),
        ("prs", "Pull Requests", st.get("prs", 0), PALETTE["lavender"]),
        ("issues", "Issues", st.get("issues", 0), PALETTE["peach"]),
        ("stars_given", "Stars Given", st.get("stars_given", 0), PALETTE["blue"]),
        ("stars_received", "Stars Received", st.get("stars_received", 0), PALETTE["mint"]),
    ]

    # Grid 2x3 calibrado para 265x190 (escala 1:1 en columna 32%)
    positions = [
        (10, 56), (138, 56),
        (10, 106), (138, 106),
        (10, 156), (138, 156),
    ]

    elements = []

    for (key, label, raw_value, accent), (x, y) in zip(metrics, positions):
        icon_svg = _render_stat_icon(key, x, y - 13, accent)
        formatted_val = esc(format_compact_number(raw_value))

        elements.append(
            f"""
            <g>
              {icon_svg}

              <text x="{x + 18}" y="{y - 2}"
                font-family="sans-serif"
                font-size="10.5"
                font-weight="500"
                fill="{PALETTE['neutral']}"
                opacity="0.9">
                {esc(label)}
              </text>

              <text x="{x + 18}" y="{y + 17}"
                font-family="monospace"
                font-size="15.5"
                font-weight="700"
                letter-spacing="-0.3"
                fill="{accent}">
                {formatted_val}
              </text>
            </g>
            """
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 265 190"
     width="265"
     height="190"
     direction="ltr"
     role="img"
     aria-label="GitHub Statistics">

  <text x="10" y="20"
    font-family="sans-serif"
    font-size="11"
    font-weight="600"
    fill="{PALETTE['neutral']}"
    letter-spacing="1.2">
    STATISTICS
  </text>

  <text x="255" y="20"
    text-anchor="end"
    font-family="monospace"
    font-size="10.5"
    fill="{PALETTE['neutral']}"
    opacity="0.75">
    {year}
  </text>

  <line x1="10" y1="29" x2="255" y2="29"
    stroke="{PALETTE['neutral']}"
    stroke-opacity="0.2"
    stroke-width="1" />

  {chr(10).join(elements)}

</svg>
"""
