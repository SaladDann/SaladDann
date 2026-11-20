import random
from datetime import datetime

from ..theme import PALETTE

ALIEN_SHAPES = {
    "FIRST_QUARTILE": (
        PALETTE["blue"],
        [
            (2, 0), (1, 1), (2, 1), (3, 1),
            (0, 2), (1, 2), (2, 2), (3, 2), (4, 2),
            (0, 3), (2, 3), (4, 3),
            (1, 4), (3, 4),
        ],
    ),
    "SECOND_QUARTILE": (
        PALETTE["mint"],
        [
            (0, 0), (4, 0),
            (1, 1), (2, 1), (3, 1),
            (0, 2), (1, 2), (2, 2), (3, 2), (4, 2),
            (0, 3), (1, 3), (3, 3), (4, 3),
            (0, 4), (4, 4),
        ],
    ),
    "THIRD_QUARTILE": (
        PALETTE["yellow"],
        [
            (1, 0), (2, 0), (3, 0),
            (0, 1), (1, 1), (2, 1), (3, 1), (4, 1),
            (0, 2), (2, 2), (4, 2),
            (1, 3), (2, 3), (3, 3),
            (0, 4), (2, 4), (4, 4),
        ],
    ),
    "FOURTH_QUARTILE": (
        PALETTE["peach"],
        [
            (1, 0), (3, 0),
            (0, 1), (1, 1), (2, 1), (3, 1), (4, 1),
            (0, 2), (2, 2), (4, 2),
            (0, 3), (1, 3), (2, 3), (3, 3), (4, 3),
            (1, 4), (3, 4),
        ],
    ),
}

ARENA_WIDTH = 840
ARENA_HEIGHT = 144

ARENA_LEFT = 28.0
ARENA_RIGHT = 812.0

SHIP_Y = 128.0
SHIP_HOME_X = 420.0

MONTH_PAUSE = 1.15
ENEMY_SPAWN_INTERVAL = 0.42
ENEMY_FALL_MIN = 1.35
ENEMY_FALL_MAX = 1.95
ENEMY_EXPLOSION_TIME = 0.35
SHOT_FLIGHT_TIME = 0.28
MIN_TRANSIT_TIME = 0.34
OUTRO_PAUSE = 1.6


