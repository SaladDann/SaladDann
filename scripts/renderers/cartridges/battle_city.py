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
MAX_ENEMIES = 5
MAX_STEEL_BLOCKS = 10
MAX_BRICK_BLOCKS = 16

CELL_SIZE = 11.5
CELL_GAP = 3.8
CELL_STEP = CELL_SIZE + CELL_GAP

START_POSITION = (22, 6)

LEVEL_FILL = {
    0: PALETTE["neutral"],
    1: PALETTE["mint"],
    2: PALETTE["cyan"],
    3: PALETTE["blue"],
    4: PALETTE["yellow"],
}


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _build_map_designs(
    level_grid: dict[tuple[int, int], int],
    count_grid: dict[tuple[int, int], int],
    cols: int,
    rows: int,
) -> tuple[
    set[tuple[int, int]],
    set[tuple[int, int]],
    list[tuple[int, int]],
]:
    """
    Construye diseños compactos de mapa (murallas, esquinas y trincheras)
    guiados por contribuciones sin saturar el tablero en años muy activos,
    y selecciona enemigos sobre celdas de contribución libres.
    """
    steel_blocks: set[tuple[int, int]] = set()
    brick_blocks: set[tuple[int, int]] = set()

    high_cells = sorted(
        (
            pos
            for pos, lvl in level_grid.items()
            if (
                lvl >= 3
                and pos != START_POSITION
                and 2 <= pos[0] <= cols - 3
                and 1 <= pos[1] <= rows - 2
            )
        ),
        key=lambda p: (-level_grid.get(p, 0), -count_grid.get(p, 0), p[0], p[1]),
    )

    templates = [
        ((0, 0), (1, 0), (0, 1)),      # Esquina de fortín
        ((-1, 0), (0, 0), (1, 0)),     # Muralla corta
        ((0, -1), (0, 0), (0, 1)),     # Trinchera vertical
    ]

    for idx, anchor in enumerate(high_cells):
        if len(steel_blocks) >= MAX_STEEL_BLOCKS and len(brick_blocks) >= MAX_BRICK_BLOCKS:
            break
        if any(_manhattan(anchor, s) < 7 for s in steel_blocks | brick_blocks):
            continue

        tpl = templates[idx % len(templates)]
        for dw, dd in tpl:
            cell = (anchor[0] + dw, anchor[1] + dd)
            if not (1 <= cell[0] <= cols - 2 and 0 <= cell[1] <= rows - 1):
                continue
            if cell == START_POSITION:
                continue

            lvl = level_grid.get(cell, 0)
            if lvl == 4 and len(steel_blocks) < MAX_STEEL_BLOCKS and cell not in brick_blocks:
                steel_blocks.add(cell)
            elif lvl >= 2 and len(brick_blocks) < MAX_BRICK_BLOCKS and cell not in steel_blocks:
                brick_blocks.add(cell)

    for pos, lvl in sorted(
        level_grid.items(),
        key=lambda item: (-item[1], -count_grid.get(item[0], 0), item[0][0], item[0][1]),
    ):
        if pos == START_POSITION or pos in steel_blocks or pos in brick_blocks:
            continue
        if not (1 <= pos[0] <= cols - 2 and 0 <= pos[1] <= rows - 1):
            continue
        if lvl == 4 and len(steel_blocks) < MAX_STEEL_BLOCKS:
            if all(_manhattan(pos, s) >= 4 for s in steel_blocks):
                steel_blocks.add(pos)
        elif lvl in (2, 3) and len(brick_blocks) < MAX_BRICK_BLOCKS:
            if all(_manhattan(pos, b) >= 4 for b in brick_blocks):
                brick_blocks.add(pos)

    obstacles = steel_blocks | brick_blocks | {START_POSITION}

    # Enemigos en cualquier celda de contribución libre del mapa
    enemy_candidates = [
        pos
        for pos, lvl in level_grid.items()
        if (lvl > 0 or count_grid.get(pos, 0) > 0) and pos not in obstacles
    ]
    enemy_candidates.sort(
        key=lambda p: (-level_grid.get(p, 0), -count_grid.get(p, 0), p[0], p[1])
    )

    enemy_targets: list[tuple[int, int]] = []
    for pos in enemy_candidates:
        if all(_manhattan(pos, e) >= 6 for e in enemy_targets):
            enemy_targets.append(pos)
        if len(enemy_targets) >= MAX_ENEMIES:
            break

    if len(enemy_targets) < MAX_ENEMIES:
        for col in range(cols):
            for row in range(rows):
                pos = (col, row)
                if pos not in obstacles and pos not in enemy_targets:
                    if all(_manhattan(pos, e) >= 5 for e in enemy_targets):
                        enemy_targets.append(pos)
                if len(enemy_targets) >= MAX_ENEMIES:
                    break
            if len(enemy_targets) >= MAX_ENEMIES:
                break

    enemy_targets.sort(key=lambda p: (p[0], p[1]))
    return steel_blocks, brick_blocks, enemy_targets


