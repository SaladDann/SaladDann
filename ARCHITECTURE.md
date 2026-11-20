# Profile Telemetry Engine & Cartridge Console

**Motor modular de telemetría y catálogo de proyectos para perfiles de GitHub, desarrollado en Python sin dependencias externas.**

Automatiza la extracción, el procesamiento y la representación visual de métricas de actividad y repositorios de GitHub mediante sus **APIs (GraphQL y REST)** y **GitHub Actions**. Incorpora un sistema de cartuchos visuales intercambiables (*Plug & Play*) y un catálogo web estático desplegado en **GitHub Pages** con identidad oscura y acentos pasteles.

---

## 🏗️ Arquitectura del Proyecto

```text
SaladDann/
│
├── .github/
│   └── workflows/
│       └── update-telemetry.yml     # Pipeline diario: métricas + proyectos + SVGs → commit
│
├── assets/                          # Recursos SVG estáticos y dinámicos
│   ├── 01-header-codebars.svg
│   ├── 02-metrics-stats.svg
│   ├── 02-metrics-streak.svg
│   ├── 03-side-isometric.svg
│   ├── 03-side-langs.svg
│   ├── 03-stack-flstudio.svg
│   ├── 03-stack-title.svg
│   ├── 04-footer-contrib.svg        # SVG generado por el cartucho activo
│   ├── 04-footer-wave.svg
│   └── 05-easter-waveform.svg
│
├── data/
│   ├── metrics.json                 # Instantánea estructurada de métricas
│   └── projects.json                # Catálogo estructurado y puntuado de repositorios
│
├── docs/                            # Interfaz web estática servida en GitHub Pages
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── scripts/
│   ├── fetch_metrics.py             # Extracción de métricas mediante GraphQL
│   ├── fetch_projects.py            # Extracción y puntuación de proyectos vía API de GitHub
│   ├── render_svgs.py               # Orquestador de generación de SVG
│   │
│   └── renderers/
│       ├── theme.py                 # Paleta de colores pastel centralizada
│       ├── streak_card.py           # Racha actual y mejor racha
│       ├── stats_card.py            # Commits, repositorios, PRs e issues
│       ├── isometric_matrix.py      # Matriz isométrica basada en los últimos 25 días
│       ├── langs_card.py            # Distribución completa de lenguajes con altura dinámica
│       ├── contrib_grid.py          # Consola selectora y motor de rotación
│       │
│       └── cartridges/              # 9 cartuchos visuales intercambiables
│           ├── battle_city.py
│           ├── cloud_rain.py
│           ├── invaders.py
│           ├── keroppi.py
│           ├── mario.py
│           ├── pacman.py
│           ├── pokemon.py
│           ├── scanner.py
│           └── snake.py
│
├── .gitignore
├── ARCHITECTURE.md
└── README.md
```

---

## 🔧 Instalación y Adaptación

Para integrar el motor y el catálogo de proyectos en otro perfil de GitHub, realiza un fork o clona el repositorio y copia las siguientes carpetas y archivos en tu repositorio de perfil (`<tu-usuario>/<tu-usuario>`):

- `.github/`
- `scripts/`
- `assets/`
- `data/`
- `docs/`

### 1. Permisos de GitHub Actions

Accede a la siguiente configuración:

`Settings → Actions → General → Workflow permissions`

Activa:

**Read and write permissions**

Guarda los cambios para permitir que GitHub Actions actualice los archivos SVG generados y los datos JSON (`data/metrics.json` y `data/projects.json`) mediante commits.

### 2. Autenticación con la API de GitHub (Opcional)

Para incluir métricas de contribuciones en repositorios privados o ampliar límites de consulta:

1. Genera un **Personal Access Token clásico**.
2. Habilita los permisos `repo` y `read:user`.
3. Añade el token a los secretos del repositorio con el nombre `METRICS_TOKEN` (o usa `GITHUB_TOKEN` según tu workflow).
4. Configura `update-telemetry.yml` para utilizar este secreto durante la autenticación con la API.

### 3. Despliegue del Catálogo en GitHub Pages

1. Ve a `Settings → Pages` en el repositorio.
2. En **Build and deployment → Source**, selecciona **Deploy from a branch**.
3. Elige la rama **`main`** y la carpeta **`/docs`**, y guarda los cambios.
4. Verifica que `DATA_URL` en `docs/app.js` apunte a la ruta cruda de `data/projects.json` en GitHub (`https://raw.githubusercontent.com/<usuario>/<repo>/main/data/projects.json`) para evitar errores `404` por la subcarpeta `/docs/`.

### 4. Personalización Visual

| Componente | Archivo de configuración |
|---|---|
| Información del perfil y enlace al catálogo | `README.md` |
| Paleta de colores pastel | `scripts/renderers/theme.py` y `docs/styles.css` |
| Cartuchos visuales | `scripts/renderers/cartridges/` |
| Catálogo web de proyectos | `docs/index.html`, `docs/styles.css` y `docs/app.js` |
| Frecuencia de automatización | `.github/workflows/update-telemetry.yml` |

---

