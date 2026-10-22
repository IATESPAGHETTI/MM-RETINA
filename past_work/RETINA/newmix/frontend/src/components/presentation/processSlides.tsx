"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";
import { In, SlideFrame, Pill, EASE, pct } from "./primitives";
import { PipelineDiagram, BASE_PIPELINE } from "./PipelineDiagram";
import { LADDER, BASELINE, METRIC_LABELS, type MetricKey, type Verdict as VerdictKind } from "@/lib/presentationContent";

const VERDICT_TONE: Record<VerdictKind, "neutral" | "gold" | "copper" | "olive"> = {
  baseline: "neutral",
  rejected: "copper",
  adopted: "gold",
  inconclusive: "olive",
};

const DELTA_KEYS: MetricKey[] = ["accuracy", "balancedAccuracy", "macroF1", "rocAuc"];

const exp = (id: string) => LADDER.find((e) => e.id === id)!;

/** Metric chips showing an experiment's score and its change (in points) against the frozen baseline. */
function ResultChips({ id, keys = DELTA_KEYS }: { id: string; keys?: MetricKey[] }) {
  const e = exp(id);
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-4">
      {keys.map((k) => {
        const d = (e.metrics[k] - BASELINE.metrics[k]) * 100;
        return (
          <div key={k}>
            <p className="text-sm uppercase tracking-[0.15em] text-ink-faint">{METRIC_LABELS[k]}</p>
            <p className="mt-1 flex items-baseline gap-2">
              <span className="text-3xl font-semibold tabular-nums text-ink">{pct(e.metrics[k])}</span>
              <span className={`text-lg font-medium tabular-nums ${d >= 0 ? "text-accent-champagne" : "text-accent-copper"}`}>
                {d >= 0 ? "+" : ""}
                {d.toFixed(1)}
              </span>
            </p>
          </div>
        );
      })}
    </div>
  );
}

function Col({ label, children, delay }: { label: string; children: ReactNode; delay: number }) {
  return (
    <In delay={delay} className="border-t border-white/10 pt-4">
      <p className="mb-3 text-sm uppercase tracking-[0.22em] text-accent-champagne">{label}</p>
      {children}
    </In>
  );
}

function Decision({ id, children }: { id: string; children: ReactNode }) {
  const e = exp(id);
  return (
    <div>
      <Pill tone={VERDICT_TONE[e.verdict]}>{e.verdictLabel}</Pill>
      <p className="mt-3 text-lg leading-snug text-ink-muted">{children}</p>
    </div>
  );
}

const Why = ({ children }: { children: ReactNode }) => <p className="text-lg leading-snug text-ink-muted">{children}</p>;