def _bfs_tank_path(
    start: tuple[int, int],
    goal: tuple[int, int],
    obstacles: set[tuple[int, int]],
    cols: int,
    rows: int,
) -> list[tuple[int, int]] | None:
    if start == goal:
        return []

    if (
        not (0 <= start[0] < cols and 0 <= start[1] < rows)
        or not (0 <= goal[0] < cols and 0 <= goal[1] < rows)
        or start in obstacles
        or goal in obstacles
    ):
        return None

    queue = deque([start])
    predecessors: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

    while queue:
        current = queue.popleft()
        for dw, dd in directions:
            nxt = (current[0] + dw, current[1] + dd)
            if not (0 <= nxt[0] < cols and 0 <= nxt[1] < rows):
                continue
            if nxt in predecessors or nxt in obstacles:
                continue

            predecessors[nxt] = current
            if nxt == goal:
                path = []
                node = goal
                while node != start:
                    path.append(node)
                    node = predecessors[node]
                path.reverse()
                return path

            queue.append(nxt)

    return None


def _has_clear_line_of_sight(
    shooter: tuple[int, int],
    target: tuple[int, int],
    obstacles: set[tuple[int, int]],
) -> bool:
    """Devuelve True si hay línea recta (horizontal o vertical) sin obstáculos entre shooter y target."""
    sc, sr = shooter
    tc, tr = target
    if sc == tc and sr != tr:
        step = 1 if tr > sr else -1
        for r in range(sr + step, tr, step):
            if (sc, r) in obstacles:
                return False
        return True
    if sr == tr and sc != tc:
        step = 1 if tc > sc else -1
        for c in range(sc + step, tc, step):
            if (c, sr) in obstacles:
                return False
        return True
    return False


def _aim_angle(
    shooter: tuple[int, int],
    target: tuple[int, int],
) -> int:
    dw = target[0] - shooter[0]
    dd = target[1] - shooter[1]
    if abs(dw) >= abs(dd):
        return 90 if dw > 0 else -90
    return 180 if dd > 0 else 0


def _facing_angle(
    prev_pos: tuple[int, int],
    curr_pos: tuple[int, int],
) -> int:
    dw = curr_pos[0] - prev_pos[0]
    dd = curr_pos[1] - prev_pos[1]

    if dw > 0:
        return 90
    if dw < 0:
        return -90
    if dd > 0:
        return 180
    return 0


