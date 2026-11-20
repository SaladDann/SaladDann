import math

from ..theme import PALETTE

LEVEL_ORDER = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

# Factor de escorzo vertical para vista aérea inclinada a 60° respecto al horizonte.
TILT_60_FACTOR = round(math.sin(math.radians(60.0)), 4)


def _select_lilypad_pond(
    level_grid: dict[tuple[int, int], int], max_pads: int = 22
) -> list[dict]:
    """Selecciona nenúfares reales dispersos y ordenados de izquierda a derecha."""
    by_level: dict[int, list[tuple[int, int]]] = {1: [], 2: [], 3: [], 4: []}
    for pos, lvl in level_grid.items():
        if lvl in by_level:
            by_level[lvl].append(pos)

    pool = by_level[4] + by_level[3] + by_level[2] + by_level[1]
    if not pool:
        pool = [(w, (w * 3) % 7) for w in range(2, 50, 3)]

    selected: list[tuple[int, int]] = [pool[0]]
    used = {pool[0]}

    while len(selected) < max_pads and len(used) < len(pool):
        best_pos = None
        best_score = -999.0
        for cand in pool:
            if cand in used:
                continue
            min_dist = min(
                abs(cand[0] - s[0]) + abs(cand[1] - s[1]) for s in selected
            )
            col_pen = sum(4.0 for s in selected if abs(s[0] - cand[0]) <= 1)
            score = min_dist - col_pen
            if score > best_score:
                best_score = score
                best_pos = cand

        if best_pos is None or best_score < 2.0:
            break
        selected.append(best_pos)
        used.add(best_pos)

    selected.sort(key=lambda p: (p[0], p[1]))

    pads: list[dict] = []
    for idx, pos in enumerate(selected):
        lvl = level_grid.get(pos, 2)
        pads.append(
            {
                "w": pos[0],
                "d": pos[1],
                "level": lvl,
                "has_lotus": lvl == 3 or (lvl == 4 and idx % 2 == 0),
                "has_ladybug": lvl == 4 and idx % 2 == 1,
            }
        )
    return pads


def _parabolic_arc_points(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    min_safe_y: float = 21.0,
    steps: int = 8,
) -> list[tuple[float, float, float, float]]:
    """
    Calcula una trayectoria parabólica muestreada según la distancia entre (x0, y0) y (x1, y1).
    Devuelve tuplas (x, y, sx, sy) para cada subpaso del vuelo.
    """
    dist = math.hypot(x1 - x0, y1 - y0)
    peak_h = min(14.0, max(5.5, dist * 0.14))
    top_ceiling = min(y0, y1) - peak_h
    if top_ceiling < min_safe_y:
        peak_h = max(3.0, min(y0, y1) - min_safe_y)

    points: list[tuple[float, float, float, float]] = []
    for i in range(1, steps + 1):
        u = i / steps
        su = u * u * (3.0 - 2.0 * u)
        px = x0 + (x1 - x0) * su
        base_y = y0 + (y1 - y0) * su
        arc_offset = 4.0 * peak_h * u * (1.0 - u)
        py = max(min_safe_y, base_y - arc_offset)

        if u < 0.85:
            stretch = 1.0 + 0.11 * math.sin(math.pi * u)
            sx = round(2.0 - stretch, 3)
            sy = round(stretch, 3)
        else:
            sx = 1.08
            sy = 0.92

        points.append((round(px, 1), round(py, 1), sx, sy))

    return points


