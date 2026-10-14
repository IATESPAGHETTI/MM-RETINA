import Link from "next/link";
import type { ReactNode } from "react";
import { Reveal } from "@/components/Reveal";
import { VERIFIED_GAMMA_FACTS } from "@/lib/content";
import { HEADLINE, METRIC_LABELS, STANDALONE, formatMetric, type MetricKey } from "@/lib/results";

export const metadata = {
  title: "Model card — MM-RETINA",
  description:
    "Intended use, training data, evaluation, limitations and ethical considerations for the MM-RETINA glaucoma grading model.",
};

const METRIC_ORDER: MetricKey[] = [
  "accuracy",
  "balanced_accuracy",
  "macro_f1",
  "roc_auc_ovr_macro",
  "cohen_kappa",
  "quadratic_weighted_kappa",
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Reveal className="grid gap-4 border-t border-white/10 py-10 md:grid-cols-[12rem_1fr] md:gap-10">
      <h2 className="text-sm font-medium uppercase tracking-[0.2em] text-ink-faint">{title}</h2>
      <div className="space-y-4 text-sm leading-relaxed text-ink-muted">{children}</div>
    </Reveal>
  );
}

function Bullets({ items }: { items: readonly string[] }) {
  return (
    <ul className="space-y-2">
      {items.map((t) => (
        <li key={t} className="flex gap-3">
          <span aria-hidden className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent-champagne" />
          <span>{t}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ModelCardPage() {
  return (
    <div className="pt-20">
      <section className="mx-auto max-w-4xl px-6 pt-20 pb-10">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-ink-faint">Model card</p>
          <h1 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">MM-RETINA fusion grader</h1>
          <p className="mt-5 max-w-2xl text-ink-muted">
            A multimodal research model that grades glaucoma severity (normal, early, progressive) from a colour
            fundus photograph and an OCT B-scan volume. This card says what it is for, what it was measured on,
            and where it should not be trusted.
          </p>
          <dl className="mt-8 grid grid-cols-2 gap-6 text-sm sm:grid-cols-4">
            {[
              ["Status", "Research prototype"],
              ["Frozen config", HEADLINE.id],
              ["Task", "3-class grading"],
              ["Data licence", VERIFIED_GAMMA_FACTS.license],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs uppercase tracking-wider text-ink-faint">{k}</dt>
                <dd className="mt-1 font-medium text-ink">{v}</dd>
              </div>
            ))}
          </dl>
        </Reveal>
      </section>

      <div className="mx-auto max-w-4xl px-6 pb-24">
        <Section title="Intended use">
          <Bullets
            items={[
              "Studying whether combining OCT and fundus imaging improves glaucoma grading over either alone.",
              "Teaching and demonstration of multimodal fusion, cross-validation discipline and explainability.",
              "A baseline to compare against on the GAMMA benchmark.",
            ]}
          />
        </Section>

        <Section title="Out of scope">
          <Bullets
            items={[
              "Clinical diagnosis, screening, triage or any decision about a real patient's care.",
              "Commercial use — the training data is licensed CC BY-NC-ND.",
              "Images from devices, populations or acquisition protocols other than those described below; the model has never been externally validated.",
              "Other diseases. A non-glaucoma pathology will still be forced into one of the three glaucoma grades.",
            ]}
          />
        </Section>

        <Section title="Architecture">
          <p>
            Two encoders, one fusion head. An EfficientNet-B0 encodes the fundus image; a ResNet18 encodes eight
            evenly-spaced B-scans from the OCT volume, which are combined by learned attention pooling. A
            cross-modal Transformer fuses the two embeddings and a linear head predicts the grade. Trained with
            focal loss and inverse-frequency class weights.
          </p>
          <p>
            Code: <code className="font-mono text-ink">training/model.py</code>. The configuration measured below is{" "}
            <code className="font-mono text-ink">{HEADLINE.id}</code> ({HEADLINE.exp}).
          </p>
        </Section>

        <Section title="Training data">
          <p>
            {VERIFIED_GAMMA_FACTS.fullName} ({VERIFIED_GAMMA_FACTS.name}): {VERIFIED_GAMMA_FACTS.pairedSamples}{" "}
            paired fundus + OCT samples from {VERIFIED_GAMMA_FACTS.patients} patients, acquired on{" "}
            {VERIFIED_GAMMA_FACTS.acquisition.oct.split(",")[0]} and{" "}
            {VERIFIED_GAMMA_FACTS.acquisition.fundus.split(",")[0]} devices. Only the {HEADLINE.numPatients}{" "}
            publicly-labelled training patients are used here; the challenge test labels are withheld.
          </p>
          <p>
            Class balance is roughly half normal, with the glaucoma cases split about evenly between early and
            progressive. See the <Link href="/dataset" className="underline underline-offset-4 hover:text-ink">dataset page</Link>{" "}
            for citation and licence terms.
          </p>
        </Section>

        <Section title="Evaluation">
          <p>
            Patient-level, grade-stratified {HEADLINE.numFolds}-fold cross-validation (seed 42): no patient appears
            in both training and evaluation folds. Mean ± standard deviation across folds:
          </p>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3">
            {METRIC_ORDER.map((k) => {
              const f = formatMetric(k, HEADLINE.metrics[k]);
              return (
                <div key={k}>
                  <dt className="text-xs uppercase tracking-wider text-ink-faint">{METRIC_LABELS[k].long}</dt>
                  <dd className="mt-1 text-lg font-medium text-ink">
                    {f.value} <span className="text-xs font-normal text-ink-faint">{f.std}</span>
                  </dd>
                </div>
              );
            })}
          </dl>
          <p>
            Full experiment series, including rejected changes:{" "}
            <Link href="/results" className="underline underline-offset-4 hover:text-ink">
              Results
            </Link>
            .
          </p>
        </Section>

        <Section title="Standalone models">
          <p>
            Visual-field (HVF) and RNFL/GCC data cannot be paired with the fundus + OCT data — no shared patient or eye
            identity — so they are not fused with it. Each has its own linear model on a Mild / Moderate / Severe scale
            and is shown next to the others, never merged into one score.
          </p>
          <ul className="space-y-2">
            {STANDALONE.map((m) => (
              <li key={m.key} className="flex gap-3">
                <span aria-hidden className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent-champagne" />
                <span>
                  <span className="text-ink">{m.label}</span>: ROC-AUC {m.reliability.roc_auc.toFixed(2)}, kappa{" "}
                  {m.reliability.kappa.toFixed(2)} — {m.reliability.label.toLowerCase()} ({m.split}).
                </span>
              </li>
            ))}
          </ul>
          <p>
            The HVF model is deliberately run without MD / PSD / VFI (they restate the labelling rule) and performs
            about like chance; the demo says so on every result. Details on{" "}
            <Link href="/results" className="underline underline-offset-4 hover:text-ink">
              Results
            </Link>
            .
          </p>
        </Section>

        <Section title="The live demo is a different checkpoint">
          <p>
            The <Link href="/demo" className="underline underline-offset-4 hover:text-ink">demo</Link> serves earlier
            single-split checkpoints (<code className="font-mono text-ink">fusion_run1</code>, ResNet18 + ResNet18),
            not the EfficientNet-B0 model measured above — the cross-validation fold checkpoints were intentionally
            not retained. A demo prediction is therefore not evidence for the metrics on this page, or the reverse.
          </p>
        </Section>

        <Section title="Limitations">
          <Bullets
            items={[
              `Small sample: ${HEADLINE.numPatients} labelled patients. Fold-to-fold standard deviations are large (accuracy ± ${(HEADLINE.metrics.accuracy.std * 100).toFixed(1)} points), so small differences between configurations are not reliable.`,
              "Single dataset, single acquisition protocol. No external validation, no out-of-distribution detection.",
              "Probabilities are not calibrated. The demo's “review” flag is a simple margin heuristic, not a clinical safety mechanism.",
              "Grad-CAM is available for the fundus branch only. It shows where the network looked, not why the eye is glaucomatous.",
              "In the demo, a single uploaded OCT image is repeated across the eight slice positions — a real forward pass, but not equivalent to a true volume.",
            ]}
          />
        </Section>

        <Section title="Ethical considerations">
          <Bullets
            items={[
              "Fundus and OCT images are health data. The demo backend processes uploads in memory and never writes them to disk; do not upload images of real patients to a public deployment.",
              "Performance has not been stratified by age, sex, ethnicity or device, so fairness across subgroups is unknown.",
              "Automation bias is a real risk for a confident-looking grader; outputs always carry a research-use disclaimer in the UI.",
            ]}
          />
        </Section>

        <Section title="Reproduce">
          <p>
            Everything above is regenerated from the repository:{" "}
            <code className="font-mono text-ink">python scripts/export_site_results.py</code> rebuilds the numbers
            from <code className="font-mono text-ink">results/*/summary.json</code>, and{" "}
            <code className="font-mono text-ink">training/cross_validate.py</code> reproduces the folds. See{" "}
            <code className="font-mono text-ink">EXPERIMENTS.md</code> for every run.
          </p>
        </Section>
      </div>
    </div>
  );
}
