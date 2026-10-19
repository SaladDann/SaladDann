import os
import requests

USERNAME = "SaladDann"
TOKEN = os.getenv("GH_TOKEN")

headers = {
    "Accept": "application/vnd.github.v3+json"
}
if TOKEN:
    headers["Authorization"] = f"token {TOKEN}"

# Badges de tecnologías configurados con la paleta de colores sobria
LANG_BADGES = {
    "TypeScript": "https://img.shields.io/badge/TypeScript-005f73?style=flat-square&logo=typescript&logoColor=white",
    "JavaScript": "https://img.shields.io/badge/JavaScript-0a9396?style=flat-square&logo=javascript&logoColor=white",
    "Python": "https://img.shields.io/badge/Python-1e3a8a?style=flat-square&logo=python&logoColor=white",
    "Dart": "https://img.shields.io/badge/Dart-0d9488?style=flat-square&logo=dart&logoColor=white",
    "C#": "https://img.shields.io/badge/C%23-0f766e?style=flat-square&logo=c-sharp&logoColor=white",
    "Java": "https://img.shields.io/badge/Java-1e293b?style=flat-square&logo=openjdk&logoColor=white",
    "HTML": "https://img.shields.io/badge/HTML5-0a9396?style=flat-square&logo=html5&logoColor=white",
    "C++": "https://img.shields.io/badge/C%2B%2B-005f73?style=flat-square&logo=cplusplus&logoColor=white",
    "CSS": "https://img.shields.io/badge/CSS3-1e3a8a?style=flat-square&logo=css3&logoColor=white"
}

def get_repos():
    url = f"https://api.github.com/users/{USERNAME}/repos?sort=created&direction=desc&per_page=100"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error al obtener los repositorios: {response.status_code}")
    return response.json()

def generate_catalog_html(repos):
    # Filtrar forks y excluir el propio repositorio de perfil
    own_repos = [r for r in repos if not r["fork"] and r["name"].lower() != USERNAME.lower()]

    # Ordenar estrictamente por fecha de creación (los más recientes primero)
    sorted_repos = sorted(own_repos, key=lambda x: x["created_at"], reverse=True)

    # Mostrar los 8 proyectos más recientes
    featured_repos = sorted_repos[:8]

    html = '<h3 id="-catálogo-de-proyectos">📂 Catálogo de Proyectos</h3>\n\n'
    html += '<table width="100%">\n'

    for i in range(0, len(featured_repos), 2):
        html += "  <tr>\n"
        for repo in featured_repos[i:i+2]:
            name = repo["name"]
            url = repo["html_url"]
            desc = repo["description"] or "Proyecto desarrollado en GitHub."
            lang = repo["language"] or "Code"
            created_date = repo["created_at"].split("T")[0]
            stars = repo["stargazers_count"]

            badge_url = LANG_BADGES.get(
                lang,
                f"https://img.shields.io/badge/{lang}-0d9488?style=flat-square"
            )

            html += f'''    <td width="50%" valign="top">
      <h4 align="left">📁 <a href="{url}">{name}</a></h4>
      <p><sub>📅 Creado: <code>{created_date}</code> | ⭐ {stars}</sub></p>
      <p><img src="{badge_url}" alt="{lang}" /></p>
      <p>{desc}</p>
      <p><a href="{url}"><b>Ver Repositorio »</b></a></p>
    </td>\n'''
        html += "  </tr>\n"

    html += "</table>\n"
    return html

def update_readme(catalog_content):
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    start_tag = "<!-- CATALOG_START -->"
    end_tag = "<!-- CATALOG_END -->"

    start_idx = readme.find(start_tag)
    end_idx = readme.find(end_tag)

    if start_idx != -1 and end_idx != -1:
        updated_readme = (
            readme[:start_idx + len(start_tag)] +
            "\n\n" + catalog_content + "\n" +
            readme[end_idx:]
        )
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(updated_readme)
        print("README.md actualizado correctamente.")
    else:
        print("No se encontraron las etiquetas <!-- CATALOG_START --> y <!-- CATALOG_END -->.")

if __name__ == "__main__":
    repos = get_repos()
    catalog = generate_catalog_html(repos)
    update_readme(catalog)
