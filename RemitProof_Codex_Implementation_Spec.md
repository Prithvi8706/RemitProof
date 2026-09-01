# RemitProof — Codex Implementation & Execution Specification
## Razorpay AI Buildathon 2026 — AI Finance Controller

> **Purpose**
>
> This file is meant to be handed directly to Codex / Claude Code / another coding agent.
>
> Build exactly the scoped MVP described here.
>
> Do **not** expand scope unless a requirement below explicitly asks for it.

---

# 0. Project Summary

## Working Name

# RemitProof

## Tagline

> **Evidence-grounded AI for unresolved cross-border receivables.**

## Core Thesis

> **RemitProof does not merely find a plausible reconciliation. It proves whether the available evidence is sufficient to safely act on it.**

## Product Definition

RemitProof is an AI Finance Controller that investigates cross-border receivables that ordinary reconciliation could not resolve.

It:

1. runs conventional deterministic matching first,
2. sends only unresolved exceptions to the AI layer,
3. retrieves relevant invoices, customer/entity records, credit notes, and remittance emails,
4. lets the LLM construct a candidate financial explanation,
5. deterministically verifies financial correctness,
6. checks whether evidence uniquely supports the explanation,
7. either:
   - `RESOLVE`, or
   - `ABSTAIN / HUMAN REVIEW`.

## Key Principle

```text
AI proposes
    ↓
Deterministic code verifies
    ↓
Evidence sufficiency checks uniqueness
    ↓
RESOLVE
or
ABSTAIN
```

## Important Non-Goals

Do **not** build:

- generic reconciliation,
- invoice OCR,
- Gmail integration,
- Zoho integration,
- Tally integration,
- SAP integration,
- DGFT compliance automation,
- full FX conversion,
- real accounting write-back,
- settlement execution,
- authentication,
- user management,
- mobile app,
- vector database,
- embeddings infrastructure,
- generic chatbot,
- multi-agent orchestration,
- multi-model debate,
- enterprise ERP integration.

The MVP should prioritize:

```text
dataset quality
+
strong baseline
+
proof engine
+
evidence sufficiency
+
benchmark
+
clear UI
```

---

# 1. Freeze the Project Definition

Use this exact conceptual boundary:

```text
Incoming international payments
           ↓
Conventional deterministic matcher
           ↓
Easy cases resolved
           ↓
════════════════════════════════
        REMITPROOF STARTS
════════════════════════════════
           ↓
Unresolved exceptions
           ↓
Candidate retrieval
           ↓
AI investigation
           ↓
Candidate reconciliation
           ↓
Proof engine
           ↓
Evidence sufficiency
           ↓
   ┌───────────────┐
   │               │
RESOLVE         ABSTAIN
   │               │
audit trail     human review reason
```

The project is **not**:

```text
"Use an LLM to match invoices."
```

The project is:

```text
"Investigate only cases that normal reconciliation cannot uniquely resolve."
```

---

# 2. Architecture

## Recommended Stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS

### Backend

- Python
- FastAPI

### Storage

Use one of:

- SQLite, or
- JSON/CSV files

Prefer SQLite if it does not slow implementation.

### AI

Use one strong LLM API with structured JSON output.

### Evaluation

Python scripts.

## High-Level Architecture

```text
                  REMITPROOF

payments.csv / API-compatible payment records
invoices.csv
customers.json
credits.csv
emails.jsonl
supporting metadata
         │
         ▼
┌─────────────────────────────┐
│  1. CONVENTIONAL MATCHER    │
│                             │
│ - invoice refs              │
│ - exact amounts             │
│ - aliases                   │
│ - simple combinations       │
│ - date/currency constraints │
└──────────────┬──────────────┘
               │
       easy matches resolved
               │
       unresolved only
               ▼
════════════════════════════════════
          REMITPROOF STARTS
════════════════════════════════════
               │
               ▼
┌─────────────────────────────┐
│  2. CANDIDATE RETRIEVER     │
│                             │
│ - likely invoices           │
│ - customers/entities        │
│ - emails/remittance         │
│ - credits                   │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  3. AI INVESTIGATOR         │
│                             │
│ - interprets semantics      │
│ - selects evidence          │
│ - proposes resolution       │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  4. PROOF ENGINE            │
│                             │
│ - arithmetic                │
│ - currency                  │
│ - invoice state             │
│ - duplicate checks          │
│ - entity support            │
│ - credit support            │
│ - contradictions            │
│ - alternatives              │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 5. EVIDENCE SUFFICIENCY     │
│                             │
│ Is the candidate merely     │
│ plausible, or uniquely      │
│ supported?                  │
└──────────────┬──────────────┘
               │
          ┌────┴────┐
          ▼         ▼
       RESOLVE    ABSTAIN
          │         │
          ▼         ▼
     proof/audit   reason
```

