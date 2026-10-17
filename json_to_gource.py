import json
import datetime
from datetime import timezone

# --- CONFIGURACIÓN ---
REPO_NAME = "Gource"  # Nombre del repositorio

# Colores por extensión (evitando rojos para no confundir con issues)
EXTENSION_COLORS = {
    # Código fuente - tonos azules
    'cpp': '0066FF',
    'c': '0088FF',
    'h': '00AAFF',
    'hpp': '0099FF',
    # Scripts - tonos amarillos
    'py': 'FFFF00',
    'pl': 'FFDD00',
    'rb': 'FFD700',
    'sh': 'FFCC00',
    # Configuración - tonos verdes
    'conf': '00FF00',
    'config': '00FF00',
    'yaml': '00DD00',
    'yml': '00DD00',
    'json': '00EE00',
    'ini': '00CC00',
    # Documentación - tonos cyan
    'md': '00FFFF',
    'txt': '00DDDD',
    'rst': '00CCCC',
    '1': '00EEEE',
    # Build - tonos morados
    'am': '9966FF',
    'ac': 'AA77FF',
    'm4': '8855EE',
    'in': '7744DD',
    # Otros
    'gitignore': '888888',
    'log': '666666',
}

def get_color_for_file(filepath):
    """Obtiene color según extensión del archivo."""
    ext = filepath.split('.')[-1].lower() if '.' in filepath else ''
    return EXTENSION_COLORS.get(ext, '')

def convert_date_to_timestamp(date_str):
    """Convierte fecha ISO 8601 a timestamp Unix."""
    if not date_str:
        return None
    try:
        # Manejar formato con Z o sin Z
        if date_str.endswith('Z'):
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
        else:
            date_obj = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return int(date_obj.replace(tzinfo=timezone.utc).timestamp())
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
        return None


def json_to_gource_log(repo_name=REPO_NAME, output_file=None):
    """
    Transforma el JSON de issues con commits a formato Gource.
    
    Formato Gource: timestamp|author|action|path
    
    Estructura:
    1. Issue se crea como archivo virtual /issues/issue_XXX.issue
    2. Los commits relacionados aparecen con sus archivos
    3. Cuando el issue se cierra, se marca como modificado
    """
    
    # Leer el JSON
    input_file = f"{repo_name}_issues_commits.json"
    if output_file is None:
        output_file = f"{repo_name}_gource.log"
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            issues = json.load(f)
    except FileNotFoundError:
        print(f"❌ No se encontró '{input_file}'")
        return
    
    print(f"📊 Procesando {len(issues)} issues...")
    
    gource_entries = []
    
    for issue in issues:
        issue_id = issue.get('id')
        issue_title = issue.get('title', '').replace('|', '-')  # Evitar conflictos con separador
        user = issue.get('user', 'unknown')
        start_time = issue.get('start_time')
        end_time = issue.get('end_time')
        state = issue.get('state', 'open')
        labels = issue.get('labels', [])
        
        # Determinar categoría del issue basado en labels
        category = "general"
        if any("bug" in label.lower() for label in labels):
            category = "bugs"
        elif any("feature" in label.lower() or "enhancement" in label.lower() for label in labels):
            category = "features"
        elif any("doc" in label.lower() for label in labels):
            category = "docs"
        
        # Ruta virtual del issue
        issue_path = f"/issues/{category}/issue_{issue_id}.issue"
        
        # 1. CREAR el issue cuando se abre
        start_timestamp = convert_date_to_timestamp(start_time)
        if start_timestamp:
            gource_entries.append({
                'timestamp': start_timestamp,
                'author': user,
                'action': 'A',  # Add
                'path': issue_path
            })
        
        # 2. Procesar COMMITS relacionados
        related_commits = issue.get('related_commits', [])
        for commit in related_commits:
            commit_sha = commit.get('sha', '')[:7]
            commit_author = commit.get('author', user)
            commit_date = commit.get('date')
            commit_files = commit.get('files', [])
            
            commit_timestamp = convert_date_to_timestamp(commit_date)
            if not commit_timestamp:
                commit_timestamp = start_timestamp + 1 if start_timestamp else None
            
            if commit_timestamp:
                # Si hay archivos específicos del commit, usarlos
                if commit_files:
                    for file_path in commit_files:
                        # Limpiar la ruta del archivo
                        clean_path = file_path if file_path.startswith('/') else f"/{file_path}"
                        gource_entries.append({
                            'timestamp': commit_timestamp,
                            'author': commit_author,
                            'action': 'M',  # Modify
                            'path': clean_path
                        })
                
                # Modificar el issue para mostrar actividad
                gource_entries.append({
                    'timestamp': commit_timestamp,
                    'author': commit_author,
                    'action': 'M',
                    'path': issue_path
                })
        
        # 3. Procesar ARCHIVOS afectados (si no vinieron de commits)
        affected_files = issue.get('affected_files', [])
        if affected_files and not related_commits:
            # Usar un timestamp intermedio
            file_timestamp = start_timestamp + 60 if start_timestamp else None
            if file_timestamp:
                for file_path in affected_files:
                    if not file_path.startswith('discussions/'):  # Ignorar archivos ficticios
                        clean_path = file_path if file_path.startswith('/') else f"/{file_path}"
                        gource_entries.append({
                            'timestamp': file_timestamp,
                            'author': user,
                            'action': 'M',
                            'path': clean_path
                        })
        
        # 4. CERRAR el issue (si está cerrado)
        if state == 'closed' and end_time:
            end_timestamp = convert_date_to_timestamp(end_time)
            if end_timestamp:
                # Marcar el issue como "eliminado" cuando se cierra
                # O puedes usar 'M' si prefieres que siga visible
                gource_entries.append({
                    'timestamp': end_timestamp,
                    'author': user,
                    'action': 'D',  # Delete = Issue cerrado
                    'path': issue_path
                })
    
    # Ordenar por timestamp
    gource_entries.sort(key=lambda x: x['timestamp'])
    
    # Escribir archivo Gource
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in gource_entries:
            line = f"{entry['timestamp']}|{entry['author']}|{entry['action']}|{entry['path']}\n"
            f.write(line)
    
    print(f"✅ Archivo Gource generado: '{output_file}'")
    print(f"   Total de entradas: {len(gource_entries)}")
    print(f"   Issues procesados: {len(issues)}")
    
    # Estadísticas
    adds = len([e for e in gource_entries if e['action'] == 'A'])
    mods = len([e for e in gource_entries if e['action'] == 'M'])
    dels = len([e for e in gource_entries if e['action'] == 'D'])
    print(f"   Acciones: {adds} creaciones, {mods} modificaciones, {dels} cierres")
    
    return gource_entries


