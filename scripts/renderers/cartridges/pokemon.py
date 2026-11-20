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
MAX_ENCOUNTERS = 3
MAX_GRASS_PATCHES = 18
CAPTURE_HOLD_STEPS = 7

GRASS_FILL = {
    2: PALETTE["mint"],
    3: PALETTE["cyan"],
    4: PALETTE["blue"],
}

WILD_SPRITES = [
    (
        PALETTE["yellow"],
        [
            (0, 0), (4, 0), (0, 1), (4, 1),
            (1, 2), (2, 2), (3, 2),
            (1, 3), (2, 3), (3, 3),
            (1, 4), (3, 4),
        ],
    ),
    (
        PALETTE["mint"],
        [
            (1, 0), (2, 0), (3, 0),
            (0, 1), (1, 1), (2, 1), (3, 1), (4, 1),
            (1, 2), (2, 2), (3, 2),
            (0, 3), (2, 3), (4, 3),
            (1, 4), (3, 4),
        ],
    ),
    (
        PALETTE["lavender"],
        [
            (1, 0), (2, 0),
            (1, 1), (2, 1), (3, 1),
            (0, 2), (1, 2), (2, 2), (3, 2),
            (1, 3), (2, 3), (4, 3),
            (1, 4), (3, 4),
        ],
    ),
]


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _percentage(step: int, total_steps: int) -> float:
    return max(0.0, min(100.0, step * 100.0 / max(1, total_steps)))


def _keyframes(name: str, frames: list[tuple[float, str]]) -> str:
    normalized: dict[float, list[str]] = {}
    for percentage, declaration in frames:
        pct = round(max(0.0, min(100.0, percentage)), 2)
        normalized.setdefault(pct, []).append(declaration)

    lines = [
        f"    {pct:.2f}% {{ {'; '.join(normalized[pct])}; }}"
        for pct in sorted(normalized)
    ]
    return f"@keyframes {name} {{\n" + "\n".join(lines) + "\n}"


def _translate(x: float, y: float) -> str:
    return f"translate({x:.1f}px, {y:.1f}px)"


def _select_world(
    level_grid: dict[tuple[int, int], int],
    count_grid: dict[tuple[int, int], int],
    cols: int = BOARD_COLS,
    rows: int = BOARD_ROWS,
) -> tuple[dict[tuple[int, int], int], list[tuple[int, int]]]:
    """Elige parches de hierba en celdas de contribución (>=2) y hasta 3 encuentros en picos (>=3)."""
    grass_cells: dict[tuple[int, int], int] = {}

    candidates_grass = sorted(
        (
            pos for pos, lvl in level_grid.items()
            if lvl >= 2 and pos != START_POSITION
        ),
        key=lambda pos: (-level_grid.get(pos, 0), -count_grid.get(pos, 0), pos[0], pos[1]),
    )

    for pos in candidates_grass:
        if len(grass_cells) >= MAX_GRASS_PATCHES:
            break
        if all(_manhattan(pos, g) >= 4 for g in grass_cells):
            grass_cells[pos] = level_grid[pos]

    peak_candidates = sorted(
        (
            pos for pos, lvl in level_grid.items()
            if lvl >= 3 and 4 <= pos[0] <= cols - 2
        ),
        key=lambda pos: (-level_grid.get(pos, 0), -count_grid.get(pos, 0), pos[0], pos[1]),
    )

    encounters: list[tuple[int, int]] = []
    for pos in peak_candidates:
        if len(encounters) >= MAX_ENCOUNTERS:
            break
        if all(abs(pos[0] - existing[0]) >= 12 for existing in encounters):
            encounters.append(pos)
            grass_cells[pos] = level_grid[pos]

    encounters.sort(key=lambda pos: (pos[0], pos[1]))
    return grass_cells, encounters


