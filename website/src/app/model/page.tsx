import { ArchitecturePipeline } from "@/components/ArchitecturePipeline";
import { WhyMultimodal } from "@/components/WhyMultimodal";
import { GlassCard } from "@/components/GlassCard";
import { Reveal } from "@/components/Reveal";

export const metadata = { title: "Model — MM-RETINA" };

export default function ModelPage() {
  return (
    <div className="pt-20">
      <section className="mx-auto max-w-4xl px-6 pt-20 pb-8 text-center">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Model</p>
          <h1 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            Cross-modal retinal fusion
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-ink-muted">
            One encoder for the OCT volume, one for the fundus photo, and a
            transformer that learns how the two relate before predicting a grade.
          </p>
        </Reveal>
      </section>

      <WhyMultimodal />
      <ArchitecturePipeline />

      <section className="mx-auto max-w-4xl px-6 py-20">
        <Reveal>
          <h2 className="text-2xl font-semibold text-ink">OCT volume processing, in plain terms</h2>
        </Reveal>
        <Reveal delay={0.1}>
          <GlassCard className="mt-8 space-y-4 text-sm leading-relaxed text-ink-muted">
            <p>
              An OCT scan isn&apos;t one photo — it&apos;s 256 thin cross-section
              images (<span className="text-ink">B-scans</span>) stacked
              together, like slicing through the retina layer by layer.
              Feeding all 256 into a 3D network is memory-expensive, so
              instead:
            </p>
            <ol className="list-decimal space-y-2 pl-5">
              <li>Every B-scan passes through the same shared 2D encoder (a &quot;2.5D&quot; approach).</li>
              <li>This produces one embedding (a list of numbers summarizing what&apos;s important) per slice.</li>
              <li>A lightweight transformer looks across all 256 slice-embeddings at once and pools them into a single OCT-volume summary.</li>
            </ol>
            <p>
              This fits comfortably on a 6GB GPU while still letting the model
              see the whole volume, not just one slice picked at random.
            </p>
          </GlassCard>
        </Reveal>
      </section>

      <section className="mx-auto max-w-4xl px-6 pb-28">
        <Reveal>
          <h2 className="text-2xl font-semibold text-ink">What cross-attention actually does</h2>
        </Reveal>
        <Reveal delay={0.1}>
          <GlassCard className="mt-8 text-sm leading-relaxed text-ink-muted">
            <p>
              Cross-attention lets the model learn which information from one
              modality is relevant to information from another modality — for
              example, letting a structural OCT signal reweight how much the
              fundus branch&apos;s optic-disc appearance should matter for this
              particular eye.
            </p>
            <p className="mt-4 text-xs text-ink-faint">
              This visualization represents model attribution and is not proof
              of causal or clinical reasoning.
            </p>
          </GlassCard>
        </Reveal>
      </section>
    </div>
  );
}
