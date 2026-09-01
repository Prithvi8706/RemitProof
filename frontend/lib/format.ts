interface DecimalParts {
  integer: string;
  fraction: string;
  negative: boolean;
}

const MAX_DECIMAL_DIGITS = 10_000;

function parseDecimal(amount: string | number): DecimalParts {
  if (typeof amount === "number" && !Number.isFinite(amount)) {
    throw new RangeError("Monetary amount must be finite.");
  }

  const value = String(amount).trim();
  if (value.length > MAX_DECIMAL_DIGITS) {
    throw new RangeError("Monetary amount is too large to format safely.");
  }
  const match = /^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) {
    throw new RangeError(`Invalid monetary amount: ${value || "(empty)"}`);
  }

  const sign = match[1];
  const sourceInteger = match[2] ?? "0";
  const sourceFraction = match[3] ?? match[4] ?? "";
  const exponent = Number(match[5] ?? "0");
  if (!Number.isSafeInteger(exponent)) {
    throw new RangeError("Monetary amount exponent is outside the supported range.");
  }
  if (Math.abs(exponent) > MAX_DECIMAL_DIGITS) {
    throw new RangeError("Monetary amount exponent is too large to format safely.");
  }

  const digits = `${sourceInteger}${sourceFraction}`;
  const decimalIndex = sourceInteger.length + exponent;
  let integer: string;
  let fraction: string;

  if (decimalIndex <= 0) {
    integer = "0";
    fraction = `${"0".repeat(-decimalIndex)}${digits}`;
  } else if (decimalIndex >= digits.length) {
    integer = `${digits}${"0".repeat(decimalIndex - digits.length)}`;
    fraction = "";
  } else {
    integer = digits.slice(0, decimalIndex);
    fraction = digits.slice(decimalIndex);
  }

  integer = integer.replace(/^0+(?=\d)/, "");
  const isZero = !/[1-9]/.test(`${integer}${fraction}`);
  return { integer, fraction, negative: sign === "-" && !isZero };
}

function roundDecimal(parts: DecimalParts, scale: number): DecimalParts {
  const retainedFraction = parts.fraction.slice(0, scale).padEnd(scale, "0");
  const retainedDigits = `${parts.integer}${retainedFraction}`.replace(/^0+(?=\d)/, "") || "0";
  const shouldRoundUp = parts.fraction.length > scale && parts.fraction[scale] >= "5";
  const coefficient = BigInt(retainedDigits) + (shouldRoundUp ? BigInt(1) : BigInt(0));
  const divisor = BigInt(10) ** BigInt(scale);
  const integer = (coefficient / divisor).toString();
  const fraction = scale === 0 ? "" : (coefficient % divisor).toString().padStart(scale, "0");

  return {
    integer,
    fraction,
    negative: parts.negative && coefficient !== BigInt(0),
  };
}

export function formatMoney(
  amount: string | number,
  currency: string,
  locale: Intl.LocalesArgument = "en-US",
): string {
  const normalizedCurrency = currency.trim().toUpperCase();
  const currencyDefaults = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: normalizedCurrency,
  }).resolvedOptions();
  const scale = currencyDefaults.maximumFractionDigits ?? 2;
  const rounded = roundDecimal(parseDecimal(amount), scale);
  const integer = BigInt(rounded.integer);
  const templateValue = rounded.negative ? (integer === BigInt(0) ? -0 : -integer) : integer;
  const formatter = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: normalizedCurrency,
    minimumFractionDigits: scale,
    maximumFractionDigits: scale,
  });

  return formatter
    .formatToParts(templateValue)
    .map((part) => (part.type === "fraction" ? rounded.fraction : part.value))
    .join("");
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
