from collections import deque

from ..theme import PALETTE

LEVEL_ORDER = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

BOARD_COLS = 52
BOARD_ROWS = 7

CELL_SIZE = 11.5
CELL_GAP = 3.8
CELL_STEP = CELL_SIZE + CELL_GAP

START_POSITION = (0, 3)

# Sombreado suave y translúcido del tablero según el nivel de contribución
SUBTLE_SHADE = {
    0: (PALETTE["neutral"], "0.03"),
    1: (PALETTE["mint"], "0.06"),
    2: (PALETTE["cyan"], "0.08"),
    3: (PALETTE["blue"], "0.10"),
    4: (PALETTE["yellow"], "0.13"),
}

# Colores base y brillo superior según nivel de contribución del ladrillo
BRICK_PALETTE = {
    1: (PALETTE["mint"], "#ecfdf5"),
    2: (PALETTE["peach"], "#fffbeb"),
    3: (PALETTE["coral"], "#fef2f2"),
    4: (PALETTE["lavender"], "#f5f3ff"),
}


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _percentage(step: int, total_steps: int) -> float:
    return max(0.0, min(100.0, (step / max(1, total_steps)) * 100.0))


def _translate(x: float, y: float) -> str:
    return f"translate({x:.1f}px, {y:.1f}px)"


def _select_bricks_from_contributions(
    level_grid: dict[tuple[int, int], int],
    count_grid: dict[tuple[int, int], int],
    cols: int,
    rows: int,
) -> dict[tuple[int, int], int]:
    """
    Construye los ladrillos rompibles en base a las contribuciones,
    adaptándose a años poco activos o completamente llenos sin amurallar el mapa.
    """
    active_count = sum(1 for lvl in level_grid.values() if lvl >= 1)
    total_cells = max(1, cols * rows)
    density = active_count / total_cells

    # Si el año está muy lleno, dejamos carriles respirables cada 3 columnas para garantizar rutas
    high_density = density >= 0.72

    candidates = [
        pos
        for pos, lvl in level_grid.items()
        if lvl >= 1
        and pos != START_POSITION
        and 1 <= pos[0] < cols - 1
        and not (high_density and pos[0] % 3 == 0 and pos[1] != 3)
    ]

    # Ordena por mayor nivel de contribución y cantidad de aportes, luego de izquierda a derecha
    candidates.sort(
        key=lambda p: (-level_grid.get(p, 0), -count_grid.get(p, 0), p[0], p[1])
    )

    max_same_neighbors = 1 if high_density else 2
    blocks: dict[tuple[int, int], int] = {}

    for pos in candidates:
        adj_blocks = sum(1 for b in blocks if _manhattan(pos, b) == 1)
        if adj_blocks >= max_same_neighbors:
            continue
        blocks[pos] = level_grid[pos]

    return blocks


def _bfs_path(
    start: tuple[int, int],
    goal: tuple[int, int],
    blocked: set[tuple[int, int]],
    cols: int,
    rows: int,
) -> list[tuple[int, int]]:
    if start == goal:
        return []
    if goal in blocked:
        return []

    queue = deque([(start, [])])
    visited = {start}
    directions = ((1, 0), (0, 1), (0, -1), (-1, 0))

    while queue:
        (cw, cd), path = queue.popleft()
        for dw, dd in directions:
            nw, nd = cw + dw, cd + dd
            nxt = (nw, nd)
            if 0 <= nw < cols and 0 <= nd < rows and nxt not in visited and nxt not in blocked:
                new_path = path + [nxt]
                if nxt == goal:
                    return new_path
                visited.add(nxt)
                queue.append((nxt, new_path))

    return []


def _blast_reach(bomb_lvl: int, target_lvl: int, high_density: bool) -> int:
    """Escala el alcance en cruz según la contribución de la zona y el objetivo."""
    peak = max(bomb_lvl, target_lvl)
    if peak >= 4:
        return 3 if high_density else 2
    if peak == 3:
        return 2
    return 2 if high_density else 1


