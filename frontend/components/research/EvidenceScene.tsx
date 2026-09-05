"use client";

import { useEffect, useRef, useState } from "react";
import { useInView, useReducedMotion } from "framer-motion";
import { ArrowDown, Check, Mail, Pause, Play, RotateCcw, ShieldCheck } from "lucide-react";

const captions = [
  "A payment arrives. Two allocations balance.",
  "The amount proves a match is possible. The email identifies the invoices.",
  "Evidence supports one allocation. RemitProof can authorize it.",
];

export default function EvidenceScene() {
  const ref = useRef<HTMLDivElement>(null);
  const visible = useInView(ref, { amount: 0.3 });
  const reduced = useReducedMotion();
  const [step, setStep] = useState(0);
  const [paused, setPaused] = useState(false);
  const activeStep = reduced ? 2 : step;

  useEffect(() => {
    if (!visible || reduced || paused || step === 2) return;
    const timer = setTimeout(() => setStep(value => value + 1), 3600);
    return () => clearTimeout(timer);
  }, [visible, reduced, paused, step]);

  return <div ref={ref} className="payment-scene" data-step={activeStep}>
    <div className="payment-scene-top"><span>Illustrative payment · USD</span><span className="payment-scene-status">{activeStep === 2 ? "Evidence verified" : "Authorization pending"}</span></div>
    <div className="payment-desk">
      <div className="payment-receipt">
        <span>Payment received</span><strong>$10,000<span>.00</span></strong>
        <div><span>Invoice reference</span><span>Not supplied</span></div>
      </div>
      <div className="payment-connector" aria-hidden="true"><ArrowDown /></div>
      <div className="payment-options">
        <article className="payment-option payment-option-a">
          <div className="payment-option-label"><span>Proposed allocation</span><Check size={15} /><span className="sr-only">Amount balances</span></div>
          <div className="payment-invoice"><span>Invoice A</span><strong>$6,000</strong></div>
          <div className="payment-invoice"><span>Invoice B</span><strong>$4,000</strong></div>
          <div className="payment-total"><span>Total</span><strong>$10,000</strong></div>
          <div className="payment-authorization"><ShieldCheck size={17} /><span>{activeStep === 2 ? "Supported by remittance" : "Waiting for evidence"}</span></div>
        </article>
        <span className="payment-or" aria-hidden="true">or</span>
        <article className="payment-option payment-option-b">
          <div className="payment-option-label"><span>Competing allocation</span><Check size={15} /><span className="sr-only">Amount balances</span></div>
          <div className="payment-invoice"><span>Invoice C</span><strong>$10,000</strong></div>
          <div className="payment-invoice payment-invoice-empty" aria-hidden="true"><span>—</span></div>
          <div className="payment-total"><span>Total</span><strong>$10,000</strong></div>
          <div className="payment-authorization"><span>{activeStep === 2 ? "Not supported by remittance" : "Also financially valid"}</span></div>
        </article>
      </div>
      <div className="payment-email" aria-hidden={activeStep === 0}>
        <div><Mail size={18} /><span>Remittance instruction</span><span>From the payer</span></div>
        <p>“Please apply this payment to <mark>Invoice A and Invoice B</mark>.”</p>
      </div>
    </div>
    <div className="payment-scene-caption">
      <div><span className="payment-progress" aria-hidden="true">{[0,1,2].map(i => <i key={i} data-active={i <= activeStep} />)}</span><p>{captions[activeStep]}</p></div>
      {!reduced && <button type="button" onClick={() => { if (step === 2) { setStep(0); setPaused(false); } else setPaused(value => !value); }} aria-label={step === 2 ? "Replay payment illustration" : paused ? "Play payment illustration" : "Pause payment illustration"}>
        {step === 2 ? <RotateCcw size={15} /> : paused ? <Play size={15} /> : <Pause size={15} />}<span>{step === 2 ? "Replay" : paused ? "Play" : "Pause"}</span>
      </button>}
    </div>
  </div>;
}
