#!/usr/bin/env python3
"""Suggest likely same-meaning memories from lightweight similarity heuristics."""

import argparse
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher

from memory_graph_common import (
    build_package_map,
    build_reverse_load_next,
    compact_text,
    is_active_memory,
    load_memory_packages,
)


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "before",
    "being",
    "between",
    "both",
    "but",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "later",
    "may",
    "more",
    "new",
    "not",
    "of",
    "on",
    "only",
    "or",
    "so",
    "still",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "too",
    "under",
    "use",
    "uses",
    "using",
    "was",
    "were",
    "when",
    "which",
    "while",
    "with",
}

SYNONYM_MAP = {
    "boundaries": "boundary",
    "boundary": "boundary",
    "candidate": "candidate",
    "candidates": "candidate",
    "curated": "curate",
    "curating": "curate",
    "curation": "curate",
    "curator": "curate",
    "dedupe": "duplicate",
    "deduped": "duplicate",
    "deduping": "duplicate",
    "described": "description",
    "describes": "description",
    "describing": "description",
    "descriptions": "description",
    "discover": "recall",
    "discovered": "recall",
    "discovering": "recall",
    "discovery": "recall",
    "duplicates": "duplicate",
    "duplicate": "duplicate",
    "files": "file",
    "graphs": "graph",
    "layered": "layer",
    "layering": "layer",
    "layers": "layer",
    "lookups": "recall",
    "lookup": "recall",
    "memories": "memory",
    "optimize": "optimize",
    "optimized": "optimize",
    "optimizer": "optimize",
    "optimizing": "optimize",
    "optimization": "optimize",
    "parentage": "parent",
    "parents": "parent",
    "recalled": "recall",
    "recalling": "recall",
    "recalls": "recall",
    "reflections": "reflect",
    "reflection": "reflect",
    "reflective": "reflect",
    "relateds": "related",
    "reparent": "parent",
    "reparenting": "parent",
    "routes": "route",
    "routing": "route",
    "search": "recall",
    "searches": "recall",
    "searching": "recall",
    "shortlisting": "shortlist",
    "shortlists": "shortlist",
    "similarity": "similar",
    "similarities": "similar",
    "symbols": "symbol",
    "superseded": "supersede",
    "supersedes": "supersede",
    "superseding": "supersede",
    "workflow": "workflow",
    "workflows": "workflow",
}

DETAIL_TOKEN_LIMIT = 80


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Shortlist likely same-meaning memories from descriptions and nearby "
            "metadata. Suggestion-only; does not merge or rewrite memory."
        )
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include superseded, incorrect, or tombstoned memories in candidate search.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of candidates to return. Defaults to 5.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.18,
        help="Minimum score threshold from 0.0 to 1.0. Defaults to 0.18.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--memory-id",
        help="Use an existing memory package as the query surface.",
    )
    group.add_argument(
        "--description",
        help="Use this free-text description as the query surface.",
    )
    parser.add_argument(
        "--name",
        help="Optional query name when using --description.",
    )
    parser.add_argument(
        "--details",
        help="Optional query details when using --description.",
    )
    parser.add_argument(
        "--pattern-key",
        help="Optional query pattern key when using --description.",
    )
    parser.add_argument(
        "--component",
        help="Optional query component when using --description.",
    )
    parser.add_argument(
        "--kind",
        help="Optional query kind when using --description.",
    )
    parser.add_argument(
        "--layer",
        help="Optional query layer when using --description.",
    )
    parser.add_argument(
        "--related-file",
        action="append",
        default=[],
        help="Optional related file hint. Repeat as needed.",
    )
    parser.add_argument(
        "--related-symbol",
        action="append",
        default=[],
        help="Optional related symbol hint. Repeat as needed.",
    )
    return parser.parse_args()


def dedupe(values):
    result = []
    seen = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        result.append(item)
        seen.add(item)
    return result


def split_identifier_text(text):
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return text.lower()


def canonicalize_token(token):
    token = SYNONYM_MAP.get(token, token)
    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    elif token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("ed") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("es") and len(token) > 4 and not token.endswith("ses"):
        token = token[:-2]
    elif token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
        token = token[:-1]
    token = SYNONYM_MAP.get(token, token)
    return token


def tokenize_text(text):
    tokens = []
    for raw in re.findall(r"[a-z0-9]+", split_identifier_text(text)):
        token = canonicalize_token(raw)
        if not token or token in STOPWORDS:
            continue
        if len(token) <= 1 and not token.isdigit():
            continue
        tokens.append(token)
    return tokens


def normalize_text(text):
    return compact_text(split_identifier_text(text))


