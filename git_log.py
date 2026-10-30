"""Paso 2: minería del historial con un clon local de Git -> data/<repo>/commits.json

Se usa un clon *bare* y parcial (sin blobs): solo trae el historial, por lo que es liviano.
Por defecto incluye TODAS las ramas locales (--all); se puede limitar con branches en repos.toml.
"""
import re
import subprocess

from common import write_json

REC, FLD = "\x1e", "\x1f"
PRETTY = "%x1e%H%x1f%at%x1f%an%x1f%ae%x1f%P%x1f%B%x1f"
PR_MERGE = re.compile(r"^Merge pull request #(\d+)")     # merge clásico de GitHub
PR_SQUASH = re.compile(r"\(#(\d+)\)\s*$")                # squash merge: "título (#123)"


def git(repo, *args):
    r = subprocess.run(["git", "-c", "core.quotepath=false", "-c", "safe.directory=*", "-C", str(repo), *args],
                       check=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout


def ensure_clone(cfg, refresh=False):
    d = cfg["data"] / "repo.git"
    if not d.exists():
        url = f"https://github.com/{cfg['full_name']}.git"
        subprocess.run(["git", "clone", "--bare", "--filter=blob:none", url, str(d)], check=True)
    elif refresh:
        git(d, "fetch", "origin", "+refs/heads/*:refs/heads/*")
    return d


def mine(cfg, refresh=False):
    d = ensure_clone(cfg, refresh)

    # Determinar qué ramas incluir (todas por defecto, o lista explícita en repos.toml)
    branches_cfg = cfg.get("branches")  # None = todas
    if branches_cfg:
        refs = branches_cfg if isinstance(branches_cfg, list) else [branches_cfg]
    else:
        # Todas las ramas locales del clon
        refs_raw = git(d, "branch", "--format=%(refname:short)").splitlines()
        refs = [r.strip() for r in refs_raw if r.strip()]

    base_args = ["--no-renames", "--name-status", "--pretty=format:" + PRETTY]
    if cfg.get("since"):
        base_args.append(f"--since={cfg['since']}")
    if cfg.get("until"):
        base_args.append(f"--until={cfg['until']}")

    seen = set()          # deduplicar por SHA (commits compartidos entre ramas)
    commits = []
    for ref in refs:
        out = git(d, "log", ref, *base_args)
        for rec in out.split(REC)[1:]:
            sha, at, name, email, parents, msg, tail = rec.split(FLD, 6)
            if sha in seen:
                continue
            seen.add(sha)
            files = []
            for line in tail.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    files.append([parts[0][0], parts[-1]])    # (estado, ruta); sin renombrados
            msg = msg.strip()
            subject = msg.split("\n", 1)[0]
            m = PR_MERGE.match(subject) or PR_SQUASH.search(subject)
            c = {"sha": sha, "ts": int(at), "author": name, "email": email,
                 "parents": parents.split(), "msg": msg, "files": files,
                 "pr": int(m.group(1)) if m else None, "branch": ref}
            if len(c["parents"]) == 2 and c["pr"]:            # merge de PR: trae sus commits
                c["merged"] = git(d, "rev-list", f"{c['parents'][0]}..{c['parents'][1]}").split()[:500]
            commits.append(c)
    commits.sort(key=lambda c: c["ts"])                       # del más antiguo al más nuevo

    head = git(d, "rev-parse", "HEAD").strip()
    write_json(cfg["data"] / "commits.json",
               {"meta": {"repo": cfg["full_name"], "head": head,
                         "branches": refs, "n": len(commits)},
                "commits": commits})
    print(f"[gitlog] {len(commits)} commits en {len(refs)} rama(s) {refs} -> {cfg['data'] / 'commits.json'}")
    return commits
