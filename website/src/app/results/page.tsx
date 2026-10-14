import Link from "next/link";
import { HeadlineMetrics } from "@/components/HeadlineMetrics";
import { ExperimentLadder } from "@/components/ExperimentLadder";
import { AblationTable } from "@/components/AblationTable";
import { StandaloneResults } from "@/components/StandaloneResults";
import { Reveal } from "@/components/Reveal";
import { HEADLINE } from "@/lib/results";

export const metadata = {
  title: "Results — MM-RETINA",
  description: "Patient-level 5-fold cross-validation results for the multimodal glaucoma grading model, including every ablation.",
};

export default function ResultsPage() {
  const acc = (HEADLINE.metrics.accuracy.mean * 100).toFixed(0);
  const auc = HEADLINE.metrics.roc_auc_ovr_macro.mean.toFixed(2);

  return (
    <div className="pt-20">
      <section className="mx-auto max-w-4xl px-6 pt-20 pb-8 text-center">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-ink-faint">Results</p>
          <h1 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            {acc}% accuracy, {auc} ROC-AUC
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-ink-muted">
            Three-class glaucoma grading (normal / early / progressive) from fundus and OCT, measured with
            patient-level 5-fold cross-validation over {HEADLINE.numPatients} labelled patients — with the
            variance and the failed experiments left in.
          </p>
          <p className="mt-4 text-xs text-ink-faint">
            Read the intended use and limitations in the{" "}
            <Link href="/model-card" className="underline underline-offset-4 hover:text-ink">
              model card
            </Link>
            .
          </p>
        </Reveal>
      </section>

      <HeadlineMetrics />
      <ExperimentLadder />
      <AblationTable />
      <StandaloneResults />
    </div>
  );
}