def _find_line_of_sight_spot(
    enemy: tuple[int, int],
    current: tuple[int, int],
    obstacles: set[tuple[int, int]],
    cols: int,
    rows: int,
) -> tuple[tuple[int, int], list[tuple[int, int]]] | None:
    """
    Busca la celda accesible más cercana desde donde el tanque tenga línea de visión
    recta y despejada hacia `enemy`, sin tener que pegarse a él.
    """
    candidates: list[tuple[int, tuple[int, int], list[tuple[int, int]]]] = []

    for c in range(cols):
        for r in range(rows):
            cand = (c, r)
            if cand == enemy or cand in obstacles:
                continue
            if not _has_clear_line_of_sight(cand, enemy, obstacles):
                continue
            path = _bfs_tank_path(current, cand, obstacles, cols, rows)
            if path is not None:
                dist = _manhattan(cand, enemy)
                dist_penalty = 0 if 2 <= dist <= 8 else abs(dist - 4)
                score = len(path) + dist_penalty
                candidates.append((score, cand, path))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    _, best_spot, best_path = candidates[0]
    return best_spot, best_path


def _tank_sprite(
    body_color: str,
    track_color: str,
    accent_color: str = "#ffffff",
) -> str:
    return f"""
    <rect x="-8" y="-8" width="16" height="16" fill="#000" fill-opacity="0" pointer-events="none" />
    <rect x="-5.5" y="-5.5" width="2.5" height="11" fill="{track_color}"/>
    <rect x="-5.1" y="-4.1" width="1.7" height="1.2" fill="{accent_color}" fill-opacity="0.55"/>
    <rect x="-5.1" y="-1.0" width="1.7" height="1.2" fill="{accent_color}" fill-opacity="0.55"/>
    <rect x="-5.1" y="2.1" width="1.7" height="1.2" fill="{accent_color}" fill-opacity="0.55"/>
    <rect x="3" y="-5.5" width="2.5" height="11" fill="{track_color}"/>
    <rect x="3.4" y="-4.1" width="1.7" height="1.2" fill="{accent_color}" fill-opacity="0.55"/>
    <rect x="3.4" y="-1.0" width="1.7" height="1.2" fill="{accent_color}" fill-opacity="0.55"/>
    <rect x="3.4" y="2.1" width="1.7" height="1.2" fill="{accent_color}" fill-opacity="0.55"/>
    <rect x="-3.7" y="-4.7" width="7.4" height="9.4" fill="{body_color}"/>
    <rect x="-2.5" y="-3.5" width="5" height="2" fill="{accent_color}" fill-opacity="0.35"/>
    <rect x="-2.1" y="-2.1" width="4.2" height="4.2" fill="{body_color}"
          stroke="{accent_color}" stroke-opacity="0.65" stroke-width="0.6" />
    <rect x="-1.0" y="-7.5" width="2.0" height="5.5" fill="{body_color}"/>
    <rect x="-0.6" y="-7.5" width="1.2" height="1.5" fill="{accent_color}" fill-opacity="0.5"/>
"""


