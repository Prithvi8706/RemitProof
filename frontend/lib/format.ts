export function formatMoney(amount: string | number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(amount));
}

export function formatPercent(value: number, digits = 1): string {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function titleCase(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

const REASON_LABELS: Record<string, string> = {
  multiple_financially_valid_explanations:
    "Multiple financially valid explanations remain, and the available evidence does not select one.",
  contradictory_evidence:
    "The available records conflict. The allocation cannot be posted until the contradiction is resolved.",
  missing_credit_note:
    "A deduction was claimed, but a valid supporting credit note is missing.",
  unsupported_entity_relationship:
    "No explicit record supports the relationship between the payer and invoice customer.",
  unsupported_currency_mismatch:
    "Payment and invoice currencies differ. FX reconciliation is outside this prototype.",
  invoice_not_open: "A proposed invoice is no longer open and cannot receive this allocation.",
  duplicate_allocation_risk:
    "At least one record is already allocated, creating a duplicate-posting risk.",
  financial_mismatch:
    "The proposed invoices and valid credits do not equal the received payment.",
};

export function explainReason(reason: string): string {
  return REASON_LABELS[reason] ?? titleCase(reason);
}
