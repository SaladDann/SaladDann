import math

from ..theme import PALETTE

LEVEL_ORDER = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _keyframes(name: str, frames: list[str]) -> str:
    return f"@keyframes {name} {{\n" + "\n".join(frames) + "\n}"


def _percent(value: float) -> float:
    return round(_clamp(value, 0.0, 100.0), 2)


def _frame(t: float, declarations: str) -> str:
    return f"  {_percent(t):.2f}% {{ {declarations} }}"


def _svg_coin(fill: str, center_fill: str) -> str:
    return f"""
    <ellipse cx="0" cy="0" rx="3.1" ry="4.5" fill="{fill}" />
    <ellipse cx="0" cy="0" rx="1.1" ry="3.3" fill="{center_fill}" />
    <rect x="-0.65" y="-2.2" width="1.3" height="4.4"
          rx="0.4" fill="#fff3b0" fill-opacity="0.8" />
"""


def _extract_week_profiles(weeks: list[dict]) -> list[dict]:
    profiles: list[dict] = []
    for w_idx, week in enumerate(weeks):
        days = week.get("contributionDays", [])[:7]
        total_cnt = sum(
            max(0, int(d.get("contributionCount", 0) or 0))
            for d in days
        )
        levels = [
            LEVEL_ORDER.get(d.get("contributionLevel", "NONE"), 0)
            for d in days
        ]
        max_lvl = max(levels, default=0)
        active_days = sum(
            1
            for d in days
            if max(0, int(d.get("contributionCount", 0) or 0)) > 0
            or LEVEL_ORDER.get(d.get("contributionLevel", "NONE"), 0) > 0
        )

        if total_cnt >= 14 or max_lvl == 4:
            intensity = 4
        elif total_cnt >= 8 or max_lvl == 3:
            intensity = 3
        elif total_cnt >= 3 or max_lvl == 2:
            intensity = 2
        elif total_cnt > 0 or max_lvl == 1:
            intensity = 1
        else:
            intensity = 0

        profiles.append({
            "w": w_idx,
            "count": total_cnt,
            "max_lvl": max_lvl,
            "active_days": active_days,
            "intensity": intensity,
        })
    return profiles


def _ground_y_for_profile(profile: dict, base_ground_y: float = 114.0) -> float:
    lift = profile["intensity"] * 2.5
    return round(base_ground_y - lift, 1)