def token_map():
    return defaultdict(float)


def add_weighted_tokens(weights, text, weight, token_limit=None):
    if not text or weight <= 0:
        return
    tokens = tokenize_text(text)
    if token_limit is not None:
        tokens = tokens[:token_limit]
    for token in tokens:
        if weight > weights[token]:
            weights[token] = weight


def build_surface(
    *,
    memory_id,
    name,
    description,
    details,
    pattern_key,
    component,
    kind,
    layer,
    related_files,
    related_symbols,
    tags,
    parents,
    path,
    status,
):
    description = compact_text(description or "")
    details = compact_text(details or "")
    weights = token_map()
    add_weighted_tokens(weights, memory_id, 1.6)
    add_weighted_tokens(weights, name, 1.4)
    add_weighted_tokens(weights, description, 3.0)
    add_weighted_tokens(weights, details, 1.0, token_limit=DETAIL_TOKEN_LIMIT)
    add_weighted_tokens(weights, pattern_key, 1.2)
    add_weighted_tokens(weights, " ".join(tags), 0.7)
    add_weighted_tokens(weights, component, 0.5)
    add_weighted_tokens(weights, kind, 0.5)
    add_weighted_tokens(weights, layer, 0.3)
    desc_tokens = tokenize_text(description)
    desc_bigrams = set(
        "{0} {1}".format(desc_tokens[index], desc_tokens[index + 1])
        for index in range(len(desc_tokens) - 1)
    )
    return {
        "id": memory_id,
        "name": name or memory_id,
        "description": description,
        "details": details,
        "pattern_key": pattern_key or "",
        "component": component or "",
        "kind": kind or "",
        "layer": layer or "",
        "related_files": dedupe(related_files),
        "related_symbols": dedupe(related_symbols),
        "tags": dedupe(tags),
        "parents": dedupe(parents),
        "path": path or "",
        "status": status or "",
        "weights": dict(weights),
        "description_tokens": desc_tokens,
        "description_bigrams": desc_bigrams,
        "normalized_description": normalize_text(description),
    }


def build_query_surface(args, package_map, reverse_map):
    if args.memory_id:
        package = package_map.get(args.memory_id)
        if package is None:
            raise SystemExit("Unknown --memory-id `{0}`.".format(args.memory_id))
        return (
            "memory-id",
            build_surface(
                memory_id=package["id"],
                name=package["name"],
                description=package["description"],
                details=package["details"],
                pattern_key=package["pattern_key"],
                component=package["component"],
                kind=package["kind"],
                layer=package["layer"],
                related_files=package["related_files"],
                related_symbols=package["related_symbols"],
                tags=package["tags"],
                parents=reverse_map.get(package["id"], []),
                path=package["path"],
                status=package["status"],
            ),
        )
    return (
        "description",
        build_surface(
            memory_id="(proposed-memory)",
            name=args.name or "proposed-memory",
            description=args.description,
            details=args.details or "",
            pattern_key=args.pattern_key or "",
            component=args.component or "",
            kind=args.kind or "",
            layer=args.layer or "",
            related_files=args.related_file,
            related_symbols=args.related_symbol,
            tags=[],
            parents=[],
            path="",
            status="proposed",
        ),
    )


def weighted_jaccard(left, right):
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    intersection = 0.0
    union = 0.0
    for key in keys:
        intersection += min(left.get(key, 0.0), right.get(key, 0.0))
        union += max(left.get(key, 0.0), right.get(key, 0.0))
    if union == 0:
        return 0.0
    return intersection / union


def set_jaccard(left, right):
    left = set(left)
    right = set(right)
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / float(len(union))


