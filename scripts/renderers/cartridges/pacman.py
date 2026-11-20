from collections import deque

from ..theme import PALETTE

LEVEL_ORDER = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

FRIGHTENED_BLUE = PALETTE["cyan"]


def _svg_fruit(kind: str) -> str:
    if kind == "strawberry":
        return f"""
        <path d="M 0 -5.5 L 1.8 -3.8" fill="none" stroke="{PALETTE['mint']}" stroke-width="1.3" stroke-linecap="round" />
        <path d="M 0 -3.8 C 4.5 -3.8 5.2 1.8 0 5.4 C -5.2 1.8 -4.5 -3.8 0 -3.8 Z"
              fill="{PALETTE['peach']}" />
        <circle cx="-1.5" cy="0.2" r="0.8" fill="#ffffff" fill-opacity="0.7" />
        """
    return f"""
    <path d="M -1.5 -1.5 Q 0 -6.5 2.6 -6.2 M 1.5 -1.5 Q 2.2 -5.5 2.6 -6.2"
          fill="none" stroke="{PALETTE['mint']}" stroke-width="1.2" stroke-linecap="round" />
    <circle cx="-2.2" cy="1.6" r="2.8" fill="{PALETTE['coral']}" />
    <circle cx="2.2" cy="2.2" r="2.8" fill="{PALETTE['coral']}" />
    <circle cx="-2.9" cy="0.8" r="0.8" fill="#ffffff" fill-opacity="0.75" />
    <circle cx="1.5" cy="1.4" r="0.8" fill="#ffffff" fill-opacity="0.75" />
    """


def _select_arcade_items(
    level_grid: dict[tuple[int, int], int], max_items: int = 34
) -> tuple[
    set[tuple[int, int]],
    dict[tuple[int, int], str],
    tuple[int, int],
]:
    by_level: dict[int, list[tuple[int, int]]] = {1: [], 2: [], 3: [], 4: []}
    for pos, lvl in level_grid.items():
        if lvl in by_level:
            by_level[lvl].append(pos)

    strong_pool = by_level[4] if len(by_level[4]) >= 2 else (by_level[4] + by_level[3])
    if not strong_pool:
        strong_pool = [(12, 1), (26, 5), (38, 2), (46, 3)]

    # Power Pellet final reservada al cierre del ciclo en la zona derecha.
    right_pool = [c for c in strong_pool if c[0] >= 36] or strong_pool
    final_power = max(right_pool, key=lambda c: (c[0], -abs(c[1] - 3)))
    all_selected: set[tuple[int, int]] = {final_power}

    # Frutas en contribuciones fuertes (tope de 3 para mantener limpieza visual).
    fruits: dict[tuple[int, int], str] = {}
    max_fruits = 3
    for idx, cand in enumerate(sorted(strong_pool, key=lambda c: (c[0], c[1]))):
        if len(fruits) >= max_fruits:
            break
        if all(abs(cand[0] - s[0]) + abs(cand[1] - s[1]) >= 12 for s in all_selected):
            fruits[cand] = "cherry" if idx % 2 == 0 else "strawberry"
            all_selected.add(cand)

    # Priorizamos primero contribuciones mínimas/moderadas (niveles 1 y 2),
    # y solo si faltan puntos rellenamos con 3 y 4 para que los mínimos sean puntitos.
    min_buckets = [by_level[1], by_level[2], by_level[3], by_level[4]]
    ordered_dots: list[tuple[int, int]] = []
    max_len = max((len(b) for b in min_buckets), default=0)
    for i in range(max_len):
        for b in min_buckets:
            if i < len(b) and b[i] not in all_selected:
                ordered_dots.append(b[i])

    regular_pellets: set[tuple[int, int]] = set()
    while len(all_selected) < max_items and ordered_dots:
        best_dot = None
        best_score = -999.0
        for cand in ordered_dots:
            if cand in all_selected:
                continue
            min_dist = min(abs(cand[0] - s[0]) + abs(cand[1] - s[1]) for s in all_selected)
            row_pen = sum(2.0 for s in all_selected if s[1] == cand[1] and abs(s[0] - cand[0]) < 8)
            col_pen = sum(2.2 for s in all_selected if s[0] == cand[0] and abs(s[1] - cand[1]) < 4)
            score = min_dist - row_pen - col_pen
            if score > best_score:
                best_score = score
                best_dot = cand

        if best_dot is None or best_score < 2.0:
            break
        regular_pellets.add(best_dot)
        all_selected.add(best_dot)

    return regular_pellets, fruits, final_power


