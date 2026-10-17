import requests
import json
import time
import sys

# --- CONFIGURACIÓN ---
REPO_OWNER = "acaudwell"
REPO_NAME = "Gource"

# Leer token desde archivo t.txt
def cargar_token():
    try:
        with open("t.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("❌ Error: No se encontró el archivo 't.txt' con el token de GitHub.")
        print("   Crea un archivo 't.txt' con tu token de GitHub.")
        sys.exit(1)

GITHUB_TOKEN = cargar_token()

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}


# ==========================================
# PASO 1: Obtener y guardar issues en JSON
# ==========================================
def get_issues(repo_owner=REPO_OWNER, repo_name=REPO_NAME):
    """
    Obtiene todos los issues del repositorio y los guarda en issues.json
    Similar a get_commits() en tu código original.
    """
    issues_raw = []
    pagina = 1
    params = {"state": "all", "per_page": 100, "page": pagina, "sort": "created", "direction": "desc"}
    
    print(f"--- 📥 Descargando Issues de {repo_owner}/{repo_name} ---")

    while True:
        print(f"📄 Descargando página {pagina}...")
        try:
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
            resp = requests.get(url, headers=HEADERS, params=params)
            
            if resp.status_code != 200:
                print(f"Error: {resp.status_code} - {resp.reason}")
                break
                
            datos = resp.json()
            if not datos: 
                break
            
            # Filtrar solo issues (no PRs)
            for item in datos:
                if "pull_request" not in item:
                    issues_raw.append(item)
            
            print(f"   Issues encontrados en esta página: {len([i for i in datos if 'pull_request' not in i])}")
            pagina += 1
            params["page"] = pagina
            time.sleep(0.5)  # Respetar rate limit
            
        except Exception as e:
            print(f"Error: {e}")
            break

    # Guardar issues crudos en JSON
    filename = f"{repo_name}_issues.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(issues_raw, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Issues guardados en '{filename}'. Total: {len(issues_raw)}")
    return issues_raw


# ==========================================
# PASO 2: Funciones auxiliares para obtener datos relacionados
# ==========================================
def obtener_archivos_de_commit(commit_url):
    """Obtiene los archivos modificados de un commit específico."""
    files = []
    try:
        response = requests.get(commit_url, headers=HEADERS)
        if response.status_code == 200:
            commit_data = response.json()
            files_json = commit_data.get("files", [])
            for f in files_json:
                files.append({
                    "filename": f["filename"],
                    "status": f.get("status", "modified"),
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                    "changes": f.get("changes", 0)
                })
        time.sleep(0.1)
    except Exception as e:
        print(f"   ⚠️ Error obteniendo archivos del commit: {e}")
    return files


def obtener_info_de_commit(commit_sha, repo_owner=REPO_OWNER, repo_name=REPO_NAME):
    """Obtiene información detallada de un commit específico."""
    try:
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits/{commit_sha}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            return {
                "sha": commit_sha,
                "message": data.get("commit", {}).get("message", ""),
                "author": data.get("commit", {}).get("author", {}).get("name", ""),
                "date": data.get("commit", {}).get("author", {}).get("date", ""),
                "files": [f["filename"] for f in data.get("files", [])]
            }
        time.sleep(0.1)
    except Exception as e:
        print(f"   ⚠️ Error obteniendo commit {commit_sha}: {e}")
    return {"sha": commit_sha, "message": "", "author": "", "date": "", "files": []}


def obtener_info_de_pr(pr_url):
    """
    Obtiene de un PR: 
    1. Los archivos que tocó.
    2. La lista de COMMITS que pertenecen a ese PR.
    """
    files = []
    commits = []
    
    try:
        # 1. Obtener Archivos del PR
        url_files = f"{pr_url}/files"
        resp_files = requests.get(url_files, headers=HEADERS)
        if resp_files.status_code == 200:
            for f in resp_files.json():
                files.append({
                    "filename": f["filename"],
                    "status": f.get("status", "modified"),
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0)
                })
        
        # 2. Obtener Commits del PR
        url_commits = f"{pr_url}/commits"
        resp_commits = requests.get(url_commits, headers=HEADERS)
        if resp_commits.status_code == 200:
            for c in resp_commits.json():
                commits.append({
                    "sha": c["sha"],
                    "message": c.get("commit", {}).get("message", ""),
                    "author": c.get("commit", {}).get("author", {}).get("name", ""),
                    "date": c.get("commit", {}).get("author", {}).get("date", "")
                })
        
        time.sleep(0.2)
                
    except Exception as e:
        print(f"   ⚠️ Error obteniendo info del PR: {e}")
    
    return files, commits


