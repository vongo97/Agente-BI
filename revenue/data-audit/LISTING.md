# How to turn `data-audit` into the first $10

Three routes, ordered by probability of a payout this week.

---

## Route A — warm outreach (best odds, ~1–3 days)

Sell a **$10 "spreadsheet health check"** to people you already know: small
business owners, community managers, analysts, anyone who lives in Excel.

Send this to 10 people (adapt the name):

> Hola {nombre}: estoy probando un servicio pequeño de auditoría de datos.
> Te reviso un CSV/Excel tuyo y te mando un informe con errores, duplicados,
> datos personales expuestos y una nota de calidad. Son **$10** y te lo entrego
> el mismo día. Si te sirve, mándame el archivo y te paso el informe antes de
> que pagues. ¿Te interesa?

Why it works: the ask is tiny, the deliverable is tangible, and you already
have trust. Ten messages usually produce one yes.

Fulfilment: run `python audit.py <file> -o <name>_audit.html`, review the
findings by hand, add two sentences of context, send the HTML.

---

## Route B — marketplace listing (~1–3 weeks)

### Fiverr gig

**Title:** I will audit your CSV or Excel file and send a data quality report

**Description:**

> Your spreadsheet has problems you cannot see: duplicated rows, numbers stored
> as text, blank cells, outliers, and personal data you should not be sharing.
> I will audit one CSV or Excel file (up to 20,000 rows) and send you a clean,
> client-ready HTML report with:
>
> - A 0–100 data quality score
> - Every issue found, ranked by severity
> - The exact column and a suggested fix for each one
> - A privacy check for emails, phone numbers and card-like data
>
> Delivery in 24 hours. No software to install, no subscription.
>
> Send me your file and I will tell you what is wrong with it before you pay.

**Packages:** Basic $10 (1 file, 20k rows, HTML report) · Standard $25 (3 files
+ cleaned CSV) · Premium $50 (5 files + cleaned CSV + 15-min walkthrough).

**Tags:** data cleaning, csv, excel, data analysis, data quality.

### Gumroad

**Product:** Data Audit Toolkit — CSV quality report generator
**Price:** $10
**Copy:** "One Python file. No dependencies. Turn any CSV into a client-ready
data-quality report in seconds. Includes the scoring engine, PII detection and
a sample report."

---

## Route C — open-source bounty (lottery ticket, $50+)

Platforms that actually pay: **Algora**, **Opire**, **IssueHunt**, **Polar**.
They require a GitHub account plus Stripe/Alipay onboarding (KYC).

Rules for not wasting time:

- Skip anything that asks you to star repos, post a wallet address, or "claim
  free tokens". That is engagement farming, not payment.
- Skip bounties older than ~30 days with 100+ comments; they are usually dead.
- Prefer $50–$200, clear acceptance criteria, and a maintainer who replies.

Workflow: pick one issue, read the code, write the patch and tests, open a PR
with `/claim`, then wait for review. The code is the easy part; the account and
the payout onboarding are the gate.

---

## The one thing that cannot be automated

Every route ends in an account that belongs to a verified human. That is the
only step left: a PayPal/Bizum/Stripe/wallet in your name. The work above is
already done.
