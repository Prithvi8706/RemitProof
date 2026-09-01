"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { ArrowRight, Check, CircleAlert, GitCompareArrows, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { BenchmarkData, DashboardData } from "@/lib/types";
import { formatPercent } from "@/lib/format";
import { ResearchNav } from "./ResearchNav";
import { ResearchRuntime } from "./ResearchRuntime";

const EvidenceScene = dynamic(() => import("./EvidenceScene"), { ssr: false });
const spring = { type: "spring" as const, stiffness: 260, damping: 34, mass: 0.8 };

function EvidenceFallback() {
  return (
    <svg className="research-evidence-svg" viewBox="0 0 1000 400" role="img" aria-label="Several financially valid allocations diverge, while verified evidence uniquely supports one proposal">
      <path d="M40 310 C260 250 360 80 540 235 S790 330 960 278" className="hypothesis-line dashed" />
      <path d="M40 310 C240 270 370 330 530 190 S790 210 960 240" className="hypothesis-line dashed" />
      <path d="M40 310 C245 270 350 160 520 110 S780 48 960 60" className="verified-line" />
      <circle cx="960" cy="60" r="7" className="verified-point" />
      <text x="40" y="350">PROPOSAL</text><text x="960" y="38" textAnchor="end">VERIFIED EVIDENCE</text><text x="960" y="350" textAnchor="end">ALTERNATIVES ELIMINATED</text>
    </svg>
  );
}

