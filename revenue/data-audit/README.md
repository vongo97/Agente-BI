# data-audit

A single-file CSV quality auditor with **zero dependencies**. Point it at a
spreadsheet, get a client-ready HTML report with a quality score and a
prioritised list of problems.

```bash
python audit.py data.csv
python audit.py data.csv -o report.html --title "Q3 Marketing Data"
python audit.py data.csv --json > summary.json
```

Output: `data_audit.html` (self-contained, no CDN, no JS).

## What it checks

| Check | Why it matters |
| --- | --- |
| Missing values per column | Silent gaps skew every average |
| Duplicate rows | Inflates counts and revenue |
| Mixed types | `"1,200"` vs `1200` breaks aggregation |
| Outliers (1.5× IQR) | Typos and test data distort reports |
| Negative values | Refunds vs data-entry errors |
| Constant / empty columns | Dead weight in models and dashboards |
| Whitespace | `"ES"` vs `" ES"` splits group-bys |
| PII (email, phone, card, SSN, …) | Privacy / compliance risk before sharing |
| High-cardinality IDs | Useless as features, dangerous in charts |

Every finding comes with a suggested fix, so the report reads like an audit,
not a dump of statistics.

## Example

On a deliberately dirty file (11 rows, 6 columns) it returns **45/100 (F)** and
flags the duplicate row, the missing email, the mixed-type `amount` column, the
negative refund, the 1,000,000 outlier, the malformed email and the PII column.

On a clean marketing dataset it returns **98/100 (A)** with only informational
findings.

## Design notes

- Standard library only (`csv`, `statistics`, `re`, `html`, `json`).
- Handles UTF-8 (with or without BOM), cp1252 and latin-1.
- Sniffs `,` `;` `\t` `|` delimiters.
- Single file, easy to embed in a service or a CI step.

## License

MIT — use it, sell reports made with it, embed it.
