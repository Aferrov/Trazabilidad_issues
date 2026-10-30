
import bisect
import csv
import math
import re
from collections import Counter

from common import iso_to_ts

KW = r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"
REF = re.compile(r"(?<![\w/])#(\d+)")                  # "#123" (no "owner/repo#123")
TOK = re.compile(r"[A-Za-z][A-Za-z0-9]+")
STOP = set("""the and for with this that from not are was were has have had but you your can
will would should could into when then than there their them its our out all any via use used
using fix fixes fixed close closes closed resolve resolves resolved issue issues pull request
merge branch commit add adds added update updates updated""".split())
STRONG = ("event:closed", "msg:closing")               


def tokens(text):
    text = re.sub(r"https?://\S+|#\d+", " ", text)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)  
    return [t for t in (w.lower() for w in TOK.findall(text)) if t not in STOP and len(t) > 2]


def refs(msg):
    for m in REF.finditer(msg):
        yield int(m.group(1)), bool(re.search(KW + r"[:\s]+$", msg[:m.start()], re.I))


class Corpus:

    def __init__(self, commits):
        self.commits = [c for c in commits if len(c["parents"]) < 2]
        self.ts = [c["ts"] for c in self.commits]       # ya ordenados de antiguo a nuevo
        docs = [Counter(tokens(c["msg"] + " " + " ".join(p for _, p in c["files"])))
                for c in self.commits]
        df = Counter(t for d in docs for t in d)
        n = len(docs)
        self.idf = {t: math.log((n + 1) / (k + 1)) + 1 for t, k in df.items()}
        self.vecs = [self._vec(d) for d in docs]

    def _vec(self, counter):
        w = {t: (1 + math.log(f)) * self.idf[t] for t, f in counter.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in w.values())) or 1.0
        return {t: v / norm for t, v in w.items()}

    def rank(self, issue, grace_days):
        lo = iso_to_ts(issue["created_at"])
        hi = iso_to_ts(issue["closed_at"]) + grace_days * 86400
        i0, i1 = bisect.bisect_left(self.ts, lo), bisect.bisect_right(self.ts, hi)
        q = self._vec(Counter(tokens(issue["title"] + " " + issue["body"])))
        out = []
        for i in range(i0, i1):
            v = self.vecs[i]
            small, big = (q, v) if len(q) < len(v) else (v, q)
            out.append((sum(w * big.get(t, 0.0) for t, w in small.items()), self.commits[i]["sha"]))
        out.sort(reverse=True)
        return out


def _add(links, issue, sha, tier, reason, score):
    links.setdefault((issue, sha), {"issue": issue, "sha": sha, "tier": tier,
                                    "reason": reason, "score": score})


def explicit_links(issues, commits):
    shas = {c["sha"] for c in commits}
    nums = {i["number"] for i in issues if not i["is_pr"]}
    links = {}
    for i in issues:
        if i["is_pr"]:
            continue
        for ev in i["events"]:
            if ev["event"] in ("closed", "referenced") and ev["commit_id"] in shas:
                _add(links, i["number"], ev["commit_id"], "explicit", "event:" + ev["event"], 1.0)
    for c in commits:
        for n, closing in refs(c["msg"]):
            if n in nums:
                _add(links, n, c["sha"], "explicit", "msg:closing" if closing else "msg:mention", 1.0)
    return links


def pr_links(issues, commits):
    by_pr = {}
    for c in commits:
        if c["pr"]:
            by_pr.setdefault(c["pr"], []).append(c["sha"])
            by_pr[c["pr"]].extend(c.get("merged", []))
    links = {}
    for i in issues:
        if i["is_pr"]:
            continue
        prs = {t["source_number"] for t in i["timeline"]
               if t["event"] == "cross-referenced" and t["source_is_pr"]}
        for n in prs:
            for sha in by_pr.get(n, []):
                _add(links, i["number"], sha, "pr", f"pr#{n}", 0.9)
    return links


def heuristic_links(issues, corpus, cfg, only=None):
    links = {}
    for i in issues:
        if i["is_pr"] or not i["closed_at"] or (only is not None and i["number"] not in only):
            continue
        for score, sha in corpus.rank(i, cfg["grace_days"])[:cfg["top_k"]]:
            if score >= cfg["tau"]:
                _add(links, i["number"], sha, "heuristic", "tfidf+ventana", round(score, 4))
    return links


def build_links(cfg, issues, commits, tiers=("explicit", "pr", "heuristic")):
    links = {}
    if "explicit" in tiers:
        links.update(explicit_links(issues, commits))
    if "pr" in tiers:
        for k, v in pr_links(issues, commits).items():
            links.setdefault(k, v)
    if "heuristic" in tiers:
        linked = {k[0] for k in links}
        for k, v in heuristic_links(issues, Corpus(commits), cfg, only=None).items():
            if k[0] not in linked:                       # solo issues aún sin enlaces
                links.setdefault(k, v)
    return list(links.values())


def save_links(path, links):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["issue", "sha", "tier", "reason", "score"])
        w.writeheader()
        w.writerows(sorted(links, key=lambda l: (l["issue"], l["tier"], l["sha"])))


def load_links(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [{**r, "issue": int(r["issue"]), "score": float(r["score"])} for r in csv.DictReader(f)]