export function ResearchHome({ dashboard, benchmark }: { dashboard: DashboardData; benchmark: BenchmarkData }) {
  const [webgl, setWebgl] = useState(false);
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
      const large = matchMedia("(min-width: 1024px)").matches;
      try {
        const canvas = document.createElement("canvas");
        setWebgl(Boolean(!reduced && large && (canvas.getContext("webgl2") || canvas.getContext("webgl"))));
      } catch { setWebgl(false); }
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  const stages = [
    ["01", "Proposal", "AI constructs one structured hypothesis from the unresolved receipt."],
    ["02", "Financial proof", "Decimal arithmetic, state, currency, entity, credit, and duplicate checks run independently."],
    ["03", "Alternative search", "Every financially valid allocation inside the bounded candidate set is enumerated."],
    ["04", "Evidence compared", "Each cited record is tested against the proposal and every competing allocation."],
    ["05", "Authorize or block", "Only uniquely supported, non-conflicting explanations may resolve."],
  ];

  return (
    <div className="research-site" id="top">
      <a href="#main-content" className="research-skip">Skip to content</a>
      <ResearchRuntime />
      <ResearchNav />
      <main id="main-content">
        <section className="research-hero" aria-labelledby="research-title">
          <div className="research-hero-inner">
            <motion.div className="research-hero-left" initial="hidden" animate="show" variants={{ hidden:{}, show:{ transition:{ staggerChildren:0.14, delayChildren:0.15 } } }}>
              <motion.p variants={{ hidden:{opacity:0,y:22},show:{opacity:1,y:0,transition:spring} }} className="research-kicker">Adversarial verification for financial AI</motion.p>
              <motion.h1 id="research-title" variants={{ hidden:{opacity:0,y:22},show:{opacity:1,y:0,transition:spring} }}>RemitProof</motion.h1>
              <motion.p variants={{ hidden:{opacity:0,y:22},show:{opacity:1,y:0,transition:spring} }} className="research-subtitle">AI proposes. RemitProof verifies.</motion.p>
              <motion.div variants={{ hidden:{opacity:0,y:22},show:{opacity:1,y:0,transition:spring} }} className="research-hero-actions">
                <Link href="/exceptions/PAY_051" className="research-primary-cta">Explore PAY_051 <ArrowRight className="size-4" /></Link>
                <Link href="#method" className="research-text-link">Read the method</Link>
              </motion.div>
            </motion.div>
            <div className="research-metal-divider" aria-hidden="true" />
            <motion.div className="research-hero-thesis" initial={{opacity:0,y:22}} animate={{opacity:1,y:0}} transition={{...spring,delay:0.55}}>
              <p className="research-thesis-line"><em>Plausible is not justified.</em></p>
              <p>An allocation can balance perfectly while another valid explanation survives.</p>
              <p>RemitProof searches for that conflict, then asks which evidence actually distinguishes the alternatives.</p>
            </motion.div>
          </div>
          <figure className="research-hero-figure">
            <div className="research-scene">{webgl ? <EvidenceScene /> : <EvidenceFallback />}</div>
            <figcaption><span>FIGURE 01</span> Evidence must eliminate every competing financial explanation before authorization.</figcaption>
          </figure>
          <div className="research-hero-fade" aria-hidden="true" />
        </section>

        <section className="research-method-statement" id="method">
          <p className="research-kicker">CONTROL OBJECTIVE</p>
          <p>A financial explanation is safe only when the available evidence <em>uniquely supports it</em> over every competing explanation that satisfies the same financial constraints.</p>
        </section>

        <section className="research-program" aria-labelledby="program-title">
          <header className="research-section-header">
            <div><p className="research-kicker">PAY_051 · RESOLVED AFTER INVESTIGATION</p><span className="research-classification">VERIFIER PIPELINE</span></div>
            <h2 id="program-title">From proposal to authorization.</h2>
            <p>The model never emits the final decision. Deterministic proof, alternative enumeration, and evidence sufficiency own that boundary.</p>
          </header>
          <ol className="research-stage-track">
            {stages.map(([number,title,copy]) => <li key={number}><span>{number}</span><h3>{title}</h3><p>{copy}</p></li>)}
          </ol>
          <figure className="research-proof-figure">
            <div className="research-proof-grid">
              <div><p className="research-kicker">PROPOSAL A</p><strong>INV_X051A + INV_X051B</strong><span>$14,763.00</span></div>
              <GitCompareArrows aria-hidden="true" />
              <div><p className="research-kicker">ALTERNATIVE B</p><strong>INV_X051C + INV_X051D</strong><span>$14,763.00</span></div>
            </div>
            <div className="research-evidence-result"><ShieldCheck aria-hidden="true" /><div><strong>EMAIL_X051 uniquely supports Proposal A.</strong><p>Without this evidence, both allocations survive and the system abstains.</p></div></div>
            <figcaption><span>FIGURE 02</span> Equal arithmetic outcomes, unequal evidentiary support.</figcaption>
          </figure>
        </section>

        <section className="research-benchmark" id="benchmark" aria-labelledby="benchmark-title">
          <header><p className="research-kicker">FROZEN SYNTHETIC REGRESSION CORPUS</p><h2 id="benchmark-title">Measured safety behavior.</h2><p>Values below come from the committed evaluator artifacts. Cached proposal replay excludes model inference time.</p></header>
          <div className="research-metric-ledger">
            <div><span>Incorrect auto-resolution</span><strong>{formatPercent(benchmark.incorrect_auto_resolution_rate,1)}</strong></div>
            <div><span>Correct abstention</span><strong>{formatPercent(benchmark.correct_abstention_rate,1)}</strong></div>
            <div><span>Alternative detection</span><strong>{formatPercent(benchmark.alternative_detection_accuracy,1)}</strong></div>
            <div><span>Contradiction detection</span><strong>{formatPercent(benchmark.contradiction_detection_accuracy,1)}</strong></div>
          </div>
          <figure className="research-comparison">
            {[benchmark.comparison.baseline,benchmark.comparison.llm_only,benchmark.comparison.remitproof].map((system,index) => {
              const names=["Baseline","Proposal only","RemitProof"];
              return <div key={names[index]} className={index===2?"is-remitproof":""}><h3>{names[index]}</h3><div className="research-bar"><i style={{width:`${(system.wrong_auto_resolutions/Math.max(system.resolved,1))*100}%`}} /><b style={{width:`${(system.correct_resolutions/Math.max(system.resolved,1))*100}%`}} /></div><dl><div><dt>Correct</dt><dd>{system.correct_resolutions}</dd></div><div><dt>Wrong</dt><dd>{system.wrong_auto_resolutions}</dd></div><div><dt>Abstained</dt><dd>{system.correct_abstentions}</dd></div></dl></div>;
            })}
            <figcaption><span>FIGURE 03</span> Comparison restricted to {benchmark.comparison_record_count} unresolved exceptions.</figcaption>
          </figure>
        </section>

        <section className="research-cases" aria-labelledby="cases-title">
          <header><p className="research-kicker">THREE CONTROL OUTCOMES</p><h2 id="cases-title">Justified, ambiguous, contradicted.</h2></header>
          <div className="research-case-row">
            <CaseLink href="/exceptions/PAY_051" state="JUSTIFIED" id="PAY_051" icon={<Check />} copy="Two allocations balance. Remittance evidence uniquely selects one." />
            <CaseLink href="/exceptions/PAY_052" state="AMBIGUOUS" id="PAY_052" icon={<CircleAlert />} copy="Two allocations remain plausible. No evidence establishes payer intent." />
            <CaseLink href="/exceptions/PAY_056" state="CONTRADICTED" id="PAY_056" icon={<X />} copy="The proposed deduction fails against authoritative remittance evidence." />
          </div>
        </section>

        <section className="research-integrity" id="integrity">
          <p className="research-kicker">INTEGRITY NOTE</p>
          <blockquote>RemitProof does not choose the most likely answer. It proves a financial action is justified, or it blocks it.</blockquote>
          <p>{dashboard.total_receipts} synthetic receipts. {dashboard.matched_normally} resolved normally. {dashboard.exceptions} investigated exceptions. No production posting or settlement.</p>
        </section>
      </main>
      <footer className="research-footer"><div><h2>Inspect the evidence.</h2><Link href="/exceptions">Open exception library</Link></div><p>All displayed values come from committed synthetic benchmark artifacts. The model proposes; deterministic code authorizes.</p></footer>
    </div>
  );
}

function CaseLink({href,state,id,icon,copy}:{href:string;state:string;id:string;icon:React.ReactNode;copy:string}) {
  return <article><div className="research-case-state">{icon}<span>{state}</span></div><h3>{id}</h3><p>{copy}</p><Link href={href}>Inspect case <ArrowRight className="size-4" /></Link></article>;
}