def _plan_mario_course(
    profiles: list[dict],
) -> tuple[list[dict], list[dict], list[dict], int | None]:
    cols = len(profiles)
    if cols == 0:
        return [], [], [], None

    active_pool = [
        p for p in profiles[2 : max(3, cols - 12)]
        if p["count"] > 0 or p["intensity"] > 0
    ]
    ranked = sorted(
        active_pool,
        key=lambda x: (-x["count"], -x["intensity"], -x["active_days"], x["w"]),
    )

    top_w = ranked[0]["w"] if ranked else None
    second_w = ranked[1]["w"] if len(ranked) > 1 else None

    occupied: set[int] = set()
    q_blocks: list[dict] = []

    for item in ranked:
        if len(q_blocks) >= 3:
            break
        w = item["w"]
        if all(abs(w - ow) >= 9 for ow in occupied):
            if w == top_w:
                reward = "star"
            elif w == second_w:
                reward = "mushroom"
            else:
                reward = "coins"

            q_blocks.append({
                "w": w,
                "count": item["count"],
                "intensity": item["intensity"],
                "reward": reward,
            })
            occupied.add(w)

    if top_w is not None and not any(b["reward"] == "star" for b in q_blocks):
        top_item = next(p for p in profiles if p["w"] == top_w)
        replacement = {
            "w": top_w,
            "count": top_item["count"],
            "intensity": top_item["intensity"],
            "reward": "star",
        }
        if q_blocks:
            q_blocks.sort(key=lambda b: b["count"])
            q_blocks[-1] = replacement
        else:
            q_blocks.append(replacement)
        occupied = {b["w"] for b in q_blocks}

    q_blocks.sort(key=lambda b: b["w"])

    pipe_min_w = max(0, min(cols - 1, cols - 16))
    pipe_max_w = max(pipe_min_w, min(cols - 1, cols - 11))
    pipe_candidates = [
        p for p in profiles[pipe_min_w : pipe_max_w + 1]
        if p["count"] > 0 or p["intensity"] > 0
    ]
    pipe_candidates.sort(key=lambda x: (-x["count"], -x["intensity"], x["w"]))

    pipe_w = None
    for item in pipe_candidates:
        w = item["w"]
        if all(abs(w - ow) >= 5 for ow in occupied):
            pipe_w = w
            break

    if pipe_w is None:
        pipe_w = int(_clamp(cols - 13, pipe_min_w, pipe_max_w))

    pipe_profile = profiles[pipe_w]
    pipe_h = int(round(15 + pipe_profile["intensity"] * 2.5))
    pipes = [{"w": pipe_w, "h": pipe_h}]
    occupied.add(pipe_w)

    goomba_w = None
    goomba_candidates = [
        p for p in profiles[14 : max(15, min(pipe_w - 4, cols - 15))]
        if (p["count"] > 0 or p["intensity"] > 0)
        and all(abs(p["w"] - ow) >= 4 for ow in occupied)
    ]
    goomba_candidates.sort(key=lambda x: (abs(x["w"] - (cols // 2)), -x["count"]))

    if goomba_candidates:
        goomba_w = goomba_candidates[0]["w"]
        occupied.add(goomba_w)

    coin_arcs: list[dict] = []
    for item in ranked:
        w = item["w"]
        if w >= pipe_w - 3:
            continue
        if all(abs(w - ow) >= 6 for ow in occupied):
            num_coins = min(3, max(2, item["count"] // 3 or 2))
            coin_arcs.append({
                "w": w,
                "num": num_coins,
                "intensity": item["intensity"],
            })
            occupied.add(w)
            break

    return q_blocks, pipes, coin_arcs, goomba_w


def _sample_jump_arc(
    t_start: float,
    t_end: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    apex_lift: float,
    steps: int = 7,
) -> list[tuple[float, float, float]]:
    samples: list[tuple[float, float, float]] = []
    for i in range(1, steps + 1):
        u = i / steps
        t_i = t_start + (t_end - t_start) * u
        x_i = x0 + (x1 - x0) * u
        base_y = y0 + (y1 - y0) * u
        parabola = 4.0 * apex_lift * u * (1.0 - u)
        y_i = max(22.0, base_y - parabola)
        samples.append((_percent(t_i), round(x_i, 1), round(y_i, 1)))
    return samples


def render(data: dict) -> str:
    weeks = data.get("calendar_weeks", [])[-52:]

    if not weeks:
        weeks = [
            {
                "contributionDays": [
                    {
                        "contributionCount": (w * 3 + d) % 7,
                        "contributionLevel": [
                            "NONE",
                            "FIRST_QUARTILE",
                            "SECOND_QUARTILE",
                            "THIRD_QUARTILE",
                            "FOURTH_QUARTILE",
                        ][(w * 5 + d * 3) % 5],
                    }
                    for d in range(7)
                ]
            }
            for w in range(52)
        ]

    cols = len(weeks)
    if cols == 0:
        return ""

    profiles = _extract_week_profiles(weeks)

    cs = 11.5
    gap = 3.8
    step = cs + gap

    start_x = 24.0
    base_ground_y = 114.0

    flag_x = 762.0
    castle_x = 796.0

    run_window_pct = 82.0
    dur = 30.0

    q_blocks, pipes, coin_arcs, goomba_w = _plan_mario_course(profiles)

    def ground_at_w(w_idx: int) -> float:
        idx = int(_clamp(w_idx, 0, cols - 1))
        return _ground_y_for_profile(profiles[idx], base_ground_y)

    def ground_at_x(x_pos: float) -> float:
        est_w = int(round((x_pos - start_x) / step))
        return ground_at_w(est_w)

    events: list[dict] = []
    for b in q_blocks:
        events.append({
            "type": "qblock",
            "w": b["w"],
            "x": start_x + b["w"] * step + cs / 2,
            "count": b["count"],
            "intensity": b["intensity"],
            "reward": b["reward"],
        })
    for p in pipes:
        px = min(flag_x - 36.0, start_x + p["w"] * step + cs / 2)
        events.append({
            "type": "pipe",
            "w": p["w"],
            "x": px,
            "h": p["h"],
        })
    for c in coin_arcs:
        events.append({
            "type": "coins",
            "w": c["w"],
            "x": start_x + c["w"] * step + cs / 2,
            "num": c["num"],
            "intensity": c["intensity"],
        })
    if goomba_w is not None:
        events.append({
            "type": "goomba",
            "w": goomba_w,
            "x": start_x + goomba_w * step + cs / 2,
        })

    events.sort(key=lambda e: e["x"])

    def x_to_pct(x_pos: float) -> float:
        value = ((x_pos + 16.0) / (flag_x + 16.0)) * run_window_pct
        return _percent(value)

    css_rules: list[str] = []
    ground_blocks: list[str] = []
    clouds_svg: list[str] = []
    scenery_svg: list[str] = []
    props_svg: list[str] = []

    scenery_svg.append(
        f"""
        <path d="M 36 114 Q 155 78 275 114 Z" fill="{PALETTE['mint']}" fill-opacity="0.10" />
        <path d="M 430 114 Q 560 74 690 114 Z" fill="{PALETTE['mint']}" fill-opacity="0.10" />
        """
    )

    cloud_specs = [
        (140.0, 26.0, 0.95, 4.0),
        (540.0, 24.0, 0.90, 4.0),
    ]

    for ci, (cx, cy, scale, distance) in enumerate(cloud_specs):
        name = f"cloudDrift_{ci}"
        css_rules.append(
            _keyframes(name, [
                _frame(0, "transform: translateX(0px);"),
                _frame(50, f"transform: translateX({distance}px);"),
                _frame(100, "transform: translateX(0px);"),
            ])
        )
        clouds_svg.append(
            f"""
            <g style="animation: {name} {dur}s ease-in-out infinite;">
                <g transform="translate({cx}, {cy}) scale({scale})" fill="#ffffff" fill-opacity="0.28">
                    <ellipse cx="0" cy="0" rx="14" ry="7" />
                    <ellipse cx="-9" cy="3" rx="9" ry="5" />
                    <ellipse cx="9" cy="3" rx="10" ry="5.5" />
                    <ellipse cx="-3" cy="-4" rx="8" ry="5" />
                </g>
            </g>
            """
        )

    for prof in profiles:
        w = prof["w"]
        gx = start_x + w * step
        gy = _ground_y_for_profile(prof, base_ground_y)
        block_h = round(124.0 - gy, 1)
        opacity = round(0.42 + prof["intensity"] * 0.14, 2)

        ground_blocks.append(
            f"""
            <rect x="{gx:.1f}" y="{gy:.1f}" width="{cs}" height="{block_h:.1f}"
                  rx="2" fill="{PALETTE['mint']}" fill-opacity="{opacity}" />
            <rect x="{gx:.1f}" y="{gy:.1f}" width="{cs}" height="2.6"
                  rx="1" fill="{PALETTE['mint']}" />
            """
        )

    mario_positions: dict[float, tuple[float, float, float]] = {}

    def add_mario_kf(t: float, x: float, y: float, opacity: float = 1.0):
        t = _percent(t)
        mario_positions[t] = (x, y, opacity)

    add_mario_kf(0, -16.0, ground_at_w(0))

    for idx, ev in enumerate(events):
        ex = ev["x"]
        event_type = ev["type"]
        local_gy = ground_at_x(ex)

        if event_type == "qblock":
            block_y = max(48.0, local_gy - 46.0)
            x_pre = ex - 18.0
            x_post = ex + 18.0
            y_pre = ground_at_x(x_pre)
            y_post = ground_at_x(x_post)
            t_pre = x_to_pct(x_pre)
            t_hit = x_to_pct(ex)
            t_post = x_to_pct(x_post)

            add_mario_kf(t_pre, x_pre, y_pre)
            for t_s, x_s, y_s in _sample_jump_arc(
                t_pre, t_hit, x_pre, y_pre, ex, block_y + 13.0, apex_lift=6.0, steps=5
            ):
                add_mario_kf(t_s, x_s, y_s)
            for t_s, x_s, y_s in _sample_jump_arc(
                t_hit, t_post, ex, block_y + 13.0, x_post, y_post, apex_lift=2.0, steps=5
            ):
                add_mario_kf(t_s, x_s, y_s)

            qb_anim = f"qb_{idx}"
            qtext_anim = f"qtext_{idx}"
            t_hit_end = min(99, t_hit + 1.2)

            css_rules.append(
                _keyframes(qb_anim, [
                    _frame(0, f"transform: translate({ex - 6.5}px, {block_y}px); fill: {PALETTE['yellow']};"),
                    _frame(t_hit, f"transform: translate({ex - 6.5}px, {block_y}px); fill: {PALETTE['yellow']};"),
                    _frame(t_hit + 0.18, f"transform: translate({ex - 6.5}px, {block_y - 6}px); fill: {PALETTE['peach']};"),
                    _frame(t_hit + 0.42, f"transform: translate({ex - 6.5}px, {block_y - 2}px);"),
                    _frame(t_hit + 0.65, f"transform: translate({ex - 6.5}px, {block_y}px);"),
                    _frame(t_hit_end, f"transform: translate({ex - 6.5}px, {block_y}px); fill: #8b929b; fill-opacity: 0.5;"),
                    _frame(100, f"transform: translate({ex - 6.5}px, {block_y}px); fill: {PALETTE['yellow']};"),
                ])
            )

            css_rules.append(
                _keyframes(qtext_anim, [
                    _frame(t_hit, "transform: scale(1);"),
                    _frame(t_hit + 0.22, "transform: scale(1.5);"),
                    _frame(t_hit + 0.55, "transform: scale(1);"),
                    _frame(100, "transform: scale(1);"),
                ])
            )

            reward = ev["reward"]

            if reward == "star":
                star_anim = f"star_{idx}"
                css_rules.append(
                    _keyframes(star_anim, [
                        _frame(t_hit, f"transform: translate({ex}px, {block_y}px) scale(0.3) rotate(0deg); opacity: 0;"),
                        _frame(t_hit + 0.25, f"transform: translate({ex}px, {block_y - 12}px) scale(1.1) rotate(25deg); opacity: 1;"),
                        _frame(t_hit + 1.1, f"transform: translate({ex + 8}px, {block_y - 22}px) scale(1) rotate(130deg); opacity: 1;"),
                        _frame(t_hit + 2.4, f"transform: translate({ex + 17}px, {block_y - 16}px) scale(0.9) rotate(260deg); opacity: 1;"),
                        _frame(t_hit + 3.7, f"transform: translate({ex + 25}px, {block_y - 20}px) scale(0.6) rotate(360deg); opacity: 0;"),
                        _frame(100, "opacity: 0;"),
                    ])
                )
                props_svg.append(
                    f"""
                    <g opacity="0" style="animation: {star_anim} {dur}s ease-out infinite;">
                        <polygon points="0,-8 2.2,-2.5 8,-2 3.5,1.8 4.8,8 0,4.5 -4.8,8 -3.5,1.8 -8,-2 -2.2,-2.5"
                                 fill="{PALETTE['yellow']}" stroke="#ffffff" stroke-width="0.7" />
                        <circle cx="-1.8" cy="-0.8" r="0.8" fill="#1e293b" />
                        <circle cx="1.8" cy="-0.8" r="0.8" fill="#1e293b" />
                    </g>
                    """
                )
            elif reward == "mushroom":
                mush_anim = f"mush_{idx}"
                css_rules.append(
                    _keyframes(mush_anim, [
                        _frame(t_hit, f"transform: translate({ex}px, {block_y}px) scale(0.5); opacity: 0;"),
                        _frame(t_hit + 0.35, f"transform: translate({ex}px, {block_y - 12}px) scale(1.1); opacity: 1;"),
                        _frame(t_hit + 1.5, f"transform: translate({ex + 12}px, {block_y - 12}px) scale(1); opacity: 1;"),
                        _frame(t_hit + 3.0, f"transform: translate({ex + 22}px, {block_y - 5}px) scale(0.9); opacity: 0;"),
                        _frame(100, "opacity: 0;"),
                    ])
                )
                props_svg.append(
                    f"""
                    <g opacity="0" style="animation: {mush_anim} {dur}s ease-out infinite;">
                        <rect x="-3.5" y="-0.2" width="7" height="4.5" rx="1.2" fill="{PALETTE['peach']}" />
                        <path d="M -6.5 0 A 6.5 6 0 0 1 6.5 0 Z" fill="{PALETTE['coral']}" />
                        <circle cx="-2.8" cy="-2.2" r="1.5" fill="#ffffff" />
                        <circle cx="2.8" cy="-2.2" r="1.5" fill="#ffffff" />
                        <circle cx="0" cy="-4.2" r="1.2" fill="#ffffff" />
                    </g>
                    """
                )
            else:
                num_pop = 1 if ev["count"] < 8 else 2
                for c_i in range(num_pop):
                    coin_anim = f"qcoin_{idx}_{c_i}"
                    dx = (c_i - (num_pop - 1) / 2) * 6
                    t0 = t_hit + c_i * 0.25
                    css_rules.append(
                        _keyframes(coin_anim, [
                            _frame(t0, f"transform: translate({ex}px, {block_y}px) scale(0.2, 0.5); opacity: 0;"),
                            _frame(t0 + 0.2, f"transform: translate({ex + dx}px, {block_y - 10}px) scale(1, 1); opacity: 1;"),
                            _frame(t0 + 0.8, f"transform: translate({ex + dx * 1.5}px, {block_y - 18}px) scale(0.5, 1); opacity: 1;"),
                            _frame(t0 + 1.1, f"transform: translate({ex + dx * 2}px, {block_y - 22}px) scale(1, 1); opacity: 0;"),
                            _frame(100, "opacity: 0;"),
                        ])
                    )
                    props_svg.append(
                        f"""
                        <g opacity="0" style="animation: {coin_anim} {dur}s ease-out infinite;">
                            {_svg_coin(PALETTE['yellow'], PALETTE['peach'])}
                        </g>
                        """
                    )

            props_svg.append(
                f"""
                <g style="animation: {qb_anim} {dur}s ease-out infinite;">
                    <rect x="0" y="0" width="13" height="13" rx="2.2" />
                    <rect x="1.2" y="1.2" width="10.6" height="2" rx="0.8" fill="#ffffff" fill-opacity="0.35" />
                    <text x="6.5" y="10.2" text-anchor="middle" font-family="monospace" font-size="10"
                          font-weight="900" fill="#1e293b"
                          style="animation: {qtext_anim} {dur}s ease-out infinite; transform-origin: 6.5px 6.5px;">?</text>
                </g>
                """
            )

        elif event_type == "pipe":
            ph = ev["h"]
            top_y = local_gy - ph - 6.0
            x_pre = ex - 20.0
            x_post = ex + 20.0
            y_pre = ground_at_x(x_pre)
            y_post = ground_at_x(x_post)
            t_pre = x_to_pct(x_pre)
            t_top = x_to_pct(ex)
            t_post = x_to_pct(x_post)

            add_mario_kf(t_pre, x_pre, y_pre)
            for t_s, x_s, y_s in _sample_jump_arc(
                t_pre, t_top, x_pre, y_pre, ex, top_y, apex_lift=7.0, steps=6
            ):
                add_mario_kf(t_s, x_s, y_s)
            for t_s, x_s, y_s in _sample_jump_arc(
                t_top, t_post, ex, top_y, x_post, y_post, apex_lift=1.5, steps=6
            ):
                add_mario_kf(t_s, x_s, y_s)

            props_svg.append(
                f"""
                <g>
                    <rect x="{ex - 6.5}" y="{local_gy - ph}" width="13" height="{ph}" fill="{PALETTE['mint']}" />
                    <rect x="{ex - 8}" y="{local_gy - ph}" width="16" height="5.5" rx="1.3" fill="{PALETTE['mint']}" />
                    <rect x="{ex - 5.5}" y="{local_gy - ph + 1}" width="2.5" height="{max(2.0, ph - 2)}"
                          fill="#ffffff" fill-opacity="0.42" />
                </g>
                """
            )

        elif event_type == "goomba":
            x_jump = ex - 20.0
            x_land = ex + 20.0
            y_jump = ground_at_x(x_jump)
            y_land = ground_at_x(x_land)
            t_jump = x_to_pct(x_jump)
            t_stomp = x_to_pct(ex)
            t_land = x_to_pct(x_land)

            add_mario_kf(t_jump, x_jump, y_jump)
            for t_s, x_s, y_s in _sample_jump_arc(
                t_jump, t_stomp, x_jump, y_jump, ex, local_gy - 7.0, apex_lift=18.0, steps=6
            ):
                add_mario_kf(t_s, x_s, y_s)
            for t_s, x_s, y_s in _sample_jump_arc(
                t_stomp, t_land, ex, local_gy - 7.0, x_land, y_land, apex_lift=9.0, steps=6
            ):
                add_mario_kf(t_s, x_s, y_s)

            goomba_anim = f"goombaMarch_{idx}"
            stomp_end = min(99, t_stomp + 1.8)

            css_rules.append(
                _keyframes(goomba_anim, [
                    _frame(0, f"transform: translate({ex + 42}px, {local_gy}px) scale(1, 1); opacity: 0;"),
                    _frame(max(0, t_stomp - 9.5), f"transform: translate({ex + 42}px, {local_gy}px) scale(1, 1); opacity: 0;"),
                    _frame(max(0, t_stomp - 8.8), f"transform: translate({ex + 38}px, {local_gy}px) scale(1, 1); opacity: 1;"),
                    _frame(t_stomp - 0.15, f"transform: translate({ex}px, {local_gy}px) scale(1, 1); opacity: 1;"),
                    _frame(t_stomp + 0.2, f"transform: translate({ex}px, {local_gy}px) scale(1.25, 0.45); opacity: 1;"),
                    _frame(stomp_end, f"transform: translate({ex}px, {local_gy}px) scale(1.25, 0.45); opacity: 0;"),
                    _frame(100, "opacity: 0;"),
                ])
            )

            goomba_walk = f"goombaWalk_{idx}"
            css_rules.append(
                _keyframes(goomba_walk, [
                    _frame(0, "transform: translateY(0px) rotate(-3deg);"),
                    _frame(25, "transform: translateY(-1px) rotate(0deg);"),
                    _frame(50, "transform: translateY(0px) rotate(3deg);"),
                    _frame(75, "transform: translateY(-1px) rotate(0deg);"),
                    _frame(100, "transform: translateY(0px) rotate(-3deg);"),
                ])
            )

            props_svg.append(
                f"""
                <g opacity="0" style="animation: {goomba_anim} {dur}s linear infinite;">
                    <g style="animation: {goomba_walk} 0.48s ease-in-out infinite;">
                        <ellipse cx="-3.5" cy="-1" rx="2.5" ry="1.5" fill="#1e293b" />
                        <ellipse cx="3.5" cy="-1" rx="2.5" ry="1.5" fill="#1e293b" />
                        <path d="M -6.5 -4.5 Q -7 -10 0 -10.5 Q 7 -10 6.5 -4.5 Z" fill="{PALETTE['peach']}" />
                        <path d="M -3.5 -9.0 L -0.8 -7.9 M 3.5 -9.0 L 0.8 -7.9"
                              stroke="#1e293b" stroke-width="1" stroke-linecap="round" />
                        <rect x="-2.8" y="-8.3" width="1.6" height="2.7" rx="0.5" fill="#ffffff" />
                        <rect x="1.2" y="-8.3" width="1.6" height="2.7" rx="0.5" fill="#ffffff" />
                        <rect x="-2.2" y="-7.5" width="0.9" height="1.4" fill="#1e293b" />
                        <rect x="1.6" y="-7.5" width="0.9" height="1.4" fill="#1e293b" />
                    </g>
                </g>
                """
            )

        elif event_type == "coins":
            num_c = ev["num"]
            span_w = (num_c - 1) * 11
            start_cx = ex - span_w / 2
            end_cx = ex + span_w / 2

            x_pre = start_cx - 12.0
            x_post = end_cx + 12.0
            y_pre = ground_at_x(x_pre)
            y_post = ground_at_x(x_post)
            t_pre = x_to_pct(x_pre)
            t_mid = x_to_pct(ex)
            t_post = x_to_pct(x_post)

            add_mario_kf(t_pre, x_pre, y_pre)
            for t_s, x_s, y_s in _sample_jump_arc(
                t_pre, t_mid, x_pre, y_pre, ex, max(24.0, local_gy - 22.0), apex_lift=8.0, steps=5
            ):
                add_mario_kf(t_s, x_s, y_s)
            for t_s, x_s, y_s in _sample_jump_arc(
                t_mid, t_post, ex, max(24.0, local_gy - 22.0), x_post, y_post, apex_lift=2.0, steps=5
            ):
                add_mario_kf(t_s, x_s, y_s)

            for c_i in range(num_c):
                cx_i = start_cx + c_i * 11
                cy_i = max(24.0, ground_at_x(cx_i) - 22.0)

                coin_anim = f"fieldCoin_{idx}_{c_i}"
                spin_anim = f"fieldCoinSpin_{idx}_{c_i}"
                t_eat = x_to_pct(cx_i)

                css_rules.append(
                    _keyframes(coin_anim, [
                        _frame(0, f"transform: translate({cx_i}px, {cy_i}px) scale(1); opacity: 1;"),
                        _frame(t_eat, f"transform: translate({cx_i}px, {cy_i}px) scale(1); opacity: 1;"),
                        _frame(t_eat + 0.25, f"transform: translate({cx_i}px, {cy_i - 7}px) scale(1.25); opacity: 1;"),
                        _frame(t_eat + 0.55, f"transform: translate({cx_i}px, {cy_i - 13}px) scale(0.4); opacity: 0;"),
                        _frame(99, f"transform: translate({cx_i}px, {cy_i - 13}px) scale(0.4); opacity: 0;"),
                        _frame(100, f"transform: translate({cx_i}px, {cy_i}px) scale(1); opacity: 1;"),
                    ])
                )

                css_rules.append(
                    _keyframes(spin_anim, [
                        _frame(0, "transform: scaleX(1);"),
                        _frame(25, "transform: scaleX(0.18);"),
                        _frame(50, "transform: scaleX(1);"),
                        _frame(75, "transform: scaleX(0.18);"),
                        _frame(100, "transform: scaleX(1);"),
                    ])
                )

                props_svg.append(
                    f"""
                    <g style="animation: {coin_anim} {dur}s linear infinite;">
                        <g style="animation: {spin_anim} 0.8s linear infinite;">
                            {_svg_coin(PALETTE['yellow'], PALETTE['peach'])}
                        </g>
                    </g>
                    """
                )

    end_ground = ground_at_w(cols - 1)
    add_mario_kf(run_window_pct, flag_x - 16, end_ground)
    for t_s, x_s, y_s in _sample_jump_arc(
        run_window_pct, 84.5, flag_x - 16, end_ground, flag_x - 2, 52.0, apex_lift=6.0, steps=4
    ):
        add_mario_kf(t_s, x_s, y_s)
    add_mario_kf(88, flag_x - 2, end_ground)
    add_mario_kf(90.5, castle_x, end_ground)
    add_mario_kf(91.5, castle_x, end_ground, 0)
    add_mario_kf(100, -16, ground_at_w(0), 0)

    mario_frames = [
        _frame(t, f"transform: translate({x:.1f}px, {y:.1f}px); opacity: {opacity:.2f};")
        for t, (x, y, opacity) in sorted(mario_positions.items())
    ]

    css_rules.append(_keyframes("marioRun", mario_frames))

    css_rules.append(
        _keyframes("marioLegLeft", [
            _frame(0, "transform: translate(0px, 0px) rotate(20deg);"),
            _frame(25, "transform: translate(-2px, -1px) rotate(-25deg);"),
            _frame(50, "transform: translate(0px, 0px) rotate(20deg);"),
            _frame(75, "transform: translate(2px, -1px) rotate(-25deg);"),
            _frame(100, "transform: translate(0px, 0px) rotate(20deg);"),
        ])
    )

    css_rules.append(
        _keyframes("marioLegRight", [
            _frame(0, "transform: translate(0px, -1px) rotate(-25deg);"),
            _frame(25, "transform: translate(2px, 0px) rotate(20deg);"),
            _frame(50, "transform: translate(0px, -1px) rotate(-25deg);"),
            _frame(75, "transform: translate(-2px, 0px) rotate(20deg);"),
            _frame(100, "transform: translate(0px, -1px) rotate(-25deg);"),
        ])
    )

    css_rules.append(
        _keyframes("marioArmLeft", [
            _frame(0, "transform: rotate(-24deg);"),
            _frame(50, "transform: rotate(24deg);"),
            _frame(100, "transform: rotate(-24deg);"),
        ])
    )

    css_rules.append(
        _keyframes("marioArmRight", [
            _frame(0, "transform: rotate(24deg);"),
            _frame(50, "transform: rotate(-24deg);"),
            _frame(100, "transform: rotate(24deg);"),
        ])
    )

    css_rules.append(
        _keyframes("marioBounce", [
            _frame(0, "transform: translateY(0px);"),
            _frame(25, "transform: translateY(-1.4px);"),
            _frame(50, "transform: translateY(0px);"),
            _frame(75, "transform: translateY(-1.4px);"),
            _frame(100, "transform: translateY(0px);"),
        ])
    )

    css_rules.append(
        _keyframes("flagDrop", [
            _frame(0, f"transform: translate({flag_x}px, 40px);"),
            _frame(84.5, f"transform: translate({flag_x}px, 40px);"),
            _frame(88, f"transform: translate({flag_x}px, 94px);"),
            _frame(99, f"transform: translate({flag_x}px, 94px);"),
            _frame(100, f"transform: translate({flag_x}px, 40px);"),
        ])
    )

    css_rules.append(
        _keyframes("castleFlagUp", [
            _frame(0, f"transform: translate({castle_x}px, 84px); opacity: 0;"),
            _frame(91, f"transform: translate({castle_x}px, 84px); opacity: 0;"),
            _frame(92.5, f"transform: translate({castle_x}px, 68px); opacity: 1;"),
            _frame(99, f"transform: translate({castle_x}px, 68px); opacity: 1;"),
            _frame(100, f"transform: translate({castle_x}px, 84px); opacity: 0;"),
        ])
    )

    firework_specs = [
        (736.0, 32.0, 91.5, PALETTE["coral"]),
        (788.0, 22.0, 93.2, PALETTE["yellow"]),
        (812.0, 42.0, 94.8, PALETTE["blue"]),
        (758.0, 24.0, 96.4, PALETTE["lavender"]),
    ]

    fireworks_svg = []

    for fw_idx, (fx, fy, t_start, color) in enumerate(firework_specs):
        fw_anim = f"firework_{fw_idx}"
        css_rules.append(
            _keyframes(fw_anim, [
                _frame(0, f"transform: translate({fx}px, {fy}px) scale(0.2); opacity: 0;"),
                _frame(t_start, f"transform: translate({fx}px, {fy}px) scale(0.2); opacity: 0;"),
                _frame(t_start + 0.3, f"transform: translate({fx}px, {fy}px) scale(0.8); opacity: 1;"),
                _frame(t_start + 1.4, f"transform: translate({fx}px, {fy}px) scale(1.35); opacity: 1;"),
                _frame(t_start + 2.6, f"transform: translate({fx}px, {fy}px) scale(1.65); opacity: 0;"),
                _frame(100, "opacity: 0;"),
            ])
        )

        sparks = [
            '<rect x="-1.2" y="-11" width="2.4" height="3.2" />',
            '<rect x="-1.2" y="7.8" width="2.4" height="3.2" />',
            '<rect x="-11" y="-1.2" width="3.2" height="2.4" />',
            '<rect x="7.8" y="-1.2" width="3.2" height="2.4" />',
            '<rect x="-8" y="-8" width="2.6" height="2.6" />',
            '<rect x="5.4" y="-8" width="2.6" height="2.6" />',
            '<rect x="-8" y="5.4" width="2.6" height="2.6" />',
            '<rect x="5.4" y="5.4" width="2.6" height="2.6" />',
        ]

        fireworks_svg.append(
            f"""
            <g opacity="0" fill="{color}" style="animation: {fw_anim} {dur}s linear infinite;">
                {"".join(sparks)}
            </g>
            """
        )

    goal_svg = f"""
    <rect x="{flag_x - 1.2}" y="36" width="2.4" height="{base_ground_y - 36}"
          rx="1" fill="{PALETTE['neutral']}" fill-opacity="0.5" />
    <circle cx="{flag_x}" cy="35" r="3" fill="{PALETTE['yellow']}" />
    <polygon points="0,0 14,5 0,10" fill="{PALETTE['coral']}"
             style="animation: flagDrop {dur}s ease-in-out infinite;" />
    <g opacity="0" style="animation: castleFlagUp {dur}s ease-in-out infinite;">
        <rect x="-0.8" y="0" width="1.6" height="14" fill="{PALETTE['neutral']}" />
        <polygon points="0,0 10,3.5 0,7" fill="{PALETTE['yellow']}" />
    </g>
    <g transform="translate({castle_x - 14}, 82)">
        <rect x="0" y="10" width="28" height="22" rx="1.5" fill="{PALETTE['peach']}" />
        <rect x="5" y="2" width="18" height="10" fill="{PALETTE['peach']}" />
        <rect x="0" y="7" width="4" height="3" fill="{PALETTE['peach']}" />
        <rect x="12" y="7" width="4" height="3" fill="{PALETTE['peach']}" />
        <rect x="24" y="7" width="4" height="3" fill="{PALETTE['peach']}" />
        <rect x="5" y="-1" width="3.5" height="3" fill="{PALETTE['peach']}" />
        <rect x="12.2" y="-1" width="3.5" height="3" fill="{PALETTE['peach']}" />
        <rect x="19.5" y="-1" width="3.5" height="3" fill="{PALETTE['peach']}" />
        <path d="M 10 32 L 10 23 A 4 4 0 0 1 18 23 L 18 32 Z" fill="#1e293b" fill-opacity="0.75" />
    </g>
    {"".join(fireworks_svg)}
    """

    mario_sprite = f"""
    <g style="animation: marioRun {dur}s linear infinite;">
        <g style="animation: marioBounce 0.34s ease-in-out infinite;">
            <g style="animation: marioLegLeft 0.34s ease-in-out infinite; transform-origin: -2px -3px;">
                <rect x="-4.5" y="-3.5" width="3.5" height="3.5" rx="0.8" fill="{PALETTE['peach']}" />
                <rect x="-5.0" y="-1.5" width="4.5" height="2" rx="0.6" fill="#1e293b" />
            </g>
            <g style="animation: marioLegRight 0.34s ease-in-out infinite; transform-origin: 2px -3px;">
                <rect x="1.5" y="-3.5" width="3.5" height="3.5" rx="0.8" fill="{PALETTE['peach']}" />
                <rect x="1" y="-1.5" width="4.5" height="2" rx="0.6" fill="#1e293b" />
            </g>
            <rect x="-4" y="-9" width="8" height="6.5" rx="1.2" fill="{PALETTE['blue']}" />
            <rect x="-2.7" y="-8.5" width="1.3" height="4.5" rx="0.5" fill="{PALETTE['yellow']}" />
            <rect x="1.4" y="-8.5" width="1.3" height="4.5" rx="0.5" fill="{PALETTE['yellow']}" />
            <g style="animation: marioArmLeft 0.34s ease-in-out infinite; transform-origin: -4px -7px;">
                <rect x="-6.2" y="-8" width="2" height="4.2" rx="0.8" fill="{PALETTE['coral']}" />
                <circle cx="-5.2" cy="-3.7" r="1.2" fill="#ffffff" />
            </g>
            <g style="animation: marioArmRight 0.34s ease-in-out infinite; transform-origin: 4px -7px;">
                <rect x="4.2" y="-8" width="2" height="4.2" rx="0.8" fill="{PALETTE['coral']}" />
                <circle cx="5.2" cy="-3.7" r="1.2" fill="#ffffff" />
            </g>
            <rect x="-3.8" y="-14.5" width="7.6" height="6" rx="1.8" fill="{PALETTE['peach']}" />
            <rect x="-4.2" y="-12.5" width="1.3" height="2" rx="0.5" fill="{PALETTE['peach']}" />
            <rect x="1.4" y="-13" width="1.2" height="1.8" fill="#1e293b" />
            <path d="M 0.8 -10.4 L 4.4 -10.4 L 4.4 -9.4 L 1.4 -9.4 Z" fill="#1e293b" />
            <rect x="-4.2" y="-16.8" width="8.4" height="2.8" rx="1" fill="{PALETTE['coral']}" />
            <rect x="-1" y="-15" width="6.2" height="1.4" rx="0.6" fill="{PALETTE['coral']}" />
        </g>
    </g>
    """

    return f"""
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 840 132"
     width="840"
     height="132">
    <defs>
        <clipPath id="levelClip">
            <rect x="16" y="2" width="808" height="128" rx="6" />
        </clipPath>
    </defs>
    <style>
        {chr(10).join(css_rules)}
    </style>
    <g clip-path="url(#levelClip)">
        {chr(10).join(scenery_svg)}
        {chr(10).join(clouds_svg)}
        {chr(10).join(ground_blocks)}
        {chr(10).join(props_svg)}
        {goal_svg}
        {mario_sprite}
    </g>
</svg>
"""
