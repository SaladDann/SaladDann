from collections import deque

from ..theme import PALETTE

LEVEL_ORDER = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

DOT_BASE_COLOR = PALETTE["mint"]
SNAKE_COLOR = PALETTE["lavender"]
NUM_SEGMENTS = 9


def _current_body_set(route: list[tuple[int, int]], exclude_tail: bool = True) -> set[tuple[int, int]]:
    """Devuelve las celdas ocupadas por el cuerpo actual de la serpiente."""
    if not route:
        return set()
    # Si la serpiente avanza 1 casilla, la última celda de su cola se libera al moverse
    body_slice = route[-NUM_SEGMENTS:-1] if (exclude_tail and len(route) > 1) else route[-NUM_SEGMENTS:]
    return set(body_slice)


def _current_heading(route: list[tuple[int, int]]) -> tuple[int, int]:
    """Obtiene la dirección (dw, dd) del último movimiento."""
    if len(route) < 2:
        return (1, 0)
    prev_w, prev_d = route[-2]
    curr_w, curr_d = route[-1]
    dw = max(-1, min(1, curr_w - prev_w))
    dd = max(-1, min(1, curr_d - prev_d))
    return (dw, dd) if (dw != 0 or dd != 0) else (1, 0)


def _turn_candidates(heading: tuple[int, int]) -> list[tuple[int, int]]:
    """Ordena giros priorizando seguir recto, girar a la derecha, girar a la izquierda y atrás."""
    dw, dd = heading
    straight = (dw, dd)
    right = (-dd, dw)
    left = (dd, -dw)
    back = (-dw, -dd)
    return [straight, right, left, back]


def _select_dispersed_targets(
    level_grid: dict[tuple[int, int], int], max_targets: int = 38
) -> dict[tuple[int, int], int]:
    """Selecciona puntos reales maximizando la dispersión espacial (evita filas rectas)."""
    by_level: dict[int, list[tuple[int, int]]] = {1: [], 2: [], 3: [], 4: []}
    for pos, lvl in level_grid.items():
        if lvl in by_level:
            by_level[lvl].append(pos)

    quotas = {4: 10, 3: 10, 2: 10, 1: 8}
    selected: dict[tuple[int, int], int] = {}

    for lvl in (4, 3, 2, 1):
        candidates = by_level[lvl]
        quota = min(len(candidates), quotas[lvl])
        if quota == 0 or len(selected) >= max_targets:
            continue

        seed_idx = (lvl * 13) % len(candidates)
        first = candidates[seed_idx]
        if first not in selected:
            selected[first] = lvl

        while sum(1 for v in selected.values() if v == lvl) < quota and len(selected) < max_targets:
            best_pos = None
            best_score = -10**9
            for cand in candidates:
                if cand in selected:
                    continue
                min_dist = min(abs(cand[0] - s[0]) + abs(cand[1] - s[1]) for s in selected)
                same_row_penalty = sum(2 for s in selected if s[1] == cand[1] and abs(s[0] - cand[0]) < 8)
                same_col_penalty = sum(2 for s in selected if s[0] == cand[0])
                score = min_dist - same_row_penalty - same_col_penalty
                if score > best_score:
                    best_score = score
                    best_pos = cand

            if best_pos is None:
                break
            selected[best_pos] = lvl

    return selected


def _bfs_avoiding_body(
    start: tuple[int, int],
    goal: tuple[int, int],
    body_blocked: set[tuple[int, int]],
    higher_blocked: set[tuple[int, int]],
    heading: tuple[int, int],
    cols: int,
    rows: int,
) -> list[tuple[int, int]]:
    """Busca ruta casilla a casilla evitando el cuerpo y bloques de nivel superior."""
    if start == goal:
        return []

    dir_order = tuple(_turn_candidates(heading))
    queue = deque([(start, [])])
    visited = {start}
    combined_blocked = body_blocked | higher_blocked

    while queue:
        curr, path = queue.popleft()
        for dw, dd in dir_order:
            nw, nd = curr[0] + dw, curr[1] + dd
            nxt = (nw, nd)
            if not (0 <= nw < cols and 0 <= nd < rows) or nxt in visited:
                continue
            if nxt != goal and nxt in combined_blocked:
                continue

            new_path = path + [nxt]
            if nxt == goal:
                return new_path
            visited.add(nxt)
            queue.append((nxt, new_path))

    return []


