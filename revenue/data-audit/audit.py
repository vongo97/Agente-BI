#!/usr/bin/env python3
"""data-audit — a single-file CSV quality auditor.

No third-party dependencies. Reads a CSV, profiles every column, detects the
usual data-quality problems (missing values, duplicates, mixed types, outliers,
PII, whitespace, constant/empty columns) and writes a self-contained HTML
report you can send to a client.

Usage:
    python audit.py data.csv
    python audit.py data.csv -o report.html --title "Q3 Marketing Data"
    python audit.py data.csv --json > summary.json
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

MISSING = {"", "na", "n/a", "null", "none", "nan", "-", "—", "n/a"}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[\d\s().-]{7,}$")
CARD_RE = re.compile(r"^\d{13,19}$")
SSN_RE = re.compile(r"^\d{3}-\d{2}-\d{4}$")
INT_RE = re.compile(r"^[+-]?\d+$")

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)

PII_HINTS = {
    "email": "email",
    "e-mail": "email",
    "correo": "email",
    "phone": "phone",
    "telefono": "phone",
    "teléfono": "phone",
    "mobile": "phone",
    "ssn": "ssn",
    "social security": "ssn",
    "card": "card",
    "credit card": "card",
    "tarjeta": "card",
    "iban": "iban",
    "passport": "passport",
    "dni": "dni",
    "address": "address",
    "direccion": "address",
    "dirección": "address",
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


# --------------------------------------------------------------------------- #
# parsing helpers
# --------------------------------------------------------------------------- #
def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - latin-1 always decodes
        text = raw.decode("latin-1", errors="replace")

    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    rows = [{(k or "").strip(): (v or "") for k, v in row.items()} for row in reader]
    fields = [f.strip() for f in (reader.fieldnames or []) if f and f.strip()]
    return fields, rows


def to_number(value: str) -> float | None:
    s = value.strip().replace(" ", "")
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = s.replace("$", "").replace("€", "").replace("£", "").replace("%", "")
    s = s.replace(",", "")
    try:
        number = float(s)
    except ValueError:
        return None
    return -number if negative else number


def looks_like_date(value: str) -> bool:
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def infer_type(values: list[str]) -> str:
    if not values:
        return "empty"
    lowered = {v.strip().lower() for v in values}
    if lowered <= {"true", "false", "yes", "no", "y", "n", "si", "sí"}:
        return "boolean"
    if all(INT_RE.match(v.strip()) for v in values):
        return "integer"
    numeric = sum(1 for v in values if to_number(v) is not None)
    if numeric == len(values):
        return "number"
    if all(looks_like_date(v) for v in values):
        return "date"
    return "text"


def detect_pii(column: str, values: list[str]) -> str | None:
    name = column.strip().lower()
    for hint, kind in PII_HINTS.items():
        if hint in name:
            return kind
    sample = [v.strip() for v in values[:500] if v.strip()]
    if not sample:
        return None
    checks = {
        "email": lambda v: bool(EMAIL_RE.match(v)),
        "ssn": lambda v: bool(SSN_RE.match(v)),
        "card": lambda v: bool(CARD_RE.match(v.replace(" ", "").replace("-", ""))),
        "phone": lambda v: bool(PHONE_RE.match(v)) and sum(c.isdigit() for c in v) >= 7,
    }
    for kind, check in checks.items():
        hits = sum(1 for v in sample if check(v))
        if hits / len(sample) >= 0.8:
            return kind
    return None


# --------------------------------------------------------------------------- #
# profiling
# --------------------------------------------------------------------------- #
def profile_column(name: str, values: list[str]) -> dict:
    total = len(values)
    cleaned = [v.strip() for v in values]
    missing = sum(1 for v in cleaned if v.lower() in MISSING)
    present = [v for v in cleaned if v.lower() not in MISSING]
    distinct = len(set(present))
    ctype = infer_type(present)

    profile = {
        "name": name,
        "type": ctype,
        "total": total,
        "missing": missing,
        "missing_pct": round(100 * missing / total, 1) if total else 0.0,
        "distinct": distinct,
        "distinct_pct": round(100 * distinct / len(present), 1) if present else 0.0,
        "pii": detect_pii(name, present),
        "whitespace": sum(1 for v in values if v != v.strip() or "  " in v),
    }

    numeric_values = [n for n in (to_number(v) for v in present) if n is not None]
    profile["numeric_ratio"] = round(100 * len(numeric_values) / len(present), 1) if present else 0.0

    if ctype in {"integer", "number"} and numeric_values:
        profile["min"] = min(numeric_values)
        profile["max"] = max(numeric_values)
        profile["mean"] = round(statistics.fmean(numeric_values), 3)
        profile["median"] = statistics.median(numeric_values)
        profile["negatives"] = sum(1 for n in numeric_values if n < 0)
        if len(numeric_values) >= 8:
            q1, _, q3 = statistics.quantiles(numeric_values, n=4)
            iqr = q3 - q1
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            profile["outliers"] = sum(1 for n in numeric_values if n < low or n > high)
        else:
            profile["outliers"] = 0

    if ctype == "text" and present:
        lengths = [len(v) for v in present]
        profile["min_len"] = min(lengths)
        profile["max_len"] = max(lengths)
        profile["top"] = Counter(present).most_common(3)

    return profile


def build_issues(profiles: list[dict], duplicate_rows: int, total_rows: int) -> list[dict]:
    issues: list[dict] = []

    if duplicate_rows:
        pct = round(100 * duplicate_rows / total_rows, 1) if total_rows else 0.0
        issues.append({
            "severity": "high" if pct >= 5 else "medium",
            "column": "(rows)",
            "message": f"{duplicate_rows} duplicated row(s) ({pct}% of the file).",
            "fix": "Deduplicate on a stable key, or confirm duplicates are legitimate events.",
        })

    for p in profiles:
        name = p["name"]

        if p["missing_pct"] >= 20:
            issues.append({
                "severity": "high",
                "column": name,
                "message": f"{p['missing_pct']}% of values are missing.",
                "fix": "Confirm the column is populated at the source; otherwise drop it or impute deliberately.",
            })
        elif p["missing_pct"] > 0:
            issues.append({
                "severity": "medium",
                "column": name,
                "message": f"{p['missing']} missing value(s) ({p['missing_pct']}%).",
                "fix": "Decide whether blanks mean zero, unknown, or not-applicable, and document it.",
            })

        if p["type"] == "empty":
            issues.append({
                "severity": "high",
                "column": name,
                "message": "Column is completely empty.",
                "fix": "Remove it or restore the data.",
            })
        elif p["distinct"] == 1 and p["total"] > 1:
            issues.append({
                "severity": "low",
                "column": name,
                "message": "Column has a single distinct value (constant).",
                "fix": "Usually safe to drop; it adds no signal to a model or chart.",
            })

        if p["type"] == "text" and 0 < p["numeric_ratio"] < 100:
            issues.append({
                "severity": "high" if p["numeric_ratio"] >= 10 else "medium",
                "column": name,
                "message": f"Mixed types: {p['numeric_ratio']}% of values parse as numbers, the rest do not.",
                "fix": "Normalise the column (strip units/symbols, fix typos) before aggregating.",
            })

        if p.get("outliers"):
            issues.append({
                "severity": "low",
                "column": name,
                "message": f"{p['outliers']} statistical outlier(s) outside 1.5x IQR.",
                "fix": "Review them; cap, winsorise, or keep with a documented reason.",
            })

        if p.get("negatives") and p["type"] in {"integer", "number"}:
            issues.append({
                "severity": "medium",
                "column": name,
                "message": f"{p['negatives']} negative value(s) in a numeric column.",
                "fix": "Check whether negatives are valid (refunds, adjustments) or data-entry errors.",
            })

        if p["whitespace"]:
            issues.append({
                "severity": "low",
                "column": name,
                "message": f"{p['whitespace']} value(s) with leading/trailing or double spaces.",
                "fix": "Trim and collapse whitespace; otherwise joins and group-bys will split.",
            })

        if p["pii"]:
            issues.append({
                "severity": "high",
                "column": name,
                "message": f"Possible {p['pii'].upper()} data detected.",
                "fix": "Remove, hash, or tokenise before sharing this report or loading it into analytics.",
            })

        if p["type"] == "text" and p["distinct_pct"] >= 90 and p["total"] > 20:
            issues.append({
                "severity": "info",
                "column": name,
                "message": "Very high cardinality (likely an identifier).",
                "fix": "Exclude identifiers from charts and models; keep them only as keys.",
            })

    issues.sort(key=lambda i: SEVERITY_ORDER.get(i["severity"], 9))
    return issues


def score_report(profiles: list[dict], issues: list[dict], total_rows: int, duplicate_rows: int) -> tuple[int, str]:
    score = 100.0
    if total_rows:
        score -= min(25.0, 100 * duplicate_rows / total_rows * 2)
    for p in profiles:
        score -= min(15.0, p["missing_pct"] * 0.6)
        if p["type"] == "empty":
            score -= 8
        if p["distinct"] == 1 and p["total"] > 1:
            score -= 2
        if p["pii"]:
            score -= 8
        if p.get("outliers"):
            score -= min(4.0, p["outliers"] * 0.3)
        if p["whitespace"]:
            score -= 1
        if p["type"] == "text" and 0 < p["numeric_ratio"] < 100:
            score -= 6
    score = int(max(0, min(100, round(score))))
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    return score, grade


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
SEVERITY_LABEL = {"high": "High", "medium": "Medium", "low": "Low", "info": "Info"}


def render_html(report: dict) -> str:
    esc = html.escape
    score = report["score"]
    grade = report["grade"]
    accent = "#16a34a" if score >= 90 else "#65a30d" if score >= 80 else "#d97706" if score >= 70 else "#dc2626"

    issue_rows = []
    for issue in report["issues"]:
        issue_rows.append(
            f"<tr><td><span class='badge {issue['severity']}'>{SEVERITY_LABEL[issue['severity']]}</span></td>"
            f"<td class='mono'>{esc(issue['column'])}</td>"
            f"<td>{esc(issue['message'])}</td>"
            f"<td class='muted'>{esc(issue['fix'])}</td></tr>"
        )
    if not issue_rows:
        issue_rows.append("<tr><td colspan='4' class='muted'>No issues found. The file looks clean.</td></tr>")

    col_rows = []
    for p in report["columns"]:
        col_rows.append(
            f"<tr><td class='mono'>{esc(p['name'])}</td><td>{esc(p['type'])}</td>"
            f"<td class='num'>{p['missing']} ({p['missing_pct']}%)</td>"
            f"<td class='num'>{p['distinct']}</td>"
            f"<td class='num'>{p['distinct_pct']}%</td>"
            f"<td>{'<span class=\"badge high\">PII</span>' if p['pii'] else '<span class=\"muted\">-</span>'}</td></tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(report['title'])} — Data Audit</title>
<style>
  :root {{ --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --bg:#f8fafc; --card:#ffffff; --accent:{accent}; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); background:var(--bg); line-height:1.5; }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:40px 24px 64px; }}
  header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:24px; flex-wrap:wrap; margin-bottom:28px; }}
  h1 {{ font-size:28px; margin:0 0 6px; letter-spacing:-.02em; }}
  .sub {{ color:var(--muted); font-size:14px; }}
  .score {{ display:flex; align-items:center; gap:16px; background:var(--card); border:1px solid var(--line);
            border-radius:16px; padding:16px 22px; box-shadow:0 1px 2px rgba(15,23,42,.04); }}
  .score .num {{ font-size:44px; font-weight:700; color:var(--accent); line-height:1; }}
  .score .grade {{ font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:14px; margin:24px 0 32px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; }}
  .card .k {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; }}
  .card .v {{ font-size:26px; font-weight:700; margin-top:4px; }}
  h2 {{ font-size:18px; margin:32px 0 12px; letter-spacing:-.01em; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line);
           border-radius:14px; overflow:hidden; font-size:14px; }}
  th {{ text-align:left; font-size:12px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted);
        background:#f1f5f9; padding:11px 14px; border-bottom:1px solid var(--line); }}
  td {{ padding:11px 14px; border-bottom:1px solid var(--line); vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:13px; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .muted {{ color:var(--muted); }}
  .badge {{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:11px; font-weight:600;
            text-transform:uppercase; letter-spacing:.04em; }}
  .badge.high {{ background:#fee2e2; color:#b91c1c; }}
  .badge.medium {{ background:#fef3c7; color:#b45309; }}
  .badge.low {{ background:#e0f2fe; color:#0369a1; }}
  .badge.info {{ background:#e2e8f0; color:#475569; }}
  footer {{ margin-top:40px; color:var(--muted); font-size:12px; border-top:1px solid var(--line); padding-top:16px; }}
  @media (max-width:640px) {{ .score .num {{ font-size:34px; }} td, th {{ padding:9px 10px; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>{esc(report['title'])}</h1>
      <div class="sub">{esc(report['source'])} · {report['rows']} rows · {report['cols']} columns · generated {esc(report['generated'])}</div>
    </div>
    <div class="score">
      <div class="num">{score}</div>
      <div><div class="grade">Quality score</div><div class="grade">Grade {grade}</div></div>
    </div>
  </header>

  <div class="cards">
    <div class="card"><div class="k">Rows</div><div class="v">{report['rows']}</div></div>
    <div class="card"><div class="k">Columns</div><div class="v">{report['cols']}</div></div>
    <div class="card"><div class="k">Duplicate rows</div><div class="v">{report['duplicate_rows']}</div></div>
    <div class="card"><div class="k">Issues</div><div class="v">{len(report['issues'])}</div></div>
    <div class="card"><div class="k">Missing cells</div><div class="v">{report['missing_cells']}</div></div>
  </div>

  <h2>Findings</h2>
  <table>
    <thead><tr><th>Severity</th><th>Column</th><th>Finding</th><th>Suggested fix</th></tr></thead>
    <tbody>{''.join(issue_rows)}</tbody>
  </table>

  <h2>Column profile</h2>
  <table>
    <thead><tr><th>Column</th><th>Type</th><th class="num">Missing</th><th class="num">Distinct</th><th class="num">Cardinality</th><th>Privacy</th></tr></thead>
    <tbody>{''.join(col_rows)}</tbody>
  </table>

  <footer>Generated by data-audit · single-file, no third-party dependencies. Review findings before acting on them.</footer>
</div>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def audit(path: Path, title: str | None = None) -> dict:
    fields, rows = read_csv(path)
    if not fields:
        raise SystemExit("No columns found. Is this a valid CSV?")
    total_rows = len(rows)

    columns = [profile_column(name, [row.get(name, "") for row in rows]) for name in fields]

    seen = Counter(tuple(row.get(f, "") for f in fields) for row in rows)
    duplicate_rows = sum(count - 1 for count in seen.values() if count > 1)

    missing_cells = sum(p["missing"] for p in columns)
    issues = build_issues(columns, duplicate_rows, total_rows)
    score, grade = score_report(columns, issues, total_rows, duplicate_rows)

    return {
        "title": title or f"Data Audit - {path.stem}",
        "source": path.name,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rows": total_rows,
        "cols": len(fields),
        "duplicate_rows": duplicate_rows,
        "missing_cells": missing_cells,
        "score": score,
        "grade": grade,
        "issues": issues,
        "columns": columns,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Audit a CSV and produce an HTML data-quality report.")
    parser.add_argument("input", type=Path, help="Path to the CSV file")
    parser.add_argument("-o", "--output", type=Path, help="Output HTML path (default: <input>_audit.html)")
    parser.add_argument("--title", help="Report title")
    parser.add_argument("--json", action="store_true", help="Print the summary as JSON instead of writing HTML")
    args = parser.parse_args(argv)

    if not args.input.exists():
        raise SystemExit(f"File not found: {args.input}")

    report = audit(args.input, args.title)

    if args.json:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    output = args.output or args.input.with_name(f"{args.input.stem}_audit.html")
    output.write_text(render_html(report), encoding="utf-8")
    print(f"Score {report['score']}/100 (grade {report['grade']}) - {len(report['issues'])} issue(s)")
    print(f"Report written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