---

# 3. Two-Hour Kill Spike

Before building the UI, implement a minimal test spike.

## Required 10 Cases

| Case | Exception | Expected |
|---|---|---|
| 1 | Parent company pays subsidiary invoice | Resolve |
| 2 | Different legal payer name + supporting entity record | Resolve |
| 3 | Email specifies two invoices | Resolve |
| 4 | Credit deduction explained by remittance | Resolve |
| 5 | Two numeric allocations, email disambiguates | Resolve |
| 6 | Same-amount invoices, no remittance | Abstain |
| 7 | Email conflicts with credit note | Abstain |
| 8 | Claimed credit but credit note missing | Abstain |
| 9 | Payer relationship uncertain | Abstain |
| 10 | Multi-invoice + deduction + entity mismatch | Resolve |

## Compare Three Systems

```text
A. deterministic baseline only

B. LLM only

C. LLM + RemitProof verifier
```

## GO Condition

Continue full implementation only if the spike shows this pattern:

```text
Rules:
cannot solve several realistic semantic cases.

LLM-only:
solves some semantic cases but overclaims or guesses on ambiguity.

RemitProof:
retains semantic wins while blocking unsupported financial actions.
```

There must be at least **one case where:**

```text
LLM-only → RESOLVE
RemitProof → correctly ABSTAIN
```

If the verifier becomes only:

```python
if confidence > 0.8:
    resolve()
```

the thesis is not strong enough.

---

# 4. Dataset Design

## Final Dataset

Target:

```text
80 total incoming payment records
```

Recommended composition:

```text
50 conventional/easy cases
30 exception cases
```

The easy cases establish that ordinary reconciliation works.

The 30 exception cases are the actual RemitProof benchmark.

## Development vs Held-Out Evaluation

Recommended:

```text
20 development records
60 held-out benchmark records
```

Do not tune prompts against all final cases.

## Exception Classes

Include realistic examples of:

- payer alias mismatch,
- parent company payer,
- detached remittance email,
- same-amount ambiguity,
- credit deduction,
- unexplained short pay,
- multi-invoice remittance instructions,
- conflicting evidence,
- missing credit note,
- multiple valid allocations,
- missing payer identity,
- stale/closed invoice candidate,
- duplicate allocation risk,
- unsupported currency mismatch.

## Ground Truth

Every benchmark exception must contain ground-truth fields:

```text
correct_customer
correct_invoices
correct_credits
should_resolve
required_evidence
expected_reason
exception_class
```

Never expose ground truth to the model.

---

# 5. Data Model

Create the following files under:

```text
data/
```

## `data/payments.csv`

Required columns:

```text
payment_id
date
amount
currency
payer_name
bank_reference
remittance_reference
status
```

Example:

```csv
payment_id,date,amount,currency,payer_name,bank_reference,remittance_reference,status
PAY_001,2026-08-05,19650,USD,ACME US HOLDINGS SPV LLC,BRX0291,,unmatched
```

## `data/invoices.csv`

Required columns:

```text
invoice_id
customer_id
amount
currency
issue_date
due_date
description
status
```

Example:

```csv
invoice_id,customer_id,amount,currency,issue_date,due_date,description,status
INV_081,CUS_001,10000,USD,2026-06-01,2026-06-30,Platform services,open
INV_094,CUS_001,10000,USD,2026-07-01,2026-07-31,Migration services,open
```

## `data/customers.json`

Recommended schema:

```json
[
  {
    "customer_id": "CUS_001",
    "legal_name": "Acme Technologies Inc.",
    "aliases": ["Acme Tech", "Acme Technologies"],
    "parent_entities": ["ACME US HOLDINGS SPV LLC"],
    "subsidiaries": [],
    "known_payers": ["ACME US HOLDINGS SPV LLC"]
  }
]
```

## `data/credits.csv`

Required columns:

