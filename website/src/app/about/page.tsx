import { GlassCard } from "@/components/GlassCard";
import { Reveal } from "@/components/Reveal";
import { VERIFIED_GAMMA_FACTS } from "@/lib/content";

export const metadata = { title: "About — MM-RETINA" };

export default function AboutPage() {
  return (
    <div className="pt-20">
      <section className="mx-auto max-w-3xl px-6 pt-20 pb-8 text-center">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">About</p>
          <h1 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            MM-RETINA
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-ink-muted">
            An academic research prototype exploring multimodal retinal
            representation learning for glaucoma grading.
          </p>
        </Reveal>
      </section>

      <section className="mx-auto max-w-3xl px-6 py-8">
        <Reveal>
          <GlassCard className="space-y-4 text-sm leading-relaxed text-ink-muted">
            <p>
              This project combines OCT volumes and fundus photography from
              the GAMMA challenge dataset, uses cross-modal attention to fuse
              them, and evaluates whether the additional modality actually
              improves glaucoma grading over a single-modality baseline.
            </p>
            <p>
              It is a research prototype built for academic purposes. It is{" "}
              <strong className="text-ink">not</strong> a clinically validated
              tool and makes no diagnostic claims.
            </p>
          </GlassCard>
        </Reveal>
      </section>

      <section className="mx-auto max-w-3xl px-6 pb-24">
        <Reveal>
          <GlassCard className="text-sm text-ink-muted">
            <h2 className="mb-2 text-base font-medium text-ink">Citation</h2>
            <p>{VERIFIED_GAMMA_FACTS.citation}</p>
          </GlassCard>
        </Reveal>
      </section>
    </div>
  );
}
