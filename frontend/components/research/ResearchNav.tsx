"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const spring = { type: "spring" as const, stiffness: 260, damping: 34, mass: 0.8 };

export function ResearchNav() {
  const [open, setOpen] = useState<"evidence" | "about" | null>(null);
  const evidenceTrigger = useRef<HTMLButtonElement>(null);
  const aboutTrigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const trigger = open === "evidence" ? evidenceTrigger.current : aboutTrigger.current;
    const first = panel.current?.querySelector<HTMLElement>("a,button");
    first?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(null);
      if (event.key !== "Tab" || !panel.current) return;
      const items = Array.from(panel.current.querySelectorAll<HTMLElement>("a,button"));
      if (!items.length) return;
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      if (event.shiftKey && document.activeElement === firstItem) {
        event.preventDefault(); lastItem.focus();
      } else if (!event.shiftKey && document.activeElement === lastItem) {
        event.preventDefault(); firstItem.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); trigger?.focus(); };
  }, [open]);

  const links = open === "evidence"
    ? [["Case library", "/exceptions"], ["PAY_051 proof", "/exceptions/PAY_051"], ["PAY_052 conflict", "/exceptions/PAY_052"], ["PAY_056 contradiction", "/exceptions/PAY_056"]]
    : [["Method", "#method"], ["Benchmark", "#benchmark"], ["Integrity", "#integrity"]];

  return (
    <>
      <div className="research-nav-field" aria-hidden="true" />
      <header className="research-nav">
        <Link href="#top" className="research-wordmark">RemitProof</Link>
        <nav aria-label="Research site navigation" className="research-nav-actions">
          <button ref={evidenceTrigger} className="liquid-pill" onClick={() => setOpen(open === "evidence" ? null : "evidence")} aria-expanded={open === "evidence"} aria-haspopup="dialog">Evidence</button>
          <button ref={aboutTrigger} className="liquid-pill" onClick={() => setOpen(open === "about" ? null : "about")} aria-expanded={open === "about"} aria-haspopup="dialog">About</button>
        </nav>
      </header>
      <AnimatePresence>
        {open && (
          <>
            <motion.button className="research-scrim" aria-label="Close navigation menu" onClick={() => setOpen(null)} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            <motion.div ref={panel} role="dialog" aria-modal="true" aria-label={`${open} navigation`} className="research-nav-panel" initial={{ opacity: 0, scale: 0.3, borderRadius: 999, y: -16 }} animate={{ opacity: 1, scale: 1, borderRadius: 24, y: 0 }} exit={{ opacity: 0, scale: 0.3, borderRadius: 999, y: -16 }} transition={spring}>
              <button className="research-panel-close" onClick={() => setOpen(null)} aria-label="Close menu"><X className="size-4" /></button>
              <p className="research-kicker">{open === "evidence" ? "Decision records" : "Project context"}</p>
              <div className="research-panel-links">
                {links.map(([label, href], index) => (
                  <motion.div key={href} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + index * 0.018 }}>
                    <Link href={href} onClick={() => setOpen(null)}>{label}<ArrowUpRight className="size-3.5" /></Link>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
