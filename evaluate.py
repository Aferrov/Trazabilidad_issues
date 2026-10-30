"""Paso 5: evaluación formal de la recuperación de trazabilidad (I-RT) -> out/<repo>/eval.json

1) Cobertura (TRR): % de issues cerrados con al menos un commit enlazado, por nivel acumulado.
2) Corrección con verdad de referencia *oculta*: los enlaces explícitos fuertes (evento "closed"
   con commit, o "fixes #N" en el mensaje) son la verdad. Para no evaluar de forma circular, el
   texto se sanea (se quitan "#N" y palabras clave) y se mide si la heurística los recupera.
   Se compara contra un baseline de solo ventana temporal (Kondo et al.).
Limitación: un commit propuesto que no está en la verdad puede ser correcto pero sin etiquetar,
así que la precisión es una cota inferior.
"""
from collections import defaultdict

from common import write_json
from link import STRONG, Corpus


def trr(issues, links, tiers):
    closed = [i for i in issues if not i["is_pr"] and i["state"] == "closed"]
    linked = {l["issue"] for l in links if l["tier"] in tiers}
    n = sum(1 for i in closed if i["number"] in linked)
    return {"closed_issues": len(closed), "linked": n,
            "TRR": round(100 * n / len(closed), 2) if closed else None}


def ground_truth(links, commits):
    by_sha = {c["sha"]: c for c in commits}
    truth = defaultdict(set)
    for l in links:
        c = by_sha.get(l["sha"])
        if l["reason"] in STRONG and c:
            truth[l["issue"]] |= set(c["merged"]) if c.get("merged") else {c["sha"]}
    return truth


def holdout(cfg, issues, commits, links):
    corpus = Corpus(commits)
    in_corpus = {c["sha"] for c in corpus.commits}
    truth = {k: v & in_corpus for k, v in ground_truth(links, commits).items()}
    rows = []
    for i in issues:
        gt = truth.get(i["number"])
        if i["is_pr"] or not i["closed_at"] or not gt:
            continue
        ranked = corpus.rank(i, cfg["grace_days"])
        window = {s for _, s in ranked}
        pred = {s for sc, s in ranked[:cfg["top_k"]] if sc >= cfg["tau"]}
        first = next((r for r, (_, s) in enumerate(ranked, 1) if s in gt), None)
        rows.append({
            "win_recall": len(gt & window) / len(gt),
            "win_prec": len(gt & window) / len(window) if window else 0.0,
            "hit1": float(first == 1), "hit3": float(first is not None and first <= 3),
            "mrr": 1 / first if first else 0.0,
            "has_pred": bool(pred),
            "prec": len(pred & gt) / len(pred) if pred else 0.0,
            "rec": len(pred & gt) / len(gt)})
    if not rows:
        return {"n_issues": 0}
    avg = lambda k, rs=rows: round(sum(r[k] for r in rs) / len(rs), 4) if rs else 0.0
    with_pred = [r for r in rows if r["has_pred"]]
    p, r = avg("prec", with_pred), avg("rec")
    return {"n_issues": len(rows),
            "ventana_sola": {"recall": avg("win_recall"), "precision": avg("win_prec")},
            "texto_en_ventana": {"hit@1": avg("hit1"), "hit@3": avg("hit3"), "MRR": avg("mrr"),
                                 "precision": p, "recall": r,
                                 "F1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
                                 "issues_con_propuesta": round(len(with_pred) / len(rows), 4)}}


def evaluate(cfg, issues, commits, links):
    res = {"repo": cfg["full_name"], "tau": cfg["tau"], "top_k": cfg["top_k"],
           "grace_days": cfg["grace_days"],
           "TRR": {"explicit": trr(issues, links, {"explicit"}),
                   "explicit+pr": trr(issues, links, {"explicit", "pr"}),
                   "explicit+pr+heuristic": trr(issues, links, {"explicit", "pr", "heuristic"})},
           "holdout": holdout(cfg, issues, commits, links)}
    write_json(cfg["out"] / "eval.json", res)
    print(f"[eval] {cfg['full_name']}")
    for k, v in res["TRR"].items():
        print(f"   TRR {k:<22} {v['TRR']}%  ({v['linked']}/{v['closed_issues']} issues cerrados)")
    h = res["holdout"]
    if h["n_issues"]:
        print(f"   Holdout sobre {h['n_issues']} issues con verdad de referencia:")
        print(f"     ventana sola   : {h['ventana_sola']}")
        print(f"     texto+ventana  : {h['texto_en_ventana']}")
    else:
        print("   (sin issues con verdad de referencia fuerte: no se puede evaluar el holdout)")
    return res