def _render_lilypad(
    cx: float,
    cy: float,
    level: int,
    has_lotus: bool,
    has_ladybug: bool,
    decor_anim: str,
    dur: float,
) -> str:
    """Dibuja un nenúfar con estética diferenciada según el nivel de contribuciones."""
    py = cy + 2.0

    if level <= 1:
        rx, ry = 6.6, round(4.8 * TILT_60_FACTOR, 1)
        fill_col = PALETTE["blue"]
        fill_op = "0.78"
        notch = (
            f'<polygon points="{cx:.1f},{py:.1f} {cx + rx:.1f},{py - 1.5:.1f} '
            f'{cx + rx:.1f},{py + 1.5:.1f}" fill="{PALETTE["cyan"]}" fill-opacity="0.22" />'
        )
        accent = ""
    elif level == 2:
        rx, ry = 7.8, round(5.8 * TILT_60_FACTOR, 1)
        fill_col = PALETTE["mint"]
        fill_op = "0.86"
        notch = (
            f'<polygon points="{cx:.1f},{py:.1f} {cx + rx:.1f},{py - 1.8:.1f} '
            f'{cx + rx:.1f},{py + 1.8:.1f}" fill="{PALETTE["cyan"]}" fill-opacity="0.25" />'
        )
        accent = ""
    elif level == 3:
        rx, ry = 8.8, round(6.5 * TILT_60_FACTOR, 1)
        fill_col = PALETTE["mint"]
        fill_op = "0.94"
        notch = (
            f'<polygon points="{cx:.1f},{py:.1f} {cx + rx:.1f},{py - 2.0:.1f} '
            f'{cx + rx:.1f},{py + 2.0:.1f}" fill="{PALETTE["cyan"]}" fill-opacity="0.28" />'
        )
        accent = (
            f'<ellipse cx="{cx:.1f}" cy="{py:.1f}" rx="{rx - 1.4:.1f}" ry="{max(2.0, ry - 1.1):.1f}" '
            f'fill="{PALETTE["mint"]}" fill-opacity="0.25" />'
        )
    else:
        rx, ry = 9.8, round(7.2 * TILT_60_FACTOR, 1)
        fill_col = PALETTE["mint"]
        fill_op = "1.0"
        notch = (
            f'<polygon points="{cx:.1f},{py:.1f} {cx + rx:.1f},{py - 2.2:.1f} '
            f'{cx + rx:.1f},{py + 2.2:.1f}" fill="{PALETTE["yellow"]}" fill-opacity="0.32" />'
        )
        accent = (
            f'<ellipse cx="{cx:.1f}" cy="{py:.1f}" rx="{rx + 1.8:.1f}" ry="{max(2.5, ry + 1.4):.1f}" '
            f'fill="{PALETTE["yellow"]}" fill-opacity="0.14" />'
        )

    decor_svg = ""
    if has_lotus:
        decor_svg = (
            f'    <g style="transform-origin: {cx:.1f}px {cy - 2.0:.1f}px; animation: {decor_anim} {dur}s linear infinite;">\n'
            f'      <ellipse cx="{cx - 2.4:.1f}" cy="{cy - 2.0:.1f}" rx="2.4" ry="1.35" '
            f'transform="rotate(-24 {cx - 2.4:.1f} {cy - 2.0:.1f})" fill="{PALETTE["pink"]}" />\n'
            f'      <ellipse cx="{cx + 2.4:.1f}" cy="{cy - 2.0:.1f}" rx="2.4" ry="1.35" '
            f'transform="rotate(24 {cx + 2.4:.1f} {cy - 2.0:.1f})" fill="{PALETTE["pink"]}" />\n'
            f'      <ellipse cx="{cx:.1f}" cy="{cy - 3.2:.1f}" rx="1.7" ry="1.8" fill="{PALETTE["pink"]}" />\n'
            f'      <circle cx="{cx:.1f}" cy="{cy - 2.4:.1f}" r="1.5" fill="{PALETTE["yellow"]}" />\n'
            f'    </g>'
        )
    elif has_ladybug:
        decor_svg = (
            f'    <g style="animation: {decor_anim} {dur}s linear infinite;">\n'
            f'      <circle cx="{cx + 2.6:.1f}" cy="{cy - 1.4:.1f}" r="2.2" fill="{PALETTE["coral"]}" />\n'
            f'      <circle cx="{cx + 4.3:.1f}" cy="{cy - 1.4:.1f}" r="1.05" fill="#1e293b" />\n'
            f'      <circle cx="{cx + 2.0:.1f}" cy="{cy - 2.0:.1f}" r="0.45" fill="#1e293b" />\n'
            f'      <circle cx="{cx + 2.3:.1f}" cy="{cy - 0.8:.1f}" r="0.45" fill="#1e293b" />\n'
            f'    </g>'
        )

    return (
        f'    <ellipse cx="{cx:.1f}" cy="{py:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
        f'fill="{fill_col}" fill-opacity="{fill_op}" />\n'
        f'    {notch}\n'
        f'    {accent}\n'
        f'{decor_svg}'
    )


def _render_crystalline_pond_shadows() -> list[str]:
    """
    Estanque cristalino con una sombra grande y otra pequeña fijas en su zona del lago
    en escorzo de 60°, fluctuando suavemente en su lugar sin perseguir el salto.
    """
    big_ry = round(40.0 * TILT_60_FACTOR, 1)
    small_ry = round(20.0 * TILT_60_FACTOR, 1)
    return [
        '  <rect x="16" y="2" width="808" height="136" rx="6" fill="url(#pondWater)" />',
        f'  <ellipse class="pond-shadow-big" cx="395" cy="74" rx="250" ry="{big_ry}" '
        f'fill="{PALETTE["cyan"]}" fill-opacity="0.065" />',
        f'  <ellipse class="pond-shadow-small" cx="595" cy="96" rx="120" ry="{small_ry}" '
        f'fill="{PALETTE["blue"]}" fill-opacity="0.06" />',
    ]


