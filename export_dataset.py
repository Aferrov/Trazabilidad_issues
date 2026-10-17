import json
import os
from datetime import datetime
from github import Github
from git import Repo

# ================= CONFIGURACIÓN =================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "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")
REPO_GITHUB = "authorjapps/zerocode"               # Repositorio remoto en GitHub
LOCAL_REPO_PATH = "D:\zerocode"           # Ruta a tu clon local de Git
MAX_ISSUES = 200                            # Límite de prueba (ajustable)
MAX_COMMITS = 1000                           # Límite de prueba (ajustable)
# =================================================

g = Github(GITHUB_TOKEN)
remote_repo = g.get_repo(REPO_GITHUB)
local_repo = Repo(LOCAL_REPO_PATH)

print(f"[*] 1/2 Extrayendo issues cerrados de {REPO_GITHUB}...")
issues_dataset = []

# Iterar sobre issues cerrados (filtrando Pull Requests)
for issue in remote_repo.get_issues(state="closed"):
    if issue.pull_request:
        continue  # Descartar PRs para procesar únicamente issues reales
    
    issues_dataset.append({
        "issue_id": str(issue.number),
        "title": issue.title.strip() if issue.title else "",
        "description": issue.body.strip() if issue.body else "",
        "created_at": issue.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "closed_at": issue.closed_at.strftime("%Y-%m-%d %H:%M:%S") if issue.closed_at else ""
    })
    
    if len(issues_dataset) >= MAX_ISSUES:
        break

print(f"[✓] {len(issues_dataset)} issues extraídos con éxito.")

print(f"[*] 2/2 Extrayendo commits e historial del clon local...")
commits_dataset = []

# Iterar sobre el historial de confirmaciones de la rama principal
for commit in local_repo.iter_commits(local_repo.active_branch.name, max_count=MAX_COMMITS):    # Obtener el diff (código añadido / modificado) respecto a su commit padre
    diff_text = ""
    if commit.parents:
        diffs = commit.parents[0].diff(commit, create_patch=True)
        # Acumular los parches de texto (limitando a 3000 caracteres para evitar saturación de memoria)
        diff_chunks = []
        for d in diffs:
            if d.diff:
                try:
                    diff_chunks.append(d.diff.decode('utf-8', errors='ignore'))
                except Exception:
                    pass
        diff_text = "\n".join(diff_chunks)[:3000]

    # Archivos modificados en este commit
    changed_files = list(commit.stats.files.keys())
    commit_date = datetime.fromtimestamp(commit.committed_date).strftime("%Y-%m-%d %H:%M:%S")

    commits_dataset.append({
        "commit_id": commit.hexsha[:8],
        "full_sha": commit.hexsha,
        "message": commit.message.strip(),
        "files": changed_files,
        "diff": diff_text,
        "committed_at": commit_date
    })

print(f"[✓] {len(commits_dataset)} commits procesados con éxito.")

# ================= GUARDAR ARCHIVOS =================
os.makedirs("data", exist_ok=True)

with open("data/issues.json", "w", encoding="utf-8") as f:
    json.dump(issues_dataset, f, indent=2, ensure_ascii=False)

with open("data/commits.json", "w", encoding="utf-8") as f:
    json.dump(commits_dataset, f, indent=2, ensure_ascii=False)

print("\nArchivos generados en carpeta ./data/:")
print("  -> data/issues.json")
print("  -> data/commits.json")