def score_candidate(query, candidate):
    token_score = weighted_jaccard(query["weights"], candidate["weights"])
    bigram_score = set_jaccard(
        query["description_bigrams"], candidate["description_bigrams"]
    )
    description_ratio = 0.0
    if query["normalized_description"] and candidate["normalized_description"]:
        description_ratio = SequenceMatcher(
            None,
            query["normalized_description"],
            candidate["normalized_description"],
        ).ratio()

    shared_files = sorted(
        set(query["related_files"]).intersection(candidate["related_files"])
    )
    shared_symbols = sorted(
        set(query["related_symbols"]).intersection(candidate["related_symbols"])
    )
    shared_parents = sorted(set(query["parents"]).intersection(candidate["parents"]))
    shared_terms = sorted(
        set(query["weights"]).intersection(candidate["weights"]),
        key=lambda token: min(query["weights"][token], candidate["weights"][token]),
        reverse=True,
    )
    shared_bigrams = sorted(
        set(query["description_bigrams"]).intersection(candidate["description_bigrams"])
    )

    pattern_key_match = (
        1.0
        if query["pattern_key"] and query["pattern_key"] == candidate["pattern_key"]
        else 0.0
    )
    component_match = (
        1.0
        if query["component"] and query["component"] == candidate["component"]
        else 0.0
    )
    kind_match = (
        1.0 if query["kind"] and query["kind"] == candidate["kind"] else 0.0
    )
    layer_match = (
        1.0 if query["layer"] and query["layer"] == candidate["layer"] else 0.0
    )
    related_file_bonus = min(1.0, len(shared_files) / 3.0)
    related_symbol_bonus = min(1.0, len(shared_symbols) / 3.0)
    parent_bonus = min(1.0, len(shared_parents) / 2.0)

    score = (
        0.46 * token_score
        + 0.14 * bigram_score
        + 0.16 * description_ratio
        + 0.08 * pattern_key_match
        + 0.05 * related_file_bonus
        + 0.03 * related_symbol_bonus
        + 0.03 * parent_bonus
        + 0.03 * component_match
        + 0.01 * kind_match
        + 0.01 * layer_match
    )
    sparse_semantic_match = (
        not pattern_key_match
        and bigram_score == 0.0
        and token_score < 0.12
        and description_ratio < 0.45
    )
    if sparse_semantic_match:
        score -= 0.07
    score = max(0.0, min(score, 1.0))

    reasons = []
    if pattern_key_match:
        reasons.append("exact `pattern_key` match")
    if shared_terms:
        reasons.append(
            "shared core terms: {0}".format(
                ", ".join("`{0}`".format(term) for term in shared_terms[:8])
            )
        )
    if shared_bigrams:
        reasons.append(
            "shared description phrases: {0}".format(
                ", ".join("`{0}`".format(item) for item in shared_bigrams[:4])
            )
        )
    if shared_files:
        reasons.append(
            "shared `related_files`: {0}".format(
                ", ".join("`{0}`".format(item) for item in shared_files[:5])
            )
        )
    if shared_symbols:
        reasons.append(
            "shared `related_symbols`: {0}".format(
                ", ".join("`{0}`".format(item) for item in shared_symbols[:5])
            )
        )
    if shared_parents:
        reasons.append(
            "shared reverse parents: {0}".format(
                ", ".join("`{0}`".format(item) for item in shared_parents[:4])
            )
        )
    if component_match:
        reasons.append("same `component`")
    if kind_match:
        reasons.append("same `kind`")
    if layer_match:
        reasons.append("same `layer`")

    return {
        "score": score,
        "token_score": token_score,
        "bigram_score": bigram_score,
        "description_ratio": description_ratio,
        "shared_terms": shared_terms,
        "shared_bigrams": shared_bigrams,
        "shared_related_files": shared_files,
        "shared_related_symbols": shared_symbols,
        "shared_parents": shared_parents,
        "reasons": reasons,
    }


def candidate_entry(query, candidate, metrics, query_type):
    next_step = None
    if query_type == "memory-id":
        next_step = (
            "python3 skills/zero-memory-curator/scripts/scaffold_missed_recall_reflection.py "
            "--root .zero-memory/memory --daily-root .zero-memory/daily "
            "--new-memory-id {0} --existing-memory-id {1} "
            "--discovery-source semantic-shortlist"
        ).format(query["id"], candidate["id"])
    return {
        "id": candidate["id"],
        "name": candidate["name"],
        "description": candidate["description"],
        "pattern_key": candidate["pattern_key"],
        "component": candidate["component"],
        "kind": candidate["kind"],
        "layer": candidate["layer"],
        "status": candidate["status"],
        "path": candidate["path"],
        "score": round(metrics["score"], 4),
        "token_score": round(metrics["token_score"], 4),
        "bigram_score": round(metrics["bigram_score"], 4),
        "description_ratio": round(metrics["description_ratio"], 4),
        "shared_terms": metrics["shared_terms"][:8],
        "shared_bigrams": metrics["shared_bigrams"][:4],
        "shared_related_files": metrics["shared_related_files"][:5],
        "shared_related_symbols": metrics["shared_related_symbols"][:5],
        "shared_parents": metrics["shared_parents"][:4],
        "reasons": metrics["reasons"],
        "suggested_next_step": next_step,
    }