```text
credit_id
customer_id
invoice_id
amount
currency
reason
status
```

Example:

```csv
credit_id,customer_id,invoice_id,amount,currency,reason,status
CR_012,CUS_001,INV_094,350,USD,SLA service credit,valid
```

## `data/emails.jsonl`

Each line should be a JSON object.

Required fields:

```text
email_id
sender
customer_id
date
subject
body
```

Example:

```json
{"email_id":"EMAIL_019","sender":"finance@acme.example","customer_id":"CUS_001","date":"2026-08-03","subject":"September remittance","body":"Please apply our payment against INV_081 and INV_094. As agreed, we deducted the USD 350 SLA service credit."}
```

## `data/ground_truth.json`

Recommended schema:

```json
[
  {
    "payment_id": "PAY_001",
    "exception_class": "multi_invoice_credit_entity_mismatch",
    "correct_customer": "CUS_001",
    "correct_invoices": ["INV_081", "INV_094"],
    "correct_credits": ["CR_012"],
    "should_resolve": true,
    "required_evidence": ["EMAIL_019", "CR_012", "CUS_001"],
    "expected_reason": "Parent entity pays two invoices after applying a valid SLA credit."
  }
]
```

Never send this file to the LLM.

---

# 6. Strong Deterministic Baseline

The baseline must be competent.

Do not create a strawman.

## It Should Support

- explicit invoice reference match,
- exact payment amount match,
- currency equality,
- known customer IDs,
- normalized known aliases,
- known parent/entity payer mappings,
- simple date-window filtering,
- obvious one-payment-to-many-invoice subset matching,
- valid credit arithmetic,
- already-paid / closed invoice rejection,
- duplicate allocation prevention.

## Baseline Output

Use structured output:

```json
{
  "payment_id": "PAY_001",
  "status": "matched" | "unresolved",
  "matched_invoices": [],
  "matched_credits": [],
  "customer_id": null,
  "reason": "...",
  "candidate_count": 0
}
```

Only unresolved cases are passed to RemitProof.

---

# 7. Candidate Retrieval

Do not implement full RAG.

Use deterministic narrowing.

## Retrieval Pipeline

```text
payment
 ↓
same currency
 ↓
reasonable date window
 ↓
candidate customers
 ↓
known aliases / entity relationships
 ↓
possible invoice combinations
 ↓
associated credits
 ↓
associated remittance emails
```

Recommended candidate limits per exception:

```text
3–8 invoices
1–4 emails
0–3 credit notes
2–3 customer/entity records
```

## Retrieval Output

```json
{
  "payment": {},
  "candidate_customers": [],
  "candidate_invoices": [],
  "candidate_credits": [],
  "candidate_emails": []
}
```

---

# 8. AI Investigator

The LLM must return structured JSON.

Do not allow free-form text as the primary response.

## Required Output Shape

```json
{
  "payment_id": "PAY_001",
  "proposed_customer": "CUS_001",
  "invoice_ids": ["INV_081", "INV_094"],
  "credit_ids": ["CR_012"],
  "semantic_claims": [
    {
      "claim_id": "CLAIM_001",
      "claim": "The payer is an authorized parent entity for the invoice customer.",
      "evidence_ids": ["CUS_001"]
    },
    {
      "claim_id": "CLAIM_002",
      "claim": "A USD 350 SLA service credit applies to this remittance.",
      "evidence_ids": ["EMAIL_019", "CR_012"]
    }
  ],
  "evidence_ids": ["EMAIL_019", "CR_012", "CUS_001"],
  "unresolved_questions": []
}
```

## AI Responsibilities

The AI may:

- interpret remittance emails,
- identify semantic customer/entity relationships,
- interpret free-text deduction descriptions,
- associate evidence with proposed invoices,
- create a candidate reconciliation hypothesis,
- list unresolved uncertainty.

## AI Must Not

The AI must not be trusted for:

- arithmetic,
- final monetary totals,
- duplicate checks,
- invoice state,
- currency compatibility,
- authorization to resolve.

Those belong to deterministic code.

---

# 9. Proof Engine

This is a core module.

Create something like:

```text
backend/app/services/proof_engine.py
```

## Financial Proof

Validate:

```text
sum(open invoice amounts)
-
sum(valid credits)
-
allowed deterministic adjustments
=
payment amount
```

