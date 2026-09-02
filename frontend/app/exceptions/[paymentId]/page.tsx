import { ArrowLeft, CircleCheck, Info, LockKeyhole } from "lucide-react";
import Link from "next/link";
import { AlternativesPanel } from "@/components/AlternativesPanel";
import { AppFooter } from "@/components/AppFooter";
import { AppHeader } from "@/components/AppHeader";
import { DecisionPanel } from "@/components/DecisionPanel";
import { EvidencePanel } from "@/components/EvidencePanel";
import { EvidenceAlternativeMatrix } from "@/components/EvidenceAlternativeMatrix";
import { InvestigationPath } from "@/components/InvestigationPath";
import { PaymentPanel } from "@/components/PaymentPanel";
import { ProposalPanel } from "@/components/ProposalPanel";
import { ProofPanel } from "@/components/ProofPanel";
import { ApiError, getException } from "@/lib/api";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function ExceptionDetailPage({
  params,
}: {
  params: Promise<{ paymentId: string }>;
}) {
  const { paymentId } = await params;
  let detail;
  try {
    detail = await getException(paymentId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
  const isResolved = detail.decision.decision === "resolved";
  const missingEvidenceIds = Array.from(
    new Set([
      ...(detail.proof?.missing_required_evidence ?? []),
      ...(detail.sufficiency?.missing_required_evidence ?? []),
    ]),
  );

  return (
    <div className="case-site min-h-screen bg-canvas">
      <AppHeader />
      <main className="mx-auto max-w-[1440px] px-4 py-8 sm:px-6 sm:py-10">
        <nav aria-label="Breadcrumb">
          <Link
            href="/"
            className="case-back-link inline-flex items-center gap-2 rounded-md py-1 text-sm font-semibold text-muted hover:text-primary"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to dashboard
          </Link>
        </nav>

        <header className="case-page-heading mt-7 flex flex-col gap-5 border-b border-line pb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-primary">Exception investigation</p>
            <h1 className="numeric mt-2 text-3xl font-semibold tracking-[-0.035em] text-ink sm:text-4xl">
              {detail.payment.payment_id}
            </h1>
            <p className="mt-2 max-w-[70ch] text-sm text-muted">
              A transaction case: proposal, claims, evidence, competing explanations, proof, and authorization decision.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-medium text-muted">
            <LockKeyhole className="size-4 text-primary" aria-hidden="true" />
            Read-only prototype decision
          </div>
        </header>

        <InvestigationPath detail={detail} />

        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          <PaymentPanel payment={detail.payment} />
          <ProposalPanel detail={detail} />
        </div>

        <div className="mt-12 grid gap-12 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)] lg:gap-16">
          <ProofPanel detail={detail} />
          <EvidencePanel
            citedEvidence={detail.model_cited_evidence}
            auditRecords={detail.audit_records}
            missingEvidenceIds={missingEvidenceIds}
            claims={detail.proposal?.semantic_claims ?? []}
          />
        </div>

        <EvidenceAlternativeMatrix detail={detail} />

        <div className="mt-12 grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)] lg:items-start">
          <AlternativesPanel
            alternatives={detail.alternatives}
            decision={detail.decision}
            sufficiency={detail.sufficiency}
            currency={detail.payment.currency}
          />
          <DecisionPanel detail={detail} />
        </div>

        <section
          className={`mt-12 flex flex-col gap-4 border p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6 ${
            isResolved ? "border-primary/25 bg-primary-soft" : "border-warning/30 bg-warning-soft"
          }`}
          aria-label="Posting outcome"
        >
          <div className="flex items-start gap-3">
            {isResolved ? (
              <CircleCheck className="mt-0.5 size-5 shrink-0 text-primary-dark" aria-hidden="true" />
            ) : (
              <Info className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden="true" />
            )}
            <div>
              <h2 className="text-sm font-semibold text-ink">
                {isResolved ? "Resolution is supported" : "No posting action was taken"}
              </h2>
              <p className="mt-1 max-w-[72ch] text-sm leading-6 text-muted">
                {isResolved
                  ? "This prototype records a safe decision and audit trail. Production accounting write-back remains outside scope."
                  : "A controller must resolve the missing, conflicting, or non-unique evidence before this receipt can be allocated."}
              </p>
            </div>
          </div>
        </section>
      </main>
      <AppFooter />
    </div>
  );
}