def _step_toward_goal_with_free_turn(
    route: list[tuple[int, int]],
    goal: tuple[int, int],
    higher_blocked: set[tuple[int, int]],
    cols: int,
    rows: int,
    max_steps: int = 240,
) -> None:
    """Avanza casilla a casilla evaluando giros libres sin cruzar sobre el propio cuerpo."""
    steps_taken = 0
    while route[-1] != goal and steps_taken < max_steps:
        curr = route[-1]
        heading = _current_heading(route)
        body = _current_body_set(route, exclude_tail=True) - {goal}

        path = _bfs_avoiding_body(curr, goal, body, higher_blocked, heading, cols, rows)
        if path:
            route.append(path[0])
            steps_taken += 1
            continue

        # Si no hay camino directo libre del cuerpo, elegir un giro libre adyacente
        free_neighbors: list[tuple[int, int, int]] = []
        for idx_dir, (dw, dd) in enumerate(_turn_candidates(heading)):
            nw, nd = curr[0] + dw, curr[1] + dd
            nxt = (nw, nd)
            if not (0 <= nw < cols and 0 <= nd < rows):
                continue
            if nxt != goal and nxt in higher_blocked:
                continue
            if nxt not in body:
                dist = abs(nw - goal[0]) + abs(nd - goal[1])
                free_neighbors.append((dist, idx_dir, nw, nd))

        if free_neighbors:
            free_neighbors.sort(key=lambda item: (item[0], item[1]))
            _, _, bw, bd = free_neighbors[0]
            route.append((bw, bd))
            steps_taken += 1
            continue

        # Último recurso: si todas las casillas libres están ocupadas, relajar solo el cuerpo
        relaxed_path = _bfs_avoiding_body(curr, goal, set(), higher_blocked, heading, cols, rows)
        if relaxed_path:
            route.append(relaxed_path[0])
            steps_taken += 1
            continue

        break


def _walk_clean_exit(route: list[tuple[int, int]], cols: int, rows: int) -> None:
    """Lleva la serpiente hasta el borde derecho evitando su cuerpo y sale casilla a casilla."""
    body = _current_body_set(route, exclude_tail=True)
    curr = route[-1]

    # Preferir la casilla del borde derecho más cercana y libre del cuerpo
    edge_candidates = [(cols - 1, r) for r in range(rows) if (cols - 1, r) not in body]
    if not edge_candidates:
        edge_candidates = [(cols - 1, r) for r in range(rows)]

    edge_goal = min(
        edge_candidates,
        key=lambda p: (abs(p[0] - curr[0]) + abs(p[1] - curr[1]), abs(p[1] - curr[1])),
    )

    _step_toward_goal_with_free_turn(route, edge_goal, set(), cols, rows)

    # Salir casilla a casilla por la derecha manteniendo la fila de llegada
    exit_row = route[-1][1]
    start_exit_col = max(route[-1][0] + 1, cols)
    for w in range(start_exit_col, cols + NUM_SEGMENTS + 2):
        route.append((w, exit_row))


def _solve_snk_route(
    active_targets: dict[tuple[int, int], int], cols: int, rows: int
) -> tuple[list[tuple[int, int]], dict[tuple[int, int], int]]:
    """Resuelve el recorrido casilla a casilla evitando autocruce y saliendo por completo."""
    remaining = dict(active_targets)
    curr = (0, 3)
    route = [curr]
    eaten_at_step: dict[tuple[int, int], int] = {}

    if curr in remaining:
        eaten_at_step[curr] = 0
        del remaining[curr]

    for target_lvl in (1, 2, 3, 4):
        while True:
            targets = [pos for pos, lvl in remaining.items() if lvl == target_lvl]
            if not targets:
                break

            higher_blocked = {pos for pos, lvl in remaining.items() if lvl > target_lvl}
            body = _current_body_set(route, exclude_tail=True)
            heading = _current_heading(route)

            # Elegir el objetivo alcanzable sin cruzar el cuerpo y más cercano
            def _target_rank(p: tuple[int, int]) -> tuple[int, int, int, int]:
                has_free_path = 0 if _bfs_avoiding_body(route[-1], p, body, higher_blocked, heading, cols, rows) else 1
                on_body = 1 if p in body else 0
                dist = abs(p[0] - route[-1][0]) + abs(p[1] - route[-1][1])
                return (has_free_path, on_body, dist, p[0])

            nxt_target = min(targets, key=_target_rank)
            _step_toward_goal_with_free_turn(route, nxt_target, higher_blocked, cols, rows)

            # Registrar cualquier objetivo alcanzado en el trayecto hasta nxt_target
            for idx_step in range(len(route) - 1, -1, -1):
                pos = route[idx_step]
                if pos in remaining and remaining[pos] <= target_lvl:
                    if pos not in eaten_at_step:
                        eaten_at_step[pos] = idx_step
                    del remaining[pos]

            if nxt_target in remaining:
                eaten_at_step[nxt_target] = len(route) - 1
                del remaining[nxt_target]

            curr = route[-1]

    _walk_clean_exit(route, cols, rows)
    return route, eaten_at_step