def _bfs_steps(
    start: tuple[int, int],
    goal: tuple[int, int],
    cols: int,
    rows: int,
) -> list[tuple[int, int]]:
    if not (
        0 <= start[0] < cols
        and 0 <= start[1] < rows
        and 0 <= goal[0] < cols
        and 0 <= goal[1] < rows
    ):
        return []
    if start == goal:
        return []

    queue = deque([start])
    predecessors: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    directions = ((1, 0), (0, 1), (0, -1), (-1, 0))

    while queue:
        current = queue.popleft()
        for dw, dd in directions:
            nxt = (current[0] + dw, current[1] + dd)
            if not (0 <= nxt[0] < cols and 0 <= nxt[1] < rows):
                continue
            if nxt in predecessors:
                continue

            predecessors[nxt] = current
            if nxt == goal:
                path: list[tuple[int, int]] = []
                node: tuple[int, int] | None = goal
                while node is not None and node != start:
                    path.append(node)
                    node = predecessors[node]
                path.reverse()
                return path

            queue.append(nxt)

    return []


def _build_timeline(
    encounters: list[tuple[int, int]],
    cols: int,
    rows: int,
) -> tuple[list[tuple[int, int]], list[dict]]:
    curr = START_POSITION
    timeline = [curr]
    capture_events: list[dict] = []

    for target in encounters:
        stop_pos = (max(0, target[0] - 2), target[1])
        path = _bfs_steps(curr, stop_pos, cols, rows)
        for position in path:
            timeline.append(position)

        curr = stop_pos
        start_capture = len(timeline) - 1
        for _ in range(CAPTURE_HOLD_STEPS):
            timeline.append(curr)
        end_capture = len(timeline) - 1

        capture_events.append(
            {
                "target": target,
                "trainer": curr,
                "start_step": start_capture,
                "end_step": end_capture,
            }
        )

    for col in range(curr[0] + 1, cols + 2):
        timeline.append((col, curr[1]))

    return timeline, capture_events


