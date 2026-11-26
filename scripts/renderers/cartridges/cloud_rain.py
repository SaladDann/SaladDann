from ..theme import PALETTE

MONTH_NAMES_ES = {
    "01": "ENE", "02": "FEB", "03": "MAR", "04": "ABR",
    "05": "MAY", "06": "JUN", "07": "JUL", "08": "AGO",
    "09": "SEP", "10": "OCT", "11": "NOV", "12": "DIC",
}


def _extract_yearly_months(data: dict, num_months: int = 12) -> list[dict]:
    """Agrupa contribuciones por mes (YYYY-MM) en los últimos 12 meses."""
    weeks = data.get("calendar_weeks", [])
    months_map: dict[str, dict] = {}

    for week in weeks:
        for day in week.get("contributionDays", []):
            date_str = day.get("date", "")
            if len(date_str) < 7:
                continue
            ym = date_str[:7]
            if ym not in months_map:
                m_num = ym[5:7]
                months_map[ym] = {
                    "ym": ym,
                    "label": MONTH_NAMES_ES.get(m_num, m_num)[:3],
                    "total": 0,
                    "days": [],
                }
            cnt = int(day.get("contributionCount", 0) or 0)
            months_map[ym]["total"] += cnt
            months_map[ym]["days"].append(cnt)

    sorted_months = [months_map[k] for k in sorted(months_map.keys())][-num_months:]

    if not sorted_months:
        sample_totals = [6, 14, 28, 10, 42, 55, 31, 19, 48, 62, 24, 38]
        labels = ["DIC", "ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV"]
        sorted_months = [
            {
                "ym": f"2026-{i+1:02d}",
                "label": lbl[:3],
                "total": tot,
                "days": [(tot + d * 3) % 5 for d in range(28)],
            }
            for i, (lbl, tot) in enumerate(zip(labels, sample_totals))
        ]

    return sorted_months


def _cloud_profile(ratio: float, consistency: float, total: int) -> dict:
    """Combina volumen mensual y consistencia de días activos para evitar saturación."""
    score = ratio * 0.72 + consistency * 0.28
    if total <= 0 or score <= 0.04:
        return {
            "color": PALETTE["neutral"],
            "front_op": "0.28",
            "back_op": "0.14",
            "scale": 0.82,
            "dur": 4.8,
            "cols": 2,
            "lightning": False,
        }
    if score <= 0.28:
        return {
            "color": PALETTE["blue"],
            "front_op": "0.70",
            "back_op": "0.34",
            "scale": 0.90,
            "dur": 3.6,
            "cols": 3,
            "lightning": False,
        }
    if score <= 0.58:
        return {
            "color": PALETTE["mint"],
            "front_op": "0.86",
            "back_op": "0.42",
            "scale": 0.98,
            "dur": 2.7,
            "cols": 4,
            "lightning": False,
        }
    if score <= 0.84:
        return {
            "color": PALETTE["lavender"],
            "front_op": "0.94",
            "back_op": "0.48",
            "scale": 1.04,
            "dur": 2.1,
            "cols": 4,
            "lightning": True,
        }
    return {
        "color": PALETTE["peach"],
        "front_op": "1.00",
        "back_op": "0.55",
        "scale": 1.10,
        "dur": 1.65,
        "cols": 5,
        "lightning": True,
    }


