
import json
import os
import sys

from renderers.contrib_grid import render_contrib_grid
from renderers.isometric_matrix import render_isometric
from renderers.langs_card import render_langs
from renderers.stats_card import render_stats
from renderers.streak_card import render_streak

METRICS_PATH = os.path.join("data", "metrics.json")
ASSETS_DIR = "assets"


def write_svg(filename: str, content: str) -> None:
    path = os.path.join(ASSETS_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

    print(f"[OK] Generado {path}")


def resolve_cartridge_argument() -> str | None:
    """Resuelve la selección manual local o desde el entorno."""

    if len(sys.argv) > 2:
        raise ValueError(
            "Uso: python scripts/render_svgs.py [nombre_cartucho]"
        )

    cli_cartridge = (
        sys.argv[1].strip()
        if len(sys.argv) == 2
        else ""
    )

    env_cartridge = os.environ.get(
        "CONTRIB_CARTRIDGE", ""
    ).strip()

    if cli_cartridge:
        print(f"[CLI] Cartucho solicitado: {cli_cartridge}")
        return cli_cartridge

    if env_cartridge:
        print(f"[ENV] Cartucho solicitado: {env_cartridge}")
        return env_cartridge

    print("[AUTO] Se utilizará la selección automática.")
    return None


def main() -> None:

    if not os.path.exists(METRICS_PATH):
        raise FileNotFoundError(
            f"No se encontró {METRICS_PATH}. "
            "Ejecuta primero fetch_metrics.py"
        )

    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(ASSETS_DIR, exist_ok=True)

    cli_cartridge = resolve_cartridge_argument()

    write_svg(
        "02-metrics-streak.svg",
        render_streak(data)
    )

    write_svg(
        "02-metrics-stats.svg",
        render_stats(data)
    )

    write_svg(
        "03-side-isometric.svg",
        render_isometric(data)
    )

    write_svg(
        "03-side-langs.svg",
        render_langs(data)
    )

    write_svg(
        "04-footer-contrib.svg",
        render_contrib_grid(
            data,
            cartridge=cli_cartridge
        )
    )


if __name__ == "__main__":
    main()

