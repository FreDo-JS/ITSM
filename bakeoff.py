# ai-generated: 85% - Claude Code implemented CI-SPEC.md section 3 (P-14..P-22) and checked it against the practice expected.json; I reviewed the rules
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-23).

    python3 bakeoff.py --labels labels.json a.sarif b.sarif > bakeoff.json

Standard library only: it runs as `python3 -S -E bakeoff.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import unquote

CLASS_CWES = {
    "secret": {259, 260, 321, 798},
    "injection": {74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336},
    "deserialization": {502},
    "weak-crypto": {261, 326, 327, 328, 330, 331, 338, 759, 760, 916},
    "insecure-transport": {295, 297, 319, 322, 757},
    "path-traversal": {22, 23, 35, 36, 73},
    "ssrf": {918},
    "vulnerable-dependency": {937, 1035, 1104, 1395},
    "misconfiguration": {16, 215, 250, 489, 668, 732, 1188},
    "access-control": {284, 285, 639, 862, 863},
}

FIXED_TOOLS = {"trivy", "grype", "osv-scanner", "gitleaks"}
SEMGREP_NAMES = {"semgrep", "semgrep oss", "semgrep ce", "semgrep community edition", "semgrep pro"}
CWE_RE = re.compile(r"(?<![A-Za-z0-9])CWE-([0-9]+)", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+")


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value) -> list:
    return value if isinstance(value, list) else []


def tool_id(run: dict) -> str:
    name = _dict(_dict(run.get("tool")).get("driver")).get("name")
    if not isinstance(name, str):
        return "unknown"
    lowered = name.strip().lower()
    if lowered in FIXED_TOOLS:
        return lowered
    if lowered in SEMGREP_NAMES:
        return "semgrep"
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "unknown"


def _is_int(value) -> bool:
    return type(value) is int


def result_path(uri: str) -> str:
    path = unquote(uri)
    if path[:7].lower() == "file://":
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]
    return path


def in_set_file(path: str, root: str) -> str | None:
    parts = path.split("/")
    if root not in parts:
        return None
    last = len(parts) - 1 - parts[::-1].index(root)
    return "/".join(parts[last:])


def result_lines(physical: dict) -> tuple[int | None, int | None]:
    region = _dict(physical.get("region"))
    start = region.get("startLine")
    if not _is_int(start) or start < 1:
        return None, None
    end = region.get("endLine")
    if not _is_int(end) or end < start:
        end = start
    return start, end


def string_tags(holder: dict) -> list[str]:
    return [t for t in _list(_dict(holder.get("properties")).get("tags")) if isinstance(t, str)]


def find_rule(run: dict, rule_id) -> dict:
    if not isinstance(rule_id, str):
        return {}
    for rule in _list(_dict(_dict(run.get("tool")).get("driver")).get("rules")):
        if isinstance(rule, dict) and rule.get("id") == rule_id:
            return rule
    return {}


def result_classes(tool: str, run: dict, result: dict) -> set[str]:
    own = _dict(result.get("properties")).get("class")
    if isinstance(own, str) and own in CLASS_CWES:
        return {own}
    rule = find_rule(run, result.get("ruleId"))
    if tool == "gitleaks":
        return {"secret"}
    if tool in ("grype", "osv-scanner"):
        return {"vulnerable-dependency"}
    if tool == "trivy":
        mapped = {"vulnerability": "vulnerable-dependency", "secret": "secret", "misconfiguration": "misconfiguration"}
        found = {mapped[t.lower()] for t in string_tags(rule) if t.lower() in mapped}
        if found:
            return found
    classes: set[str] = set()
    for tag in string_tags(result) + string_tags(rule):
        for match in CWE_RE.finditer(tag):
            number = int(match.group(1))
            classes.update(name for name, cwes in CLASS_CWES.items() if number in cwes)
    return classes


def pep503(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.lower())


def names_package(result: dict, package: str) -> bool:
    text = _dict(result.get("message")).get("text")
    if not isinstance(text, str):
        return False
    wanted = pep503(package)
    for token in TOKEN_RE.findall(text):
        token = token.strip("._-")
        if token and pep503(token) == wanted:
            return True
    return False


def matches(result: dict, defect: dict) -> bool:
    if result["file"] != defect.get("file") or defect.get("class") not in result["classes"]:
        return False
    if defect["class"] == "vulnerable-dependency":
        return names_package(result["raw"], str(defect.get("package", "")))
    if result["start"] is None:
        return False
    return result["start"] <= defect["end_line"] and defect["start_line"] <= result["end"]


def collect(labels: dict, documents: list) -> dict[str, list[dict]]:
    root = labels["set"]
    tools: dict[str, list[dict]] = {}
    for document in documents:
        for run in _list(_dict(document).get("runs")):
            if not isinstance(run, dict):
                continue
            tool = tool_id(run)
            bucket = tools.setdefault(tool, [])
            for result in _list(run.get("results")):
                if not isinstance(result, dict):
                    continue
                kind = result.get("kind")
                if kind is not None and kind != "fail":
                    continue
                if result.get("suppressions"):
                    continue
                locations = _list(result.get("locations"))
                if not locations:
                    continue
                physical = _dict(_dict(locations[0]).get("physicalLocation"))
                uri = _dict(physical.get("artifactLocation")).get("uri")
                if not isinstance(uri, str) or not uri:
                    continue
                file = in_set_file(result_path(uri), root)
                if file is None:
                    continue
                start, end = result_lines(physical)
                rule_id = result.get("ruleId")
                bucket.append({
                    "file": file,
                    "start": start,
                    "end": end,
                    "rule": rule_id if isinstance(rule_id, str) else None,
                    "classes": result_classes(tool, run, result),
                    "raw": result,
                })
    return tools


def _ratio(numerator: int, denominator: int):
    return round(numerator / denominator, 4) if denominator else None


def confusion_matrix(labels: dict, sarif_documents: list) -> dict:
    defects = labels["defects"]
    tools: dict[str, dict] = {}
    for tool, results in collect(labels, sarif_documents).items():
        found: set[int] = set()
        false_positives: set[tuple] = set()
        for result in results:
            hit = False
            for index, defect in enumerate(defects):
                if matches(result, defect):
                    found.add(index)
                    hit = True
            if not hit:
                false_positives.add((result["rule"], result["file"], result["start"], result["end"]))
        tp, fp = len(found), len(false_positives)
        fn = len(defects) - tp
        tools[tool] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": _ratio(tp, tp + fp),
            "recall": _ratio(tp, tp + fn),
            "f1": _ratio(2 * tp, 2 * tp + fp + fn),
        }
    return {"set": labels["set"], "defects": len(defects), "tools": tools}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    with open(args.labels, encoding="utf-8-sig") as fh:
        labels = json.load(fh)
    documents = []
    for path in args.sarif:
        with open(path, encoding="utf-8-sig") as fh:
            documents.append(json.load(fh))
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