def render_markdown(result):
    query = result["query"]
    lines = [
        "# Similar Memory Shortlist",
        "",
        "- Root: `{0}`".format(result["root"]),
        "- Query Type: `{0}`".format(result["query_type"]),
        "- Include Inactive: `{0}`".format(
            "yes" if result["include_inactive"] else "no"
        ),
        "- Limit: {0}".format(result["limit"]),
        "- Minimum Score: {0:.2f}".format(result["min_score"]),
        "- Candidate Count: {0}".format(result["count"]),
        "- Note: heuristic shortlist only; review manually before merge, re-parent, or supersede.",
        "",
        "## Query",
        "",
        "- ID: `{0}`".format(query["id"]),
        "- Name: `{0}`".format(query["name"]),
        "- Description: {0}".format(query["description"] or "(missing)"),
    ]
    if query["pattern_key"]:
        lines.append("- Pattern Key: `{0}`".format(query["pattern_key"]))
    if query["component"]:
        lines.append("- Component: `{0}`".format(query["component"]))
    if query["kind"]:
        lines.append("- Kind: `{0}`".format(query["kind"]))
    if query["layer"]:
        lines.append("- Layer: `{0}`".format(query["layer"]))
    if query["related_files"]:
        lines.append(
            "- Related Files: {0}".format(
                ", ".join("`{0}`".format(item) for item in query["related_files"])
            )
        )
    if query["related_symbols"]:
        lines.append(
            "- Related Symbols: {0}".format(
                ", ".join("`{0}`".format(item) for item in query["related_symbols"])
            )
        )
    lines.append("")

    if not result["candidates"]:
        lines.extend(["No likely same-meaning memories met the current threshold.", ""])
        return "\n".join(lines)

    lines.extend(["## Candidates", ""])
    for index, candidate in enumerate(result["candidates"], start=1):
        lines.append("### {0}. {1}".format(index, candidate["id"]))
        lines.append("")
        lines.append("- Score: {0:.3f}".format(candidate["score"]))
        lines.append(
            "- Score Breakdown: token={0:.3f}, bigram={1:.3f}, description={2:.3f}".format(
                candidate["token_score"],
                candidate["bigram_score"],
                candidate["description_ratio"],
            )
        )
        lines.append("- Description: {0}".format(candidate["description"] or "(missing)"))
        lines.append("- Status/Layer: `{0}` / `{1}`".format(candidate["status"], candidate["layer"]))
        if candidate["pattern_key"]:
            lines.append("- Pattern Key: `{0}`".format(candidate["pattern_key"]))
        if candidate["reasons"]:
            for reason in candidate["reasons"]:
                lines.append("- Signal: {0}".format(reason))
        if candidate["suggested_next_step"]:
            lines.append(
                "- Suggested Next Step: `{0}`".format(
                    candidate["suggested_next_step"]
                )
            )
        lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    packages, duplicate_ids = load_memory_packages(args.root)
    if duplicate_ids:
        raise SystemExit(
            "Memory graph has duplicate IDs; resolve them before running semantic shortlist."
        )
    package_map = build_package_map(packages)
    reverse_map = build_reverse_load_next(package_map, include_inactive=True)
    query_type, query = build_query_surface(args, package_map, reverse_map)

    candidates = []
    for package in packages:
        if not args.include_inactive and not is_active_memory(package):
            continue
        if query_type == "memory-id" and package["id"] == query["id"]:
            continue
        candidate = build_surface(
            memory_id=package["id"],
            name=package["name"],
            description=package["description"],
            details=package["details"],
            pattern_key=package["pattern_key"],
            component=package["component"],
            kind=package["kind"],
            layer=package["layer"],
            related_files=package["related_files"],
            related_symbols=package["related_symbols"],
            tags=package["tags"],
            parents=reverse_map.get(package["id"], []),
            path=package["path"],
            status=package["status"],
        )
        metrics = score_candidate(query, candidate)
        if metrics["score"] < args.min_score:
            continue
        candidates.append(candidate_entry(query, candidate, metrics, query_type))

    candidates.sort(
        key=lambda item: (
            -item["score"],
            -item["token_score"],
            -item["description_ratio"],
            item["id"],
        )
    )
    candidates = candidates[: max(args.limit, 0)]

    result = {
        "root": args.root,
        "query_type": query_type,
        "include_inactive": args.include_inactive,
        "limit": args.limit,
        "min_score": args.min_score,
        "count": len(candidates),
        "query": {
            "id": query["id"],
            "name": query["name"],
            "description": query["description"],
            "pattern_key": query["pattern_key"],
            "component": query["component"],
            "kind": query["kind"],
            "layer": query["layer"],
            "related_files": query["related_files"],
            "related_symbols": query["related_symbols"],
        },
        "candidates": candidates,
    }

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