def json_to_gource_detailed(repo_name=REPO_NAME, output_file=None):
    """
    Estructura: Cada archivo es una rama principal, issues son hijos.
    
    /gource_settings.cpp/
      gource_settings.cpp      ← archivo (color por extensión .cpp)
      issue_33.issue           ← issue (rojo)
      issue_46.issue           ← issue (rojo)
    
    Así se ve claramente qué archivo tiene cuántas issues relacionadas.
    """
    
    input_file = f"{repo_name}_issues_commits.json"
    if output_file is None:
        output_file = f"{repo_name}_gource_detailed.log"
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            issues = json.load(f)
    except FileNotFoundError:
        print(f"❌ No se encontró '{input_file}'")
        return
    
    print(f"📊 Generando log para issues con PR...")
    
    gource_entries = []
    archivos_creados = set()
    issues_procesados = 0
    
    for issue in issues:
        issue_id = issue.get('id')
        resolution_type = issue.get('resolution_type', 'manual')
        
        if resolution_type != 'PR_linked':
            continue
        
        affected_files = issue.get('affected_files', [])
        affected_files = [f for f in affected_files if not f.startswith('discussions/')]
        
        if not affected_files:
            continue
        
        issues_procesados += 1
        user = issue.get('user', 'unknown')
        start_time = issue.get('start_time')
        end_time = issue.get('end_time')
        state = issue.get('state', 'open')
        
        start_timestamp = convert_date_to_timestamp(start_time)
        if not start_timestamp:
            continue
        
        for file_path in affected_files:
            # Obtener nombre del archivo (ej: gource_settings.cpp)
            filename = file_path.split('/')[-1] if '/' in file_path else file_path
            
            # Rama base: nombre del archivo como directorio
            # /gource_settings.cpp/
            file_branch = f"/{filename}"
            
            # 1. Crear el ARCHIVO dentro de su rama (mantiene color por extensión)
            file_node = f"{file_branch}/{filename}"
            if file_node not in archivos_creados:
                gource_entries.append({
                    'timestamp': start_timestamp,
                    'author': user,
                    'action': 'A',
                    'path': file_node,
                    'color': ''  # Color natural por extensión
                })
                archivos_creados.add(file_node)
            
            # 2. Crear la ISSUE como hermana del archivo (ROJO)
            issue_node = f"{file_branch}/issue_{issue_id}.issue"
            gource_entries.append({
                'timestamp': start_timestamp + 1,
                'author': user,
                'action': 'A',
                'path': issue_node,
                'color': 'FF0000'
            })
            
            # 3. Cierre del issue
            if state == 'closed' and end_time:
                end_timestamp = convert_date_to_timestamp(end_time)
                if end_timestamp:
                    gource_entries.append({
                        'timestamp': end_timestamp,
                        'author': user,
                        'action': 'D',
                        'path': issue_node,
                        'color': ''
                    })
    
    # Ordenar
    gource_entries.sort(key=lambda x: x['timestamp'])
    
    # Escribir
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in gource_entries:
            if entry.get('color'):
                line = f"{entry['timestamp']}|{entry['author']}|{entry['action']}|{entry['path']}|{entry['color']}\n"
            else:
                line = f"{entry['timestamp']}|{entry['author']}|{entry['action']}|{entry['path']}\n"
            f.write(line)
    
    print(f"✅ Archivo Gource generado: '{output_file}'")
    print(f"   Issues PR_linked: {issues_procesados}")
    print(f"   Archivos únicos: {len(archivos_creados)}")
    print(f"   Total entradas: {len(gource_entries)}")
    
    return gource_entries