def render(data: dict) -> str:
    weeks = data.get("calendar_weeks", [])[-52:]
    if not weeks:
        weeks = [
            {
                "contributionDays": [
                    {
                        "contributionLevel": [
                            "NONE",
                            "FIRST_QUARTILE",
                            "SECOND_QUARTILE",
                            "THIRD_QUARTILE",
                            "FOURTH_QUARTILE",
                        ][(w * 5 + d * 3) % 5]
                    }
                    for d in range(7)
                ]
            }
            for w in range(52)
        ]

    rows = 7
    cs, gap = 11.5, 3.8
    step = cs + gap
    start_x, start_y = 24.0, 20.0

    raw_grid: dict[tuple[int, int], int] = {}
    for w_idx, week in enumerate(weeks):
        for d_idx, day in enumerate(week.get("contributionDays", [])[:rows]):
            lvl_str = day.get("contributionLevel", "NONE")
            raw_grid[(w_idx, d_idx)] = LEVEL_ORDER.get(lvl_str, 0)

    pads = _select_lilypad_pond(raw_grid, max_pads=22)
    num_pads = max(1, len(pads))
    dur = round(min(36.0, max(22.0, num_pads * 1.05)), 1)
    active_span = 94.0

    pond_elements = _render_crystalline_pond_shadows()

    css_rules = [
        """
        @keyframes pondShadowBigPulse {
          0%, 100% { transform: translate(0px, 0px) scale(1.0, 1.0); opacity: 0.75; }
          50% { transform: translate(10px, -1.5px) scale(1.05, 0.96); opacity: 1.0; }
        }
        @keyframes pondShadowSmallPulse {
          0%, 100% { transform: translate(0px, 0px) scale(1.0, 1.0); opacity: 0.7; }
          50% { transform: translate(-12px, 1.5px) scale(0.93, 1.06); opacity: 1.0; }
        }
        @keyframes keroHeadTilt {
          0%, 100% { transform: rotate(0deg) translateY(0px); }
          35% { transform: rotate(4.5deg) translateY(-0.6px); }
          70% { transform: rotate(-3.5deg) translateY(0.4px); }
        }
        @keyframes keroFeetKick {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          35% { transform: translateY(1.2px) rotate(-8deg); }
          75% { transform: translateY(-0.6px) rotate(5deg); }
        }
        @keyframes keroBlink {
          0%, 92%, 100% { transform: scaleY(1); }
          95% { transform: scaleY(0.12); }
        }
        .pond-shadow-big {
          transform-box: fill-box;
          transform-origin: center;
          animation: pondShadowBigPulse 8.5s ease-in-out infinite;
        }
        .pond-shadow-small {
          transform-box: fill-box;
          transform-origin: center;
          animation: pondShadowSmallPulse 6.2s ease-in-out infinite;
        }
        .kero-head {
          transform-box: fill-box;
          transform-origin: center bottom;
          animation: keroHeadTilt 1.35s ease-in-out infinite;
        }
        .kero-feet {
          transform-box: fill-box;
          transform-origin: center top;
          animation: keroFeetKick 1.35s ease-in-out infinite;
        }
        .kero-eyes {
          transform-box: fill-box;
          transform-origin: center;
          animation: keroBlink 4.8s ease-in-out infinite;
        }
        .keroppi-static { display: none; }
        @media (prefers-reduced-motion: reduce) {
          .pond-shadow-big, .pond-shadow-small, .kero-head, .kero-feet, .kero-eyes { animation: none; }
          .keroppi-motion { display: none; }
          .keroppi-static { display: block; }
        }
        """
    ]

    lilypads_svg: list[str] = []
    keroppi_kf: list[str] = []

    first_cx = round(start_x + pads[0]["w"] * step + cs / 2.0, 1)
    first_cy = round(start_y + pads[0]["d"] * step + cs / 2.0, 1)
    keroppi_kf.append(f"  0.00% {{ transform: translate(-18.0px, {first_cy}px) scale(1.0, 1.0); }}")

    arc_steps = 8

    for idx, pad in enumerate(pads):
        cx = round(start_x + pad["w"] * step + cs / 2.0, 1)
        cy = round(start_y + pad["d"] * step + cs / 2.0, 1)

        prev_x = (
            -18.0
            if idx == 0
            else round(start_x + pads[idx - 1]["w"] * step + cs / 2.0, 1)
        )
        prev_y = (
            first_cy
            if idx == 0
            else round(start_y + pads[idx - 1]["d"] * step + cs / 2.0, 1)
        )

        slot_start = (idx / num_pads) * active_span
        slot_end = ((idx + 1) / num_pads) * active_span
        slot_len = slot_end - slot_start

        flight_end = slot_start + slot_len * 0.78
        touch_end = slot_start + slot_len * 0.92

        arc_pts = _parabolic_arc_points(
            x0=prev_x,
            y0=prev_y,
            x1=cx,
            y1=cy,
            min_safe_y=21.0,
            steps=arc_steps,
        )

        for s_i, (px, py, sx, sy) in enumerate(arc_pts, start=1):
            t_pt = slot_start + (flight_end - slot_start) * (s_i / arc_steps)
            keroppi_kf.append(
                f"  {t_pt:.2f}% {{ transform: translate({px:.1f}px, {py:.1f}px) scale({sx:.3f}, {sy:.3f}); }}"
            )

        keroppi_kf.append(
            f"  {min(99.4, flight_end + 0.18):.2f}% {{ transform: translate({cx:.1f}px, {cy:.1f}px) scale(1.08, 0.92); }}"
        )
        keroppi_kf.append(
            f"  {touch_end:.2f}% {{ transform: translate({cx:.1f}px, {cy:.1f}px) scale(1.0, 1.0); }}"
        )

        t_land = flight_end
        rip_anim = f"rip_{idx}"
        rip_outer_anim = f"rip_outer_{idx}"
        t_rip_end = min(98.8, t_land + slot_len * 1.65)
        t_outer_start = min(97.5, t_land + slot_len * 0.18)
        t_outer_end = min(99.8, t_land + slot_len * 2.25)

        css_rules.append(
            f"@keyframes {rip_anim} {{\n"
            f"  0%, {t_land:.2f}% {{ transform: translate({cx}px, {cy + 2}px) scale(0.5); opacity: 0; }}\n"
            f"  {min(99.5, t_land + 0.25):.2f}% {{ transform: translate({cx}px, {cy + 2}px) scale(0.92); opacity: 0.68; }}\n"
            f"  {min(99.7, t_land + (t_rip_end - t_land) * 0.55):.2f}% {{ transform: translate({cx}px, {cy + 2}px) scale(2.05); opacity: 0.34; }}\n"
            f"  {t_rip_end:.2f}%, 100% {{ transform: translate({cx}px, {cy + 2}px) scale(3.15); opacity: 0; }}\n"
            f"}}"
        )
        css_rules.append(
            f"@keyframes {rip_outer_anim} {{\n"
            f"  0%, {t_outer_start:.2f}% {{ transform: translate({cx}px, {cy + 2}px) scale(0.6); opacity: 0; }}\n"
            f"  {min(99.6, t_outer_start + 0.25):.2f}% {{ transform: translate({cx}px, {cy + 2}px) scale(1.05); opacity: 0.44; }}\n"
            f"  {min(99.8, t_outer_start + (t_outer_end - t_outer_start) * 0.6):.2f}% {{ transform: translate({cx}px, {cy + 2}px) scale(2.45); opacity: 0.18; }}\n"
            f"  {t_outer_end:.2f}%, 100% {{ transform: translate({cx}px, {cy + 2}px) scale(3.95); opacity: 0; }}\n"
            f"}}"
        )

        pad_rx = round(6.8 + pad["level"] * 0.75, 1)
        pad_ry = round((4.8 + pad["level"] * 0.5) * TILT_60_FACTOR, 1)
        rip_rx = round(pad_rx + 3.2, 1)
        rip_ry = round((pad_ry + 2.2) * TILT_60_FACTOR, 1)

        decor_anim = f"decor_{idx}"
        if pad["has_lotus"] or pad["has_ladybug"]:
            t_eat = min(97.0, t_land + 0.2)
            css_rules.append(
                f"@keyframes {decor_anim} {{\n"
                f"  0%, {t_eat:.2f}% {{ opacity: 1; transform: scale(1); }}\n"
                f"  {t_eat + 0.4:.2f}%, 98.5% {{ opacity: 0.2; transform: scale(0.65); }}\n"
                f"  100% {{ opacity: 1; transform: scale(1); }}\n"
                f"}}"
            )

        pad_body = _render_lilypad(
            cx=cx,
            cy=cy,
            level=pad["level"],
            has_lotus=pad["has_lotus"],
            has_ladybug=pad["has_ladybug"],
            decor_anim=decor_anim,
            dur=dur,
        )

        lilypads_svg.append(
            f"  <g>\n"
            f'    <ellipse cx="0" cy="0" rx="{rip_rx:.1f}" ry="{rip_ry:.1f}" '
            f'fill="{PALETTE["cyan"]}" fill-opacity="0.07" stroke="{PALETTE["cyan"]}" stroke-width="1.05" opacity="0" '
            f'style="animation: {rip_anim} {dur}s ease-out infinite;" />\n'
            f'    <ellipse cx="0" cy="0" rx="{rip_rx + 1.5:.1f}" ry="{rip_ry + 1.2:.1f}" '
            f'fill="none" stroke="{PALETTE["blue"]}" stroke-width="0.75" opacity="0" '
            f'style="animation: {rip_outer_anim} {dur}s ease-out infinite;" />\n'
            f"{pad_body}\n"
            f"  </g>"
        )

    last_cx = round(start_x + pads[-1]["w"] * step + cs / 2.0, 1)
    last_cy = round(start_y + pads[-1]["d"] * step + cs / 2.0, 1)
    exit_arc = _parabolic_arc_points(
        x0=last_cx,
        y0=last_cy,
        x1=865.0,
        y1=last_cy,
        min_safe_y=21.0,
        steps=6,
    )
    for e_i, (px, py, sx, sy) in enumerate(exit_arc, start=1):
        t_ex = 94.0 + (6.0 * e_i / len(exit_arc))
        keroppi_kf.append(
            f"  {t_ex:.2f}% {{ transform: translate({px:.1f}px, {py:.1f}px) scale({sx:.3f}, {sy:.3f}); }}"
        )

    css_rules.append("@keyframes keroppiHop {\n" + "\n".join(keroppi_kf) + "\n}")

    keroppi_body = f"""
    <g class="kero-feet">
      <ellipse cx="-4.2" cy="3.8" rx="2.4" ry="1.3" fill="{PALETTE['mint']}" />
      <ellipse cx="4.2" cy="3.8" rx="2.4" ry="1.3" fill="{PALETTE['mint']}" />
    </g>
    <rect x="-4.5" y="-0.5" width="9.0" height="4.2" rx="2.0" fill="#ffffff" />
    <rect x="-4.3" y="0.6" width="8.6" height="1.2" fill="{PALETTE['coral']}" />
    <rect x="-4.0" y="2.4" width="8.0" height="1.1" fill="{PALETTE['coral']}" />
    <g class="kero-head">
      <ellipse cx="0" cy="-4.2" rx="7.2" ry="5.0" fill="{PALETTE['mint']}" />
      <g class="kero-eyes">
        <circle cx="-3.1" cy="-8.4" r="3.1" fill="#ffffff" stroke="{PALETTE['mint']}" stroke-width="0.9" />
        <circle cx="3.1" cy="-8.4" r="3.1" fill="#ffffff" stroke="{PALETTE['mint']}" stroke-width="0.9" />
        <circle cx="-2.6" cy="-8.3" r="1.25" fill="#1e293b" />
        <circle cx="3.6" cy="-8.3" r="1.25" fill="#1e293b" />
      </g>
      <ellipse cx="-4.8" cy="-3.6" rx="1.4" ry="0.9" fill="{PALETTE['pink']}" />
      <ellipse cx="4.8" cy="-3.6" rx="1.4" ry="0.9" fill="{PALETTE['pink']}" />
      <path d="M -2.2 -3.2 L 0 -1.8 L 2.2 -3.2" fill="none" stroke="#1e293b" stroke-width="0.95" stroke-linecap="round" stroke-linejoin="round" />
    </g>
    """

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 140" width="840" height="140" role="img" aria-label="Arte gráfico estilo estanque de Keroppi">
  <defs>
    <clipPath id="pondClip">
      <rect x="16" y="2" width="808" height="136" rx="6" />
    </clipPath>
    <linearGradient id="pondWater" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{PALETTE['cyan']}" stop-opacity="0.07" />
      <stop offset="50%" stop-color="{PALETTE['blue']}" stop-opacity="0.035" />
      <stop offset="100%" stop-color="{PALETTE['mint']}" stop-opacity="0.055" />
    </linearGradient>
  </defs>
  <style>
{chr(10).join(css_rules)}
  </style>
  <g clip-path="url(#pondClip)">
{chr(10).join(pond_elements)}
{chr(10).join(lilypads_svg)}
    <g class="keroppi-motion">
      <g style="animation: keroppiHop {dur}s linear infinite;">
        {keroppi_body}
      </g>
    </g>
    <g class="keroppi-static">
      <g transform="translate({first_cx}, {first_cy})">
        {keroppi_body}
      </g>
    </g>
  </g>
</svg>
"""
