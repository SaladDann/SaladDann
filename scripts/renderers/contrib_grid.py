import os
import subprocess
from datetime import datetime, timezone

from .cartridges import CARTRIDGES

ROTATE_EVERY_DAYS = 1
# 0 desactiva la fijación temporal para garantizar rotación diaria constante;
# súbelo a 1 o 2 solo si deseas fijar un cartucho recién creado.
NEW_CARTRIDGE_PRIORITY_DAYS = 0

SECONDS_PER_DAY = 86400

CARTRIDGES_DIR = os.path.join(
    os.path.dirname(__file__),
    "cartridges",
)


def get_file_created_timestamp(filepath: str) -> float:
    """Obtiene el timestamp del primer commit del archivo."""
    try:
        result = subprocess.check_output(
            [
                "git",
                "log",
                "--follow",
                "--format=%ct",
                "--reverse",
                "--",
                filepath,
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()

        if result:
            return float(result.splitlines()[0])

    except (subprocess.SubprocessError, ValueError):
        pass

    return 0.0


def _resolve_reference_timestamp() -> float:
    """
    Permite simular otra fecha en pruebas locales con CONTRIB_DATE (ISO 8601, ej: 2026-11-20)
    o usar la hora actual en UTC en producción / GitHub Actions.
    """
    override_date = os.environ.get("CONTRIB_DATE", "").strip()
    if override_date:
        dt = datetime.fromisoformat(override_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()

    return datetime.now(timezone.utc).timestamp()


def pick_cartridge() -> str:
    available = sorted(CARTRIDGES.keys())

    if not available:
        raise RuntimeError("No hay cartuchos disponibles.")

    # 1. Selección manual: tiene prioridad absoluta.
    forced = os.environ.get("CONTRIB_CARTRIDGE", "").strip()
    if forced:
        if forced not in CARTRIDGES:
            raise ValueError(
                f"Cartucho '{forced}' inexistente. "
                f"Disponibles: {', '.join(available)}"
            )
        print(f"[MANUAL] Cartucho seleccionado: {forced}")
        return forced

    now_ts = _resolve_reference_timestamp()
    rotate_days = max(1, int(ROTATE_EVERY_DAYS))

    # 2. Prioridad temporal opcional para cartuchos nuevos (solo si > 0).
    if NEW_CARTRIDGE_PRIORITY_DAYS > 0:
        newest_name = None
        newest_ts = 0.0

        for name in available:
            path = os.path.join(CARTRIDGES_DIR, f"{name}.py")
            if not os.path.isfile(path):
                continue

            timestamp = get_file_created_timestamp(path)
            if timestamp > newest_ts:
                newest_ts = timestamp
                newest_name = name

        if (
            newest_name
            and newest_ts > 0
            and 0 <= now_ts - newest_ts <= NEW_CARTRIDGE_PRIORITY_DAYS * SECONDS_PER_DAY
        ):
            print(f"[AUTO] Prioridad para cartucho nuevo: {newest_name}")
            return newest_name

    # 3. Rotación cíclica diaria (cada ROTATE_EVERY_DAYS días).
    day_index = int(now_ts // SECONDS_PER_DAY)
    period_index = day_index // rotate_days

    offset_raw = os.environ.get("CONTRIB_ROTATION_OFFSET", "0").strip()
    try:
        offset = int(offset_raw)
    except ValueError:
        offset = 0

    selected_index = (period_index + offset) % len(available)
    selected = available[selected_index]

    print(
        f"[AUTO] Día UTC: {day_index} | Período: {period_index} "
        f"| Índice: {selected_index}/{len(available)} | Cartucho: {selected}"
    )

    return selected


def render_contrib_grid(data: dict, cartridge: str | None = None) -> str:
    selected = cartridge if cartridge is not None else pick_cartridge()
    if selected not in CARTRIDGES:
        raise ValueError(
            f"Cartucho '{selected}' no existe. Opciones: {', '.join(CARTRIDGES)}"
        )

    print(f"[CONSOLE] Cartucho activo: {selected}")
    return CARTRIDGES[selected](data)