Use decimal-safe arithmetic.

Use Python `Decimal`, not floating-point.

## State Proof

Verify:

```text
invoice is open
credit is valid
payment is unresolved
invoice not already fully allocated
payment not already reconciled
credit not already consumed
```

## Currency Proof

For MVP:

```text
payment currency == invoice currency == credit currency
```

If not:

```text
ABSTAIN
reason = unsupported_currency_mismatch
```

Do not build a full FX engine.

## Entity Proof

If:

```text
payer_name != invoice_customer_legal_name
```

require explicit support from one of:

- known alias,
- parent entity,
- subsidiary mapping,
- known payer record,
- explicit remittance evidence.

The LLM saying names "look related" is insufficient.

---

# 10. Evidence Sufficiency / Uniqueness

This is the main differentiator.

Create:

```text
backend/app/services/evidence_sufficiency.py
```

## Goal

Determine whether the proposed reconciliation is merely possible or uniquely justified.

## Example

Payment:

```text
USD 19,650
```

Two valid numeric explanations:

```text
Option A:
INV_081 + INV_094 - CR_012 = 19,650

Option B:
INV_055 + INV_063 = 19,650
```

If an email explicitly says:

```text
"Apply this payment to INV_081 and INV_094 after the SLA credit."
```

then evidence supports A and eliminates B.

If the email only says:

```text
"September payment attached."
```

then both remain plausible.

Result:

```text
HUMAN REVIEW REQUIRED
```

## Required Sufficiency Checks

At minimum evaluate:

```text
financial_validity
entity_support
credit_support
alternative_allocations_exist
evidence_disambiguates_alternatives
contradictions_exist
missing_required_evidence
duplicate_risk
```

## Suggested Result Object

```json
{
  "financial_validity": true,
  "entity_support": true,
  "credit_support": true,
  "alternative_allocations_exist": true,
  "evidence_disambiguates_alternatives": true,
  "contradictions_exist": false,
  "missing_required_evidence": [],
  "duplicate_risk": false,
  "safe_to_resolve": true,
  "abstention_reason": null
}
```

---

# 11. Counterfactual Evidence Feature

If time allows, add a lightweight feature:

> **Which evidence is decision-critical?**

For each supporting evidence item:

1. temporarily remove it,
2. recompute sufficiency,
3. check whether the decision changes.

Example:

```text
With EMAIL_019:
RESOLVE

Without EMAIL_019:
2 valid allocations remain
→ ABSTAIN
```

Show:

```text
EMAIL_019 is decision-critical evidence.
Without it, RemitProof would abstain.
```

This is optional but high-value.

---

# 12. Decision States

Use exactly three user-facing states:

```text
MATCHED NORMALLY
```

```text
REMITPROOF RESOLVED
```

```text
HUMAN REVIEW REQUIRED
```

Do not create unnecessary state complexity.

## Internal Decision Object

Recommended:

```json
{
  "payment_id": "PAY_001",
  "decision": "matched_normally" | "resolved" | "human_review",
  "customer_id": "CUS_001",
  "invoice_ids": [],
  "credit_ids": [],
  "proof": {},
  "evidence": [],
  "reason": "...",
  "latency_ms": 0
}
```

---

# 13. Frontend / UI

Build only two major screens.

## Screen 1 — Dashboard

Route:

```text
/
```

Display:

```text
REMITPROOF

80 Incoming Receipts

50 Matched Normally
30 Exceptions Investigated

18 Safely Resolved
12 Human Review

Incorrect Auto-Resolution: X%
Throughput: X records/min
```

All values must come from benchmark output.

Do not hardcode benchmark numbers.

## Dashboard Sections

Recommended:

- total receipts,
- matched normally,
- exceptions,
- resolved by RemitProof,
- human review,
- incorrect auto-resolution,
- throughput,
- recent exceptions table.

## Exception Table

Columns:

```text
payment
payer
amount
currency
status
exception class
decision
```

Clicking a row opens the exception detail page.

## Screen 2 — Exception Detail

Route example:

```text
/exceptions/[payment_id]
```

Suggested layout:

