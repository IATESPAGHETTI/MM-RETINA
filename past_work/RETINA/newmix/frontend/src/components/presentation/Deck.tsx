"use client";

import Link from "next/link";
import { ReactNode, useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { SLIDES } from "./slides";
import { EASE } from "./primitives";

const subscribeHash = (cb: () => void) => {
  window.addEventListener("hashchange", cb);
  return () => window.removeEventListener("hashchange", cb);
};
const readHash = () => {
  const n = parseInt(window.location.hash.slice(1), 10);
  return Number.isNaN(n) ? 0 : Math.max(0, Math.min(SLIDES.length - 1, n - 1));
};

const CANVAS_W = 1280;
const MAX_SCALE = 1.35;

/** Lays the slide out on a fixed-width canvas, then scales it to fit the stage — so slides never scroll. */
function Fit({ children }: { children: ReactNode }) {
  const areaRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState<{ scale: number; h: number } | null>(null);

  useEffect(() => {
    const area = areaRef.current;
    const inner = innerRef.current;
    if (!area || !inner) return;
    const measure = () => {
      const h = inner.offsetHeight;
      const scale = Math.min((area.clientWidth - 16) / CANVAS_W, (area.clientHeight - 40) / h, MAX_SCALE);
      setBox({ scale, h });
    };
    const ro = new ResizeObserver(measure);
    ro.observe(area);
    ro.observe(inner);
    return () => ro.disconnect();
  }, []);

  const scale = box?.scale ?? 1;
  return (
    <div ref={areaRef} className="flex h-full w-full items-center justify-center overflow-hidden">
      <div style={{ width: CANVAS_W * scale, height: (box?.h ?? 0) * scale, opacity: box ? 1 : 0 }} className="shrink-0 transition-opacity duration-200">
        <div ref={innerRef} style={{ width: CANVAS_W, transform: `scale(${scale})`, transformOrigin: "top left" }} className="@container py-6">
          {children}
        </div>
      </div>
    </div>
  );
}

const PRESENTATION_ONLY = process.env.NEXT_PUBLIC_PRESENTATION_ONLY === "1";

export function Deck() {
  // The URL hash is the source of truth, so /presentation#5 deep-links and Back steps through slides.
  const index = useSyncExternalStore(subscribeHash, readHash, () => 0);
  const [dir, setDir] = useState(1);
  const touchX = useRef<number | null>(null);
  const last = SLIDES.length - 1;

  const go = useCallback(
    (next: number) => {
      const n = Math.max(0, Math.min(last, next));
      if (n === readHash()) return;
      setDir(n > readHash() ? 1 : -1);
      window.location.hash = `#${n + 1}`;
    },
    [last],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") {
        e.preventDefault();
        go(index + 1);
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        go(index - 1);
      } else if (e.key === "Home") go(0);
      else if (e.key === "End") go(last);
      else if (e.key.toLowerCase() === "f") {
        if (document.fullscreenElement) void document.exitFullscreen();
        else void document.documentElement.requestFullscreen?.();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, index, last]);

  const slide = SLIDES[index];

  return (
    <div
      className="fixed inset-0 z-[70] overflow-hidden bg-bg text-ink"
      onTouchStart={(e) => (touchX.current = e.touches[0].clientX)}
      onTouchEnd={(e) => {
        if (touchX.current === null) return;
        const dx = e.changedTouches[0].clientX - touchX.current;
        touchX.current = null;
        if (Math.abs(dx) > 50) go(index + (dx < 0 ? 1 : -1));
      }}
    >
      <div className="atmosphere" aria-hidden />
      <div className="noise" aria-hidden />

      {/* Top bar */}
      <header className="absolute inset-x-0 top-0 z-20 flex items-center justify-between px-5 py-4 sm:px-8">
        <Link href="/" className="flex items-center gap-2 text-sm font-semibold tracking-wide text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne">
          <span className="h-2 w-2 rounded-full bg-accent-champagne" aria-hidden />
          MM&#8209;RETINA
        </Link>
        <div className="flex items-center gap-4 text-sm text-ink-faint">
          <span className="hidden uppercase tracking-[0.2em] sm:inline">{slide.section}</span>
          <span className="tabular-nums text-ink-muted">
            {String(index + 1).padStart(2, "0")} / {String(SLIDES.length).padStart(2, "0")}
          </span>
          {!PRESENTATION_ONLY && (
            <Link href="/research/journey" className="rounded-full border border-white/12 px-3 py-1 text-ink-muted transition-colors hover:bg-white/5 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne">
            Exit
          </Link>
          )}
        </div>
      </header>

      {/* Slide stage */}
      <main
        id="deck-stage"
        aria-live="polite"
        className={`absolute inset-x-4 top-14 z-10 overflow-hidden bottom-16`}
      >
        <AnimatePresence mode="wait" custom={dir}>
          <motion.section
            key={slide.id}
            custom={dir}
            aria-label={`Slide ${index + 1}: ${slide.section}`}
            initial={{ opacity: 0, x: dir * 48 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: dir * -48 }}
            transition={{ duration: 0.45, ease: EASE }}
            className="h-full"
          >
            <Fit>{slide.render()}</Fit>
          </motion.section>
        </AnimatePresence>
      </main>

      {/* Bottom controls */}
      <footer className="absolute inset-x-0 bottom-0 z-30 flex items-center justify-between gap-4 px-5 pb-4 sm:px-8">
        <nav aria-label="Slides" className="flex flex-1 items-center justify-center gap-1.5">
          {SLIDES.map((s, i) => (
            <button
              key={s.id}
              type="button"
              onClick={() => go(i)}
              aria-label={`Go to slide ${i + 1}`}
              aria-current={i === index}
              className="group py-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne"
            >
              <span
                className={`block h-1 rounded-full transition-all duration-300 ${
                  i === index ? "w-8 bg-accent-champagne" : i < index ? "w-4 bg-white/40 group-hover:bg-white/60" : "w-4 bg-white/15 group-hover:bg-white/35"
                }`}
              />
            </button>
          ))}
        </nav>

        <div className="flex gap-2">
          {[
            { label: "Previous slide", d: -1, glyph: "←", disabled: index === 0 },
            { label: "Next slide", d: 1, glyph: "→", disabled: index === last },
          ].map((b) => (
            <button
              key={b.label}
              type="button"
              aria-label={b.label}
              disabled={b.disabled}
              onClick={() => go(index + b.d)}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-white/12 text-sm text-ink-muted transition-colors hover:bg-white/5 hover:text-ink disabled:opacity-30 disabled:hover:bg-transparent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
            >
              {b.glyph}
            </button>
          ))}
        </div>
      </footer>
    </div>
  );
}
