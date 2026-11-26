import importlib
import pkgutil
from typing import Callable

CARTRIDGES: dict[str, Callable[[dict], str]] = {}

for _, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if not is_pkg and not module_name.startswith("_"):
        module = importlib.import_module(f"{__name__}.{module_name}")
        if hasattr(module, "render"):
            CARTRIDGES[module_name] = module.render