```text
┌─────────────────┬──────────────────────┐
│ PAYMENT         │ DECISION             │
│                 │                      │
│ USD 19,650      │ ✓ SAFE TO RESOLVE    │
│ Acme Holdings   │                      │
├─────────────────┼──────────────────────┤
│ EVIDENCE        │ PROOF                │
│                 │                      │
│ INV_081         │ Arithmetic      ✓    │
│ INV_094         │ Entity          ✓    │
│ EMAIL_019       │ Credit          ✓    │
│ CR_012          │ Contradiction   ✓    │
│ Customer record │ Uniqueness      ✓    │
├─────────────────┴──────────────────────┤
│ PROPOSED ALLOCATION                    │
│                                        │
│ INV_081                  $10,000        │
│ INV_094                  $10,000        │
│ SLA Credit                 -$350        │
│                           ───────        │
│ Received                 $19,650 ✓      │
└────────────────────────────────────────┘
```

For abstention:

```text
⚠ HUMAN REVIEW REQUIRED

2 financially valid explanations remain.

No available evidence uniquely determines
which customer/invoice allocation was intended.
```

The abstention page should look intentional and polished.

---

# 14. Benchmark & Evaluation

Do not evaluate only overall accuracy.

Create:

```text
backend/scripts/evaluate.py
```

## Required Metrics

| Metric | Definition / Purpose |
|---|---|
| Baseline match rate | Percentage solved before AI |
| Exception resolution rate | Exceptions safely resolved by RemitProof |
| Resolution accuracy | Correct resolutions / resolvable exceptions |
| Incorrect auto-resolution rate | Wrong resolutions / all auto-resolutions |
| Correct abstention rate | Ambiguous cases correctly escalated |
| False escalation rate | Resolvable cases unnecessarily escalated |
| Entity-resolution accuracy | Correct payer/customer relationship decisions |
| Evidence precision | Cited evidence actually relevant |
| Arithmetic correctness | Must be 100% |
| Retrieval accuracy | Correct invoice/email/credit present in candidate set |
| Throughput | Records or exceptions per minute |
| Mean latency | Average decision latency |

## Primary Safety Metric

# Incorrect Auto-Resolution Rate

The system should prefer:

```text
human review
```

over:

```text
confidently wrong financial action
```

## Comparison Table

Generate something like:

| Metric | Baseline | LLM Only | RemitProof |
|---|---:|---:|---:|
| Resolved | X | X | X |
| Correct resolutions | X | X | X |
| Wrong auto-resolutions | X | X | X |
| Correct abstentions | X | X | X |
| False escalations | X | X | X |

Never invent values.

---

# 15. Razorpay Integration Story

Do not overbuild production integration.

## Real / API-Compatible

Treat these as real-compatible surfaces:

- Razorpay invoice concepts/API-compatible records,
- Razorpay payment records,
- bank-transfer payment fields,
- payer/remittance fields where available,
- standard webhook-compatible payment events if useful.

## Synthetic but Realistic

Use synthetic data for:

- MoneySaver International Bank Transfer transaction records,
- merchant ERP records,
- customer master,
- email/remittance inbox,
- credit notes,
- internal accounting data.

## Simulated Actions

Do not pretend to perform:

- real MoneySaver document submission,
- real settlement,
- real ERP posting,
- real accounting write-back.

## README Disclosure

Include:

```text
Razorpay Invoice data:
Public-API compatible.

Bank-transfer/payment fields:
Modeled on documented Razorpay payment schemas.

International Bank Transfer records:
Realistic synthetic dataset modeled on documented exporter workflows.

Merchant ERP/customer/email data:
Synthetic.

Final posting:
Prototype only; no production accounting write-back.
```

---

# 16. Explicit Scope Cuts

Do not implement:

```text
OCR
Gmail API
Zoho
Tally
SAP
NetSuite
Pinecone
vector DB
embeddings
generic chatbot
full FX engine
DGFT compliance
real settlement
accounting write-back
authentication
multi-user support
mobile app
multi-agent system
multi-model debate
complex permissions
enterprise deployment
```

If implementation time is running short, cut in this order:

```text
1. counterfactual evidence feature
2. fancy charts
3. advanced filtering
4. extra exception classes
5. database persistence
6. animation/polish
```

Never cut:

```text
baseline
AI investigator
proof engine
evidence sufficiency
abstention
benchmark
hero UI
```

---

# 17. 25-Hour Execution Plan

## Total

```text
25 focused hours
```

## Schedule

