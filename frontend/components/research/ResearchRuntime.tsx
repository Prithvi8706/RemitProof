"use client";

import Lenis from "lenis";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useEffect, useRef } from "react";

export const scrollVelocity = { current: 0, target: 0 };

export function ResearchRuntime() {
  const left = useRef<HTMLDivElement>(null);
  const right = useRef<HTMLDivElement>(null);

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let lenis: Lenis | null = null;
    const tick = (time: number) => {
      lenis?.raf(time * 1000);
      scrollVelocity.current += (scrollVelocity.target - scrollVelocity.current) * 0.08;
      if (Math.abs(scrollVelocity.current) < 0.001 && Math.abs(scrollVelocity.target) < 0.001) {
        scrollVelocity.current = 0;
      }
    };

    if (!reduced) {
      lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 1, smoothWheel: true, anchors: true });
      lenis.on("scroll", ({ velocity }: { velocity: number }) => {
        scrollVelocity.target = gsap.utils.clamp(-1, 1, velocity * 0.018);
        ScrollTrigger.update();
      });
      gsap.ticker.add(tick);
      gsap.ticker.lagSmoothing(0);
    }

    const context = gsap.context(() => {
      if (reduced) return;
      gsap.to(left.current, {
        xPercent: 4,
        yPercent: 12,
        ease: "none",
        scrollTrigger: { trigger: document.documentElement, start: "top top", end: "bottom bottom", scrub: 0.6 },
      });
      gsap.to(right.current, {
        xPercent: -5,
        yPercent: -10,
        ease: "none",
        scrollTrigger: { trigger: document.documentElement, start: "top top", end: "bottom bottom", scrub: 0.6 },
      });
      gsap.fromTo(".research-hero-inner", { y: 0, opacity: 1 }, {
        y: "12vh", opacity: 0, ease: "none", immediateRender: false,
        scrollTrigger: { trigger: ".research-hero", start: "top top", end: "bottom top", scrub: true },
      });
      gsap.fromTo(".research-stage-track li", { opacity: 0.28, y: 18 }, {
        opacity: 1,
        y: 0,
        stagger: 0.08,
        ease: "none",
        scrollTrigger: { trigger: ".research-stage-track", start: "top 88%", end: "top 28%", scrub: 0.35 },
      });
      gsap.fromTo(".research-proof-figure", { opacity: 0.35, y: 20 }, {
        opacity: 1,
        y: 0,
        ease: "none",
        scrollTrigger: { trigger: ".research-proof-figure", start: "top 88%", end: "top 42%", scrub: 0.35 },
      });
      gsap.fromTo(".research-comparison .research-bar b, .research-comparison .research-bar i", { scaleX: 0 }, {
        scaleX: 1,
        transformOrigin: "left center",
        ease: "none",
        scrollTrigger: { trigger: ".research-comparison", start: "top 80%", end: "top 28%", scrub: 1 },
      });
    });

    let pointerFrame = 0;
    let activeGlass: HTMLElement | null = null;
    const onPointer = (event: PointerEvent) => {
      const target = (event.target as HTMLElement).closest<HTMLElement>(".liquid-pill,.research-nav-panel");
      if (!target || reduced) return;
      activeGlass = target;
      if (pointerFrame) return;
      pointerFrame = requestAnimationFrame(() => {
        if (!activeGlass) return;
        const bounds = activeGlass.getBoundingClientRect();
        activeGlass.style.setProperty("--mx", `${event.clientX - bounds.left}px`);
        activeGlass.style.setProperty("--my", `${event.clientY - bounds.top}px`);
        activeGlass.style.setProperty("--glow", "1");
        pointerFrame = 0;
      });
    };
    const onPointerOut = (event: PointerEvent) => {
      const target = (event.target as HTMLElement).closest<HTMLElement>(".liquid-pill,.research-nav-panel");
      target?.style.setProperty("--glow", "0");
    };
    document.addEventListener("pointermove", onPointer, { passive: true });
    document.addEventListener("pointerout", onPointerOut, { passive: true });

    return () => {
      context.revert();
      lenis?.destroy();
      gsap.ticker.remove(tick);
      document.removeEventListener("pointermove", onPointer);
      document.removeEventListener("pointerout", onPointerOut);
      if (pointerFrame) cancelAnimationFrame(pointerFrame);
      scrollVelocity.current = 0;
      scrollVelocity.target = 0;
    };
  }, []);

  return (
    <div className="research-background" aria-hidden="true">
      <div ref={left} className="research-light research-light-left" />
      <div ref={right} className="research-light research-light-right" />
    </div>
  );
}