def render(data: dict) -> str:
    weeks = data.get("calendar_weeks", [])[-52:]
    if not weeks:
        weeks = [
            {
                "contributionDays": [
                    {
                        "contributionLevel": [
                            "NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"
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

    active_targets = _select_dispersed_targets(raw_grid, max_targets=38)
    route, eaten_at_step = _solve_snk_route(active_targets, cols, rows)

    total_steps = max(1, len(route) - 1)
    dur = round(min(48.0, max(28.0, total_steps * 0.11)), 1)

    scales = [1.00, 0.92, 0.84, 0.76, 0.68, 0.60, 0.52, 0.44, 0.36]
    css_rules = []
    snake_rects = []

    for seg_idx in range(NUM_SEGMENTS):
        scale = scales[seg_idx]
        size = round(cs * scale, 2)
        offset = round((cs - size) / 2.0, 2)
        rx = round(2.6 * scale, 2)

        kf_lines = []
        for idx in range(len(route)):
            pct = round((idx / total_steps) * 100.0, 2)
            pos_idx = max(0, idx - seg_idx)
            pw, pd = route[pos_idx]
            px = round(start_x + pw * step + offset, 1)
            py = round(start_y + pd * step + offset, 1)

            if pct >= 98.5:
                op = "0"
            elif pct >= 94.5:
                op = str(round(max(0.0, (98.5 - pct) / 4.0), 2))
            elif pct <= 1.5 and seg_idx > 0:
                op = "0"
            else:
                op = "1"

            kf_lines.append(
                f"  {pct:.2f}% {{ transform: translate({px}px, {py}px); opacity: {op}; }}"
            )

        css_rules.append(f"@keyframes snkSeg{seg_idx} {{\n" + "\n".join(kf_lines) + "\n}")
        snake_rects.append(
            f'  <rect width="{size}" height="{size}" rx="{rx}" fill="{SNAKE_COLOR}" '
            f'style="animation: snkSeg{seg_idx} {dur}s linear infinite;" />'
        )

    inv_level = {v: k for k, v in LEVEL_ORDER.items()}
    cell_css = []
    cell_rects = []

    for w_idx in range(cols):
        for d_idx in range(rows):
            pos = (w_idx, d_idx)
            x = round(start_x + w_idx * step, 1)
            y = round(start_y + d_idx * step, 1)

            if pos not in active_targets:
                fill, op = (PALETTE["neutral"], "0.07")
                cell_rects.append(
                    f'  <rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="2.6" fill="{fill}" fill-opacity="{op}" />'
                )
            else:
                lvl_name = inv_level[active_targets[pos]]
                base_op = {"FIRST_QUARTILE": "0.24", "SECOND_QUARTILE": "0.48", "THIRD_QUARTILE": "0.76", "FOURTH_QUARTILE": "1.00"}[lvl_name]
                eat_pct = min(93.5, max(0.2, round((eaten_at_step[pos] / total_steps) * 100.0, 2)))
                after_pct = min(94.0, round(eat_pct + 0.25, 2))
                anim_name = f"c_{w_idx}_{d_idx}"

                cell_css.append(
                    f"@keyframes {anim_name} {{\n"
                    f"  0%, {eat_pct:.2f}% {{ fill: {DOT_BASE_COLOR}; fill-opacity: {base_op}; }}\n"
                    f"  {after_pct:.2f}%, 97.5% {{ fill: {PALETTE['neutral']}; fill-opacity: 0.07; }}\n"
                    f"  99.2%, 100% {{ fill: {DOT_BASE_COLOR}; fill-opacity: {base_op}; }}\n"
                    f"}}"
                )
                cell_rects.append(
                    f'  <rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="2.6" fill="{DOT_BASE_COLOR}" fill-opacity="{base_op}" '
                    f'style="animation: {anim_name} {dur}s linear infinite;" />'
                )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 124" width="840" height="124">
  <style>
{chr(10).join(css_rules)}
{chr(10).join(cell_css)}
  </style>
{chr(10).join(cell_rects)}
{chr(10).join(snake_rects)}
</svg>
"""
