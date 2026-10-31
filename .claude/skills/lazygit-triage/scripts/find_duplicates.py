#!/usr/bin/env python3
"""Rank earlier issues by text similarity to a new issue (TF-IDF cosine).

Usage:
    # search a saved index, only issues created before the cutoff
    python3 find_duplicates.py --issue-file issue.json \
        --index issue-index.json --before 2026-04-10T08:00:00Z [--top 5]

    # build the index from a live repo (run by the workflow pre-step, not the agent)
    python3 find_duplicates.py --build-index --repo owner/name --out issue-index.json

issue.json: {"number": N, "title": "...", "body": "..."}
index:      [{"number", "title", "body", "created_at", "state"}, ...]

Prints a JSON list of the top-k candidates with a score in [0, 1]. This only
ranks; whether a candidate is really the same root symptom is the model's
judgement (see SKILL.md step 5).
"""
import argparse
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*[a-z0-9]|[a-z0-9]")
BODY_EXCERPT = 2000  # characters kept per indexed issue
# Words in every issue template; they carry no signal for similarity.
STOPWORDS = set("""
a an and are as at be but by can do does for from has have i if in into is it
its me my no not of on or so that the this to was were when which will with
you your lazygit git bug describe expected behavior behaviour steps reproduce
version os additional context screenshots go click see error what happened
""".split())


def tokenize(text):
    return [t for t in TOKEN_RE.findall((text or "").lower()) if t not in STOPWORDS]


def tfidf_vectors(docs):
    """docs: list of token lists -> list of {term: weight} (L2-normalised)."""
    df = Counter(term for doc in docs for term in set(doc))
    n = len(docs)
    vectors = []
    for doc in docs:
        tf = Counter(doc)
        vec = {t: c * (math.log((1 + n) / (1 + df[t])) + 1) for t, c in tf.items()}
        norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
        vectors.append({t: w / norm for t, w in vec.items()})
    return vectors


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(t, 0.0) for t, w in a.items())


def rank(issue, index, before, top=5):
    """Top candidates from index created strictly before `before` (ISO string)."""
    pool = [i for i in index
            if i["created_at"] < before and i["number"] != issue.get("number")]
    if not pool:
        return []
    # Title counted twice: titles are short and the most specific part.
    def text(i):
        return f"{i['title']} {i['title']} {i.get('body') or ''}"
    vectors = tfidf_vectors([tokenize(text(issue))] + [tokenize(text(i)) for i in pool])
    query, rest = vectors[0], vectors[1:]
    scored = sorted(zip(pool, rest), key=lambda p: cosine(query, p[1]), reverse=True)
    return [{"number": i["number"], "title": i["title"], "state": i.get("state"),
             "created_at": i["created_at"], "score": round(cosine(query, v), 3)}
            for i, v in scored[:top]]


def build_index(repo):
    """All issues (not PRs) of repo via `gh api --paginate`. Needs gh + token."""
    out = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", f"repos/{repo}/issues?state=all&per_page=100"],
        capture_output=True, text=True, encoding="utf-8", check=True).stdout
    # --slurp wraps the pages in one outer array: [[page1...], [page2...]].
    issues = [i for page in json.loads(out) for i in page]
    return [{"number": i["number"], "title": i["title"],
             "body": (i.get("body") or "")[:BODY_EXCERPT],
             "created_at": i["created_at"], "state": i["state"]}
            for i in issues if "pull_request" not in i]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-file")
    parser.add_argument("--index")
    parser.add_argument("--before")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--repo")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.build_index:
        if not (args.repo and args.out):
            parser.error("--build-index needs --repo and --out")
        Path(args.out).write_text(json.dumps(build_index(args.repo)), encoding="utf-8")
        return 0

    if not (args.issue_file and args.index and args.before):
        parser.error("search needs --issue-file, --index and --before")
    issue = json.loads(Path(args.issue_file).read_text(encoding="utf-8"))
    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    print(json.dumps(rank(issue, index, args.before, args.top), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
