import argparse
import ast
import os
from pathlib import Path


def _load_token() -> str | None:
    token_file = Path(__file__).parent / "token.txt"
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
        if token and not token.startswith("ghp_TuToken"): 
            return token
    return os.environ.get("GITHUB_TOKEN")

from common import load_cfg, read_json
from evaluate import evaluate
from fetch_issues import fetch
from git_log import mine
from link import build_links, load_links, save_links
from render import render
from transformer import transform


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("step", choices=["all", "fetch", "gitlog", "link", "transform", "eval", "render"])
    ap.add_argument("repo", help="clave del bloque [repos.<clave>] en repos.toml")
    ap.add_argument("--refresh", action="store_true", help="ignora la caché y vuelve a descargar")
    ap.add_argument("--tiers", default="explicit,pr,heuristic", help="niveles de enlace a usar")
    ap.add_argument("--preview", action="store_true", help="abre Gource en ventana en vez de video")
    ap.add_argument("--set", action="append", default=[], metavar="CLAVE=VALOR",
                    help="sobrescribe un parámetro de repos.toml (p. ej. --set tau=0.3 --set depth=3)")
    a = ap.parse_args()

    cfg = load_cfg(a.repo)
    for kv in a.set:
        k, v = kv.split("=", 1)
        try:
            cfg[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            cfg[k] = v
    d = cfg["data"]
    steps = ["fetch", "gitlog", "link", "transform", "eval", "render"] if a.step == "all" else [a.step]

    for s in steps:
        if s == "fetch":
            fetch(cfg, _load_token(), a.refresh)
        elif s == "gitlog":
            mine(cfg, a.refresh)
        else:
            issues = read_json(d / "issues.json")["issues"]
            commits = read_json(d / "commits.json")["commits"]
            if s == "link":
                links = build_links(cfg, issues, commits, tuple(a.tiers.split(",")))
                save_links(cfg["out"] / "links.csv", links)
                n = {t: sum(1 for l in links if l["tier"] == t) for t in ("explicit", "pr", "heuristic")}
                print(f"[link] {len(links)} enlaces {n} -> {cfg['out'] / 'links.csv'}")
                continue
            if s == "render":
                render(cfg, a.preview)
                continue
            links = load_links(cfg["out"] / "links.csv")
            (transform if s == "transform" else evaluate)(cfg, issues, commits, links)


if __name__ == "__main__":
    main()