def _compute_cross_cells(
    bomb_pos: tuple[int, int],
    reach: int,
    cols: int,
    rows: int,
) -> list[tuple[int, int]]:
    bc, br = bomb_pos
    cells: list[tuple[int, int]] = [bomb_pos]
    for dw, dd in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for r_step in range(1, reach + 1):
            nc, nr = bc + dw * r_step, br + dd * r_step
            if 0 <= nc < cols and 0 <= nr < rows:
                cells.append((nc, nr))
    return cells


def _find_safe_escape_path(
    plant_pos: tuple[int, int],
    danger_cells: set[tuple[int, int]],
    blocked: set[tuple[int, int]],
    cols: int,
    rows: int,
    max_escape_steps: int = 5,
) -> list[tuple[int, int]]:
    """Aleja a Bomberman fuera del alcance de la explosión antes de que detone."""
    visited = {plant_pos}
    queue = deque([(plant_pos, [])])
    best_fallback: list[tuple[int, int]] = []
    best_score = -10**9

    while queue:
        curr, path = queue.popleft()
        if len(path) > max_escape_steps:
            continue

        if curr not in danger_cells and len(path) >= 1:
            return path

        min_danger_dist = min((_manhattan(curr, d) for d in danger_cells), default=99)
        score = min_danger_dist * 10 - len(path) * 2
        if len(path) >= 1 and score > best_score:
            best_score = score
            best_fallback = path

        for dw, dd in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nw, nd = curr[0] + dw, curr[1] + dd
            nxt = (nw, nd)
            if (
                0 <= nw < cols
                and 0 <= nd < rows
                and nxt not in visited
                and nxt not in blocked
                and len(path) + 1 <= max_escape_steps
            ):
                visited.add(nxt)
                queue.append((nxt, path + [nxt]))

    return best_fallback


def _plan_bomberman_cycle(
    candidate_blocks: dict[tuple[int, int], int],
    level_grid: dict[tuple[int, int], int],
    cols: int,
    rows: int,
    high_density: bool,
) -> tuple[
    list[tuple[int, int]],
    dict[tuple[int, int], int],
    list[dict],
    dict[tuple[int, int], int],
]:
    """
    Coloca bombas sin límite artificial mientras haya bloques alcanzables guiados por
    las contribuciones, destruyendo los bloques que tocan y dejando su sombreado sutil.
    """
    pool = dict(candidate_blocks)
    placed_blocks: dict[tuple[int, int], int] = {}
    curr = START_POSITION
    timeline: list[tuple[int, int]] = [curr]
    bomb_events: list[dict] = []
    destroyed_at_step: dict[tuple[int, int], int] = {}

    # Guarda de seguridad solo para evitar bucles infinitos si el resto queda inalcanzable
    safety_limit = max(1, len(pool) + 4)
    iterations = 0

    while pool and iterations < safety_limit:
        iterations += 1

        # Prioriza bloques de mayor contribución y más cercanos a la posición actual
        ordered_targets = sorted(
            pool.keys(),
            key=lambda p: (-pool[p], _manhattan(p, curr), p[0], p[1]),
        )

        chosen_target = None
        chosen_plant_pos = None
        chosen_path: list[tuple[int, int]] = []

        for target in ordered_targets:
            adj_candidates = sorted(
                (
                    (target[0] + dw, target[1] + dd)
                    for dw, dd in ((-1, 0), (0, -1), (0, 1), (1, 0))
                    if 0 <= target[0] + dw < cols
                    and 0 <= target[1] + dd < rows
                    and (target[0] + dw, target[1] + dd) not in pool
                ),
                key=lambda pos: _manhattan(pos, curr),
            )
            for plant_cand in adj_candidates:
                if plant_cand == curr:
                    chosen_target = target
                    chosen_plant_pos = plant_cand
                    chosen_path = []
                    break
                path = _bfs_path(curr, plant_cand, set(pool.keys()), cols, rows)
                if path:
                    chosen_target = target
                    chosen_plant_pos = plant_cand
                    chosen_path = path
                    break
            if chosen_target is not None:
                break

        if chosen_target is None or chosen_plant_pos is None:
            break

        for step_pos in chosen_path:
            timeline.append(step_pos)

        curr = chosen_plant_pos
        plant_step = len(timeline) - 1

        reach = _blast_reach(
            level_grid.get(chosen_plant_pos, 1),
            pool.get(chosen_target, 1),
            high_density,
        )
        cross_cells = _compute_cross_cells(chosen_plant_pos, reach, cols, rows)
        danger_set = set(cross_cells)

        escape_steps = _find_safe_escape_path(
            chosen_plant_pos,
            danger_set,
            set(pool.keys()),
            cols,
            rows,
            max_escape_steps=reach + 2,
        )
        for esc_pos in escape_steps:
            curr = esc_pos
            timeline.append(curr)

        # Latido breve previo a la explosión
        timeline.append(curr)

        explode_step = len(timeline) - 1
        end_blast_step = explode_step + 2
        for _ in range(2):
            timeline.append(curr)

        hit_blocks: list[tuple[int, int]] = []
        for c_pos in cross_cells:
            if c_pos in pool:
                placed_blocks[c_pos] = pool[c_pos]
                hit_blocks.append(c_pos)
                if c_pos not in destroyed_at_step:
                    destroyed_at_step[c_pos] = explode_step
                del pool[c_pos]

        bomb_events.append(
            {
                "pos": chosen_plant_pos,
                "reach": reach,
                "cross_cells": cross_cells,
                "hit_blocks": hit_blocks,
                "plant_step": plant_step,
                "explode_step": explode_step,
                "end_blast_step": end_blast_step,
            }
        )

    # Salir por el borde derecho al terminar la ronda de bombas
    exit_row = curr[1]
    exit_path = _bfs_path(curr, (cols - 1, exit_row), set(pool.keys()), cols, rows)
    if not exit_path and curr != (cols - 1, exit_row):
        exit_path = _bfs_path(curr, (cols - 1, exit_row), set(), cols, rows)

    for step_pos in exit_path:
        timeline.append(step_pos)

    final_row = timeline[-1][1]
    for w in range(cols, cols + 4):
        timeline.append((w, final_row))

    return timeline, placed_blocks, bomb_events, destroyed_at_step