# ==========================================
# PASO 3: Procesar issues con commits y archivos
# ==========================================
def get_issue_list(repo_owner=REPO_OWNER, repo_name=REPO_NAME):
    """
    Lee los issues de 'issues.json' y los procesa para agregar:
    - Commits relacionados (con detalle)
    - Archivos afectados
    Similar a get_commit_list() en tu código original.
    """
    # Leer issues del archivo JSON
    input_filename = f"{repo_name}_issues.json"
    try:
        with open(input_filename, "r", encoding="utf-8") as f:
            issues_raw = json.load(f)
    except FileNotFoundError:
        print(f"❌ No se encontró '{input_filename}'. Ejecuta get_issues() primero.")
        return []
    
    print(f"\n--- 🔄 Procesando {len(issues_raw)} issues para obtener commits y archivos ---")
    
    issues_procesados = []
    
    for idx, item in enumerate(issues_raw):
        issue_num = item['number']
        print(f"\n📌 [{idx + 1}/{len(issues_raw)}] Procesando Issue #{issue_num}: {item['title'][:50]}...")
        
        # Datos de relación
        commits_relacionados = []
        archivos_afectados = []
        metodo_cierre = "manual"
        prs_relacionados = []

        # Usar Timeline para buscar la relación profunda
        timeline_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_num}/timeline"
        events = []
        try:
            resp = requests.get(timeline_url, headers=HEADERS, params={"per_page": 100})
            if resp.status_code == 200:
                events = resp.json()
            time.sleep(0.3)
        except Exception as e:
            print(f"   ⚠️ Error obteniendo timeline: {e}")

        archivos_set = set()
        
        for event in events:
            if not isinstance(event, dict):
                continue
                
            evt_type = event.get('event', '')
            
            # CASO 1: Commit cierra Issue directamente
            if evt_type == 'closed' and event.get('commit_id'):
                sha = event['commit_id']
                metodo_cierre = "direct_commit"
                
                # Obtener información detallada del commit
                commit_info = obtener_info_de_commit(sha, repo_owner, repo_name)
                commits_relacionados.append(commit_info)
                archivos_set.update(commit_info.get('files', []))
                print(f"   🔗 Commit directo encontrado: {sha[:7]}")

            # CASO 2: Enlace vía Pull Request
            elif evt_type == 'cross-referenced':
                source = event.get('source', {})
                if source and source.get('type') == 'issue':
                    issue_data = source.get('issue', {})
                    if 'pull_request' in issue_data:
                        pr_url = issue_data['pull_request']['url']
                        pr_number = issue_data.get('number')
                        metodo_cierre = "PR_linked"
                        
                        print(f"   🔗 PR #{pr_number} encontrado, extrayendo commits y archivos...")
                        
                        # Extraer commits y archivos del PR
                        files_pr, commits_pr = obtener_info_de_pr(pr_url)
                        
                        prs_relacionados.append({
                            "number": pr_number,
                            "title": issue_data.get('title', ''),
                            "url": issue_data.get('html_url', ''),
                            "state": issue_data.get('state', '')
                        })
                        
                        for f in files_pr:
                            archivos_set.add(f['filename'])
                        
                        for c in commits_pr:
                            if not any(existing['sha'] == c['sha'] for existing in commits_relacionados):
                                commits_relacionados.append(c)

            # CASO 3: Commit referenciado
            elif evt_type == 'referenced' and event.get('commit_id'):
                sha = event['commit_id']
                if not any(c['sha'] == sha for c in commits_relacionados):
                    commit_info = obtener_info_de_commit(sha, repo_owner, repo_name)
                    commits_relacionados.append(commit_info)
                    archivos_set.update(commit_info.get('files', []))
                    print(f"   📎 Commit referenciado: {sha[:7]}")

        # Convertir archivos a lista con más detalle
        archivos_afectados = list(archivos_set)
        
        # Si no hay archivos, crear uno ficticio para Gource
        if not archivos_afectados:
            archivos_afectados = [f"discussions/issue_{issue_num}.txt"]

        # Construir objeto del issue procesado
        issue_obj = {
            "id": issue_num,
            "title": item['title'],
            "body": item.get('body', ''),
            "user": item['user']['login'],
            "start_time": item['created_at'],
            "end_time": item.get('closed_at'),
            "state": item['state'],
            "labels": [label['name'] for label in item.get('labels', [])],
            "resolution_type": metodo_cierre,
            "related_prs": prs_relacionados,
            "related_commits": commits_relacionados,
            "affected_files": archivos_afectados,
            "stats": {
                "total_commits": len(commits_relacionados),
                "total_files": len(archivos_afectados),
                "total_prs": len(prs_relacionados)
            }
        }
        
        issues_procesados.append(issue_obj)
        
        if commits_relacionados:
            print(f"   ✅ {len(commits_relacionados)} commits, {len(archivos_afectados)} archivos")
        else:
            print(f"   ⚪ Sin commits relacionados")

    # Guardar issues procesados
    output_filename = f"{repo_name}_issues_commits.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(issues_procesados, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Procesamiento completado. Resultado en '{output_filename}'")
    print(f"   Total issues: {len(issues_procesados)}")
    print(f"   Con commits: {len([i for i in issues_procesados if i['related_commits']])}")
    
    return issues_procesados


# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================
if __name__ == "__main__":
    # PASO 1: Descargar issues y guardar en issues.json
    print("=" * 60)
    print("PASO 1: Descargando issues del repositorio...")
    print("=" * 60)
    get_issues()
    
    # PASO 2: Procesar issues para obtener commits y archivos
    print("\n" + "=" * 60)
    print("PASO 2: Procesando issues para obtener commits relacionados...")
    print("=" * 60)
    issues = get_issue_list()
    
    print("\n" + "=" * 60)
    print("✅ PROCESO COMPLETADO")
    print("=" * 60)
    print("Archivos generados:")
    print(f"  📄 {REPO_NAME}_issues.json - Issues crudos del repositorio")
    print(f"  📄 {REPO_NAME}_issues_commits.json - Issues con commits y archivos relacionados")