| Day | Hours | Goal |
|---|---:|---|
| Aug 31 | 5h | Kill spike + architecture |
| Sep 1 | 5h | Dataset + baseline + proof engine |
| Sep 2 | 5h | AI investigator + evidence sufficiency + evaluation |
| Sep 3 | 4h | Dashboard + exception detail UI |
| Sep 4 | 4h | Final benchmark + polish + README + architecture |
| Sep 5 | 2h | Video + repo cleanup + final submission |

## Day 1 — Prove the Thesis

### Hour 0–0.5
Create repository and project structure.

### Hour 0.5–1
Create 10 synthetic spike cases.

### Hour 1–1.5
Implement deterministic baseline.

### Hour 1.5–2
Implement minimal LLM investigator.

### Hour 2–3
Implement deterministic proof engine.

### Hour 3–4
Run all 10 cases.

### Hour 4–5
Evaluate:

```text
GO
MODIFY
KILL
```

No frontend before the spike works.

## Day 2 — Build Core Engine

Implement:

```text
dataset generator
80-record dataset
baseline matcher
candidate retrieval
proof engine
audit objects
unit tests
```

By end of day:

```bash
python scripts/evaluate.py
```

must run end-to-end without frontend.

## Day 3 — Make AI Valuable

Implement:

```text
structured AI investigator
semantic entity interpretation
remittance understanding
credit/deduction interpretation
alternative allocation detection
evidence sufficiency
abstention
```

Then:

1. freeze prompts,
2. freeze logic,
3. generate held-out benchmark,
4. run benchmark,
5. record failures honestly.

## Day 4 — Build UI

Build:

```text
Dashboard
Exception Detail
```

No extra screens unless core work is complete.

Hero cases:

1. one complex successful resolution,
2. one deliberate abstention.

## Day 5 — Submission Preparation

Generate:

```text
results/metrics.json
results/results.csv
docs/failure_analysis.md
docs/architecture.md
README.md
```

Also create the architecture diagram.

Run final benchmark.

Fix only high-priority issues.

## Final Submission Day

Do:

```text
bugs
recording
README
repo cleanup
final benchmark
submission
```

Do not add new features.

---

# 18. Five-Minute Pitch Structure

## 0:00–0:30 — Problem

Say:

> Most reconciliation demos show AI matching easy transactions. Easy transactions do not need AI.

Show:

```text
80 receipts

50 reconciled normally
30 unresolved
```

## 0:30–0:55 — Thesis

Say:

> RemitProof starts where normal reconciliation stops.

Show architecture.

## 0:55–2:15 — Hero Resolution

Use a case like:

```text
Payment:
USD 19,650

Payer:
ACME US HOLDINGS SPV LLC
```

Evidence:

```text
INV_081      10,000
INV_094      10,000
CR_012         -350
-------------------
Payment       19,650
```

Show:

- payer/entity relationship,
- remittance email,
- credit note,
- alternative allocation detection,
- deterministic verification,
- resolution.

## 2:15–3:00 — Abstention

Show a case where:

```text
2 valid allocations remain
```

and no evidence disambiguates.

Result:

```text
HUMAN REVIEW REQUIRED
```

Say:

> In finance, unresolved is better than confidently wrong.

## 3:00–3:45 — Architecture

Explain:

```text
AI = semantic investigation
Code = financial proof
```

## 3:45–4:35 — Benchmark

Show actual:

```text
Baseline vs LLM Only vs RemitProof
```

Highlight:

```text
incorrect auto-resolution
correct abstention
```

## 4:35–5:00 — Razorpay Fit

Explain:

> Razorpay already owns payment-side evidence and international payment workflows. RemitProof explores the residual finance work left when structured payment signals do not uniquely explain a receipt.

---

# 19. Star Metric

The star metric is:

# Incorrect Auto-Resolution Rate

Not merely:

```text
auto-match rate
```

The objective is:

```text
maximize justified automation

subject to

incorrect auto-resolution ≈ 0
```

Human escalation is acceptable.

A confidently wrong financial action is not.

---

# 20. What Makes This Competitive

By final submission, aim to have:

```text
✓ 60+ held-out benchmark records

✓ strong deterministic baseline

✓ AI only touches unresolved cases

✓ at least 4 meaningful exception classes

✓ evidence-grounded entity/remittance reasoning

✓ deterministic arithmetic correctness = 100%

✓ explicit alternative-hypothesis checking

✓ correct abstention behavior

✓ comparison against LLM-only

✓ real failure cases shown honestly

✓ one polished resolution demo

✓ one polished abstention demo

✓ clear architecture

✓ reproducible benchmark

✓ no fake Razorpay APIs or capabilities
```

