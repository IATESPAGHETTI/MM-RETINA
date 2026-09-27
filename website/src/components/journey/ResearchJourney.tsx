"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Reveal } from "@/components/Reveal";
import { CountUp } from "./CountUp";
import { JourneyNav, JourneyMobileProgress } from "./JourneyNav";
import { Stage, Kicker, StageTitle, ExperimentCard, DecisionNote, MetricBarRow } from "./JourneyPieces";
import {
  EXP01,
  EXP05,
  EXP06,
  AUDIT,
  C01,
  C01B,
  EYE_CASE,
  RNFL_AUDIT_LAYERS,
  RNFL_CONCLUSION,
  M01,
  FINAL_STACK,
  CLOSING_LINE,
} from "@/lib/journeyContent";

const EASE = [0.16, 1, 0.3, 1] as const;

export function ResearchJourney() {
  return (
    <div className="relative">
      <JourneyNav />
      <JourneyMobileProgress />

      <HeroStage />
      <GammaStage />
      <Exp01Stage />
      <Exp05Stage />
      <Exp06Stage />
      <AuditStage />
      <C01Stage />
      <C01bStage />
      <EyeCaseStage />
      <RnflStage />
      <M01Stage />
      <ConclusionStage />
    </div>
  );
}

function HeroStage() {
  return (
    <Stage id="hero" className="flex min-h-[80vh] flex-col items-center justify-center text-center">
      <Reveal>
        <p className="mb-6 text-xs uppercase tracking-[0.3em] text-ink-faint">The research journey</p>
      </Reveal>
      <Reveal delay={0.1}>
        <h1 className="max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl">
          Can multiple retinal data sources
          <br className="hidden sm:block" /> teach a better glaucoma model?
        </h1>
      </Reveal>

      <Reveal delay={0.3} className="mt-16 flex flex-wrap items-center justify-center gap-4">
        {["Fundus", "OCT", "Clinical data"].map((label, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 + i * 0.15, duration: 0.7, ease: EASE }}
            className="glass rounded-full px-6 py-3 text-sm text-ink-muted"
          >
            {label}
          </motion.div>
        ))}
      </Reveal>

      <Reveal delay={0.9} className="mt-16 max-w-lg text-base leading-relaxed text-ink-muted">
        <p>Before combining anything, we checked whether the data could actually be combined.</p>
      </Reveal>
    </Stage>
  );
}

function GammaStage() {
  return (
    <Stage id="gamma">
      <Reveal>
        <Kicker>Stage 01 &middot; Start here</Kicker>
        <StageTitle>GAMMA: 100 labeled patients, two views per eye.</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-12">
        <div className="glass grid grid-cols-2 gap-6 rounded-2xl p-8 sm:grid-cols-4">
          {[
            { label: "Patients", value: "100" },
            { label: "Modalities", value: "Fundus + OCT" },
            { label: "Classes", value: "3" },
            { label: "Split", value: "5-fold, patient-level" },
          ].map((f) => (
            <div key={f.label}>
              <p className="text-xl font-semibold tracking-tight text-ink">{f.value}</p>
              <p className="mt-1 text-xs uppercase tracking-wide text-ink-faint">{f.label}</p>
            </div>
          ))}
        </div>
      </Reveal>

      <Reveal delay={0.25} className="mt-8 flex flex-wrap gap-3">
        {["Normal", "Early", "Progressive"].map((label) => (
          <span key={label} className="rounded-full border border-white/10 px-4 py-1.5 text-sm text-ink-muted">
            {label}
          </span>
        ))}
      </Reveal>

      <Reveal delay={0.35} className="mt-14 flex flex-col items-center gap-3 text-center text-sm text-ink-faint">
        <span>100 patients</span>
        <span aria-hidden>&darr;</span>
        <span>patient-level 5-fold CV</span>
        <span aria-hidden>&darr;</span>
        <span className="text-ink">baseline</span>
      </Reveal>
    </Stage>
  );
}