def _bomberman_sprite() -> str:
    return f"""
    <g style="animation: walkBob 0.55s ease-in-out infinite;">
      <rect x="-4.0" y="-5.2" width="8.0" height="6.8" rx="3.4"
            fill="{PALETTE['lavender']}" stroke="#0f172a" stroke-width="0.9" />
      <rect x="-2.4" y="-3.2" width="4.8" height="2.4" rx="1.0"
            fill="#0f172a" fill-opacity="0.82" />
      <circle cx="-1.1" cy="-2.0" r="0.7" fill="{PALETTE['yellow']}" />
      <circle cx="1.1" cy="-2.0" r="0.7" fill="{PALETTE['yellow']}" />
      <rect x="-3.4" y="1.4" width="6.8" height="3.6" rx="1.4"
            fill="{PALETTE['blue']}" stroke="#0f172a" stroke-width="0.6" />
      <rect x="-3.2" y="4.6" width="2.5" height="1.6" rx="0.6"
            fill="{PALETTE['coral']}" />
      <rect x="0.7" y="4.6" width="2.5" height="1.6" rx="0.6"
            fill="{PALETTE['coral']}" />
    </g>
    """


def _detailed_brick_svg(
    x: float,
    y: float,
    cs: float,
    blk_lvl: int,
    anim_name: str,
    duration: float,
) -> str:
    """Dibuja un ladrillo con borde marcado, luz superior y dos hiladas visibles."""
    base_col, hi_col = BRICK_PALETTE.get(blk_lvl, (PALETTE["peach"], "#fffbeb"))
    mortar = "#0f172a"
    mid_y = round(y + cs * 0.5, 1)
    top_joint_x = round(x + cs * 0.42, 1)
    bot_joint_x = round(x + cs * 0.62, 1)
    bot_y = round(y + cs - 1.0, 1)

    return (
        f'<g style="animation: {anim_name} {duration}s linear infinite;">'
        f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="2.0" '
        f'fill="{base_col}" stroke="{mortar}" stroke-width="1.15" />'
        f'<rect x="{x + 1.2:.1f}" y="{y + 1.2:.1f}" width="{cs - 2.4:.1f}" height="2.0" rx="0.8" '
        f'fill="{hi_col}" fill-opacity="0.75" />'
        f'<line x1="{x + 0.8:.1f}" y1="{mid_y}" x2="{x + cs - 0.8:.1f}" y2="{mid_y}" '
        f'stroke="{mortar}" stroke-opacity="0.78" stroke-width="1.05" />'
        f'<line x1="{top_joint_x}" y1="{y + 1.0:.1f}" x2="{top_joint_x}" y2="{mid_y}" '
        f'stroke="{mortar}" stroke-opacity="0.72" stroke-width="1.0" />'
        f'<line x1="{bot_joint_x}" y1="{mid_y}" x2="{bot_joint_x}" y2="{bot_y}" '
        f'stroke="{mortar}" stroke-opacity="0.72" stroke-width="1.0" />'
        f"</g>"
    )