def merge_logs(repo_name=REPO_NAME, git_log_file="gource_original.log", output_file=None):
    """
    Unificación Cronológica (Chronological Merging):
    - Lee el log nativo de Git
    - Lee el JSON de issues
    - Crea issues como archivos .issue en /issues/ (color rojo)
    - Los archivos afectados se modifican en sus rutas reales (no duplicados)
    - Mezcla todo ordenando por timestamp
    """
    
    input_file = f"{repo_name}_issues_commits.json"
    if output_file is None:
        output_file = f"{repo_name}_merged.log"
    
    # 1. Leer log de Git original y aplicar colores por extensión
    git_entries = []
    try:
        with open(git_log_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 4:
                    filepath = parts[3]
                    # Aplicar color según extensión
                    file_color = get_color_for_file(filepath)
                    git_entries.append({
                        'timestamp': int(parts[0]),
                        'author': parts[1],
                        'action': parts[2],
                        'path': filepath,
                        'color': file_color
                    })
    except FileNotFoundError:
        print(f"❌ No se encontró '{git_log_file}'")
        return
    
    print(f"📊 Log Git cargado: {len(git_entries)} entradas (con colores por extensión)")
    
    # 2. Leer issues JSON
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            issues = json.load(f)
    except FileNotFoundError:
        print(f"❌ No se encontró '{input_file}'")
        return
    
    # 3. Generar entradas de issues (misma estructura que json_to_gource_detailed)
    issue_entries = []
    archivos_issues = set()
    issues_procesados = 0
    
    for issue in issues:
        issue_id = issue.get('id')
        resolution_type = issue.get('resolution_type', 'manual')
        
        if resolution_type != 'PR_linked':
            continue
        
        affected_files = issue.get('affected_files', [])
        affected_files = [f for f in affected_files if not f.startswith('discussions/')]
        
        if not affected_files:
            continue
        
        issues_procesados += 1
        user = issue.get('user', 'unknown')
        start_time = issue.get('start_time')
        end_time = issue.get('end_time')
        state = issue.get('state', 'open')
        
        start_timestamp = convert_date_to_timestamp(start_time)
        if not start_timestamp:
            continue
        
        for file_path in affected_files:
            filename = file_path.split('/')[-1] if '/' in file_path else file_path
            
            # Rama: /archivo/
            file_branch = f"/{filename}"
            
            # Crear archivo en su rama (si no existe)
            file_node = f"{file_branch}/{filename}"
            if file_node not in archivos_issues:
                issue_entries.append({
                    'timestamp': start_timestamp,
                    'author': user,
                    'action': 'A',
                    'path': file_node,
                    'color': ''
                })
                archivos_issues.add(file_node)
            
            # Crear issue como hijo del archivo (ROJO)
            issue_node = f"{file_branch}/issue_{issue_id}.issue"
            issue_entries.append({
                'timestamp': start_timestamp + 1,
                'author': user,
                'action': 'A',
                'path': issue_node,
                'color': 'FF0000'
            })
            
            # Cierre del issue
            if state == 'closed' and end_time:
                end_timestamp = convert_date_to_timestamp(end_time)
                if end_timestamp:
                    issue_entries.append({
                        'timestamp': end_timestamp,
                        'author': user,
                        'action': 'D',
                        'path': issue_node,
                        'color': ''
                    })
    
    print(f"📊 Issues procesados: {issues_procesados}")
    
    # 4. Combinar y ordenar cronológicamente
    all_entries = git_entries + issue_entries
    all_entries.sort(key=lambda x: x['timestamp'])
    
    # 5. Escribir archivo unificado
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in all_entries:
            if entry.get('color'):
                line = f"{entry['timestamp']}|{entry['author']}|{entry['action']}|{entry['path']}|{entry['color']}\n"
            else:
                line = f"{entry['timestamp']}|{entry['author']}|{entry['action']}|{entry['path']}\n"
            f.write(line)
    
    print(f"✅ Log unificado generado: '{output_file}'")
    print(f"   Entradas Git: {len(git_entries)}")
    print(f"   Entradas Issues: {len(issue_entries)}")
    print(f"   Total combinado: {len(all_entries)}")
    
    return all_entries


if __name__ == "__main__":
    print("=" * 60)
    print("GENERANDO ARCHIVOS GOURCE")
    print("=" * 60)
    
    # Versión simple
    print("\n📌 Versión Simple:")
    json_to_gource_log()
    
    # Versión detallada
    print("\n📌 Versión Detallada:")
    json_to_gource_detailed()
    
    # Versión UNIFICADA (merge con log de Git)
    print("\n📌 Versión Unificada (Git + Issues):")
    merge_logs()
    
    print("\n" + "=" * 60)
    print("✅ CONVERSIÓN COMPLETADA")
    print("=" * 60)
    print("\nPara visualizar con Gource:")
    print(f"  gource {REPO_NAME}_gource.log")
    print(f"  gource {REPO_NAME}_gource_detailed.log --file-idle-time 0")
    print(f"  gource {REPO_NAME}_merged.log --file-idle-time 0  <- RECOMENDADO")