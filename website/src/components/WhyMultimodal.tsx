import Image from "next/image";
import { Reveal } from "./Reveal";

export function WhyMultimodal() {
  return (
    <section className="relative mx-auto max-w-5xl px-6 py-32">
      <Reveal>
        <p className="mb-4 text-xs uppercase tracking-[0.3em] text-ink-faint">Why multimodal</p>
        <h2 className="max-w-lg text-4xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-5xl">
          Two retinal views.
          <br />
          One learned representation.
        </h2>
      </Reveal>

      <div className="mt-20 grid grid-cols-1 gap-10 md:grid-cols-2">
        <Reveal>
          <div className="relative aspect-[220/160] overflow-hidden rounded-2xl border border-white/8 bg-bg-elevated">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/oct-volume/0001/128.jpg"
              alt="Real OCT B-scan, GAMMA sample 0001, slice 128 of 256"
              className="h-full w-full object-cover"
            />
          </div>
          <div className="mt-4 flex flex-col gap-1">
            <span className="text-2xl font-semibold tracking-tight text-ink">OCT</span>
            <span className="text-sm text-ink-muted">Detailed structural information — cross-sectional layers of the retina</span>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="relative aspect-[220/160] overflow-hidden rounded-2xl border border-white/8">
            <Image
              src="/samples/gamma-0001-fundus.jpg"
              alt="Real color fundus photograph from the GAMMA dataset"
              fill
              sizes="(min-width: 768px) 45vw, 90vw"
              className="object-cover"
              style={{ filter: "saturate(0.85) contrast(1.05)" }}
            />
          </div>
          <div className="mt-4 flex flex-col gap-1">
            <span className="text-2xl font-semibold tracking-tight text-ink">Fundus</span>
            <span className="text-sm text-ink-muted">A broader color photograph of the retina and optic disc</span>
          </div>
        </Reveal>
      </div>

      <Reveal delay={0.25} className="mx-auto mt-16 max-w-xl text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-accent-champagne">Fused representation</p>
        <p className="mt-4 text-ink-muted leading-relaxed">
          The model processes both separately, then learns how the two
          sources of information relate to each other before making a
          prediction — instead of relying on only one view of the eye.
        </p>
      </Reveal>
    </section>
  );
}
