# Product

## Register

product

## Users

Finance controllers and receivables operators investigating cross-border payments that ordinary reconciliation could not resolve. They work under time pressure, often across bank records, invoices, credit notes, customer masters, and detached remittance messages. Their primary task is to decide whether a proposed allocation is safe to post or must be escalated.

## Product Purpose

RemitProof investigates only unresolved receivables. An AI investigator proposes a semantic explanation, deterministic code verifies financial and record-state correctness, and an evidence-sufficiency layer tests whether the explanation is uniquely supported. Success means maximizing justified automation while keeping incorrect auto-resolution at or near zero. When evidence is incomplete, contradictory, or non-unique, the product must make human review feel like a deliberate safety outcome.

## Brand Personality

Rigorous, composed, accountable. The voice is concise and specific, with the calm confidence of an experienced controller presenting an audit trail. It does not oversell model confidence or hide uncertainty.

## Anti-references

- Generic AI reconciliation dashboards that celebrate match volume without showing proof or ambiguity.
- Chatbot-first finance products that replace an operational workflow with a conversation pane.
- Flashy trading-terminal aesthetics, speculative neon fintech, decorative glass panels, and noisy live-data theatrics.
- Generic SaaS metric-card grids with no narrative distinction between normal matches, verified resolutions, and abstentions.
- Interfaces that imply real settlement, ERP write-back, or Razorpay capabilities the prototype does not perform.

## Design Principles

1. Lead with the safety outcome. Incorrect auto-resolution and human-review decisions must be visible before secondary performance metrics.
2. Make proof inspectable. Every resolved exception should connect allocation arithmetic, entity support, credit support, contradictions, and uniqueness in one readable audit trail.
3. Treat abstention as a first-class result. Human review must look intentional, precise, and useful, never like an error state.
4. Separate ordinary reconciliation from AI investigation. The interface should make it obvious that RemitProof starts only after the deterministic baseline stops.
5. Prefer operational clarity over decoration. Dense financial evidence should remain scannable, accessible, and credible under scrutiny.

## Accessibility & Inclusion

Target WCAG 2.2 AA. Do not rely on color alone for decision states, maintain keyboard-visible focus, support reduced motion, use readable numeric alignment, and keep essential evidence legible at 200% zoom and on narrow screens.
