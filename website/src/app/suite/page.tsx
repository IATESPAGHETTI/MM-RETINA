import { SuiteHero } from "@/components/suite/SuiteHero";
import { ModuleExplorer } from "@/components/suite/ModuleExplorer";
import { EvidenceStrip } from "@/components/suite/EvidenceStrip";
import { FeatureGrid } from "@/components/suite/FeatureGrid";
import { RunIt } from "@/components/suite/RunIt";
import { Reveal } from "@/components/Reveal";

export const metadata = {
  title: "Retina Suite — MM-RETINA",
  description:
    "Three retinal projects in one workspace: GAMMA multimodal glaucoma grading, glaucoma staging from clinical measurements, and diabetes vessel analysis.",
};

export default function SuitePage() {
  return (
    <>
      <SuiteHero />
      <ModuleExplorer />
      <EvidenceStrip />
      <FeatureGrid />
      <RunIt />

      <section className="px-6 pb-24">
        <Reveal className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-white/[0.03] p-6 text-center text-sm leading-relaxed text-ink-muted md:p-8">
          <p className="text-ink">Research prototype. Not a medical device.</p>
          <p className="mt-2">
            Nothing here replaces an ophthalmologist&apos;s examination. The diabetes HbA1c estimate is
            experimental and unvalidated, and the live GAMMA endpoints serve early single-split demonstration
            checkpoints rather than the cross-validated models reported above. Sample images are from the GAMMA
            dataset (CC BY-NC-ND).
          </p>
        </Reveal>
      </section>
    </>
  );
}