def render(data: dict) -> str:
    months = _extract_yearly_months(data, num_months=12)
    max_total = max((m["total"] for m in months), default=1) or 1

    count = len(months)
    margin_x = 18.0
    usable_w = 840.0 - 2 * margin_x
    slot_w = usable_w / max(1, count)

    css_rules = [
        """@keyframes cloudHover {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-1.5px); }
}
@keyframes rainStream {
  0% { transform: translateY(-10px); opacity: 0; }
  16% { opacity: 0.92; }
  82% { opacity: 0.78; }
  100% { transform: translateY(22px); opacity: 0; }
}
@keyframes flashBolt {
  0%, 85%, 90%, 94%, 100% { opacity: 0; }
  87%, 92% { opacity: 0.9; }
}
@keyframes ripplePulse {
  0%, 100% { transform: scaleX(0.6); opacity: 0.18; }
  50% { transform: scaleX(1.12); opacity: 0.52; }
}
.cloud-static { display: none; }
@media (prefers-reduced-motion: reduce) {
  .cloud-motion { display: none; }
  .cloud-static { display: block; }
}"""
    ]

    clouds_motion_svg = []
    clouds_static_svg = []

    for idx, m in enumerate(months):
        total = m["total"]
        ratio = (total / max_total) if max_total > 0 else 0.0
        days = m["days"]
        active_days = sum(1 for d in days if d > 0)
        consistency = (active_days / len(days)) if days else 0.0

        prof = _cloud_profile(ratio, consistency, total)
        col = prof["color"]
        cx = slot_w / 2.0
        slot_x = margin_x + idx * slot_w
        label_3 = str(m["label"])[:3].upper()

        num_cols = prof["cols"]
        col_offsets = [
            (c_i - (num_cols - 1) / 2.0) * 9.5 for c_i in range(num_cols)
        ]

        rain_groups = []
        static_bits_svg = []

        if total > 0:
            for c_i, dx in enumerate(col_offsets):
                rx = cx + dx
                dur = round(prof["dur"] * (0.92 + (c_i % 3) * 0.1), 2)
                delay = round(-((idx * 0.45) + (c_i * 0.62)), 2)

                stream_items = []
                for r_i in range(5):
                    sample_idx = (c_i * 5 + r_i) % max(1, len(days))
                    active_day = days[sample_idx] > 0 if days else False
                    ry = 48 + r_i * 11

                    if (c_i + r_i) % 3 == 2:
                        # Gota líquida sutil intercalada en el flujo
                        drop_elem = (
                            f'<ellipse cx="{rx:.1f}" cy="{ry - 2.5:.1f}" rx="1.2" ry="2.8" '
                            f'fill="{col}" fill-opacity="0.72" />'
                        )
                        stream_items.append(drop_elem)
                    else:
                        bit = "1" if active_day else "0"
                        bit_op = "0.92" if active_day else "0.28"
                        bit_elem = (
                            f'<text x="{rx:.1f}" y="{ry}" text-anchor="middle" font-family="monospace" '
                            f'font-size="9.5" font-weight="700" fill="{col}" fill-opacity="{bit_op}">{bit}</text>'
                        )
                        stream_items.append(bit_elem)
                        if c_i < 2 and r_i < 2:
                            static_bits_svg.append(bit_elem)

                rain_groups.append(
                    f'      <g style="animation: rainStream {dur}s linear {delay}s infinite;">\n'
                    f"        {''.join(stream_items)}\n"
                    f"      </g>"
                )

        bolt_svg = ""
        if prof["lightning"] and total > 0:
            bolt_delay = round(-idx * 0.85, 2)
            bolt_dur = round(3.4 + (idx % 3) * 0.7, 2)
            bx = cx + min(14.0, slot_w * 0.24)
            bolt_svg = (
                f'    <polygon points="{bx:.1f},35 {bx - 4.5:.1f},48 {bx:.1f},48 {bx - 3.5:.1f},61 '
                f'{bx + 5.5:.1f},45 {bx + 0.5:.1f},45" fill="{PALETTE["yellow"]}" opacity="0" '
                f'style="animation: flashBolt {bolt_dur}s ease-in-out {bolt_delay}s infinite;" />'
            )

        ripple_svg = ""
        static_ripple_svg = ""
        if total > 0:
            rip_delay = round(-idx * 0.4, 2)
            rip_w = round(10 + ratio * 16, 1)
            ripple_svg = (
                f'    <ellipse cx="{cx:.1f}" cy="116" rx="{rip_w}" ry="2.2" fill="{col}" '
                f'style="transform-origin: {cx:.1f}px 116px; animation: ripplePulse {prof["dur"]}s ease-in-out {rip_delay}s infinite;" />'
            )
            static_ripple_svg = (
                f'    <ellipse cx="{cx:.1f}" cy="116" rx="{rip_w}" ry="2.2" fill="{col}" opacity="0.38" />'
            )

        hover_dur = round(4.4 + (idx % 4) * 0.55, 2)
        hover_delay = round(-(idx * 0.73), 2)
        sc = prof["scale"]
        aria_label = f"{label_3}: {total} contribuciones en {active_days} días activos"

        def _cloud_body(animated: bool) -> str:
            hover_style = (
                f' style="animation: cloudHover {hover_dur}s ease-in-out {hover_delay}s infinite;"'
                if animated
                else ""
            )
            return f"""    <g{hover_style}>
      <g transform="translate({cx:.1f}, 27) scale({sc:.2f})">
        <path d="M -6 10 L 24 10 A 4.5 4.5 0 0 0 24 1 L 21 1 A 8 8 0 0 0 9 -6 A 12 12 0 0 0 -12 -4 A 9 9 0 0 0 -6 10 Z"
          fill="{col}" fill-opacity="{prof['back_op']}" />
        <path d="M -24 14 L 22 14 A 5 5 0 0 0 22 4 L 19 4 A 9 9 0 0 0 6 -5 A 14 14 0 0 0 -17 -3 A 10 10 0 0 0 -24 4 A 5 5 0 0 0 -24 14 Z"
          fill="{col}" fill-opacity="{prof['front_op']}" />
        <text x="-1.0" y="7.8" text-anchor="middle" font-family="monospace"
          font-size="7.8" font-weight="800" letter-spacing="0.6"
          fill="#0f172a" fill-opacity="0.72">{label_3}</text>
      </g>
    </g>"""

        clouds_motion_svg.append(
            f"""  <g transform="translate({slot_x:.1f}, 6)" role="group" aria-label="{aria_label}">
    <g mask="url(#slotRainMask)">
{chr(10).join(rain_groups)}
    </g>
{bolt_svg}
{_cloud_body(animated=True)}
{ripple_svg}
  </g>"""
        )

        clouds_static_svg.append(
            f"""  <g transform="translate({slot_x:.1f}, 6)">
    {''.join(static_bits_svg)}
{_cloud_body(animated=False)}
{static_ripple_svg}
  </g>"""
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 132" width="840" height="132" role="img" aria-label="Nubes de actividad mensual con lluvia de bits y ondas">
  <defs>
    <linearGradient id="rainGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="white" stop-opacity="0" />
      <stop offset="15%" stop-color="white" stop-opacity="1" />
      <stop offset="78%" stop-color="white" stop-opacity="1" />
      <stop offset="100%" stop-color="white" stop-opacity="0" />
    </linearGradient>
    <mask id="slotRainMask" maskUnits="userSpaceOnUse" x="2" y="36" width="{slot_w - 4:.1f}" height="78">
      <rect x="2" y="36" width="{slot_w - 4:.1f}" height="78" fill="url(#rainGrad)" />
    </mask>
  </defs>
  <style>
{chr(10).join(css_rules)}
  </style>
  <g class="cloud-motion">
{chr(10).join(clouds_motion_svg)}
  </g>
  <g class="cloud-static">
{chr(10).join(clouds_static_svg)}
  </g>
</svg>
"""
