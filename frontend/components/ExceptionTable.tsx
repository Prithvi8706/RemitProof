import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { DecisionBadge } from "@/components/DecisionBadge";
import { formatMoney, titleCase } from "@/lib/format";
import type { ExceptionSummary } from "@/lib/types";

export function ExceptionTable({
  exceptions,
  caption = "Unresolved-payment investigations",
}: {
  exceptions: ExceptionSummary[];
  caption?: string;
}) {
  if (exceptions.length === 0) {
    return (
      <div className="border-y border-line bg-surface px-5 py-8 text-sm leading-6 text-muted">
        No exception investigations are available in this result set.
      </div>
    );
  }

  return (
    <div className="table-scroll border-y border-line">
      <table className="w-full min-w-[920px] border-collapse text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-surface text-xs font-semibold text-muted">
          <tr>
            <th className="px-4 py-3.5 sm:px-5" scope="col">Payment</th>
            <th className="px-4 py-3.5" scope="col">Payer</th>
            <th className="px-4 py-3.5 text-right" scope="col">Amount</th>
            <th className="px-4 py-3.5" scope="col">Exception class</th>
            <th className="px-4 py-3.5" scope="col">Decision</th>
            <th className="px-4 py-3.5 text-right sm:px-5" scope="col">Audit</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {exceptions.map((exception) => (
            <tr key={exception.payment_id} className="bg-canvas hover:bg-surface/70">
              <td className="px-4 py-4 font-semibold text-ink sm:px-5">
                <Link className="rounded-sm hover:text-primary" href={`/exceptions/${exception.payment_id}`}>
                  {exception.payment_id}
                </Link>
                <div className="mt-0.5 text-xs font-normal text-muted">{exception.date}</div>
              </td>
              <td className="max-w-[240px] px-4 py-4 text-ink">{exception.payer}</td>
              <td className="numeric whitespace-nowrap px-4 py-4 text-right font-semibold text-ink">
                {formatMoney(exception.amount, exception.currency)}
              </td>
              <td className="px-4 py-4 text-muted">{titleCase(exception.exception_class)}</td>
              <td className="px-4 py-4"><DecisionBadge decision={exception.decision} compact /></td>
              <td className="px-4 py-4 text-right sm:px-5">
                <Link
                  className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-semibold text-primary hover:bg-primary-soft"
                  href={`/exceptions/${exception.payment_id}`}
                >
                  View proof
                  <ArrowUpRight className="size-3.5" aria-hidden="true" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
