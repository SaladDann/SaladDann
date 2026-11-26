const DATA_URL = "https://raw.githubusercontent.com/SaladDann/SaladDann/main/data/projects.json";

const PALETTE = {
    blue: "#A2D2FF",
    mint: "#B7E4C7",
    lavender: "#CDB4DB",
    peach: "#FBC4AB",
    coral: "#FFADAD",
    yellow: "#FFF3B0",
    cyan: "#8ECAE6",
    pink: "#FFAFCC",
    neutral: "#808080"
};

const LANG_COLORS = [
    PALETTE.blue,
    PALETTE.lavender,
    PALETTE.mint,
    PALETTE.peach,
    PALETTE.yellow,
    PALETTE.cyan,
    PALETTE.pink,
    PALETTE.coral
];

const state = {
    data: null,
    projects: [],
    filterType: "all", // "all" | "original" | "fork"
    language: "all",
    query: ""
};

function escapeHtml(value = "") {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function sanitizeUrl(url = "") {
    const trimmed = String(url).trim();
    if (/^https?:\/\//i.test(trimmed)) {
        return trimmed;
    }
    return "#";
}

function getLangColor(lang = "") {
    if (!lang || lang === "General" || lang === "Code") {
        return PALETTE.neutral;
    }
    let hash = 0;
    for (let i = 0; i < lang.length; i += 1) {
        hash = (hash * 31 + lang.charCodeAt(i)) >>> 0;
    }
    return LANG_COLORS[hash % LANG_COLORS.length];
}

function renderLanguageSvg(lang, color) {
    const key = String(lang || "").toLowerCase();
    const c = escapeHtml(color);

    const customSvgs = {
        python: `
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <rect x="1.5" y="1.5" width="13" height="13" rx="2.5" stroke="${c}" stroke-width="1.2"/>
        <path d="M5 5.5h4.5v2H6.5v3H5V5.5z" fill="${c}"/>
        <circle cx="9.5" cy="10" r="1.3" fill="${c}"/>
      </svg>`,
        typescript: `
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <rect x="1.5" y="1.5" width="13" height="13" rx="2" stroke="${c}" stroke-width="1.2"/>
        <path d="M4.2 6.2h3.4M5.9 6.2v5.3M8.8 10.7c.4.5 1 .8 1.7.8.9 0 1.5-.5 1.5-1.2 0-.7-.5-1-1.5-1.3-.9-.3-1.4-.6-1.4-1.3 0-.7.6-1.2 1.4-1.2.6 0 1.1.2 1.4.6" stroke="${c}" stroke-width="1.25" stroke-linecap="round"/>
      </svg>`,
        javascript: `
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <rect x="1.5" y="1.5" width="13" height="13" rx="2" stroke="${c}" stroke-width="1.2"/>
        <path d="M6.4 6.2v3.7c0 1.1-.6 1.7-1.6 1.7-.5 0-.9-.2-1.2-.5M11.6 6.8c-.3-.4-.8-.6-1.4-.6-.8 0-1.3.4-1.3 1 0 .6.4.9 1.3 1.2 1 .3 1.5.7 1.5 1.5 0 .9-.7 1.5-1.7 1.5-.8 0-1.4-.3-1.8-.8" stroke="${c}" stroke-width="1.25" stroke-linecap="round"/>
      </svg>`,
        dart: `
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <polygon points="8,2 13.5,7.5 11.5,13.5 5.5,13.5 2.5,8" stroke="${c}" stroke-width="1.25" stroke-linejoin="round"/>
        <path d="M5.5 5.5l5 5" stroke="${c}" stroke-width="1.25" stroke-linecap="round"/>
      </svg>`,
        "c#": `
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <rect x="1.5" y="1.5" width="13" height="13" rx="2" stroke="${c}" stroke-width="1.2"/>
        <path d="M5.5 5v6M9.5 5v6M4 7.2h7M4 9.5h7" stroke="${c}" stroke-width="1.2" stroke-linecap="round"/>
      </svg>`,
        java: `
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M4.5 9.5h6.5v1.5a2.5 2.5 0 0 1-2.5 2.5h-1.5A2.5 2.5 0 0 1 4.5 11V9.5z" stroke="${c}" stroke-width="1.2"/>
        <path d="M11 10h1.2a1.3 1.3 0 0 1 0 2.6H10.8" stroke="${c}" stroke-width="1.2"/>
        <path d="M6.5 3.5c0 1 1 1.2 1 2.2M9 3.5c0 1 1 1.2 1 2.2" stroke="${c}" stroke-width="1.2" stroke-linecap="round"/>
      </svg>`,
        "c++": `
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <rect x="1.5" y="1.5" width="13" height="13" rx="2" stroke="${c}" stroke-width="1.2"/>
        <path d="M6.8 6.3A2.4 2.4 0 1 0 6.8 9.7M9.3 7v2.4M8.1 8.2h2.4M12.2 7v2.4M11 8.2h2.4" stroke="${c}" stroke-width="1.15" stroke-linecap="round"/>
      </svg>`,
        html: `
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M3 2.5h10l-1 9.5-4 1.5-4-1.5-1-9.5z" stroke="${c}" stroke-width="1.2" stroke-linejoin="round"/>
        <path d="M5.5 6h5l-.3 2.5H6.2l.2 1.8 1.6.5 1.6-.5.1-.9" stroke="${c}" stroke-width="1.15" stroke-linecap="round"/>
      </svg>`,
        css: `
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M3 2.5h10l-1 9.5-4 1.5-4-1.5-1-9.5z" stroke="${c}" stroke-width="1.2" stroke-linejoin="round"/>
        <path d="M5.5 6h5l-.2 1.8H6.5M6.4 8.2h3.8l-.2 2.1-2 .6-2-.6-.1-.7" stroke="${c}" stroke-width="1.15" stroke-linecap="round"/>
      </svg>`
    };

    if (customSvgs[key]) {
        return `<span class="lang-badge-svg">${customSvgs[key]}</span>`;
    }

    const monograms = {
        "jupyter notebook": "JP",
        shell: "SH",
        bash: "SH",
        powershell: "PS",
        kotlin: "KT",
        swift: "SW",
        go: "GO",
        rust: "RS",
        php: "PHP",
        sql: "SQL"
    };
    const label = monograms[key] || lang.slice(0, 2).toUpperCase();

    return `
    <span class="lang-badge-svg">
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <rect x="1.5" y="1.5" width="13" height="13" rx="2" stroke="${c}" stroke-width="1.2"/>
        <text x="8" y="10.4" text-anchor="middle" fill="${c}" font-size="6.2" font-family="monospace" font-weight="700">${escapeHtml(label)}</text>
      </svg>
    </span>
  `;
}

function renderLanguageBadge(lang) {
    const cleanLang = lang || "General";
    const color = getLangColor(cleanLang);

    return `
    <span class="repo-lang" style="--lang-tint: ${escapeHtml(color)};">
      ${renderLanguageSvg(cleanLang, color)}
      <span>${escapeHtml(cleanLang)}</span>
    </span>
  `;
}

function renderCard(project, isFeaturedCard = false) {
    const safeName = escapeHtml(project.name);
    const safeUrl = escapeHtml(sanitizeUrl(project.html_url));
    const safeDesc = escapeHtml(
        project.description || "Proyecto en desarrollo o repositorio sin descripción pública."
    );
    const safeDate = escapeHtml(project.created_at || project.year || "");

    const hasHomepage = Boolean(
        project.homepage && /^https?:\/\//i.test(project.homepage.trim())
    );
    const safeHomepage = hasHomepage ? escapeHtml(project.homepage.trim()) : "";

    const tags = [];
    if (project.featured) {
        tags.push(`<span class="tag tag-featured">Destacado</span>`);
    }
    if (project.is_fork) {
        tags.push(`<span class="tag tag-fork">Fork</span>`);
    } else {
        tags.push(`<span class="tag tag-original">Original</span>`);
    }
    if (project.archived) {
        tags.push(`<span class="tag tag-archived">Archivado</span>`);
    }

    const metaParts = [];
    if (safeDate) metaParts.push(safeDate);
    if ((project.stars || 0) > 0) metaParts.push(`★ ${project.stars}`);
    if ((project.forks || 0) > 0) metaParts.push(`⑂ ${project.forks}`);

    return `
    <article class="repo-card ${isFeaturedCard ? "is-featured" : ""}" role="listitem">
      <div>
        <div class="repo-head">
          <h3 class="repo-name">
            <a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeName}</a>
          </h3>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            ${tags.join("")}
          </div>
        </div>
        <p class="repo-desc">${safeDesc}</p>
      </div>

      <div class="repo-foot">
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
          ${renderLanguageBadge(project.language)}
          <span>${metaParts.join(" · ")}</span>
        </div>

        <div class="repo-actions">
          ${hasHomepage
            ? `<a href="${safeHomepage}" target="_blank" rel="noopener noreferrer">Demo ↗</a>`
            : ""
        }
          <a href="${safeUrl}" target="_blank" rel="noopener noreferrer">Repo →</a>
        </div>
      </div>
    </article>
  `;
}

function renderKpis(snapshot) {
    const projects = snapshot.projects || [];
    const summary = snapshot.summary || {};

    const total = summary.total_projects ?? projects.length;
    const originals =
        summary.original_projects ?? projects.filter((p) => !p.is_fork).length;
    const featured =
        summary.featured_projects ?? projects.filter((p) => p.featured).length;
    const langs = Array.isArray(summary.languages)
        ? summary.languages.length
        : new Set(
            projects
                .map((p) => p.language)
                .filter((l) => l && l !== "General" && l !== "Code")
        ).size;

    document.getElementById("kpi-total").textContent = total;
    document.getElementById("kpi-originals").textContent = originals;
    document.getElementById("kpi-featured").textContent = featured;
    document.getElementById("kpi-langs").textContent = langs;

    if (snapshot.generated_at) {
        const dateObj = new Date(snapshot.generated_at);
        if (!Number.isNaN(dateObj.getTime())) {
            document.getElementById("generated-meta").textContent =
                `Actualizado: ${dateObj.toISOString().slice(0, 10)} UTC`;
        }
    }
}

function populateLanguageFilter(projects) {
    const select = document.getElementById("lang-filter");
    const langs = [
        ...new Set(
            projects
                .map((p) => p.language)
                .filter((l) => l && l !== "General" && l !== "Code")
        )
    ].sort((a, b) => a.localeCompare(b));

    for (const lang of langs) {
        const option = document.createElement("option");
        option.value = lang;
        option.textContent = lang;
        select.appendChild(option);
    }
}

function getFilteredProjects() {
    const q = state.query.trim().toLowerCase();

    return state.projects.filter((p) => {
        if (state.filterType === "original" && p.is_fork) return false;
        if (state.filterType === "fork" && !p.is_fork) return false;
        if (state.language !== "all" && p.language !== state.language) return false;

        if (q) {
            const haystack = `${p.name} ${p.description} ${p.language} ${p.year}`.toLowerCase();
            if (!haystack.includes(q)) return false;
        }

        return true;
    });
}

function renderFeatured() {
    const section = document.getElementById("featured-section");
    const grid = document.getElementById("featured-grid");
    const featured = state.projects.filter((p) => p.featured);

    if (featured.length === 0) {
        section.hidden = true;
        return;
    }

    section.hidden = false;
    grid.innerHTML = featured.map((p) => renderCard(p, true)).join("");
}

function renderCatalog() {
    const container = document.getElementById("catalog-container");
    const countEl = document.getElementById("results-count");
    const filtered = getFilteredProjects();

    countEl.textContent =
        `${filtered.length} ${filtered.length === 1 ? "proyecto" : "proyectos"}`;

    if (filtered.length === 0) {
        container.innerHTML = `
      <div class="empty-msg">
        No hay proyectos que coincidan con los filtros actuales.
      </div>
    `;
        return;
    }

    const grouped = new Map();
    for (const project of filtered) {
        const year = project.year || "Sin fecha";
        if (!grouped.has(year)) {
            grouped.set(year, []);
        }
        grouped.get(year).push(project);
    }

    const sortedYears = [...grouped.keys()].sort((a, b) => b.localeCompare(a));

    container.innerHTML = sortedYears
        .map((year) => {
            const items = grouped.get(year);
            return `
        <div class="year-group">
          <div class="year-header">
            <div class="year-cloud">
              <span class="year-cloud-dot"></span>
              <span>${escapeHtml(year)}</span>
            </div>
            <div class="year-line"></div>
          </div>
          <div class="cards-grid" role="list">
            ${items.map((p) => renderCard(p, false)).join("")}
          </div>
        </div>
      `;
        })
        .join("");
}

function bindEvents() {
    document.querySelectorAll("[data-filter-type]").forEach((btn) => {
        btn.addEventListener("click", () => {
            document
                .querySelectorAll("[data-filter-type]")
                .forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            state.filterType = btn.dataset.filterType;
            renderCatalog();
        });
    });

    document.getElementById("lang-filter").addEventListener("change", (e) => {
        state.language = e.target.value;
        renderCatalog();
    });

    document.getElementById("search-input").addEventListener("input", (e) => {
        state.query = e.target.value;
        renderCatalog();
    });
}

async function init() {
    bindEvents();

    try {
        const res = await fetch(DATA_URL, { cache: "no-store" });
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        const snapshot = await res.json();
        state.data = snapshot;
        state.projects = Array.isArray(snapshot.projects) ? snapshot.projects : [];

        renderKpis(snapshot);
        populateLanguageFilter(state.projects);
        renderFeatured();
        renderCatalog();
    } catch (err) {
        document.getElementById("results-count").textContent = "Error al cargar";
        document.getElementById("catalog-container").innerHTML = `
      <div class="empty-msg">
        No se pudo cargar <code>data/projects.json</code> (${escapeHtml(err.message)}).
        Asegúrate de servir la carpeta desde un servidor local (por ejemplo <code>python -m http.server 8080</code>).
      </div>
    `;
    }
}

init();
