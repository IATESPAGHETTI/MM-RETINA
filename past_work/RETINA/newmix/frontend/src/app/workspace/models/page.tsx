"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type ModelsInfo } from "@/lib/api";
import { Badge, Callout, ErrorNote, LoadingBlock, PageHeader, Panel } from "@/components/ui/primitives";

type M = { mean: number; sd: number };
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const get = (o: unknown, path: string[]): unknown => path.reduce<unknown>((a, k) => (a && typeof a === "object" ? (a as Record<string, unknown>)[k] : undefined), o);

function octLabel(k: string) {
  if (k === "paper_hybrid") return "Paper architecture: U-Net + InceptionV3, 512 px (tuned)";
  if (k === "hybrid") return "ResNet18 + U-Net branch (fine-tuned)";
  if (k === "resnet18") return "ResNet18 (fine-tuned) · deployed";
  if (k === "efficientnet_b0") return "EfficientNet-B0 (fine-tuned)";
  const m = k.match(/^probe_(.+)_C(.+)$/);
  return m ? `${m[1] === "resnet18" ? "ResNet18" : "EfficientNet-B0"} frozen + logistic head (C=${m[2]})` : k;
}

function best(clin: ModelsInfo["clinical"], task: string, variant: string, metric: string) {
  const algos = ["logreg", "rf", "hgb"];
  const rows = algos
    .map((a) => ({ a, m: get(clin, [`${task}/${variant}/${a}`, metric]) as M | undefined }))
    .filter((r): r is { a: string; m: M } => !!r.m);
  return rows.sort((x, y) => y.m.mean - x.m.mean)[0];
}