## 🎮 Consola de Cartuchos

**Módulo:** `scripts/renderers/cartridges/`

El componente `04-footer-contrib.svg` funciona mediante un sistema modular de cartuchos. Cada cartucho implementa un renderizador visual independiente sobre lienzo limpio (sin títulos superiores), permitiendo incorporar nuevas animaciones y diseños sin modificar el motor de generación principal.

### Ciclo de funcionamiento

**01 — Autodescubrimiento**

Cualquier archivo `.py` añadido dentro de `cartridges/` que implemente la siguiente interfaz se detecta automáticamente:

```python
def render(data: dict) -> str:
    ...
```

**02 — Prioridad de estreno**

Los cartuchos recién incorporados reciben prioridad exclusiva durante sus primeros **7 días**. El sistema determina su antigüedad mediante el historial de Git (`fetch-depth: 0`).

**03 — Rotación automática**

Una vez finalizado el período de estreno, la consola alterna determinísticamente entre los cartuchos disponibles cada **5 días**.

### Cartuchos disponibles (9)

| Cartucho | Concepto visual |
|---|---|
| `battle_city.py` | Combate táctico de tanques estilo NES protegiendo la base del águila |
| `cloud_rain.py` | 12 nubes mensuales con lluvia binaria, relámpagos y ondas proporcionales |
| `invaders.py` | Intercepción arcade de naves pixel-art descendentes con cierre `YOU WIN!` |
| `keroppi.py` | Saltos parabólicos de Kero Kero Keroppi sobre nenúfares, flores de loto y ondas de mayor alcance sobre estanque translúcido |
| `mario.py` | Scroll lateral con bloques `?` (monedas, hongo y estrella), Goomba y castillo con pirotecnia |
| `pacman.py` | Evasión por el tablero y contraataque final contra fantasmas vulnerables |
| `pokemon.py` | Exploración en la hierba alta y captura de Pokémon salvajes con Pokébolas |
| `scanner.py` | Interfaz de exploración y detección de actividad |
| `snake.py` | Serpiente ortogonal estilo `snk` devorando contribuciones dispersas de menor a mayor |

---

## 🧪 Ejecución y Pruebas Locales

### Requisitos

- Python 3.x (cero dependencias externas).
- Token de GitHub (para la extracción de métricas y proyectos).
- Git.

### 1. Extraer métricas y catálogo de proyectos de GitHub

En Bash / Linux / macOS:

```bash
export GITHUB_TOKEN="tu_token"
export GITHUB_ACTOR="tu_usuario"

python scripts/fetch_metrics.py
python scripts/fetch_projects.py
```

En PowerShell (Windows):

```powershell
$env:GITHUB_TOKEN = "tu_token"
$env:GITHUB_ACTOR = "tu_usuario"

python scripts/fetch_metrics.py
python scripts/fetch_projects.py
```

Obtiene las métricas del perfil mediante la API GraphQL y genera `data/metrics.json`, además de consultar los repositorios y actualizar `data/projects.json` con puntuación automática de relevancia.

### 2. Generar todos los recursos SVG (con rotación automática)

```bash
python scripts/render_svgs.py
```

### 3. Probar un cartucho específico directamente desde consola (Ejemplos)

```bash
python scripts/render_svgs.py battle_city
python scripts/render_svgs.py keroppi
python scripts/render_svgs.py invaders
python scripts/render_svgs.py snake
```

### 4. Previsualizar el catálogo web localmente

```bash
python -m http.server 8080
```

Abre `http://localhost:8080/docs/` en el navegador para comprobar los filtros, la búsqueda, las tarjetas y el agrupamiento por año.

### 5. Publicar cambios en GitHub

```bash
git status
git add .
git commit -m "chore(portfolio): update telemetry, projects catalog and docs"
git push
```

---

## ⚙️ Tecnologías utilizadas

| Tecnología | Aplicación |
|---|---|
| Python | Lógica principal, extracción de datos y motor de renderizado |
| GitHub GraphQL & REST APIs | Extracción de métricas y repositorios del perfil |
| SVG + CSS `@keyframes` | Gráficos vectoriales y animaciones fluidas |
| HTML5 + CSS3 + JavaScript | Página estática de proyectos con identidad oscura y acentos pasteles |
| GitHub Actions & GitHub Pages | Automatización diaria y despliegue web gratuito |
| Git | Control de versiones e historial de estreno de cartuchos |

---

## 💡 Filosofía de diseño

- **Arquitectura modular:** componentes independientes y responsabilidades separadas.
- **Cero dependencias externas:** funcionamiento mediante bibliotecas estándar de Python.
- **Telemetría y catálogo automatizados:** extracción periódica de métricas y proyectos reales.
- **Cartuchos intercambiables:** incorporación de nuevos diseños sin alterar el núcleo.
- **Rotación determinística:** selección automática basada en reglas temporales.
- **Renderizado dinámico:** generación de elementos SVG y vistas de catálogo a partir de datos estructurados.

---

*Un motor de telemetría y catálogo extensible que transforma la actividad de GitHub en una experiencia visual automatizada y personalizable.*