def _draw_grass_patch(x: float, y: float, lvl: int) -> str:
    tint = GRASS_FILL.get(lvl, PALETTE["mint"])
    return f"""
    <g fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.88">
        <path d="M {x + 2.8:.1f} {y + 10.0:.1f} L {x + 2.0:.1f} {y + 6.0:.1f}
                 M {x + 5.8:.1f} {y + 10.0:.1f} L {x + 5.8:.1f} {y + 3.6:.1f}
                 M {x + 8.8:.1f} {y + 10.0:.1f} L {x + 9.7:.1f} {y + 6.4:.1f}"
              stroke="{tint}" stroke-width="1.25" />
        <path d="M {x + 5.8:.1f} {y + 3.6:.1f} l 1.1 -1.1"
              stroke="{PALETTE['yellow']}" stroke-width="0.9" opacity="0.7" />
    </g>
    """


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
        missing = BOARD_COLS - len(weeks)
        weeks = [empty_week.copy() for _ in range(missing)] + weeks

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

    grass_cells, encounters = _select_world(level_grid, count_grid, cols, rows)
    timeline, capture_events = _build_timeline(encounters, cols, rows)

    total_steps = max(1, len(timeline) - 1)
    duration = round(min(38.0, max(22.0, total_steps * 0.16)), 1)

    board_svg: list[str] = []
    for (col, row), lvl in sorted(grass_cells.items()):
        x = round(start_x + col * step, 1)
        y = round(start_y + row * step, 1)
        board_svg.append(_draw_grass_patch(x, y, lvl))

    css_rules: list[str] = []
    items_svg: list[str] = []

    for idx, capture in enumerate(capture_events):
        target_col, target_row = capture["target"]
        trainer_col, trainer_row = capture["trainer"]

        target_x = round(start_x + target_col * step + cs / 2, 1)
        target_y = round(start_y + target_row * step + cs / 2, 1)
        trainer_x = round(start_x + trainer_col * step + cs / 2, 1)
        trainer_y = round(start_y + trainer_row * step + cs / 2, 1)

        start_pct = _percentage(capture["start_step"], total_steps)
        end_pct = _percentage(capture["end_step"], total_steps)
        interval = max(0.0, end_pct - start_pct)

        alert_end = start_pct + interval * 0.22
        throw_mid = start_pct + interval * 0.45
        ball_hit = start_pct + interval * 0.65
        caught = start_pct + interval * 0.88

        pokemon_color, pixels = WILD_SPRITES[idx % len(WILD_SPRITES)]
        pixel_size = 2.1
        pixel_rects = "".join(
            f'<rect x="{gx * pixel_size - 5.2:.1f}" y="{gy * pixel_size - 5.2:.1f}" '
            f'width="{pixel_size:.1f}" height="{pixel_size:.1f}" />'
            for gx, gy in pixels
        )

        pokemon_anim = f"wildPokemon_{idx}"
        css_rules.append(
            _keyframes(
                pokemon_anim,
                [
                    (0, f"opacity: 1; transform: {_translate(target_x, target_y)} scale(1)"),
                    (ball_hit, f"opacity: 1; transform: {_translate(target_x, target_y)} scale(1)"),
                    (min(100.0, ball_hit + 0.4), f"opacity: 0; transform: {_translate(target_x, target_y)} scale(0.2)"),
                    (99.0, f"opacity: 0; transform: {_translate(target_x, target_y)} scale(0.2)"),
                    (100.0, f"opacity: 1; transform: {_translate(target_x, target_y)} scale(1)"),
                ],
            )
        )
        items_svg.append(
            f"""
            <g fill="{pokemon_color}" style="transform-box: fill-box; transform-origin: center; animation: {pokemon_anim} {duration}s linear infinite;">
                {pixel_rects}
            </g>
            """
        )

        alert_anim = f"alert_{idx}"
        css_rules.append(
            _keyframes(
                alert_anim,
                [
                    (0, f"opacity: 0; transform: {_translate(trainer_x, trainer_y - 12)} scale(0.5)"),
                    (start_pct, f"opacity: 0; transform: {_translate(trainer_x, trainer_y - 12)} scale(0.5)"),
                    (min(100.0, start_pct + 0.3), f"opacity: 1; transform: {_translate(trainer_x, trainer_y - 15)} scale(1)"),
                    (alert_end, f"opacity: 1; transform: {_translate(trainer_x, trainer_y - 15)} scale(1)"),
                    (min(100.0, alert_end + 0.3), f"opacity: 0; transform: {_translate(trainer_x, trainer_y - 15)} scale(0.5)"),
                    (100.0, f"opacity: 0; transform: {_translate(trainer_x, trainer_y - 15)} scale(0.5)"),
                ],
            )
        )
        items_svg.append(
            f"""
            <g opacity="0" style="transform-box: fill-box; transform-origin: center; animation: {alert_anim} {duration}s linear infinite;">
                <rect x="-4.5" y="-6.5" width="9" height="9" rx="2" fill="{PALETTE['neutral']}" stroke="{PALETTE['yellow']}" stroke-width="0.9" />
                <text x="0" y="0.6" text-anchor="middle" font-family="monospace" font-size="8" font-weight="900" fill="{PALETTE['coral']}">!</text>
            </g>
            """
        )

        throw_anim = f"throwBall_{idx}"
        middle_x = round((trainer_x + target_x) / 2, 1)
        middle_y = round(min(trainer_y, target_y) - 16, 1)
        css_rules.append(
            _keyframes(
                throw_anim,
                [
                    (0, f"opacity: 0; transform: {_translate(trainer_x, trainer_y)} rotate(0deg)"),
                    (alert_end, f"opacity: 0; transform: {_translate(trainer_x, trainer_y)} rotate(0deg)"),
                    (min(100.0, alert_end + 0.2), f"opacity: 1; transform: {_translate(trainer_x, trainer_y - 2)} rotate(0deg)"),
                    (throw_mid, f"opacity: 1; transform: {_translate(middle_x, middle_y)} rotate(180deg)"),
                    (ball_hit, f"opacity: 1; transform: {_translate(target_x, target_y)} rotate(360deg)"),
                    (caught, f"opacity: 1; transform: {_translate(target_x, target_y)} rotate(360deg)"),
                    (min(100.0, caught + 0.6), f"opacity: 0; transform: {_translate(target_x, target_y)} scale(0.4)"),
                    (100.0, f"opacity: 0; transform: {_translate(target_x, target_y)} scale(0.4)"),
                ],
            )
        )
        items_svg.append(
            f"""
            <g opacity="0" style="transform-box: fill-box; transform-origin: center; animation: {throw_anim} {duration}s linear infinite;">
                <circle cx="0" cy="0" r="4.2" fill="{PALETTE['neutral']}" />
                <path d="M -4.2 0 A 4.2 4.2 0 0 1 4.2 0 Z" fill="{PALETTE['coral']}" />
                <line x1="-4.2" y1="0" x2="4.2" y2="0" stroke="{PALETTE['yellow']}" stroke-width="1.0" />
                <circle cx="0" cy="0" r="1.3" fill="{PALETTE['yellow']}" />
            </g>
            """
        )

        stars_anim = f"captureStars_{idx}"
        stars_start = max(0.0, caught - 0.4)
        stars_end = min(100.0, caught + 1.1)
        css_rules.append(
            _keyframes(
                stars_anim,
                [
                    (0, f"opacity: 0; transform: {_translate(target_x, target_y - 4)} scale(0.4)"),
                    (stars_start, f"opacity: 0; transform: {_translate(target_x, target_y - 4)} scale(0.4)"),
                    (caught, f"opacity: 1; transform: {_translate(target_x, target_y - 9)} scale(1.15)"),
                    (stars_end, f"opacity: 0; transform: {_translate(target_x, target_y - 13)} scale(1.3)"),
                    (100.0, f"opacity: 0; transform: {_translate(target_x, target_y - 13)} scale(1.3)"),
                ],
            )
        )
        items_svg.append(
            f"""
            <g opacity="0" fill="{PALETTE['yellow']}" style="transform-box: fill-box; transform-origin: center; animation: {stars_anim} {duration}s linear infinite;">
                <polygon points="-6,-2 -5,-4 -4,-2 -2,-1 -4,0 -5,2 -6,0 -8,-1" />
                <polygon points="0,-6 1,-8 2,-6 4,-5 2,-4 1,-2 0,-4 -2,-5" />
                <polygon points="6,-2 7,-4 8,-2 10,-1 8,0 7,2 6,0 4,-1" />
            </g>
            """
        )

    trainer_frames = []
    for idx, (col, row) in enumerate(timeline):
        percentage = _percentage(idx, total_steps)
        cx = round(start_x + col * step + cs / 2, 1)
        cy = round(start_y + row * step + cs / 2, 1)
        trainer_frames.append((percentage, f"transform: {_translate(cx, cy)}"))

    css_rules.append(_keyframes("trainerWalk", trainer_frames))

    trainer_sprite = f"""
    <g class="trainer" style="animation: trainerWalk {duration}s linear infinite;">
        <rect x="-3.4" y="4.2" width="2.6" height="1.8" rx="0.6" fill="{PALETTE['neutral']}" />
        <rect x="0.8" y="4.2" width="2.6" height="1.8" rx="0.6" fill="{PALETTE['neutral']}" />
        <rect x="-4" y="-1.2" width="8" height="5.5" rx="1.4" fill="{PALETTE['blue']}" />
        <rect x="-1" y="-1.2" width="2" height="5.5" fill="{PALETTE['mint']}" />
        <rect x="-3.8" y="-6.8" width="7.6" height="5.8" rx="2" fill="{PALETTE['peach']}" />
        <rect x="-1.8" y="-4.8" width="1.1" height="1.8" fill="{PALETTE['neutral']}" />
        <rect x="1.5" y="-4.8" width="1.1" height="1.8" fill="{PALETTE['neutral']}" />
        <rect x="-4.2" y="-9.2" width="8.4" height="2.8" rx="1.2" fill="{PALETTE['coral']}" />
        <rect x="-1.2" y="-8.5" width="2.4" height="1.4" rx="0.5" fill="{PALETTE['yellow']}" />
        <rect x="-0.5" y="-7.4" width="5.6" height="1.2" rx="0.6" fill="{PALETTE['coral']}" />
    </g>
    """

    css_rules.append(
        """
        @media (prefers-reduced-motion: reduce) {
            .trainer {
                animation: none !important;
            }
        }
        """
    )

    return f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 840 124"
        width="840"
        height="124"
        role="img"
        aria-label="Ruta de contribuciones con hierba alta y encuentros animados"
    >
        <defs>
            <clipPath id="pokeClip">
                <rect x="16" y="2" width="808" height="120" rx="6" />
            </clipPath>
        </defs>

        <style>
            {chr(10).join(css_rules)}
        </style>

        <g clip-path="url(#pokeClip)">
            {chr(10).join(board_svg)}
            {chr(10).join(items_svg)}
            {trainer_sprite}
        </g>
    </svg>
    """
