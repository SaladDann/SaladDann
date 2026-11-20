from .theme import PALETTE, esc


def render_stats(data: dict) -> str:
    st = data["stats"]
    year = data.get("generated_at", "2026")[:4]
    commits = esc(st["commits_year"])
    repos = esc(st["repos"])
    prs = esc(st["prs"])
    issues = esc(st["issues"])

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 140" width="280" height="140">
  <text x="14" y="22" font-family="sans-serif" font-size="11" font-weight="600" fill="{PALETTE['neutral']}" letter-spacing="1.2">ESTADÍSTICAS</text>
  <line x1="14" y1="30" x2="266" y2="30" stroke="{PALETTE['neutral']}" stroke-opacity="0.2" stroke-width="1" />

  <text x="14" y="56" font-family="monospace" font-size="12" fill="{PALETTE['neutral']}">Commits ({esc(year)})</text>
  <text x="266" y="56" text-anchor="end" font-family="monospace" font-size="13" font-weight="700" fill="{PALETTE['blue']}">{commits}</text>

  <text x="14" y="80" font-family="monospace" font-size="12" fill="{PALETTE['neutral']}">Repositorios</text>
  <text x="266" y="80" text-anchor="end" font-family="monospace" font-size="13" font-weight="700" fill="{PALETTE['mint']}">{repos}</text>

  <text x="14" y="104" font-family="monospace" font-size="12" fill="{PALETTE['neutral']}">Pull Requests</text>
  <text x="266" y="104" text-anchor="end" font-family="monospace" font-size="13" font-weight="700" fill="{PALETTE['lavender']}">{prs}</text>

  <text x="14" y="128" font-family="monospace" font-size="12" fill="{PALETTE['neutral']}">Issues Resueltos</text>
  <text x="266" y="128" text-anchor="end" font-family="monospace" font-size="13" font-weight="700" fill="{PALETTE['peach']}">{issues}</text>
</svg>
"""