function Exp01Stage() {
  return (
    <Stage id="exp01">
      <Reveal>
        <Kicker>Stage 02 &middot; Frozen benchmark</Kicker>
        <StageTitle>{EXP01.id}</StageTitle>
      </Reveal>

      <div className="mt-14 grid grid-cols-1 gap-10 sm:grid-cols-2">
        <Reveal delay={0.1}>
          <p className="text-xs uppercase tracking-widest text-ink-faint">Accuracy</p>
          <CountUp value={EXP01.accuracy * 100} decimals={1} suffix="%" className="text-5xl font-semibold tracking-tight text-ink" />
        </Reveal>
        <Reveal delay={0.2}>
          <p className="text-xs uppercase tracking-widest text-ink-faint">ROC-AUC</p>
          <CountUp value={EXP01.rocAuc * 100} decimals={1} suffix="%" className="text-5xl font-semibold tracking-tight text-ink" />
        </Reveal>
      </div>

      <Reveal delay={0.35} className="mt-12 text-sm text-ink-muted">
        Baseline established.
      </Reveal>
    </Stage>
  );
}

function Exp05Stage() {
  const metrics: { label: string; value: number }[] = [
    { label: "Accuracy", value: EXP05.accuracy },
    { label: "Balanced Accuracy", value: EXP05.balancedAccuracy },
    { label: "Macro F1", value: EXP05.macroF1 },
    { label: "ROC-AUC", value: EXP05.rocAuc },
    { label: "Kappa", value: EXP05.kappa },
    { label: "QWK", value: EXP05.qwk },
  ];

  return (
    <Stage id="exp05">
      <Reveal>
        <Kicker>Stage 04 &middot; Breakthrough</Kicker>
        <StageTitle>{EXP05.id}</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-10 flex flex-wrap items-center gap-4 text-sm">
        <span className="rounded-full border border-white/15 px-4 py-1.5 text-ink-muted line-through decoration-white/30">
          ResNet18 fundus
        </span>
        <span aria-hidden className="text-ink-faint">
          &rarr;
        </span>
        <span className="rounded-full border border-accent-champagne/40 bg-accent-champagne/10 px-4 py-1.5 text-ink">
          EfficientNet-B0 fundus
        </span>
      </Reveal>

      <div className="mt-12 grid grid-cols-2 gap-x-8 gap-y-10 sm:grid-cols-3">
        {metrics.map((m, i) => (
          <Reveal key={m.label} delay={0.1 * i}>
            <p className="text-xs uppercase tracking-widest text-ink-faint">{m.label}</p>
            <CountUp
              value={m.value * 100}
              decimals={1}
              suffix="%"
              className={i === 0 ? "text-4xl font-semibold tracking-tight text-ink" : "text-2xl font-semibold tracking-tight text-ink"}
            />
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.6} className="mt-16 flex flex-col items-center gap-4 text-center">
        <span className="rounded-full border border-accent-champagne/50 bg-accent-champagne/10 px-4 py-1.5 text-xs uppercase tracking-[0.2em] text-accent-champagne">
          Frozen reference
        </span>
        <span aria-hidden className="text-2xl">
          &#128274;
        </span>
        <DecisionNote label={`Freeze ${EXP05.id}`}>{EXP05.result} {EXP05.decision}</DecisionNote>
      </Reveal>
    </Stage>
  );
}

function Exp06Stage() {
  return (
    <Stage id="exp06">
      <Reveal>
        <Kicker>Stage 05 &middot; Challenge</Kicker>
        <StageTitle>Can more sophisticated fusion do better?</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-10 flex flex-col items-center gap-3 text-center text-sm text-ink-faint">
        <span>Vector fusion</span>
        <span aria-hidden>&darr;</span>
        <span>Token-level fusion</span>
        <span aria-hidden>&darr;</span>
        <span className="text-ink">Transformer</span>
      </Reveal>

      <Reveal delay={0.3} className="mt-14 flex flex-col items-center gap-2 text-center">
        <p className="text-xs uppercase tracking-widest text-ink-faint">ROC-AUC</p>
        <p className="text-3xl font-semibold tracking-tight text-ink">
          {(EXP05.rocAuc * 100).toFixed(1)}% <span className="text-ink-faint">&rarr;</span> {(EXP06.rocAuc * 100).toFixed(1)}%
        </p>
      </Reveal>

      <Reveal delay={0.5} className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div className="text-center">
          <p className="text-xs uppercase tracking-widest text-ink-faint">Balanced Accuracy</p>
          <p className="mt-1 text-xl font-semibold text-ink">
            {(EXP05.balancedAccuracy * 100).toFixed(1)}% <span className="text-ink-faint">&rarr;</span> {(EXP06.balancedAccuracy * 100).toFixed(1)}%
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs uppercase tracking-widest text-ink-faint">Macro F1</p>
          <p className="mt-1 text-xl font-semibold text-ink">
            {(EXP05.macroF1 * 100).toFixed(1)}% <span className="text-ink-faint">&rarr;</span> {(EXP06.macroF1 * 100).toFixed(1)}%
          </p>
        </div>
      </Reveal>

      <Reveal delay={0.65} className="mx-auto mt-12 max-w-xl text-center text-sm leading-relaxed text-ink-muted">
        A higher ROC-AUC did not automatically mean a better overall or more stable model.
      </Reveal>

      <Reveal delay={0.75} className="mt-10">
        <ExperimentCard
          eyebrow={EXP06.id}
          title="Token-level fusion"
          summary={`Result: ${EXP06.result}`}
          detail={[
            { label: "Why", value: EXP06.why },
            { label: "Result", value: EXP06.result },
            { label: "Decision", value: EXP06.decision },
          ]}
        />
      </Reveal>

      <Reveal delay={0.85} className="mt-10 text-center text-sm text-ink-faint">
        {EXP05.id} remains frozen.
      </Reveal>
    </Stage>
  );
}

function AuditStage() {
  return (
    <Stage id="audit">
      <Reveal>
        <Kicker>Stage 06 &middot; The other data</Kicker>
        <StageTitle>But what about the other clinical data?</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-14">
        <NoFabricatedFusion />
      </Reveal>

      <Reveal delay={0.35} className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
        {[
          { name: "GAMMA", detail: `${AUDIT.gammaPatients} patients · ${AUDIT.gammaModalities}` },
          { name: "HVF", detail: `${AUDIT.hvfEyes} eyes / ${AUDIT.hvfPatients} patients` },
          { name: "RNFL/GCC", detail: `${AUDIT.rnflRows} eye-level rows` },
        ].map((d) => (
          <div key={d.name} className="glass rounded-2xl p-6 text-center">
            <p className="text-lg font-semibold text-ink">{d.name}</p>
            <p className="mt-1 text-xs text-ink-muted">{d.detail}</p>
          </div>
        ))}
      </Reveal>

      <Reveal delay={0.5} className="mt-14">
        <div className="mx-auto flex max-w-xl flex-col gap-3">
          {AUDIT.steps.map((step) => (
            <div key={step.label} className="flex items-center justify-between rounded-lg border border-white/8 px-4 py-3 text-sm">
              <span className="text-ink-muted">{step.label}</span>
              <span className={step.verified ? "text-accent-olive" : "text-ink-faint"}>
                {step.verified ? `✓ ${step.note ?? "verified"}` : "not found"}
              </span>
            </div>
          ))}
        </div>
      </Reveal>

      <Reveal delay={0.65} className="mt-16 text-center">
        <p className="text-5xl font-semibold tracking-tight text-ink">0</p>
        <p className="mt-2 text-sm text-ink-muted">verified HVF &harr; RNFL/GCC pairs</p>
      </Reveal>

      <Reveal delay={0.75} className="mt-10 text-center text-sm text-ink-muted">
        {AUDIT.gammaClinicalCoverage}.
      </Reveal>

      <Reveal delay={0.85} className="mt-8 text-center">
        <p className="text-lg font-semibold tracking-tight text-ink">No fabricated cohort.</p>
      </Reveal>
    </Stage>
  );
}

function NoFabricatedFusion() {
  const [joined, setJoined] = useState(false);
  return (
    <div className="flex flex-col items-center">
      <div className="flex w-full max-w-md items-end justify-between">
        {["GAMMA", "HVF", "RNFL/GCC"].map((name) => (
          <div key={name} className="flex flex-col items-center gap-2">
            <motion.span
              animate={{ y: joined ? 14 : 0 }}
              transition={{ duration: 0.6, ease: EASE }}
              className="h-2 w-2 rounded-full bg-accent-champagne"
            />
            <span className="text-xs text-ink-muted">{name}</span>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={() => setJoined((v) => !v)}
        className="mt-6 rounded-full border border-white/15 px-4 py-1.5 text-xs text-ink-muted transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
      >
        {joined ? "Reset" : "Try to join them"}
      </button>
      <AnimatePresence>
        {joined && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-4 max-w-xs text-center text-xs text-ink-faint"
          >
            No verified patient/eye/date key. We didn&apos;t force the join.
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

function C01Stage() {
  return (
    <Stage id="c01">
      <Reveal>
        <Kicker>Stage 07 &middot; The surprise</Kicker>
        <StageTitle>{C01.id}</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-10 flex flex-col items-center gap-2 text-center text-sm text-ink-faint">
        <span>HVF</span>
        <span aria-hidden>&darr;</span>
        <span>{C01.model}</span>
      </Reveal>

      <Reveal delay={0.3} className="mt-6 text-center">
        <CountUp value={C01.accuracy * 100} decimals={1} suffix="%" className="text-7xl font-semibold tracking-tight text-ink" />
        <p className="mt-2 text-sm text-ink-muted">Accuracy</p>
      </Reveal>

      <Reveal delay={0.55} className="mt-14 flex flex-wrap justify-center gap-3">
        {C01.features.map((f) => (
          <span key={f} className="rounded-full border border-accent-copper/40 bg-accent-copper/10 px-4 py-1.5 text-sm text-ink">
            {f}
          </span>
        ))}
      </Reveal>

      <Reveal delay={0.7} className="mx-auto mt-8 max-w-lg rounded-xl border border-accent-copper/30 bg-accent-copper/5 p-5 text-center text-sm leading-relaxed text-ink-muted">
        Wait. These features are closely related to the severity label.
      </Reveal>

      <Reveal delay={0.85} className="mt-8 text-center text-xs uppercase tracking-[0.2em] text-ink-faint">
        Label-proxy investigation &rarr; {C01.nextStep}
      </Reveal>
    </Stage>
  );
}

function C01bStage() {
  const [revealed, setRevealed] = useState(false);

  return (
    <Stage id="c01b">
      <Reveal>
        <Kicker>Stage 08 &middot; Removing the proxies</Kicker>
        <StageTitle>{C01B.id}</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-10 flex flex-wrap justify-center gap-3">
        {C01B.removed.map((f) => (
          <motion.span
            key={f}
            animate={revealed ? { opacity: 0.35, x: -6, textDecoration: "line-through" } : { opacity: 1, x: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="rounded-full border border-white/15 px-4 py-1.5 text-sm text-ink-muted"
          >
            {f} &times;
          </motion.span>
        ))}
      </Reveal>

      <div className="mt-14 flex justify-center">
        <button
          type="button"
          onClick={() => setRevealed(true)}
          disabled={revealed}
          className="rounded-full bg-white/95 px-6 py-2.5 text-sm font-medium text-black transition-transform hover:-translate-y-0.5 hover:shadow-lg disabled:cursor-default disabled:opacity-40 disabled:hover:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
        >
          {revealed ? "Proxies removed" : "Remove MD / PSD / VFI and rerun"}
        </button>
      </div>

      <div className="mx-auto mt-14 grid max-w-lg grid-cols-2 gap-8 text-center">
        <div>
          <p className="text-xs uppercase tracking-widest text-ink-faint">Accuracy</p>
          <p className="mt-2 text-4xl font-semibold tracking-tight text-ink">
            {revealed ? `${(C01B.accuracy * 100).toFixed(1)}%` : `${(C01.accuracy * 100).toFixed(1)}%`}
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-ink-faint">Balanced Accuracy</p>
          <p className="mt-2 text-4xl font-semibold tracking-tight text-ink">
            {revealed ? `${(C01B.balancedAccuracy * 100).toFixed(1)}%` : `${(C01.balancedAccuracy * 100).toFixed(1)}%`}
          </p>
        </div>
      </div>

      <AnimatePresence>
        {revealed && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="mx-auto mt-14 max-w-lg"
          >
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-ink-faint">
                  <th className="py-2 text-left font-normal">Experiment</th>
                  <th className="py-2 text-right font-normal">Accuracy</th>
                  <th className="py-2 text-right font-normal">Kappa</th>
                </tr>
              </thead>
              <tbody className="text-ink">
                <tr className="border-b border-white/5">
                  <td className="py-2">{C01.id}</td>
                  <td className="py-2 text-right tabular-nums">{(C01.accuracy * 100).toFixed(1)}%</td>
                  <td className="py-2 text-right tabular-nums">{C01.kappa.toFixed(3)}</td>
                </tr>
                <tr>
                  <td className="py-2">{C01B.id}</td>
                  <td className="py-2 text-right tabular-nums">{(C01B.accuracy * 100).toFixed(1)}%</td>
                  <td className="py-2 text-right tabular-nums">{C01B.kappa.toFixed(3)}</td>
                </tr>
              </tbody>
            </table>

            <p className="mx-auto mt-10 max-w-md text-center text-sm leading-relaxed text-ink-muted">
              The apparent {C01.id} performance was largely driven by severity-related proxy variables.
            </p>

            <p className="mx-auto mt-10 max-w-md text-center text-base font-medium text-ink">
              A high number is not automatically a good experiment.
            </p>
            <p className="mt-2 text-center text-sm text-ink-faint">Feature provenance matters.</p>

            <div className="mt-10 flex justify-center">
              <DecisionNote label={`Do not claim ${C01.id} = ${(C01.accuracy * 100).toFixed(1)}% clinical performance`}>
                {C01B.conclusion}
              </DecisionNote>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Stage>
  );
}

function EyeCaseStage() {
  return (
    <Stage id="eyecase">
      <Reveal>
        <Kicker>Stage 09 &middot; Eye-level discovery</Kicker>
        <StageTitle>Patient {EYE_CASE.patientId}</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div className="glass rounded-2xl p-8 text-center">
          <p className="text-xs uppercase tracking-widest text-ink-faint">Right eye</p>
          <p className="mt-3 text-2xl font-semibold text-ink">{EYE_CASE.right.severity}</p>
        </div>
        <div className="glass rounded-2xl p-8 text-center">
          <p className="text-xs uppercase tracking-widest text-ink-faint">Left eye</p>
          <p className="mt-3 text-2xl font-semibold text-ink">{EYE_CASE.left.severity}</p>
        </div>
      </Reveal>

      <Reveal delay={0.35} className="mt-10 flex flex-col items-center gap-2 text-center text-sm text-ink-muted">
        <span>Same patient &middot; Same study date ({EYE_CASE.date})</span>
        <span>Different eye severity</span>
      </Reveal>

      <Reveal delay={0.5} className="mx-auto mt-10 max-w-lg text-center text-sm leading-relaxed text-ink-muted">
        {EYE_CASE.takeaway}
      </Reveal>
    </Stage>
  );
}

function RnflStage() {
  return (
    <Stage id="rnfl">
      <Reveal>
        <Kicker>Stage 10 &middot; Forensic audit</Kicker>
        <StageTitle>RNFL/GCC workbook</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-12 flex flex-col items-center gap-3">
        {RNFL_AUDIT_LAYERS.map((layer, i) => (
          <motion.div
            key={layer}
            initial={{ opacity: 0.9 }}
            whileInView={{ opacity: 0.35 + (i / RNFL_AUDIT_LAYERS.length) * 0.1 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.06, duration: 0.6 }}
            className="w-full max-w-sm rounded-lg border border-white/8 bg-white/[0.02] px-4 py-2 text-center text-sm text-ink-muted"
          >
            {layer}
          </motion.div>
        ))}
      </Reveal>

      <Reveal delay={0.6} className="mt-14 text-center">
        <p className="text-xl font-semibold tracking-wide text-ink sm:text-2xl">{RNFL_CONCLUSION.headline}</p>
      </Reveal>

      <Reveal delay={0.75} className="mx-auto mt-6 max-w-lg text-center text-sm leading-relaxed text-ink-muted">
        {RNFL_CONCLUSION.detail}
      </Reveal>

      <Reveal delay={0.9} className="mt-8 text-center text-sm text-ink-faint">
        {RNFL_CONCLUSION.decision}
      </Reveal>
    </Stage>
  );
}

function M01Stage() {
  const kappaValues = M01.rows.flatMap((r) => [r.independent, r.shared]);
  const max = Math.max(...kappaValues) * 1.15;

  return (
    <Stage id="m01">
      <Reveal>
        <Kicker>Stage 11 &middot; Shared representation</Kicker>
        <StageTitle>{M01.question}</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-12 flex flex-col items-center gap-3 text-center text-sm text-ink-faint">
        <div className="flex gap-4">
          <span>GAMMA</span>
          <span>HVF</span>
          <span>RNFL/GCC</span>
        </div>
        <span aria-hidden>&darr;</span>
        <span className="rounded-lg border border-white/10 px-4 py-2 text-ink">Shared latent representation</span>
      </Reveal>

      <Reveal delay={0.35} className="mx-auto mt-14 max-w-xl">
        {M01.rows.map((row) => (
          <MetricBarRow key={row.metric} label={row.metric} a={row.independent} b={row.shared} aLabel="Independent" bLabel="Shared" max={max} />
        ))}
      </Reveal>

      <Reveal delay={0.5} className="mx-auto mt-8 max-w-xl text-xs leading-relaxed text-ink-faint">
        {M01.note}
      </Reveal>

      <Reveal delay={0.6} className="mt-12 text-center">
        <p className="text-lg font-medium text-ink">Small + mixed effect</p>
        <p className="mt-2 text-sm text-ink-faint">{M01.decision}</p>
      </Reveal>
    </Stage>
  );
}

function ConclusionStage() {
  return (
    <Stage id="conclusion" className="pb-40">
      <Reveal>
        <Kicker>Final stage &middot; Evidence stack</Kicker>
        <StageTitle>MM-RETINA</StageTitle>
      </Reveal>

      <Reveal delay={0.15} className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2">
        {FINAL_STACK.map((card) => (
          <div key={card.title} className="glass rounded-2xl p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-accent-champagne">{card.title}</p>
            <ul className="mt-3 space-y-1 text-sm text-ink-muted">
              {card.lines.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        ))}
      </Reveal>

      <Reveal delay={0.35} className="mx-auto mt-20 max-w-xl text-center">
        <p className="text-2xl font-semibold leading-snug tracking-tight text-ink">
          The result is not just a model. It is a validated research process.
        </p>
        <p className="mt-4 text-base text-ink-muted">
          We kept what the data supported and rejected what it could not prove.
        </p>
      </Reveal>

      <Reveal delay={0.5} className="mx-auto mt-20 max-w-lg border-t border-white/10 pt-10 text-center text-sm italic leading-relaxed text-ink-muted">
        {CLOSING_LINE}
      </Reveal>
    </Stage>
  );
}