def _fire_cross_svg(
    start_x: float,
    start_y: float,
    step: float,
    cs: float,
    cross_cells: list[tuple[int, int]],
) -> str:
    """Dibuja llamas y chispas visibles en cada casilla de la explosión en cruz."""
    parts: list[str] = []
    half = cs / 2.0

    for cc, cr in cross_cells:
        cx = round(start_x + cc * step + half, 1)
        cy = round(start_y + cr * step + half, 1)

        parts.append(
            f'<g transform="translate({cx}, {cy})">'
            f'<circle cx="0" cy="0" r="5.0" fill="{PALETTE["coral"]}" fill-opacity="0.82" />'
            f'<polygon points="0,-5.8 2.8,-1.2 4.8,2.0 1.6,4.8 -1.6,4.8 -4.8,2.0 -2.8,-1.2" '
            f'fill="{PALETTE["peach"]}" />'
            f'<circle cx="0" cy="0.5" r="2.5" fill="{PALETTE["yellow"]}" />'
            f'<rect x="-5.0" y="-4.2" width="1.8" height="1.8" rx="0.4" fill="{PALETTE["yellow"]}" />'
            f'<rect x="3.2" y="-3.8" width="1.8" height="1.8" rx="0.4" fill="{PALETTE["coral"]}" />'
            f'<rect x="3.0" y="3.0" width="1.7" height="1.7" rx="0.4" fill="{PALETTE["yellow"]}" />'
            f"</g>"
        )

    return "".join(parts)


