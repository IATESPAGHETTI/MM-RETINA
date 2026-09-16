"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type OCTViewerProps = {
  sampleId: string;
  numSlices: number;
  className?: string;
};

/** Real, interactive OCT B-scan viewer — drags through actual extracted
 * slices from a GAMMA .mhd/.raw volume (see dataset/extract_oct_slices.py),
 * not a stand-in animation. Frames are served as plain static JPEGs from
 * /public/oct-volume/<sampleId>/, so only the currently-viewed (and a small
 * look-ahead window of) slices are ever fetched — never the whole volume. */
export function OCTViewer({ sampleId, numSlices, className }: OCTViewerProps) {
  const [index, setIndex] = useState(Math.floor(numSlices / 2));
  const [playing, setPlaying] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const slicePath = (i: number) => `/oct-volume/${sampleId}/${String(i).padStart(3, "0")}.jpg`;

  // Prefetch a small neighborhood around the current slice so scrubbing
  // feels instant without ever loading all 256 frames at once.
  useEffect(() => {
    const preloadRange = 6;
    for (let d = -preloadRange; d <= preloadRange; d++) {
      const i = index + d;
      if (i < 0 || i >= numSlices) continue;
      const img = new window.Image();
      img.src = slicePath(i);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, numSlices, sampleId]);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % numSlices);
    }, 45);
    return () => clearInterval(id);
  }, [playing, numSlices]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowLeft") setIndex((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight") setIndex((i) => Math.min(numSlices - 1, i + 1));
      if (e.key === " ") {
        e.preventDefault();
        setPlaying((p) => !p);
      }
    },
    [numSlices]
  );

  return (
    <div
      ref={containerRef}
      className={className}
      role="group"
      aria-label={`Interactive OCT B-scan viewer, sample ${sampleId}`}
      tabIndex={0}
      onKeyDown={onKeyDown}
    >
      <div className="relative aspect-[320/620] w-full overflow-hidden rounded-2xl border border-white/8 bg-bg-elevated">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={slicePath(index)}
          alt={`OCT B-scan ${index + 1} of ${numSlices}, GAMMA sample ${sampleId}`}
          className="h-full w-full object-cover"
          draggable={false}
        />
        <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between p-4 font-mono text-[10px] uppercase tracking-wider text-ink-muted">
          <span>OCT volume — GAMMA {sampleId}</span>
          <span>
            B-scan {String(index + 1).padStart(3, "0")} / {numSlices}
          </span>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          onClick={() => {
            setPlaying(false);
            setIndex((i) => Math.max(0, i - 1));
          }}
          aria-label="Previous slice"
          className="rounded-full border border-white/12 p-2 text-ink-muted transition-colors hover:border-white/30 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path d="M15 19l-7-7 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        <button
          type="button"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? "Pause" : "Play through volume"}
          className="rounded-full border border-white/12 p-2 text-ink-muted transition-colors hover:border-white/30 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne"
        >
          {playing ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <rect x="6" y="5" width="4" height="14" />
              <rect x="14" y="5" width="4" height="14" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        <input
          type="range"
          min={0}
          max={numSlices - 1}
          value={index}
          onChange={(e) => {
            setPlaying(false);
            setIndex(Number(e.target.value));
          }}
          className="h-1 flex-1 cursor-pointer appearance-none rounded-full bg-white/10 accent-[var(--accent-champagne)]"
          aria-label="B-scan position"
        />

        <button
          type="button"
          onClick={() => {
            setPlaying(false);
            setIndex((i) => Math.min(numSlices - 1, i + 1));
          }}
          aria-label="Next slice"
          className="rounded-full border border-white/12 p-2 text-ink-muted transition-colors hover:border-white/30 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path d="M9 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
