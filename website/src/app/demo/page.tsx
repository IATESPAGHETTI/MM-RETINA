"use client";

import { useState } from "react";
import { GlassCard } from "@/components/GlassCard";
import { DemoBadge } from "@/components/DemoBadge";
import { Reveal } from "@/components/Reveal";

export default function DemoPage() {
  const [attempted, setAttempted] = useState(false);

  return (
    <div className="pt-20">
      <section className="mx-auto max-w-3xl px-6 pt-20 pb-8 text-center">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Demo</p>
          <h1 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            Inference demo
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-ink-muted">
            Research prototype. Not for clinical diagnosis.
          </p>
        </Reveal>
      </section>

      <section className="mx-auto max-w-2xl px-6 py-8">
        <Reveal className="mb-6 flex justify-center">
          <DemoBadge text="No inference backend connected yet" />
        </Reveal>

        <Reveal delay={0.1}>
          <GlassCard strong>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => setAttempted(true)}
                className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/20 p-8 text-center transition-colors hover:border-white/40 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
              >
                <span className="text-sm font-medium text-ink">Drop OCT volume</span>
                <span className="text-xs text-ink-faint">or click to select</span>
              </button>
              <button
                type="button"
                onClick={() => setAttempted(true)}
                className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/20 p-8 text-center transition-colors hover:border-white/40 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
              >
                <span className="text-sm font-medium text-ink">Drop fundus image</span>
                <span className="text-xs text-ink-faint">or click to select</span>
              </button>
            </div>

            <button
              type="button"
              onClick={() => setAttempted(true)}
              disabled
              className="mt-6 w-full cursor-not-allowed rounded-full bg-white/20 px-6 py-3 text-sm font-medium text-white/50"
            >
              Run inference
            </button>

            {attempted && (
              <p className="mt-4 rounded-lg border border-amber-300/20 bg-amber-300/10 p-3 text-sm text-amber-200">
                This is a UI preview only. No model is deployed behind this
                page yet, so no prediction is generated — showing one here
                would misrepresent an untrained/unconnected system as a real
                result.
              </p>
            )}
          </GlassCard>
        </Reveal>

        <Reveal delay={0.2} className="mt-6">
          <p className="text-center text-xs text-ink-faint">
            Once a trained model is served behind an API, this page will send
            the uploaded OCT volume and fundus image there and render the
            actual returned grade, confidence, and Grad-CAM attribution —
            never a hardcoded example.
          </p>
        </Reveal>
      </section>
    </div>
  );
}