def _bfs_path(
    start: tuple[int, int],
    goal: tuple[int, int],
    cols: int,
    rows: int,
) -> list[tuple[int, int]]:
    if start == goal:
        return []
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        (cw, cd), path = queue.popleft()
        dirs = ((1, 0), (0, 1), (0, -1), (-1, 0)) if cw <= goal[0] else ((-1, 0), (0, 1), (0, -1), (1, 0))
        for dw, dd in dirs:
            nw, nd = cw + dw, cd + dd
            nxt = (nw, nd)
            if 0 <= nw < cols and 0 <= nd < rows and nxt not in visited:
                new_path = path + [nxt]
                if nxt == goal:
                    return new_path
                visited.add(nxt)
                queue.append((nxt, new_path))
    return []


def _step_toward(
    curr: tuple[float, float],
    target: tuple[float, float],
    max_step: float,
) -> tuple[float, float]:
    dx = target[0] - curr[0]
    dy = target[1] - curr[1]
    dist = (dx * dx + dy * dy) ** 0.5
    if dist <= max_step or dist == 0:
        return target
    ratio = max_step / dist
    return (curr[0] + dx * ratio, curr[1] + dy * ratio)


def _build_smooth_cycle(
    regular_pellets: set[tuple[int, int]],
    fruits: dict[tuple[int, int], str],
    final_power: tuple[int, int],
    cols: int,
    rows: int,
) -> tuple[
    list[tuple[float, float, int]],
    list[list[tuple[float, float]]],
    dict[tuple[int, int], float],
    float,
    list[float | None],
]:
    # Todo lo demás se come antes de ir a final_power para que siempre sea el último ítem comido.
    remaining = (regular_pellets | set(fruits.keys())) - {final_power}
    curr = (0, 3)
    grid_path: list[tuple[int, int]] = [curr]
    eaten_grid_idx: dict[tuple[int, int], int] = {}

    if curr in remaining:
        eaten_grid_idx[curr] = 0
        remaining.remove(curr)

    while remaining:
        nxt = min(
            remaining,
            key=lambda p: abs(p[0] - curr[0]) * 1.15 + abs(p[1] - curr[1]) * 0.9,
        )
        for step_pos in _bfs_path(curr, nxt, cols, rows):
            grid_path.append(step_pos)
            if step_pos in remaining:
                eaten_grid_idx[step_pos] = len(grid_path) - 1
                remaining.remove(step_pos)
        curr = nxt

    for step_pos in _bfs_path(curr, final_power, cols, rows):
        grid_path.append(step_pos)
    power_grid_idx = len(grid_path) - 1
    eaten_grid_idx[final_power] = power_grid_idx

    pac_pts: list[tuple[float, float, int]] = []
    sub_steps = 3
    for i in range(len(grid_path)):
        x1, y1 = float(grid_path[i][0]), float(grid_path[i][1])
        if i == 0:
            pac_pts.append((x1, y1, 0))
            continue
        x0, y0 = float(grid_path[i - 1][0]), float(grid_path[i - 1][1])
        dw = x1 - x0
        dd = y1 - y0
        angle = 180 if dw < 0 else (90 if dd > 0 else (-90 if dd < 0 else 0))
        for s in range(1, sub_steps + 1):
            t = s / sub_steps
            pac_pts.append((x0 + dw * t, y0 + dd * t, angle))

    power_frame_idx = power_grid_idx * sub_steps

    lags = [5, 10, 15, 20]
    ghost_pts: list[list[tuple[float, float]]] = [[] for _ in range(4)]
    for f_idx in range(len(pac_pts)):
        for g_i, lag in enumerate(lags):
            src_idx = f_idx - lag
            if src_idx < 0:
                ghost_pts[g_i].append((-1.5 - (lag - src_idx) * 0.25, pac_pts[0][1]))
            else:
                ghost_pts[g_i].append((pac_pts[src_idx][0], pac_pts[src_idx][1]))

    p_pos = (pac_pts[-1][0], pac_pts[-1][1])
    g_pos = [(ghost_pts[g][-1][0], ghost_pts[g][-1][1]) for g in range(4)]
    ghost_eaten_idx: list[float | None] = [None, None, None, None]

    hunt_order = sorted(
        range(4),
        key=lambda g: ((g_pos[g][0] - p_pos[0]) ** 2 + (g_pos[g][1] - p_pos[1]) ** 2) ** 0.5,
    )

    pac_speed = 0.68
    ghost_flee_speed = 0.24
    max_hunt_frames = 95

    for _ in range(max_hunt_frames):
        alive = [g for g in hunt_order if ghost_eaten_idx[g] is None]
        if not alive:
            break

        target_g = alive[0]
        prev_p = p_pos
        p_pos = _step_toward(p_pos, g_pos[target_g], pac_speed)
        dx = p_pos[0] - prev_p[0]
        dy = p_pos[1] - prev_p[1]
        if abs(dx) >= abs(dy):
            angle = 0 if dx >= 0 else 180
        else:
            angle = 90 if dy >= 0 else -90

        pac_pts.append((p_pos[0], p_pos[1], angle))
        curr_f = float(len(pac_pts) - 1)

        for g_i in range(4):
            if ghost_eaten_idx[g_i] is None:
                flee_dx = 1.0 if g_pos[g_i][0] >= p_pos[0] else -1.0
                flee_dy = 0.35 if g_pos[g_i][1] < (rows - 1) * 0.5 else -0.35
                flee_target = (
                    max(0.0, min(float(cols - 1), g_pos[g_i][0] + flee_dx * 3.0)),
                    max(0.0, min(float(rows - 1), g_pos[g_i][1] + flee_dy * 2.0)),
                )
                g_pos[g_i] = _step_toward(g_pos[g_i], flee_target, ghost_flee_speed)

                dist_to_pac = ((g_pos[g_i][0] - p_pos[0]) ** 2 + (g_pos[g_i][1] - p_pos[1]) ** 2) ** 0.5
                if dist_to_pac <= 0.45:
                    ghost_eaten_idx[g_i] = curr_f

            ghost_pts[g_i].append(g_pos[g_i])

    exit_x = float(cols + 1)
    exit_y = p_pos[1]
    while p_pos[0] < exit_x:
        p_pos = _step_toward(p_pos, (exit_x, exit_y), pac_speed)
        pac_pts.append((p_pos[0], p_pos[1], 0))
        for g_i in range(4):
            ghost_pts[g_i].append(g_pos[g_i])

    total_frames = max(1, len(pac_pts) - 1)
    eaten_at_pct = {
        pos: (g_idx * sub_steps / total_frames) * 100.0
        for pos, g_idx in eaten_grid_idx.items()
    }
    trigger_pct = (power_frame_idx / total_frames) * 100.0
    ghost_eaten_pct = [
        (e_idx / total_frames) * 100.0 if e_idx is not None else None
        for e_idx in ghost_eaten_idx
    ]

    return pac_pts, ghost_pts, eaten_at_pct, trigger_pct, ghost_eaten_pct


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

    cols = len(weeks)
    rows = 7
    cs, gap = 11.5, 3.8
    step = cs + gap
    start_x, start_y = 24.0, 12.0

    raw_grid: dict[tuple[int, int], int] = {}
    for w_idx, week in enumerate(weeks):
        for d_idx, day in enumerate(week.get("contributionDays", [])[:rows]):
            lvl_str = day.get("contributionLevel", "NONE")
            raw_grid[(w_idx, d_idx)] = LEVEL_ORDER.get(lvl_str, 0)

    regular_pellets, fruits, final_power = _select_arcade_items(raw_grid, max_items=34)
    pac_pts, ghost_pts, eaten_at_pct, trigger_pct, ghost_eaten_pct = _build_smooth_cycle(
        regular_pellets, fruits, final_power, cols, rows
    )

    total_pts = max(1, len(pac_pts) - 1)
    dur = round(min(44.0, max(26.0, total_pts * 0.045)), 1)

    pac_kf = []
    for idx, (pw, pd, angle) in enumerate(pac_pts):
        pct = (idx / total_pts) * 100.0
        cx = round(start_x + pw * step + cs / 2.0, 1)
        cy = round(start_y + pd * step + cs / 2.0, 1)
        pac_kf.append(f"  {pct:.2f}% {{ transform: translate({cx}px, {cy}px) rotate({angle}deg); }}")

    css_rules = [f"@keyframes pacMove {{\n" + "\n".join(pac_kf) + "\n}"]

    normal_ghost_colors = [PALETTE["coral"], PALETTE["pink"], PALETTE["blue"], PALETTE["peach"]]
    ghosts_svg = []

    t_vuln = min(98.5, trigger_pct + 0.1)

    for g_idx, g_color in enumerate(normal_ghost_colors):
        pts = ghost_pts[g_idx]
        eaten_pct = ghost_eaten_pct[g_idx]

        g_kf = []
        for idx, (gw, gd) in enumerate(pts):
            pct = (idx / total_pts) * 100.0
            cx = round(start_x + gw * step + cs / 2.0, 1)
            cy = round(start_y + gd * step + cs / 2.0, 1)
            op = "0" if (eaten_pct is not None and pct >= eaten_pct) else "1"
            g_kf.append(f"  {pct:.2f}% {{ transform: translate({cx}px, {cy}px); opacity: {op}; }}")

        css_rules.append(f"@keyframes ghostMove{g_idx} {{\n" + "\n".join(g_kf) + "\n}")
        css_rules.append(
            f"@keyframes ghostBody{g_idx} {{\n"
            f"  0%, {trigger_pct:.2f}% {{ fill: {g_color}; }}\n"
            f"  {t_vuln:.2f}%, 99.2% {{ fill: {FRIGHTENED_BLUE}; }}\n"
            f"  100% {{ fill: {g_color}; }}\n"
            f"}}"
        )
        css_rules.append(
            f"@keyframes ghostNormalFace{g_idx} {{\n"
            f"  0%, {trigger_pct:.2f}% {{ opacity: 1; }}\n"
            f"  {t_vuln:.2f}%, 99.2% {{ opacity: 0; }}\n"
            f"  100% {{ opacity: 1; }}\n"
            f"}}"
        )
        css_rules.append(
            f"@keyframes ghostScaredFace{g_idx} {{\n"
            f"  0%, {trigger_pct:.2f}% {{ opacity: 0; }}\n"
            f"  {t_vuln:.2f}%, 99.2% {{ opacity: 1; }}\n"
            f"  100% {{ opacity: 0; }}\n"
            f"}}"
        )

        ghosts_svg.append(
            f"""  <g style="animation: ghostMove{g_idx} {dur}s linear infinite;">
    <path d="M -5.8 5.8 L -5.8 -1 A 5.8 5.8 0 0 1 5.8 -1 L 5.8 5.8 L 3.8 3.8 L 1.9 5.8 L 0 3.8 L -1.9 5.8 L -3.8 3.8 Z"
      fill="{g_color}" style="animation: ghostBody{g_idx} {dur}s linear infinite;" />
    <g style="animation: ghostNormalFace{g_idx} {dur}s linear infinite;">
      <circle cx="-2.1" cy="-1.4" r="1.35" fill="#ffffff" />
      <circle cx="2.1" cy="-1.4" r="1.35" fill="#ffffff" />
      <circle cx="-1.6" cy="-1.4" r="0.7" fill="#1e293b" />
      <circle cx="2.6" cy="-1.4" r="0.7" fill="#1e293b" />
    </g>
    <g opacity="0" style="animation: ghostScaredFace{g_idx} {dur}s linear infinite;">
      <circle cx="-2.0" cy="-1.5" r="0.95" fill="#ffffff" />
      <circle cx="2.0" cy="-1.5" r="0.95" fill="#ffffff" />
      <path d="M -3.4 2.0 L -2.0 1.0 L -0.7 2.0 L 0.7 1.0 L 2.0 2.0 L 3.4 1.0" fill="none" stroke="#ffffff" stroke-width="0.9" stroke-linecap="round" />
    </g>
  </g>"""
        )

    cell_css = []
    board_elements = []

    for w_idx in range(cols):
        for d_idx in range(rows):
            pos = (w_idx, d_idx)
            x = round(start_x + w_idx * step, 1)
            y = round(start_y + d_idx * step, 1)
            cx = round(x + cs / 2.0, 1)
            cy = round(y + cs / 2.0, 1)

            board_elements.append(
                f'  <rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="2.6" fill="{PALETTE["neutral"]}" fill-opacity="0.07" />'
            )

            if pos == final_power:
                eat_pct = min(97.0, max(0.2, eaten_at_pct[pos]))
                after_pct = min(97.5, eat_pct + 0.25)
                anim_name = f"power_{w_idx}_{d_idx}"
                cell_css.append(
                    f"@keyframes {anim_name} {{\n"
                    f"  0%, {eat_pct:.2f}% {{ opacity: 1; }}\n"
                    f"  {after_pct:.2f}%, 99.0% {{ opacity: 0; }}\n"
                    f"  100% {{ opacity: 1; }}\n"
                    f"}}"
                )
                board_elements.append(
                    f'  <circle cx="{cx}" cy="{cy}" r="4.2" fill="{PALETTE["yellow"]}" '
                    f'style="animation: {anim_name} {dur}s linear infinite;" />'
                )
            elif pos in fruits:
                eat_pct = min(97.0, max(0.2, eaten_at_pct[pos]))
                after_pct = min(97.5, eat_pct + 0.25)
                anim_name = f"fruit_{w_idx}_{d_idx}"
                cell_css.append(
                    f"@keyframes {anim_name} {{\n"
                    f"  0%, {eat_pct:.2f}% {{ opacity: 1; }}\n"
                    f"  {after_pct:.2f}%, 99.0% {{ opacity: 0; }}\n"
                    f"  100% {{ opacity: 1; }}\n"
                    f"}}"
                )
                board_elements.append(
                    f'  <g transform="translate({cx}, {cy})" '
                    f'style="animation: {anim_name} {dur}s linear infinite;">'
                    f"{_svg_fruit(fruits[pos])}"
                    f"  </g>"
                )
            elif pos in regular_pellets:
                eat_pct = min(97.0, max(0.2, eaten_at_pct[pos]))
                after_pct = min(97.5, eat_pct + 0.25)
                anim_name = f"p_{w_idx}_{d_idx}"
                cell_css.append(
                    f"@keyframes {anim_name} {{\n"
                    f"  0%, {eat_pct:.2f}% {{ opacity: 1; }}\n"
                    f"  {after_pct:.2f}%, 99.0% {{ opacity: 0; }}\n"
                    f"  100% {{ opacity: 1; }}\n"
                    f"}}"
                )
                board_elements.append(
                    f'  <circle cx="{cx}" cy="{cy}" r="2.2" fill="{PALETTE["mint"]}" '
                    f'style="animation: {anim_name} {dur}s linear infinite;" />'
                )

    pacman_svg = f"""  <g style="animation: pacMove {dur}s linear infinite;">
    <path d="M 0 0 L 6.2 -4.0 A 7.2 7.2 0 1 0 6.2 4.0 Z" fill="{PALETTE['yellow']}">
      <animate attributeName="d"
        values="M 0 0 L 6.2 -4.0 A 7.2 7.2 0 1 0 6.2 4.0 Z; M 0 0 L 7.1 -0.5 A 7.2 7.2 0 1 0 7.1 0.5 Z; M 0 0 L 6.2 -4.0 A 7.2 7.2 0 1 0 6.2 4.0 Z"
        dur="0.28s" repeatCount="indefinite" />
    </path>
  </g>"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 124" width="840" height="124">
  <defs>
    <clipPath id="boardClip">
      <rect x="18" y="4" width="804" height="116" rx="6" />
    </clipPath>
  </defs>
  <style>
{chr(10).join(css_rules)}
{chr(10).join(cell_css)}
  </style>
  <g clip-path="url(#boardClip)">
{chr(10).join(board_elements)}
{chr(10).join(ghosts_svg)}
{pacman_svg}
  </g>
</svg>
"""
