## Autor
- **Nombre:** Arleen Maritza Ferro Vásquez
# Gource Issues Visualization

Herramienta para visualizar issues de GitHub junto con la actividad de commits usando [Gource](https://gource.io/).

## 📋 Descripción

Este proyecto extrae issues de un repositorio de GitHub y los transforma en un formato compatible con Gource, permitiendo visualizar:
- **Issues** como nodos rojos
- **Archivos afectados** por cada issue
- **Timeline unificado** de commits + issues

## 🛠️ Requisitos

- Python 3.x
- [Gource](https://gource.io/) instalado
- Token de GitHub (para acceder a la API)

## 📁 Archivos

| Archivo | Descripción |
|---------|-------------|
| `extraer_issues.py` | Extrae issues de GitHub y genera JSONs |
| `json_to_gource.py` | Convierte JSONs a formato Gource |
| `file_colours.txt` | Colores personalizados por extensión |

## 🚀 Instalación y Uso

### 1. Configurar Token de GitHub

Crea un archivo `t.txt` en la raíz del proyecto con tu token de GitHub:

```
ghp_TuTokenAqui...
```

> ⚠️ **Importante:** Este archivo está en `.gitignore` y NO se sube al repositorio.

### 2. Configurar el Repositorio

Edita `extraer_issues.py` y `json_to_gource.py` para cambiar:

```python
REPO_OWNER = "usuario"
REPO_NAME = "nombre-repo"
```

### 3. Extraer Issues

```bash
python extraer_issues.py
```

Esto genera:
- `{REPO_NAME}_issues.json` - Issues crudos
- `{REPO_NAME}_issues_commits.json` - Issues con commits relacionados

 de issues

## 📄 Licencia

MIT
