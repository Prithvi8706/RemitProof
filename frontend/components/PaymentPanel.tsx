import { Building2, CalendarDays, Landmark, ReceiptText } from "lucide-react";
import { formatMoney } from "@/lib/format";
import type { PaymentRecord } from "@/lib/types";

export function PaymentPanel({ payment }: { payment: PaymentRecord }) {
  const rows = [
    { label: "Payer", value: payment.payer_name, icon: Building2 },
    { label: "Received", value: payment.date, icon: CalendarDays },
    { label: "Bank reference", value: payment.bank_reference || "Not supplied", icon: Landmark },
    { label: "Remittance reference", value: payment.remittance_reference || "Detached or missing", icon: ReceiptText },
  ];

  return (
    <section aria-labelledby="payment-title" className="border border-line bg-canvas">
      <div className="border-b border-line bg-surface px-5 py-4 sm:px-6">
        <h2 id="payment-title" className="text-sm font-semibold text-ink">Payment</h2>
      </div>
      <div className="px-5 py-6 sm:px-6">
        <div className="numeric text-4xl font-semibold tracking-[-0.035em] text-ink">
          {formatMoney(payment.amount, payment.currency)}
        </div>
        <dl className="mt-7 divide-y divide-line">
          {rows.map(({ label, value, icon: Icon }) => (
            <div key={label} className="grid gap-2 py-3.5 sm:grid-cols-[minmax(130px,0.42fr)_minmax(0,0.58fr)] sm:gap-4">
              <dt className="flex items-center gap-2 text-xs font-medium text-muted">
                <Icon className="size-3.5" aria-hidden="true" />
                {label}
              </dt>
              <dd className="min-w-0 break-words text-sm font-medium text-ink sm:text-right">{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