def _get_month_key(day: dict, week_idx: int, total_weeks: int) -> str:
    raw_date = day.get("date")
    if raw_date:
        try:
            parsed = datetime.strptime(str(raw_date)[:10], "%Y-%m-%d")
            return parsed.strftime("%Y-%m")
        except ValueError:
            pass

    raw_month = day.get("month")
    if raw_month:
        month = str(raw_month)
        if len(month) >= 7 and month[4] == "-":
            return month[:7]

    month_idx = min(11, (week_idx * 12) // max(total_weeks, 1))
    return f"2000-{month_idx + 1:02d}"


def _get_contribution_count(day: dict) -> int:
    if "contributionCount" in day:
        try:
            return max(0, int(day["contributionCount"] or 0))
        except (ValueError, TypeError):
            return 0

    level = day.get("contributionLevel", "NONE")
    return 0 if level == "NONE" else 1


def _render_minimal_outro(dur: float, outro_start: float, outro_end: float) -> str:
    """Cierre sobrio: un pulso geométrico sutil en el centro antes del reinicio."""
    t0 = max(0.0, min(100.0, (outro_start / dur) * 100.0))
    t_in = max(0.0, min(100.0, ((outro_start + 0.25) / dur) * 100.0))
    t_peak = max(0.0, min(100.0, (((outro_start + outro_end) / 2.0) / dur) * 100.0))
    t_out = max(0.0, min(100.0, ((outro_end - 0.25) / dur) * 100.0))
    t1 = max(0.0, min(100.0, (outro_end / dur) * 100.0))

    cx = ARENA_WIDTH / 2.0
    cy = 68.0

    return f"""
    <g transform="translate({cx:.1f}, {cy:.1f})" opacity="0">
      <animate
        attributeName="opacity"
        values="0;0;0.75;0.35;0.75;0;0"
        keyTimes="0;{t0 / 100:.5f};{t_in / 100:.5f};{t_peak / 100:.5f};{t_out / 100:.5f};{t1 / 100:.5f};1"
        dur="{dur}s"
        repeatCount="indefinite"
      />
      <line x1="-26" y1="0" x2="26" y2="0" stroke="{PALETTE['neutral']}" stroke-opacity="0.22" stroke-width="1"/>
      <rect x="-4" y="-4" width="8" height="8" rx="1.5" fill="{PALETTE['mint']}" fill-opacity="0.7"/>
      <circle cx="-15" cy="0" r="1.6" fill="{PALETTE['blue']}" fill-opacity="0.65"/>
      <circle cx="15" cy="0" r="1.6" fill="{PALETTE['peach']}" fill-opacity="0.65"/>
    </g>
    """


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
                        ][(w * 7 + d * 3) % 5]
                    }
                    for d in range(7)
                ]
            }
            for w in range(52)
        ]

    total_weeks = len(weeks)
    cs, gap = 11.5, 3.8
    step = cs + gap
    start_x, start_y = 24.0, 12.0
    muzzle_y = SHIP_Y - 12.0

    base_grid_svg: list[str] = []
    cell_coords: dict[tuple[int, int], tuple[float, float, float, float]] = {}
    monthly_active_cells: dict[str, list[dict]] = {}

    for w_idx, week in enumerate(weeks):
        gx = start_x + w_idx * step
        for d_idx, day in enumerate(week.get("contributionDays", [])[:7]):
            gy = start_y + d_idx * step
            gcx = gx + cs / 2.0
            gcy = gy + cs / 2.0
            cell_coords[(w_idx, d_idx)] = (gx, gy, gcx, gcy)

            base_grid_svg.append(
                f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{cs:.1f}" height="{cs:.1f}" '
                f'rx="2" fill="{PALETTE["neutral"]}" fill-opacity="0.035"/>'
            )

            level = day.get("contributionLevel", "NONE")
            count = _get_contribution_count(day)
            if count > 0 and level in ALIEN_SHAPES:
                month_key = _get_month_key(day, w_idx, total_weeks)
                monthly_active_cells.setdefault(month_key, []).append({
                    "w": w_idx,
                    "d": d_idx,
                    "gx": gx,
                    "gy": gy,
                    "level": level,
                    "count": count,
                })

    active_months = sorted(monthly_active_cells.keys())
    cursor = 0.0
    ship_cursor_t = 0.0
    ship_cursor_x = SHIP_HOME_X

    scheduled_events: list[dict] = []
    wave_markers: list[dict] = []
    ship_waypoints: list[tuple[float, float]] = [(0.0, SHIP_HOME_X)]

    for wave_idx, month_key in enumerate(active_months):
        cells = monthly_active_cells[month_key]
        pause_start = cursor
        wave_start = pause_start + MONTH_PAUSE

        wave_markers.append({
            "wave_idx": wave_idx,
            "start": pause_start,
            "end": wave_start,
        })

        seed = sum(ord(ch) * (i + 1) for i, ch in enumerate(f"{month_key}:{len(cells)}"))
        rng = random.Random(seed)

        shuffled_cells = list(cells)
        rng.shuffle(shuffled_cells)
        wave_sample = shuffled_cells[:14]

        raw_items: list[dict] = []
        for e_idx, cell in enumerate(wave_sample):
            spawn_x = rng.uniform(ARENA_LEFT, ARENA_RIGHT)
            target_y = rng.uniform(18.0, 92.0)
            zig = 7.5 if e_idx % 2 == 0 else -7.5
            paint_coord = cell_coords[(cell["w"], cell["d"])]
            raw_items.append({
                "e_idx": e_idx,
                "cell": cell,
                "spawn_x": spawn_x,
                "ecx": spawn_x + 5.5,
                "target_y": target_y,
                "zig": zig,
                "paint_x": paint_coord[0],
                "paint_y": paint_coord[1],
            })

        ordered_items: list[dict] = []
        remaining = list(raw_items)
        route_x = ship_cursor_x

        while remaining:
            best_idx = min(
                range(len(remaining)),
                key=lambda i: abs(remaining[i]["ecx"] - route_x),
            )
            chosen = remaining.pop(best_idx)
            ordered_items.append(chosen)
            route_x = chosen["ecx"]

        max_enemy_end = wave_start

        for seq_idx, item in enumerate(ordered_items):
            ecx = item["ecx"]
            dist_px = abs(ecx - ship_cursor_x)
            transit_dur = max(MIN_TRANSIT_TIME, dist_px / 950.0)

            earliest_arrive = max(wave_start + 0.25, ship_cursor_t + transit_dur)
            shot_start_t = earliest_arrive + 0.05
            hit_t = shot_start_t + SHOT_FLIGHT_TIME
            boom_end_t = hit_t + ENEMY_EXPLOSION_TIME

            fall_dur = rng.uniform(ENEMY_FALL_MIN, ENEMY_FALL_MAX)
            spawn_t = max(wave_start, hit_t - fall_dur)

            max_enemy_end = max(max_enemy_end, boom_end_t)

            if ecx != ship_cursor_x:
                ship_waypoints.append((earliest_arrive, ecx))
            ship_waypoints.append((hit_t, ecx))

            ship_cursor_t = hit_t
            ship_cursor_x = ecx

            scheduled_events.append({
                "id": f"w{wave_idx}_e{seq_idx}",
                "level": item["cell"]["level"],
                "count": item["cell"]["count"],
                "spawn_x": item["spawn_x"],
                "target_y": item["target_y"],
                "zig": item["zig"],
                "spawn_t": spawn_t,
                "shot_start_t": shot_start_t,
                "hit_t": hit_t,
                "boom_end_t": boom_end_t,
                "paint_x": item["paint_x"],
                "paint_y": item["paint_y"],
            })

        cursor = max_enemy_end + 0.25

    return_start_t = cursor
    return_dur = max(0.5, abs(SHIP_HOME_X - ship_cursor_x) / 900.0)
    return_end_t = return_start_t + return_dur
    outro_start_t = return_end_t + 0.15
    outro_end_t = outro_start_t + OUTRO_PAUSE
    dur = round(max(8.0, outro_end_t + 0.4), 2)

    if ship_cursor_x != SHIP_HOME_X:
        ship_waypoints.append((return_end_t, SHIP_HOME_X))
    ship_waypoints.append((dur, SHIP_HOME_X))

    css_rules: list[str] = []
    sprites_svg: list[str] = []
    paint_grid_svg: list[str] = []

    for marker in wave_markers:
        m_anim = f"waveBar_{marker['wave_idx']}"
        t0 = max(0.0, min(100.0, (marker["start"] / dur) * 100.0))
        t1 = max(0.0, min(100.0, ((marker["start"] + 0.12) / dur) * 100.0))
        t2 = max(0.0, min(100.0, ((marker["end"] - 0.12) / dur) * 100.0))
        t3 = max(0.0, min(100.0, (marker["end"] / dur) * 100.0))

        css_rules.append(
            f"@keyframes {m_anim} {{\n"
            f"  0%, {t0:.2f}% {{ opacity: 0; }}\n"
            f"  {t1:.2f}%, {t2:.2f}% {{ opacity: 1; }}\n"
            f"  {t3:.2f}%, 100% {{ opacity: 0; }}\n"
            f"}}"
        )
        wave_color = PALETTE[["blue", "mint", "yellow", "peach", "lavender"][marker["wave_idx"] % 5]]
        sprites_svg.append(
            f'<rect x="24" y="5" width="792" height="2" rx="1" '
            f'fill="{wave_color}" fill-opacity="0.25" opacity="0" '
            f'style="animation: {m_anim} {dur}s linear infinite;"/>'
        )

    for ev in scheduled_events:
        ev_id = ev["id"]
        color, pixels = ALIEN_SHAPES[ev["level"]]
        weight_scale = 1.0 + min(0.25, max(0, ev["count"] - 1) * 0.04)

        t_spawn = max(0.0, min(100.0, (ev["spawn_t"] / dur) * 100.0))
        t_mid = max(0.0, min(100.0, (((ev["spawn_t"] + ev["hit_t"]) / 2.0) / dur) * 100.0))
        t_shot_start = max(0.0, min(100.0, (ev["shot_start_t"] / dur) * 100.0))
        t_hit = max(0.0, min(100.0, (ev["hit_t"] / dur) * 100.0))
        t_boom = max(0.0, min(100.0, (ev["boom_end_t"] / dur) * 100.0))
        t_shot_fade = min(100.0, t_hit + 0.12)

        sx = ev["spawn_x"]
        ty = ev["target_y"]
        zig = ev["zig"]
        ecx = sx + 5.5
        ecy = ty + 5.5

        alien_anim = f"alien_{ev_id}"
        css_rules.append(
            f"@keyframes {alien_anim} {{\n"
            f"  0%, {t_spawn:.2f}% {{ transform: translate({sx:.1f}px, -16px) scale({0.75 * weight_scale:.2f}); opacity: 0; }}\n"
            f"  {min(100.0, t_spawn + 0.15):.2f}% {{ transform: translate({sx:.1f}px, 4px) scale({weight_scale:.2f}); opacity: 1; }}\n"
            f"  {t_mid:.2f}% {{ transform: translate({sx + zig:.1f}px, {(ty + 4)/2:.1f}px) scale({weight_scale:.2f}); opacity: 1; }}\n"
            f"  {t_hit:.2f}% {{ transform: translate({sx:.1f}px, {ty:.1f}px) scale({weight_scale:.2f}); opacity: 1; }}\n"
            f"  {t_boom:.2f}%, 100% {{ transform: translate({sx:.1f}px, {ty:.1f}px) scale({weight_scale * 1.45:.2f}); opacity: 0; }}\n"
            f"}}"
        )

        shot_anim = f"shot_{ev_id}"
        css_rules.append(
            f"@keyframes {shot_anim} {{\n"
            f"  0%, {t_shot_start:.2f}% {{ transform: translate({ecx:.1f}px, {muzzle_y:.1f}px); opacity: 0; }}\n"
            f"  {min(100.0, t_shot_start + 0.05):.2f}% {{ opacity: 1; }}\n"
            f"  {t_hit:.2f}% {{ transform: translate({ecx:.1f}px, {ecy:.1f}px); opacity: 1; }}\n"
            f"  {t_shot_fade:.2f}%, 100% {{ transform: translate({ecx:.1f}px, {ecy:.1f}px); opacity: 0; }}\n"
            f"}}"
        )

        boom_anim = f"boom_{ev_id}"
        css_rules.append(
            f"@keyframes {boom_anim} {{\n"
            f"  0%, {t_hit:.2f}% {{ opacity: 0; transform: translate({ecx:.1f}px, {ecy:.1f}px) scale(0.3); }}\n"
            f"  {min(100.0, t_hit + 0.10):.2f}% {{ opacity: 1; transform: translate({ecx:.1f}px, {ecy:.1f}px) scale(1.0); }}\n"
            f"  {t_boom:.2f}%, 100% {{ opacity: 0; transform: translate({ecx:.1f}px, {ecy:.1f}px) scale(1.65); }}\n"
            f"}}"
        )

        cell_anim = f"cell_{ev_id}"
        css_rules.append(
            f"@keyframes {cell_anim} {{\n"
            f"  0%, {t_hit:.2f}% {{ opacity: 0; }}\n"
            f"  {min(100.0, t_hit + 0.15):.2f}%, 100% {{ opacity: 1; }}\n"
            f"}}"
        )

        px_size = 2.2
        rects = "".join(
            f'<rect x="{px * px_size:.1f}" y="{py * px_size:.1f}" '
            f'width="{px_size:.1f}" height="{px_size:.1f}"/>'
            for px, py in pixels
        )

        sprites_svg.append(
            f'<g opacity="0" fill="{color}" style="animation: {alien_anim} {dur}s linear infinite;">{rects}</g>'
        )
        sprites_svg.append(
            f'<g opacity="0" style="animation: {shot_anim} {dur}s linear infinite;">'
            f'<rect x="-2.0" y="-6.5" width="4.0" height="13" rx="1" fill="{PALETTE["coral"]}" opacity="0.28"/>'
            f'<rect x="-1.0" y="-5.0" width="2.0" height="10" rx="1" fill="{PALETTE["coral"]}"/>'
            f'</g>'
        )
        sprites_svg.append(
            f'<g opacity="0" fill="{PALETTE["coral"]}" style="animation: {boom_anim} {dur}s linear infinite;">'
            f'<rect x="-5.5" y="-5.5" width="2.4" height="2.4"/>'
            f'<rect x="3.1" y="-5.5" width="2.4" height="2.4"/>'
            f'<rect x="-5.5" y="3.1" width="2.4" height="2.4"/>'
            f'<rect x="3.1" y="3.1" width="2.4" height="2.4"/>'
            f'</g>'
        )

        paint_grid_svg.append(
            f'<rect x="{ev["paint_x"]:.1f}" y="{ev["paint_y"]:.1f}" '
            f'width="{cs:.1f}" height="{cs:.1f}" rx="2" '
            f'fill="{color}" fill-opacity="0.11" opacity="0" '
            f'style="animation: {cell_anim} {dur}s linear infinite;"/>'
        )

    ship_kf: list[str] = []
    for t_sec, wx in ship_waypoints:
        pct = max(0.0, min(100.0, (t_sec / dur) * 100.0))
        ship_kf.append(f"  {pct:.2f}% {{ transform: translate({wx:.1f}px, {SHIP_Y:.1f}px); }}")

    css_rules.append(
        "@keyframes heroShip {\n"
        + "\n".join(ship_kf)
        + "\n}\n"
        """
        .invaders-static { display: none; }
        @media (prefers-reduced-motion: reduce) {
          .invaders-motion { display: none; }
          .invaders-static { display: block; }
        }
        """
    )

    static_sprites: list[str] = []
    for ev in scheduled_events:
        color, pixels = ALIEN_SHAPES[ev["level"]]
        px_size = 2.2
        rects = "".join(
            f'<rect x="{px * px_size:.1f}" y="{py * px_size:.1f}" '
            f'width="{px_size:.1f}" height="{px_size:.1f}"/>'
            for px, py in pixels
        )
        static_sprites.append(
            f'<g transform="translate({ev["spawn_x"]:.1f}, {ev["target_y"]:.1f})" fill="{color}" opacity="0.9">{rects}</g>'
        )

    ship_markup = f"""
        <polygon points="0,-8 -9,4 -4,4 -4,7 4,7 4,4 9,4" fill="{PALETTE["blue"]}" />
        <rect x="-2" y="-10" width="4" height="3" fill="{PALETTE["mint"]}" />
        <rect x="-1" y="-12" width="2" height="2" fill="{PALETTE["coral"]}" />
    """

    outro_svg = _render_minimal_outro(dur, outro_start_t, outro_end_t)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ARENA_WIDTH} {ARENA_HEIGHT}" width="{ARENA_WIDTH}" height="{ARENA_HEIGHT}" role="img" aria-label="Arte gráfico estilo Space Invaders">
  <defs>
    <clipPath id="arenaClip">
      <rect x="16" y="2" width="808" height="140" rx="6" />
    </clipPath>
  </defs>
  <style>
{chr(10).join(css_rules)}
  </style>
  <g clip-path="url(#arenaClip)">
{chr(10).join(base_grid_svg)}
    <g class="invaders-motion">
{chr(10).join(paint_grid_svg)}
{chr(10).join(sprites_svg)}
      <g style="animation: heroShip {dur}s ease-in-out infinite;">
        {ship_markup}
      </g>
{outro_svg}
    </g>
    <g class="invaders-static">
{chr(10).join(static_sprites)}
      <g transform="translate({SHIP_HOME_X:.1f}, {SHIP_Y:.1f})">
        {ship_markup}
      </g>
    </g>
  </g>
</svg>
"""