def _build_base_dock_svg(
    start_x: float,
    step: float,
    cs: float,
    dock_y: float,
    dock_h: float,
) -> str:
    """
    Dibuja una zona de base ampliada fuera del calendario (en la franja inferior),
    con el águila protegida por muros al centro y detalles de agua y bosque a los lados.
    """
    center_x = round(start_x + 25 * step + cs / 2, 1)
    mid_y = round(dock_y + dock_h / 2, 1)

    # Agua pixelada a la izquierda y derecha (fuera del núcleo de la base)
    water_patches: list[str] = []
    for wx in (64.0, 128.0, 624.0, 692.0):
        wy = round(dock_y + 3.0, 1)
        water_patches.append(
            f"""
            <rect x="{wx}" y="{wy}" width="24" height="8" rx="1.5"
                  fill="{PALETTE['cyan']}" fill-opacity="0.24" />
            <rect x="{wx + 3}" y="{wy + 2.5}" width="7" height="1.2"
                  fill="#ffffff" fill-opacity="0.45" />
            <rect x="{wx + 13}" y="{wy + 5.2}" width="8" height="1.2"
                  fill="#ffffff" fill-opacity="0.45" />
            """
        )

    # Bosque pixelado (copas de árboles en tonos mint) intercalado en la franja
    forest_patches: list[str] = []
    for tx in (210.0, 224.0, 238.0, 540.0, 554.0, 568.0):
        ty = round(dock_y + 2.2, 1)
        forest_patches.append(
            f"""
            <rect x="{tx}" y="{ty}" width="9" height="9" rx="2"
                  fill="{PALETTE['mint']}" fill-opacity="0.34" />
            <rect x="{tx + 2}" y="{ty + 2}" width="5" height="4" rx="1"
                  fill="{PALETTE['mint']}" fill-opacity="0.62" />
            """
        )

    # Muros de ladrillo y acero en U alrededor del águila en la zona ampliada
    wall_top_y = round(dock_y + 1.2, 1)
    wall_side_y = round(dock_y + 5.2, 1)
    brick_w = 6.2
    brick_h = 3.6

    fort_bricks: list[str] = []
    for bx in (
        center_x - 16.5,
        center_x - 9.8,
        center_x + 3.6,
        center_x + 10.3,
    ):
        fort_bricks.append(
            f"""
            <rect x="{bx:.1f}" y="{wall_top_y:.1f}" width="{brick_w}" height="{brick_h}" rx="0.7"
                  fill="{PALETTE['peach']}" fill-opacity="0.92" />
            """
        )

    for sx in (center_x - 16.5, center_x + 10.3):
        fort_bricks.append(
            f"""
            <rect x="{sx:.1f}" y="{wall_side_y:.1f}" width="{brick_w}" height="{brick_h}" rx="0.7"
                  fill="{PALETTE['peach']}" fill-opacity="0.92" />
            """
        )

    # Detalle de acero en los extremos del fortín
    for stx in (center_x - 23.2, center_x + 17.0):
        fort_bricks.append(
            f"""
            <rect x="{stx:.1f}" y="{wall_top_y:.1f}" width="5.4" height="7.6" rx="1"
                  fill="{PALETTE['blue']}" fill-opacity="0.88" />
            <rect x="{stx + 1.5:.1f}" y="{wall_top_y + 1.8:.1f}" width="2.4" height="4.0"
                  fill="#ffffff" fill-opacity="0.4" />
            """
        )

    eagle_cy = round(dock_y + 7.2, 1)

    return f"""
    <rect x="16" y="{dock_y}" width="808" height="{dock_h:.1f}" rx="3"
          fill="{PALETTE['neutral']}" fill-opacity="0.055" />
    {"".join(water_patches)}
    {"".join(forest_patches)}
    {"".join(fort_bricks)}
    <g transform="translate({center_x}, {eagle_cy})">
        <rect x="-5.2" y="-4.5" width="10.4" height="9.0" rx="1.2"
              fill="{PALETTE['lavender']}" fill-opacity="0.16"
              stroke="{PALETTE['lavender']}" stroke-width="0.8" />
        <polygon points="0,-3.2 -3.6,-0.7 -1.5,1.1 -2.6,3.1 0,2.0 2.6,3.1 1.5,1.1 3.6,-0.7"
                 fill="{PALETTE['yellow']}" />
    </g>
    """