The submission should not sound like:

> "We built AI reconciliation."

It should sound like:

> **We built an evidence-and-verification layer for AI-generated financial resolutions, where every autonomous action must be provably supported or the system abstains.**

---

# 21. Final Lock

## Name

# RemitProof

## Track

AI Finance Controller

## Problem

Unresolved cross-border receivables.

## Product Boundary

```text
normal reconciliation
        ↓
unresolved exception
        ↓
RemitProof
```

## Thesis

Normal reconciliation handles easy cases.

AI should investigate only the residual semantic exceptions.

## Technical Differentiator

# Proof-Carrying Financial Resolution

Every automatic resolution must satisfy:

```text
financial validity
+
entity support
+
evidence support
+
no unresolved contradiction
+
no equally plausible unsupported alternative
```

Otherwise:

# ABSTAIN

## Immediate Objective

Before building the full product:

```text
10-case spike
↓
baseline vs LLM-only vs RemitProof
↓
GO / MODIFY / KILL
```

Do not proceed because the idea sounds good.

Proceed only if the spike proves that:

```text
LLM semantic reasoning adds value
+
deterministic verification prevents bad actions
+
evidence sufficiency meaningfully distinguishes
plausible from justified resolutions
```

---

# 22. Recommended Repository Structure

Codex should create approximately this structure:

```text
remitproof/
│
├── README.md
├── .env.example
├── .gitignore
│
├── data/
│   ├── payments.csv
│   ├── invoices.csv
│   ├── credits.csv
│   ├── customers.json
│   ├── emails.jsonl
│   ├── ground_truth.json
│   ├── dev/
│   └── benchmark/
│
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── dashboard.py
│   │   │   ├── exceptions.py
│   │   │   └── benchmark.py
│   │   ├── models/
│   │   │   ├── payment.py
│   │   │   ├── invoice.py
│   │   │   ├── customer.py
│   │   │   ├── credit.py
│   │   │   ├── email.py
│   │   │   ├── investigation.py
│   │   │   └── decision.py
│   │   ├── services/
│   │   │   ├── baseline_matcher.py
│   │   │   ├── candidate_retriever.py
│   │   │   ├── ai_investigator.py
│   │   │   ├── proof_engine.py
│   │   │   ├── evidence_sufficiency.py
│   │   │   ├── alternative_finder.py
│   │   │   ├── evaluator.py
│   │   │   └── audit_builder.py
│   │   ├── prompts/
│   │   │   └── investigator.txt
│   │   └── utils/
│   │       ├── money.py
│   │       ├── normalization.py
│   │       └── loaders.py
│   ├── tests/
│   │   ├── test_baseline.py
│   │   ├── test_proof_engine.py
│   │   ├── test_evidence_sufficiency.py
│   │   └── test_cases.py
│   └── scripts/
│       ├── generate_dataset.py
│       ├── run_spike.py
│       └── evaluate.py
│
├── frontend/
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx
│   │   └── exceptions/
│   │       └── [paymentId]/
│   │           └── page.tsx
│   ├── components/
│   │   ├── MetricCard.tsx
│   │   ├── ExceptionTable.tsx
│   │   ├── PaymentPanel.tsx
│   │   ├── EvidencePanel.tsx
│   │   ├── ProofPanel.tsx
│   │   ├── AllocationPanel.tsx
│   │   └── DecisionBadge.tsx
│   └── lib/
│       └── api.ts
│
├── results/
│   ├── metrics.json
│   ├── results.csv
│   └── confusion_breakdown.csv
│
└── docs/
    ├── architecture.md
    ├── failure_analysis.md
    ├── benchmark_methodology.md
    └── demo_script.md
```

---

# 23. Suggested API Endpoints

Implement only what the frontend needs.

## `GET /api/dashboard`

Example response:

```json
{
  "total_receipts": 80,
  "matched_normally": 50,
  "exceptions": 30,
  "resolved_by_remitproof": 18,
  "human_review": 12,
  "incorrect_auto_resolution_rate": 0.0,
  "throughput_per_minute": 12.4
}
```

## `GET /api/exceptions`

