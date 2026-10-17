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

### 4. Generar Log de Git Original

```bash
gource --output-custom-log gource_original.log
```

### 5. Generar Logs de Gource

```bash
python json_to_gource.py
```

Esto genera:
- `{REPO_NAME}_gource.log` - Log simple
- `{REPO_NAME}_gource_detailed.log` - Solo issues con archivos
- `{REPO_NAME}_merged.log` - Git + Issues combinados

### 6. Visualizar con Gource

**Solo issues:**
```bash
gource Gource_gource_detailed.log --file-idle-time 0 --seconds-per-day 0.1 --key
```

**Git + Issues (recomendado):**
```bash
gource Gource_merged.log --file-idle-time 0 --seconds-per-day 0.1 --key --start-date "2015-01-01"
```

## 🎨 Colores

| Elemento | Color |
|----------|-------|
| Issues (`.issue`) | 🔴 Rojo |
| Código (`.cpp`, `.h`) | 🔵 Azul |
| Scripts (`.py`, `.sh`) | 🟡 Amarillo |
| Docs (`.md`, `.txt`) | 🔵 Cyan |
| Build (`.am`, `.m4`) | 🟣 Morado |

## 📊 Estructura de Visualización

```
/archivo.cpp/
  ├── archivo.cpp      ← Archivo (color por extensión)
  ├── issue_33.issue   ← Issue relacionada (rojo)
  └── issue_46.issue   ← Otra issue (rojo)
```

## 📝 Notas

- Solo se visualizan issues cerrados vía Pull Request (`PR_linked`)
- Los archivos afectados se obtienen de los commits del PR
- El log merged combina la historia de Git con los eventos de issues

## 📄 Licencia

MIT
