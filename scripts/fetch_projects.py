import json
import os
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_ACTOR", "SaladDann")
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUTPUT_PATH = os.path.join("data", "projects.json")

# Repos excluidos del portafolio (perfil, catálogo viejo u otros auxiliares)
EXCLUDED_REPOS = {
    USERNAME.lower(),
    "my-projects",
}

# Opcional: nombres en minúsculas para forzar siempre como destacados
FORCE_FEATURED: list[str] = []

# Cuántos proyectos destacar automáticamente
AUTO_FEATURED_LIMIT = 4

# Cambia a True si prefieres ocultar repos archivados
EXCLUDE_ARCHIVED = False


def fetch_repos(username: str, token: str | None) -> list[dict]:
    all_repos: list[dict] = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{username}/repos"
            f"?sort=updated&direction=desc&per_page=100&page={page}"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{username}-Portfolio-Catalog",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            batch = json.loads(resp.read().decode("utf-8"))

        if not batch:
            break

        all_repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return all_repos


def recency_points(updated_raw: str) -> int:
    if not updated_raw:
        return 0
    try:
        dt = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
        days_ago = max(0, (datetime.now(timezone.utc) - dt).days)
        if days_ago <= 30:
            return 25
        if days_ago <= 90:
            return 18
        if days_ago <= 180:
            return 12
        if days_ago <= 365:
            return 6
        return 2
    except ValueError:
        return 0


def compute_score(project: dict) -> int:
    score = 0
    if not project["is_fork"]:
        score += 40
    if not project["archived"]:
        score += 15
    if project["has_description"]:
        score += 20
    if project["homepage"]:
        score += 20

    score += recency_points(project["_updated_raw"])
    score += min(project["stars"] * 5, 15)
    score += min(project["forks"] * 3, 10)
    return score


def build_portfolio_snapshot(repos: list[dict], generated_at: str | None = None) -> dict:
    forced_set = {name.lower() for name in FORCE_FEATURED}
    items: list[dict] = []
    languages_set: set[str] = set()

    for r in repos:
        name = r.get("name", "")
        key = name.lower()
        archived = bool(r.get("archived", False))
        is_fork = bool(r.get("fork", False))

        if key in EXCLUDED_REPOS:
            continue
        if EXCLUDE_ARCHIVED and archived:
            continue

        created_raw = r.get("created_at", "")
        updated_raw = r.get("updated_at", "")
        year = created_raw.split("-")[0] if "-" in created_raw else "Sin fecha"
        language = r.get("language") or "General"
        if language not in {"General", "Code"}:
            languages_set.add(language)

        raw_desc = (r.get("description") or "").strip()
        has_description = bool(raw_desc)
        description = (
            raw_desc
            if has_description
            else "Proyecto en desarrollo o repositorio sin descripción pública."
        )

        homepage = (r.get("homepage") or "").strip()
        if homepage and not homepage.startswith(("http://", "https://")):
            homepage = f"https://{homepage}"

        item = {
            "name": name,
            "html_url": r.get("html_url", ""),
            "homepage": homepage,
            "description": description,
            "language": language,
            "year": year,
            "created_at": created_raw.split("T")[0],
            "updated_at": updated_raw.split("T")[0],
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "is_fork": is_fork,
            "archived": archived,
            "has_description": has_description,
            "_updated_raw": updated_raw,
        }
        item["score"] = compute_score(item)
        items.append(item)

    # Candidatos ordenados por puntaje y luego por actualización más reciente
    ranked = sorted(
        items,
        key=lambda p: (
            1 if p["name"].lower() in forced_set else 0,
            p["score"],
            p["_updated_raw"],
        ),
        reverse=True,
    )

    featured_names: set[str] = set()
    for p in ranked:
        key = p["name"].lower()
        if key in forced_set or len(featured_names) < AUTO_FEATURED_LIMIT:
            if not p["is_fork"] or key in forced_set:
                featured_names.add(key)

    # Si no hubo suficientes originales, rellena hasta el límite con los mejores restantes
    if len(featured_names) < AUTO_FEATURED_LIMIT:
        for p in ranked:
            key = p["name"].lower()
            if key not in featured_names:
                featured_names.add(key)
            if len(featured_names) >= AUTO_FEATURED_LIMIT:
                break

    for p in items:
        p["featured"] = p["name"].lower() in featured_names

    # Destacados primero (por score), luego el resto por fecha de creación descendente
    featured_list = sorted(
        [p for p in items if p["featured"]],
        key=lambda p: (p["score"], p["_updated_raw"]),
        reverse=True,
    )
    regular_list = sorted(
        [p for p in items if not p["featured"]],
        key=lambda p: p["created_at"],
        reverse=True,
    )

    ordered = featured_list + regular_list
    for p in ordered:
        p.pop("has_description", None)
        p.pop("_updated_raw", None)

    return {
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "username": USERNAME,
        "summary": {
            "total_projects": len(ordered),
            "original_projects": sum(1 for p in ordered if not p["is_fork"]),
            "featured_projects": len(featured_list),
            "languages": sorted(languages_set),
        },
        "projects": ordered,
    }


def _without_timestamp(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k != "generated_at"}


def load_existing_snapshot(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def main() -> None:
    raw_repos = fetch_repos(USERNAME, GH_TOKEN)
    now_iso = datetime.now(timezone.utc).isoformat()
    snapshot = build_portfolio_snapshot(raw_repos, generated_at=now_iso)

    existing = load_existing_snapshot(OUTPUT_PATH)
    if existing is not None and _without_timestamp(existing) == _without_timestamp(snapshot):
        print(f"[SKIP] Sin cambios reales en proyectos; se conserva {OUTPUT_PATH}")
        return

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(
        f"[OK] {snapshot['summary']['total_projects']} proyectos "
        f"({snapshot['summary']['featured_projects']} destacados) en {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