Return exception list.

## `GET /api/exceptions/{payment_id}`

Return:

```json
{
  "payment": {},
  "decision": {},
  "proposed_allocation": [],
  "evidence": [],
  "proof": {},
  "alternatives": [],
  "counterfactuals": []
}
```

## `POST /api/run/{payment_id}`

Optional. Runs investigation for one payment.

## `POST /api/run-batch`

Optional. Runs all unresolved exceptions.

## `GET /api/benchmark`

Returns final benchmark metrics.

---

# 24. Core Processing Pipeline

Implement one orchestration function:

```python
def process_payment(payment_id: str):
    payment = load_payment(payment_id)

    baseline_result = baseline_match(payment)

    if baseline_result.status == "matched":
        return build_normal_match_decision(baseline_result)

    candidates = retrieve_candidates(payment)

    proposal = investigate_with_llm(
        payment=payment,
        candidates=candidates
    )

    proof = verify_candidate(
        payment=payment,
        proposal=proposal,
        candidates=candidates
    )

    alternatives = find_valid_alternatives(
        payment=payment,
        candidates=candidates
    )

    sufficiency = evaluate_evidence_sufficiency(
        payment=payment,
        proposal=proposal,
        proof=proof,
        alternatives=alternatives,
        candidates=candidates
    )

    return build_final_decision(
        proposal=proposal,
        proof=proof,
        sufficiency=sufficiency
    )
```

The exact code may differ, but preserve this architecture.

---

# 25. Acceptance Criteria

The MVP is considered complete only if all of the following are true.

## Functional

- [ ] baseline matcher works,
- [ ] unresolved cases reach AI,
- [ ] AI outputs valid structured JSON,
- [ ] proof engine independently verifies money,
- [ ] ambiguous cases can abstain,
- [ ] dashboard displays benchmark results,
- [ ] exception page displays evidence and proof.

## Safety

- [ ] Python `Decimal` used for monetary arithmetic,
- [ ] no LLM arithmetic is trusted,
- [ ] duplicate allocations blocked,
- [ ] closed invoices blocked,
- [ ] invalid credits blocked,
- [ ] unsupported currency mismatch abstains,
- [ ] unsupported entity relationship abstains,
- [ ] contradictory evidence abstains,
- [ ] non-unique supported explanation abstains.

## Evaluation

- [ ] benchmark has 50+ records,
- [ ] metrics generated automatically,
- [ ] ground truth hidden from model,
- [ ] baseline vs LLM-only vs RemitProof comparison exists,
- [ ] failure cases saved,
- [ ] incorrect auto-resolution measured,
- [ ] throughput measured.

## Demo

- [ ] one complex resolution case is polished,
- [ ] one human-review case is polished,
- [ ] dashboard tells the story within seconds,
- [ ] architecture is clear,
- [ ] no fake integration claims.

---

# 26. Instructions to Coding Agent

When implementing this repository:

1. Build backend functionality before UI.
2. Start with the 10-case spike.
3. Do not build any feature outside the explicit scope.
4. Keep financial logic deterministic.
5. Force all LLM output through a strict structured schema.
6. Keep model prompts versioned in files.
7. Make all benchmark metrics reproducible.
8. Never hardcode benchmark results into frontend components.
9. Keep synthetic data realistic and internally consistent.
10. Favor readable code over abstraction-heavy architecture.
11. Add tests to the proof engine before adding UI polish.
12. If a feature threatens the 25-hour schedule, cut it.
13. Preserve the project's core differentiation:
    - alternative hypothesis detection,
    - evidence sufficiency,
    - abstention.
14. Do not turn this into generic AI reconciliation.
15. Do not turn this into a generic finance chatbot.

---

# 27. Final Mental Model

```text
         NORMAL RECONCILIATION
                  ↓
          unresolved payment
                  ↓
════════════════════════════════
             REMITPROOF
════════════════════════════════
                  ↓
         retrieve evidence
                  ↓
          AI hypothesis
                  ↓
        deterministic proof
                  ↓
       search for alternatives
                  ↓
       evidence sufficient?
             /          \
           yes          no
            ↓            ↓
        RESOLVE       ABSTAIN
```

The project succeeds only if the demo proves:

> **A plausible financial explanation is not automatically a justified financial action.**

RemitProof should make that difference visible, measurable, and safe.