def _percentage(step: int, total_steps: int) -> float:
    return max(0.0, min(100.0, (step / max(1, total_steps)) * 100.0))


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
                        "contributionCount": ((week * 7 + day * 3) % 9),
                        "contributionLevel": synthetic_levels[(week * 7 + day * 3) % 5],
                    }
                    for day in range(BOARD_ROWS)
                ]
            }
            for week in range(BOARD_COLS)
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
    start_y = 6.5

    raw_grid: dict[tuple[int, int], int] = {}
    count_grid: dict[tuple[int, int], int] = {}

    for week_index, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        for day_index, day in enumerate(days[:rows]):
            pos = (week_index, day_index)
            lvl = LEVEL_ORDER.get(day.get("contributionLevel", "NONE"), 0)
            cnt = max(0, int(day.get("contributionCount", 0) or 0))
            raw_grid[pos] = lvl
            count_grid[pos] = cnt

    steel_blocks, brick_blocks, enemy_targets = _build_map_designs(
        raw_grid, count_grid, cols, rows
    )

    solid_obstacles = steel_blocks | brick_blocks

    curr = START_POSITION
    hero_timeline: list[tuple[tuple[int, int], int]] = [(curr, 0)]
    battles: list[dict] = []

    for enemy in enemy_targets:
        spot_result = _find_line_of_sight_spot(enemy, curr, solid_obstacles, cols, rows)
        if spot_result is None:
            continue

        shooter, path = spot_result
        for position in path:
            previous = hero_timeline[-1][0]
            angle = _facing_angle(previous, position)
            hero_timeline.append((position, angle))

        curr = shooter
        shot_angle = _aim_angle(shooter, enemy)
        fire_start_step = len(hero_timeline)

        for _ in range(4):
            hero_timeline.append((curr, shot_angle))

        battles.append(
            {
                "enemy": enemy,
                "shooter": shooter,
                "fire_step": fire_start_step,
                "hit_step": fire_start_step + 2,
                "level": raw_grid.get(enemy, 1),
            }
        )

    return_path = _bfs_tank_path(curr, START_POSITION, solid_obstacles, cols, rows)
    if return_path is not None:
        for position in return_path:
            previous = hero_timeline[-1][0]
            angle = _facing_angle(previous, position)
            hero_timeline.append((position, angle))

    hero_timeline.append((START_POSITION, 0))

    total_steps = max(1, len(hero_timeline) - 1)
    duration = round(min(40.0, max(24.0, total_steps * 0.22)), 1)

    hero_start_cx = round(start_x + START_POSITION[0] * step + cs / 2, 2)
    hero_start_cy = round(start_y + START_POSITION[1] * step + cs / 2, 2)

    board_height = round((rows - 1) * step + cs, 1)
    dock_y = round(start_y + board_height + 2.5, 1)
    dock_h = max(12.0, round(122.0 - dock_y, 1))

    board_svg: list[str] = []

    for col in range(cols):
        for row in range(rows):
            position = (col, row)
            x = round(start_x + col * step, 1)
            y = round(start_y + row * step, 1)

            if position in steel_blocks:
                board_svg.append(
                    f"""
                    <rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="1.5"
                          fill="{PALETTE['blue']}" fill-opacity="0.92" />
                    <rect x="{x + 2.5:.1f}" y="{y + 2.5:.1f}" width="{cs - 5:.1f}" height="{cs - 5:.1f}"
                          fill="#ffffff" fill-opacity="0.45" />
                    """
                )
            elif position in brick_blocks:
                board_svg.append(
                    f"""
                    <rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="1"
                          fill="{PALETTE['peach']}" fill-opacity="0.92" />
                    <path d="M {x} {y + cs / 2:.1f} H {x + cs:.1f} M {x + cs / 2:.1f} {y} V {y + cs / 2:.1f}"
                          fill="none" stroke="#1e293b" stroke-opacity="0.28" stroke-width="0.8" />
                    """
                )
            else:
                lvl_op = 0.025 + raw_grid.get(position, 0) * 0.015
                board_svg.append(
                    f"""
                    <rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="2"
                          fill="{PALETTE['neutral']}" fill-opacity="{lvl_op:.3f}"
                          stroke="{PALETTE['neutral']}" stroke-opacity="0.04" stroke-width="1" />
                    """
                )

    base_dock_svg = _build_base_dock_svg(start_x, step, cs, dock_y, dock_h)

    hero_keyframes: list[str] = []
    for index, (position, angle) in enumerate(hero_timeline):
        col, row = position
        percentage = _percentage(index, total_steps)
        cx = round(start_x + col * step + cs / 2, 1)
        cy = round(start_y + row * step + cs / 2, 1)
        hero_keyframes.append(
            f"{percentage:.2f}% {{ transform: translate({cx}px, {cy}px) rotate({angle}deg); }}"
        )

    css_rules = [
        "@keyframes heroTank {\n" + "\n".join(hero_keyframes) + "\n}",
    ]

    combat_svg: list[str] = []

    for battle_index, battle in enumerate(battles):
        enemy_col, enemy_row = battle["enemy"]
        shooter_col, shooter_row = battle["shooter"]
        enemy_lvl = battle["level"]

        cell_x = round(start_x + enemy_col * step, 1)
        cell_y = round(start_y + enemy_row * step, 1)
        enemy_x = round(cell_x + cs / 2, 1)
        enemy_y = round(cell_y + cs / 2, 1)
        shooter_x = round(start_x + shooter_col * step + cs / 2, 1)
        shooter_y = round(start_y + shooter_row * step + cs / 2, 1)

        fire_pct = _percentage(battle["fire_step"], total_steps)
        hit_pct = _percentage(battle["hit_step"], total_steps)

        explosion_start = min(100.0, hit_pct + 0.3)
        explosion_end = min(100.0, hit_pct + 2.2)
        if explosion_end <= explosion_start:
            explosion_end = 100.0

        paint_anim = f"gridPaint_{battle_index}"
        paint_color = LEVEL_FILL.get(enemy_lvl, PALETTE["mint"])
        css_rules.append(
            f"""
            @keyframes {paint_anim} {{
                0%, {hit_pct:.2f}% {{ opacity: 0; }}
                {explosion_start:.2f}%, 98.5% {{ opacity: 0.72; }}
                100% {{ opacity: 0; }}
            }}
            """
        )
        combat_svg.append(
            f"""
            <rect
                class="grid-painted"
                x="{cell_x}" y="{cell_y}"
                width="{cs}" height="{cs}"
                rx="2"
                fill="{paint_color}"
                fill-opacity="0.55"
                stroke="{paint_color}"
                stroke-width="0.9"
                opacity="0"
                style="animation: {paint_anim} {duration}s linear infinite;"
            />
            """
        )

        enemy_anim = f"enemyTank_{battle_index}"
        spawn_pct = max(0.0, hit_pct - 8.0)
        visible_pct = max(spawn_pct, hit_pct - 1.5)

        css_rules.append(
            f"""
            @keyframes {enemy_anim} {{
                0%, {spawn_pct:.2f}% {{
                    transform: translate({enemy_x}px, -10px) rotate(180deg);
                    opacity: 0;
                    animation-timing-function: cubic-bezier(.33,1,.68,1);
                }}
                {visible_pct:.2f}%, {hit_pct:.2f}% {{
                    transform: translate({enemy_x}px, {enemy_y}px) rotate(180deg);
                    opacity: 1;
                }}
                {explosion_start:.2f}%, 100% {{
                    transform: translate({enemy_x}px, {enemy_y}px) rotate(180deg);
                    opacity: 0;
                }}
            }}
            """
        )

        combat_svg.append(
            f"""
            <g class="enemy-tank"
               style="opacity: 0; transform-box: fill-box; transform-origin: center;
                      will-change: transform, opacity; animation: {enemy_anim} {duration}s linear infinite;">
                {_tank_sprite(PALETTE['lavender'], PALETTE['neutral'])}
            </g>
            """
        )

        shell_anim = f"shell_{battle_index}"
        shell_start = min(100.0, fire_pct + 0.15)
        shell_end = min(100.0, hit_pct + 0.2)
        shot_angle = _aim_angle(battle["shooter"], battle["enemy"])

        css_rules.append(
            f"""
            @keyframes {shell_anim} {{
                0%, {fire_pct:.2f}% {{ transform: translate({shooter_x}px, {shooter_y}px) rotate({shot_angle}deg); opacity: 0; }}
                {shell_start:.2f}% {{ transform: translate({shooter_x}px, {shooter_y}px) rotate({shot_angle}deg); opacity: 1; }}
                {hit_pct:.2f}% {{ transform: translate({enemy_x}px, {enemy_y}px) rotate({shot_angle}deg); opacity: 1; }}
                {shell_end:.2f}%, 100% {{ transform: translate({enemy_x}px, {enemy_y}px) rotate({shot_angle}deg); opacity: 0; }}
            }}
            """
        )

        combat_svg.append(
            f"""
            <rect class="shell" x="-1.2" y="-2.5" width="2.4" height="5"
                  fill="{PALETTE['coral']}" opacity="0"
                  style="transform-box: fill-box; transform-origin: center;
                         will-change: transform, opacity; animation: {shell_anim} {duration}s linear infinite;
                         animation-fill-mode: both;" />
            """
        )

        boom_anim = f"tankBoom_{battle_index}"

        css_rules.append(
            f"""
            @keyframes {boom_anim} {{
                0%, {hit_pct:.2f}% {{ transform: translate({enemy_x}px, {enemy_y}px) scale(0.3); opacity: 0; }}
                {explosion_start:.2f}% {{
                    transform: translate({enemy_x}px, {enemy_y}px) scale(1.0);
                    opacity: 1;
                    animation-timing-function: cubic-bezier(.22,1,.36,1);
                }}
                {explosion_end:.2f}%, 100% {{ transform: translate({enemy_x}px, {enemy_y}px) scale(1.7); opacity: 0; }}
            }}
            """
        )

        combat_svg.append(
            f"""
            <g class="pixel-explosion" opacity="0" shape-rendering="crispEdges"
               style="transform-box: fill-box; transform-origin: center;
                      will-change: transform, opacity; animation: {boom_anim} {duration}s linear infinite;
                      animation-fill-mode: both;">
                <rect x="-2.5" y="-2.5" width="5" height="5" fill="{PALETTE['yellow']}"/>
                <rect x="-6" y="-6" width="2.5" height="2.5" fill="{PALETTE['coral']}"/>
                <rect x="3.5" y="-6" width="2.5" height="2.5" fill="{PALETTE['coral']}"/>
                <rect x="-6" y="3.5" width="2.5" height="2.5" fill="{PALETTE['coral']}"/>
                <rect x="3.5" y="3.5" width="2.5" height="2.5" fill="{PALETTE['coral']}"/>
                <rect x="-1" y="-8" width="2" height="2" fill="{PALETTE['yellow']}"/>
                <rect x="-1" y="6" width="2" height="2" fill="{PALETTE['yellow']}"/>
            </g>
            """
        )

    hero_tank_svg = f"""
    <g class="hero-tank"
       style="transform-box: fill-box; transform-origin: center;
              will-change: transform; animation: heroTank {duration}s linear infinite;">
        {_tank_sprite(PALETTE['yellow'], PALETTE['peach'])}
    </g>
    """

    css_rules.append(
        f"""
        @media (prefers-reduced-motion: reduce) {{
            .hero-tank, .enemy-tank, .shell, .pixel-explosion, .grid-painted {{
                animation: none !important;
            }}
            .hero-tank {{
                transform: translate({hero_start_cx}px, {hero_start_cy}px) rotate(0deg);
            }}
            .enemy-tank, .shell, .pixel-explosion, .grid-painted {{
                opacity: 0 !important;
            }}
        }}
        """
    )

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg"
         viewBox="0 0 840 124" width="840" height="124"
         role="img" aria-label="Arte gráfico animado">
        <defs>
            <clipPath id="battleClip">
                <rect x="16" y="2" width="808" height="120" rx="6"/>
            </clipPath>
        </defs>

        <style>
            {chr(10).join(css_rules)}
        </style>

        <g clip-path="url(#battleClip)">
            {base_dock_svg}
            {chr(10).join(board_svg)}
            {chr(10).join(combat_svg)}
            {hero_tank_svg}
        </g>
    </svg>
    """