def render(data: dict) -> str:
    weeks = data.get("calendar_weeks", [])[-BOARD_COLS:]

    if not weeks:
        synthetic_levels = (
            "NONE",
            "FIRST_QUARTILE",
            "SECOND_QUARTILE",
            "THIRD_QUARTILE",
            "FOURTH_QUARTILE",
        )
        weeks = [
            {
                "contributionDays": [
                    {
                        "contributionCount": ((w * 7 + d * 3) % 9),
                        "contributionLevel": synthetic_levels[(w * 7 + d * 3) % 5],
                    }
                    for d in range(BOARD_ROWS)
                ]
            }
            for w in range(BOARD_COLS)
        ]

    if len(weeks) < BOARD_COLS:
        empty_week = {
            "contributionDays": [
                {"contributionCount": 0, "contributionLevel": "NONE"}
                for _ in range(BOARD_ROWS)
            ]
        }
        weeks = [empty_week.copy() for _ in range(BOARD_COLS - len(weeks))] + weeks

    cols = BOARD_COLS
    rows = BOARD_ROWS
    cs = CELL_SIZE
    step = CELL_STEP
    start_x = 24.0
    start_y = 12.0

    level_grid: dict[tuple[int, int], int] = {}
    count_grid: dict[tuple[int, int], int] = {}

    for w_idx, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        for d_idx, day in enumerate(days[:rows]):
            pos = (w_idx, d_idx)
            level_grid[pos] = LEVEL_ORDER.get(day.get("contributionLevel", "NONE"), 0)
            count_grid[pos] = max(0, int(day.get("contributionCount", 0) or 0))

    active_count = sum(1 for lvl in level_grid.values() if lvl >= 1)
    high_density = (active_count / max(1, cols * rows)) >= 0.72

    candidate_blocks = _select_bricks_from_contributions(level_grid, count_grid, cols, rows)
    timeline, placed_blocks, bomb_events, destroyed_at_step = _plan_bomberman_cycle(
        candidate_blocks, level_grid, cols, rows, high_density
    )

    total_steps = max(1, len(timeline) - 1)
    # Cadencia fluida de caminata (~0.28s por paso, entre 24s y 55s según longitud del ciclo)
    duration = round(min(55.0, max(24.0, total_steps * 0.28)), 1)

    css_rules: list[str] = [
        "@keyframes walkBob {\n"
        "  0%, 100% { transform: translateY(0px); }\n"
        "  50% { transform: translateY(-0.9px); }\n"
        "}"
    ]
    board_svg: list[str] = []
    effects_svg: list[str] = []

    for col in range(cols):
        for row in range(rows):
            pos = (col, row)
            x = round(start_x + col * step, 1)
            y = round(start_y + row * step, 1)
            lvl = level_grid.get(pos, 0)
            shade_color, shade_op = SUBTLE_SHADE.get(lvl, SUBTLE_SHADE[0])

            if pos in placed_blocks:
                blk_lvl = placed_blocks[pos]
                break_pct = min(
                    95.5,
                    max(0.5, round(_percentage(destroyed_at_step.get(pos, total_steps), total_steps), 2)),
                )
                after_pct = min(96.0, round(break_pct + 0.35, 2))

                shade_anim = f"shade_{col}_{row}"
                block_anim = f"block_{col}_{row}"

                css_rules.append(
                    f"@keyframes {shade_anim} {{\n"
                    f"  0%, {break_pct:.2f}% {{ opacity: 0.03; }}\n"
                    f"  {after_pct:.2f}%, 98.0% {{ opacity: {shade_op}; }}\n"
                    f"  99.5%, 100% {{ opacity: 0.03; }}\n"
                    f"}}"
                )
                css_rules.append(
                    f"@keyframes {block_anim} {{\n"
                    f"  0%, {break_pct:.2f}% {{ opacity: 0.98; }}\n"
                    f"  {after_pct:.2f}%, 98.0% {{ opacity: 0; }}\n"
                    f"  99.5%, 100% {{ opacity: 0.98; }}\n"
                    f"}}"
                )

                board_svg.append(
                    f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="2.4" '
                    f'fill="{shade_color}" opacity="0.03" '
                    f'style="animation: {shade_anim} {duration}s linear infinite;" />'
                )
                board_svg.append(
                    _detailed_brick_svg(x, y, cs, blk_lvl, block_anim, duration)
                )
            else:
                board_svg.append(
                    f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="2.4" '
                    f'fill="{shade_color}" fill-opacity="{shade_op}" />'
                )

    for b_idx, bomb in enumerate(bomb_events):
        bc, br = bomb["pos"]
        bx = round(start_x + bc * step + cs / 2, 1)
        by = round(start_y + br * step + cs / 2, 1)

        plant_pct = round(_percentage(bomb["plant_step"], total_steps), 2)
        exp_pct = round(_percentage(bomb["explode_step"], total_steps), 2)
        end_pct = round(min(98.5, _percentage(bomb["end_blast_step"], total_steps)), 2)
        show_start = round(min(97.5, plant_pct + 0.2), 2)
        after_exp = round(min(98.0, exp_pct + 0.2), 2)

        pulse_span = max(0.5, exp_pct - show_start)
        p1 = round(show_start + pulse_span * 0.25, 2)
        p2 = round(show_start + pulse_span * 0.50, 2)
        p3 = round(show_start + pulse_span * 0.75, 2)
        p4 = round(max(p3, exp_pct - 0.15), 2)

        bomb_anim = f"bomb_{b_idx}"
        css_rules.append(
            f"@keyframes {bomb_anim} {{\n"
            f"  0%, {plant_pct:.2f}% {{ opacity: 0; transform: {_translate(bx, by)} scale(0.5); }}\n"
            f"  {show_start:.2f}% {{ opacity: 1; transform: {_translate(bx, by)} scale(0.95); }}\n"
            f"  {p1:.2f}% {{ opacity: 1; transform: {_translate(bx, by)} scale(1.18); }}\n"
            f"  {p2:.2f}% {{ opacity: 1; transform: {_translate(bx, by)} scale(0.90); }}\n"
            f"  {p3:.2f}% {{ opacity: 1; transform: {_translate(bx, by)} scale(1.26); }}\n"
            f"  {p4:.2f}%, {exp_pct:.2f}% {{ opacity: 1; transform: {_translate(bx, by)} scale(1.35); }}\n"
            f"  {after_exp:.2f}%, 100% {{ opacity: 0; transform: {_translate(bx, by)} scale(1.42); }}\n"
            f"}}"
        )
        effects_svg.append(
            f'<g opacity="0" style="transform-box: fill-box; transform-origin: center; animation: {bomb_anim} {duration}s linear infinite;">'
            f'<circle cx="0" cy="0.5" r="4.5" fill="{PALETTE["neutral"]}" stroke="{PALETTE["yellow"]}" stroke-width="0.9" />'
            f'<circle cx="-1.3" cy="-0.8" r="1.1" fill="#ffffff" fill-opacity="0.4" />'
            f'<line x1="2.2" y1="-3.5" x2="4.4" y2="-5.4" stroke="{PALETTE["coral"]}" stroke-width="1.25" stroke-linecap="round" />'
            f'<circle cx="4.6" cy="-5.6" r="1.4" fill="{PALETTE["yellow"]}" />'
            f"</g>"
        )

        blast_anim = f"blast_{b_idx}"
        css_rules.append(
            f"@keyframes {blast_anim} {{\n"
            f"  0%, {exp_pct:.2f}% {{ opacity: 0; }}\n"
            f"  {after_exp:.2f}%, {end_pct:.2f}% {{ opacity: 0.95; }}\n"
            f"  {min(99.2, round(end_pct + 0.4, 2)):.2f}%, 100% {{ opacity: 0; }}\n"
            f"}}"
        )

        effects_svg.append(
            f'<g opacity="0" style="animation: {blast_anim} {duration}s linear infinite;">'
            + _fire_cross_svg(start_x, start_y, step, cs, bomb["cross_cells"])
            + "</g>"
        )

    hero_kf: list[str] = []
    for idx, (col, row) in enumerate(timeline):
        pct = round(_percentage(idx, total_steps), 2)
        cx = round(start_x + col * step + cs / 2, 1)
        cy = round(start_y + row * step + cs / 2, 1)
        hero_kf.append(
            f"  {pct:.2f}% {{ transform: {_translate(cx, cy)}; animation-timing-function: ease-in-out; }}"
        )

    css_rules.append("@keyframes bomberMove {\n" + "\n".join(hero_kf) + "\n}")

    start_cx = round(start_x + START_POSITION[0] * step + cs / 2, 1)
    start_cy = round(start_y + START_POSITION[1] * step + cs / 2, 1)

    css_rules.append(
        f"""@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; }}
  .bomber-hero {{ transform: {_translate(start_cx, start_cy)}; }}
}}"""
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 124" width="840" height="124" role="img" aria-label="Cartucho de Bomberman sobre la grilla de contribuciones">
  <defs>
    <clipPath id="bomberClip">
      <rect x="18" y="4" width="804" height="116" rx="6" />
    </clipPath>
  </defs>
  <style>
{chr(10).join(css_rules)}
  </style>
  <g clip-path="url(#bomberClip)">
{chr(10).join(board_svg)}
{chr(10).join(effects_svg)}
    <g class="bomber-hero" style="animation: bomberMove {duration}s linear infinite;">
      {_bomberman_sprite()}
    </g>
  </g>
</svg>
"""