export default function ModelsPage() {
  const [data, setData] = useState<ModelsInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.models().then(setData).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(() => {
    const t = setTimeout(load, 0);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Evidence"
        title="Models and evidence"
        description="Every number here is read from the cross-validation results written by the training scripts. Splits are patient-grouped, so one patient's two eyes never straddle train and test."
      />
      {error && <ErrorNote message={error} onRetry={load} />}
      {!data && !error && <LoadingBlock label="Loading results…" />}
      {data && <Content d={data} />}
    </div>
  );
}

function Content({ d }: { d: ModelsInfo }) {
  const clin = d.clinical;
  const base = clin.baseline_majority as unknown as { binary: number; multiclass: number } | undefined;
  const variants: { key: string; label: string; note: string; leak?: boolean }[] = [
    { key: "structural", label: "Structural features", note: "RNFL, GCC, CDR, IOP, age, sex" },
    { key: "structural_noage", label: "Structural, no age", note: "Same without age (controls are younger)" },
    { key: "with_hvf_md", label: "Structural + visual-field MD", note: "MD defines the severity label, so this is circular", leak: true },
  ];
  const fusion = d.fusion as {
    oct_arch?: string; clinical_algo?: string;
    rows?: Record<string, { accuracy: number; balanced_accuracy: number; qwk: number; auc_glaucoma: number }>;
    fused_minus_clinical?: { accuracy: { mean: number; ci95: number[] }; balanced_accuracy: { mean: number; ci95: number[] } };
    n_eyes?: number; n_patients?: number;
  };
  const gamma = d.gamma;
  const gammaRows: [string, string][] = [["fundus", "Fundus only"], ["oct", "OCT only"], ["fusion", "Fundus + OCT"], ["fusion_effnetb0", "Fundus + OCT (EfficientNet-B0)"]];

  return (
    <>
      {/* ---------------- clinical ---------------- */}
      <Panel
        title="Clinical-feature model: what the features can and cannot prove"
        subtitle={`4-class balanced accuracy (Control / Mild / Moderate / Severe), best of three algorithms, mean of 3 seeds of 5-fold CV · ${fusion.n_eyes ?? 303} eyes`}
      >
        <ul className="space-y-5">
          {variants.map((v) => {
            const r = best(clin, "multiclass", v.key, "balanced_accuracy");
            if (!r) return null;
            return (
              <li key={v.key}>
                <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-sm text-ink">
                    {v.label} {v.leak && <Badge tone="bad">circular</Badge>}
                  </p>
                  <p className="text-sm tabular-nums text-ink-muted">
                    {pct(r.m.mean)} <span className="text-ink-faint">± {(r.m.sd * 100).toFixed(1)} · {r.a}</span>
                  </p>
                </div>
                <div className="relative h-2.5 overflow-hidden rounded-full bg-white/[0.06]">
                  <div className={`h-full rounded-full ${v.leak ? "bg-bad/70" : "bg-accent-champagne"}`} style={{ width: `${r.m.mean * 100}%` }} />
                  {base && <div className="absolute inset-y-0 w-px bg-ink-faint" style={{ left: `${(1 / 4) * 100}%` }} title="chance for 4 balanced classes" />}
                </div>
                <p className="mt-1 text-xs text-ink-faint">{v.note}</p>
              </li>
            );
          })}
        </ul>
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <Callout tone="warn" title="Why the third bar is not a result">
            In this cohort the severity label is a rule on visual-field MD (Mild above −6 dB, Moderate to −12 dB, Severe below). A model that is given MD reads its own definition. The honest figure is the first bar.
          </Callout>
          <Callout tone="info" title="Binary (glaucoma vs control)">
            {(() => {
              const b = best(clin, "binary", "structural", "accuracy");
              const a = best(clin, "binary", "structural", "auc");
              const l = best(clin, "binary", "with_hvf_md", "accuracy");
              return b && a && l
                ? `Structural features reach ${pct(b.m.mean)} accuracy and ${a.m.mean.toFixed(2)} AUC (${b.a}). Adding MD lifts it to ${pct(l.m.mean)}, in line with the 91–93% the paper reports for clinical features, where MD is one of the top-ranked inputs.`
                : "Not available.";
            })()}
          </Callout>
        </div>
      </Panel>

      {/* ---------------- OCT ---------------- */}
      <Panel title="OCT B-scan model" subtitle="Single optic-nerve-head B-scan per eye, fixed 30-epoch budget, no test-fold model selection, 3 seeds">
        {d.oct.length === 0 ? (
          <p className="text-sm text-ink-faint">No OCT results found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="text-left text-xs text-ink-faint">
                <tr className="border-b border-line">
                  <th className="py-2 pr-4 font-medium">Model</th>
                  <th className="px-3 py-2 text-right font-medium">Seeds</th>
                  <th className="px-3 py-2 text-right font-medium">4-class accuracy</th>
                  <th className="px-3 py-2 text-right font-medium">Balanced acc.</th>
                  <th className="px-3 py-2 text-right font-medium">QWK</th>
                  <th className="px-3 py-2 text-right font-medium">Glaucoma vs control AUC</th>
                </tr>
              </thead>
              <tbody>
                {d.oct.map((r) => (
                  <tr key={r.arch} className="border-b border-line last:border-0">
                    <td className="py-3 pr-4 text-ink">{octLabel(r.arch)}</td>
                    <td className="px-3 py-3 text-right tabular-nums text-ink-faint">{r.seeds}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{pct(r.acc)} <span className="text-ink-faint">± {(r.acc_sd * 100).toFixed(1)}</span></td>
                    <td className="px-3 py-3 text-right tabular-nums">{pct(r.bal)}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{r.qwk.toFixed(2)}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{r.auc.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-4 text-xs leading-relaxed text-ink-faint">
          The paper&apos;s hybrid uses InceptionV3 and reports 87.5% on four classes. Its ImageNet weights were not available offline, so this is not a replication; the &quot;hybrid&quot; here adds a small U-Net branch to ResNet18. One B-scan carries limited severity information.
        </p>
      </Panel>

      {/* ---------------- why the paper number is high ---------------- */}
      {d.paper_protocol && d.paper_protocol.length > 0 && (
        <Panel title="Why the paper's accuracy is not reproducible" subtitle="Same model (the paper's architecture), same 1,818 augmented images, same training. Only the split differs.">
          <ul className="space-y-5">
            {d.paper_protocol.map((r) => {
              const leaky = r.protocol.startsWith("image");
              return (
                <li key={r.protocol}>
                  <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-2">
                    <p className="text-sm text-ink">
                      {leaky ? "Random image split (paper-style)" : "Patient-grouped split"} {leaky && <Badge tone="bad">leaks</Badge>}
                    </p>
                    <p className="text-sm tabular-nums text-ink-muted">
                      {pct(r.test_acc)} accuracy <span className="text-ink-faint">· {pct(r.test_balanced_acc)} balanced</span>
                    </p>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-white/[0.06]">
                    <div className={`h-full rounded-full ${leaky ? "bg-bad/70" : "bg-accent-champagne"}`} style={{ width: `${r.test_acc * 100}%` }} />
                  </div>
                  <p className="mt-1 text-xs text-ink-faint">
                    {Math.round(r.test_images_with_sibling_in_train * 100)}% of test images have an augmented copy of the same scan in the training set · {r.n_train} train / {r.n_test} test
                  </p>
                </li>
              );
            })}
          </ul>
          <div className="mt-5">
            <Callout tone="warn" title="What this shows, and what it does not">
              Augmenting 303 scans into 1,818 and then splitting at random puts near-copies of each test image in training, and accuracy jumps from about 50% to 81%, close to the paper&apos;s reported 87.5%. This demonstrates that protocol can produce such numbers. It does not prove the paper used it, because its split is not described. One seed, 10 epochs, about 180 test images.
            </Callout>
          </div>
        </Panel>
      )}

      {/* ---------------- fusion ---------------- */}
      <Panel title="Fusion: does combining OCT and clinical help?" subtitle={`Late fusion: weighted average of the two probability vectors · ${fusion.n_patients ?? "—"} patients`}>
        {!fusion.rows ? (
          <p className="text-sm text-ink-faint">Fusion results have not been generated yet.</p>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-ink-faint">
                <tr className="border-b border-line">
                  <th className="py-2 pr-4 font-medium">Input</th>
                  <th className="px-3 py-2 text-right font-medium">Accuracy</th>
                  <th className="px-3 py-2 text-right font-medium">Balanced</th>
                  <th className="px-3 py-2 text-right font-medium">QWK</th>
                  <th className="px-3 py-2 text-right font-medium">AUC</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(fusion.rows).map(([k, r]) => (
                  <tr key={k} className="border-b border-line last:border-0">
                    <td className="py-3 pr-4 text-ink">{k}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{pct(r.accuracy)}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{pct(r.balanced_accuracy)}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{r.qwk.toFixed(2)}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{r.auc_glaucoma.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {fusion.fused_minus_clinical && (() => {
              const f = fusion.fused_minus_clinical.balanced_accuracy;
              const sig = f.ci95[0] > 0;
              return (
                <div className="mt-4">
                  <Callout tone={sig ? "ok" : "info"} title={sig ? "Fusion helps" : "No reliable gain from fusion"}>
                    Fused minus clinical, balanced accuracy: {(f.mean * 100).toFixed(1)} points (95% patient-bootstrap interval {(f.ci95[0] * 100).toFixed(1)} to {(f.ci95[1] * 100).toFixed(1)}).{" "}
                    {sig ? "The interval excludes zero." : "The interval includes zero, so the data do not show that adding the image improves on the clinical numbers."}
                  </Callout>
                </div>
              );
            })()}
          </>
        )}
      </Panel>

      {/* ---------------- deferral ---------------- */}
      {d.defer && d.defer.clinical && (
        <Panel title="Deferring uncertain cases" subtitle="When confidence is below a cut-off, the app withholds the stage and recommends a visual-field test. Cut-offs come from out-of-fold predictions, pooled over 3 seeds.">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead className="text-left text-xs text-ink-faint">
                <tr className="border-b border-line">
                  <th className="py-2 pr-4 font-medium">Model</th>
                  <th className="px-3 py-2 text-right font-medium">Answers all</th>
                  <th className="px-3 py-2 text-right font-medium">Answers 80%</th>
                  <th className="px-3 py-2 text-right font-medium">Answers 60%</th>
                  <th className="px-3 py-2 text-right font-medium">Deferred cases were right</th>
                </tr>
              </thead>
              <tbody>
                {(["clinical", "fused", "oct"] as const).map((k) => {
                  const r = d.defer?.[k];
                  if (!r) return null;
                  return (
                    <tr key={k} className="border-b border-line last:border-0">
                      <td className="py-3 pr-4 text-ink">{k === "clinical" ? "Clinical (deployed lead)" : k === "fused" ? "Fused OCT + clinical" : "OCT scan alone"}</td>
                      <td className="px-3 py-3 text-right tabular-nums">{pct(r.table["100%"].accuracy)}</td>
                      <td className="px-3 py-3 text-right tabular-nums text-accent-champagne">{pct(r.table["80%"].accuracy)}</td>
                      <td className="px-3 py-3 text-right tabular-nums">{pct(r.table["60%"].accuracy)}</td>
                      <td className="px-3 py-3 text-right tabular-nums text-ink-faint">{pct(r.accuracy_deferred)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="mt-4">
            <Callout tone="info" title="Reading this honestly">
              Accuracy rises because the model stops answering its hardest cases, not because it got better. The price is that about one case in five is returned as inconclusive. Cut-offs are measured on held-out eyes; whether new patients behave the same way has not been tested. The OCT scan alone stays weak even when it answers, so it is never presented as a dependable stager.
            </Callout>
          </div>
        </Panel>
      )}

      {/* ---------------- GAMMA ---------------- */}
      <Panel title="GAMMA multimodal model" subtitle={`${gamma.dataset ?? "GAMMA"} · classes Normal / Early / Progressive`}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <thead className="text-left text-xs text-ink-faint">
              <tr className="border-b border-line">
                <th className="py-2 pr-4 font-medium">Input</th>
                <th className="px-3 py-2 text-right font-medium">Accuracy</th>
                <th className="px-3 py-2 text-right font-medium">Balanced</th>
                <th className="px-3 py-2 text-right font-medium">Macro-F1</th>
                <th className="px-3 py-2 text-right font-medium">AUC</th>
              </tr>
            </thead>
            <tbody>
              {gammaRows.map(([k, label]) => {
                const r = gamma[k];
                if (!r || typeof r !== "object" || !("accuracy" in r)) return null;
                return (
                  <tr key={k} className="border-b border-line last:border-0">
                    <td className="py-3 pr-4 text-ink">{label}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{pct(r.accuracy.mean)} <span className="text-ink-faint">± {(r.accuracy.sd * 100).toFixed(1)}</span></td>
                    <td className="px-3 py-3 text-right tabular-nums">{pct(r.balanced_accuracy.mean)}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{r.macro_f1.mean.toFixed(2)}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{r.auc.mean.toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs leading-relaxed text-ink-faint">
          Small cohort (300 eyes), so fold-to-fold spread is large. The live demo serves single-split checkpoints, not these cross-validation models.
        </p>
      </Panel>

      {/* ---------------- diabetes ---------------- */}
      <Panel title="Diabetes models" action={<Badge tone="warn">No validation on file</Badge>}>
        <p className="text-sm leading-relaxed text-ink-muted">{d.diabetes.note} They are included as delivered; the interface labels their output experimental, and no accuracy claim is made for them.</p>
      </Panel>
    </>
  );
}