export function FusionExplainedSlide() {
  const rows = [
    { name: "Fundus only", acc: 0.73, auc: 0.876, sd: "±15.6" },
    { name: "OCT only", acc: 0.661, auc: 0.842, sd: "±8.9" },
    { name: "Fusion", acc: 0.71, auc: 0.892, sd: "±5.2" },
  ];
  return (
    <SlideFrame compact kicker="Step 1 · The starting model" title="How fusion works — EXP-01, the frozen baseline.">
      <PipelineDiagram config={BASE_PIPELINE} />
      <div className="mt-6 grid gap-8 @lg:grid-cols-2">
        <Col label="What happens" delay={0.6}>
          <ol className="space-y-2 text-lg leading-snug text-ink-muted">
            <li><span className="text-ink">1.</span> Each modality gets its own encoder → one vector.</li>
            <li><span className="text-ink">2.</span> A small transformer lets fundus and OCT vectors attend to each other.</li>
            <li><span className="text-ink">3.</span> One severity grade comes out. Focal loss + class weights handle imbalance.</li>
          </ol>
        </Col>
        <Col label="Why fusion · first CV comparison" delay={0.7}>
          <div className="space-y-2">
            {rows.map((r) => (
              <div key={r.name} className="grid grid-cols-[8rem_1fr_1fr_1fr] gap-2 text-lg">
                <span className={r.name === "Fusion" ? "text-accent-champagne" : "text-ink-muted"}>{r.name}</span>
                <span className="tabular-nums text-ink">{pct(r.acc)} <span className="text-sm text-ink-faint">acc</span></span>
                <span className="tabular-nums text-ink">{pct(r.auc)} <span className="text-sm text-ink-faint">AUC</span></span>
                <span className="tabular-nums text-ink-faint">{r.sd} SD</span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-base text-ink-faint">Fusion: best AUC and the steadiest folds.</p>
        </Col>
      </div>
    </SlideFrame>
  );
}

export function Exp02Slide() {
  return (
    <SlideFrame compact kicker="Step 2 · EXP-02 · Change the OCT input" title="2.5D: give each OCT slice its two neighbours.">
      <PipelineDiagram
        config={{
          ...BASE_PIPELINE,
          sampler: { title: "8 slices × 3-slice stacks", sub: "[i−1, i, i+1] as 3 channels" },
          changed: ["sampler"],
        }}
      />
      <div className="mt-6 grid gap-8 @lg:grid-cols-3">
        <Col label="Why we tried it" delay={0.6}>
          <Why>On the OCT-only model, 2.5D beat single slices cleanly (66.1% → 68.0% accuracy). Would it lift fusion too?</Why>
        </Col>
        <Col label="Result vs baseline" delay={0.7}>
          <ResultChips id="EXP-02" />
        </Col>
        <Col label="Decision" delay={0.8}>
          <Decision id="EXP-02">The OCT-only win didn&apos;t transfer. ROC-AUC tied, but F1 and balanced accuracy fell.</Decision>
        </Col>
      </div>
    </SlideFrame>
  );
}

export function SlicesSlide() {
  return (
    <SlideFrame compact kicker="Step 3 · EXP-03 & EXP-04 · Change the OCT input" title="More slices: 8 → 12 → 16. Did more OCT help?">
      <PipelineDiagram
        config={{
          ...BASE_PIPELINE,
          sampler: { title: "12 → 16 single slices", sub: "denser coverage of the macula" },
          octEnc: { title: "ResNet18 + attention pool", sub: "12 / 16 slice vectors → 1" },
          changed: ["sampler"],
        }}
      />
      <div className="mt-6 grid gap-8 @lg:grid-cols-3">
        <Col label="Why we tried it" delay={0.6}>
          <Why>More B-scans should cover more of the retina. Everything else held identical.</Why>
        </Col>
        <Col label="Accuracy" delay={0.7}>
          <div className="space-y-3">
            {[
              { id: "EXP-01", label: "8 slices" },
              { id: "EXP-03", label: "12 slices" },
              { id: "EXP-04", label: "16 slices" },
            ].map((r) => (
              <div key={r.id} className="grid grid-cols-[6rem_1fr_4rem] items-center gap-3">
                <span className="text-lg text-ink-muted">{r.label}</span>
                <div className="h-3 rounded-sm bg-white/[0.05]">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${exp(r.id).metrics.accuracy * 100}%` }}
                    transition={{ duration: 0.9, delay: 0.8, ease: EASE }}
                    className={`h-full rounded-sm ${r.id === "EXP-01" ? "bg-white/35" : "bg-accent-copper/70"}`}
                  />
                </div>
                <span className="text-right text-lg tabular-nums text-ink">{pct(exp(r.id).metrics.accuracy)}</span>
              </div>
            ))}
          </div>
        </Col>
        <Col label="Decision" delay={0.8}>
          <Decision id="EXP-03">Steadily worse. With 100 patients, extra slices likely add overfitting capacity, not signal.</Decision>
        </Col>
      </div>
    </SlideFrame>
  );
}

export function Exp05Slide() {
  return (
    <SlideFrame compact kicker="Step 4 · EXP-05 · Change the fundus encoder" title="The breakthrough: swap ResNet18 for EfficientNet-B0.">
      <PipelineDiagram
        config={{
          ...BASE_PIPELINE,
          fundusEnc: { title: "EfficientNet-B0", sub: "4.01M parameters — 2.8× smaller" },
          changed: ["fundusEnc"],
        }}
      />
      <div className="mt-6 grid gap-8 @lg:grid-cols-3">
        <Col label="Why we tried it" delay={0.6}>
          <Why>OCT depth wasn&apos;t the bottleneck, so we looked at the fundus branch. EfficientNet-B0 is a more parameter-efficient backbone.</Why>
        </Col>
        <Col label="Result vs baseline" delay={0.7}>
          <ResultChips id="EXP-05" />
        </Col>
        <Col label="Decision" delay={0.8}>
          <Decision id="EXP-05">All six metrics improved, on essentially every fold. Frozen as the reference model.</Decision>
        </Col>
      </div>
    </SlideFrame>
  );
}

export function Exp06Slide() {
  return (
    <SlideFrame compact kicker="Step 5 · EXP-06 · Change the fusion" title="Token fusion: keep the detail instead of pooling.">
      <PipelineDiagram
        config={{
          ...BASE_PIPELINE,
          fundusEnc: { title: "EfficientNet-B0", sub: "spatial feature map → 25 tokens" },
          octEnc: { title: "ResNet18", sub: "one token per slice, no pooling" },
          fusion: { title: "Token transformer", sub: "25 fundus + 8 OCT tokens · 2 layers" },
          changed: ["fusion"],
        }}
      />
      <div className="mt-6 grid gap-8 @lg:grid-cols-3">
        <Col label="Why we tried it" delay={0.6}>
          <Why>Pooling each modality to one vector throws away spatial detail. Let a transformer see all of it.</Why>
        </Col>
        <Col label="Result vs baseline (EXP-01)" delay={0.7}>
          <ResultChips id="EXP-06" />
          <p className="mt-3 text-base text-ink-faint">vs EXP-05: ROC-AUC +1.1, but balanced acc. −2.1 and spread ~2× wider.</p>
        </Col>
        <Col label="Decision" delay={0.8}>
          <Decision id="EXP-06">Higher AUC, but less stable and lower balanced accuracy. EXP-05 stays frozen.</Decision>
        </Col>
      </div>
    </SlideFrame>
  );
}
