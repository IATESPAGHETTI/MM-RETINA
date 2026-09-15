import { DatasetFacts } from "@/components/DatasetFacts";
import { GlassCard } from "@/components/GlassCard";
import { Reveal } from "@/components/Reveal";
import { VERIFIED_GAMMA_FACTS, VERIFIED_GRAPE_FACTS } from "@/lib/content";

export const metadata = { title: "Dataset — MM-RETINA" };

export default function DatasetPage() {
  return (
    <div className="pt-20">
      <section className="mx-auto max-w-4xl px-6 pt-20 pb-8 text-center">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Dataset</p>
          <h1 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            Where the data comes from
          </h1>
        </Reveal>
      </section>

      <DatasetFacts />

      <section className="mx-auto max-w-4xl px-6 py-12">
        <Reveal>
          <GlassCard className="space-y-4 text-sm leading-relaxed text-ink-muted">
            <h2 className="text-lg font-medium text-ink">{VERIFIED_GAMMA_FACTS.fullName} (GAMMA)</h2>
            <p>
              Released for the GAMMA challenge (OMIA8 / MICCAI 2021), GAMMA is
              the primary dataset here: it pairs a 2D color fundus photograph
              with a 3D OCT volume for the <em>same eye and examination</em>.
            </p>
            <ul className="list-disc space-y-1 pl-5">
              <li>{VERIFIED_GAMMA_FACTS.pairedSamples} paired samples across {VERIFIED_GAMMA_FACTS.patients} patients</li>
              <li>Each OCT volume: {VERIFIED_GAMMA_FACTS.bscansPerVolume} B-scans, {VERIFIED_GAMMA_FACTS.acquisition.oct}</li>
              <li>Fundus: {VERIFIED_GAMMA_FACTS.acquisition.fundus}</li>
              <li>Grades: {VERIFIED_GAMMA_FACTS.classes.join(" / ")} (derived from visual-field mean deviation thresholds)</li>
              <li>License: {VERIFIED_GAMMA_FACTS.license} — accept terms on the official page before use</li>
            </ul>
            <p className="text-xs text-ink-faint">
              Citation: {VERIFIED_GAMMA_FACTS.citation}
            </p>
            <a
              href={VERIFIED_GAMMA_FACTS.officialUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-block text-ink underline underline-offset-4 hover:text-accent-cyan"
            >
              Official challenge page →
            </a>
          </GlassCard>
        </Reveal>

        <Reveal delay={0.1} className="mt-8">
          <GlassCard className="space-y-4 text-sm leading-relaxed text-ink-muted">
            <h2 className="text-lg font-medium text-ink">{VERIFIED_GRAPE_FACTS.name} (secondary dataset)</h2>
            <p>
              GRAPE is a separate, longitudinal glaucoma cohort — it is{" "}
              <strong className="text-ink">not merged with GAMMA</strong>. It
              is used, if at all, as an independent generalization study, never
              concatenated to fabricate additional &quot;paired&quot; samples.
            </p>
            <ul className="list-disc space-y-1 pl-5">
              <li>{VERIFIED_GRAPE_FACTS.baselineEyeRecords} baseline eye records, {VERIFIED_GRAPE_FACTS.followUpVisits} follow-up visits</li>
              <li>{VERIFIED_GRAPE_FACTS.fundusPhotographs} original fundus photographs</li>
              <li>Modalities: {VERIFIED_GRAPE_FACTS.modalities.join(", ")}</li>
              <li>License: {VERIFIED_GRAPE_FACTS.license}</li>
            </ul>
            <a
              href={VERIFIED_GRAPE_FACTS.collectionUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-block text-ink underline underline-offset-4 hover:text-accent-cyan"
            >
              Figshare collection →
            </a>
          </GlassCard>
        </Reveal>

        <Reveal delay={0.2} className="mt-8">
          <GlassCard className="text-sm leading-relaxed text-ink-muted">
            <h2 className="mb-3 text-lg font-medium text-ink">Patient-level splitting</h2>
            <p>
              {VERIFIED_GAMMA_FACTS.patients} patients producing {VERIFIED_GAMMA_FACTS.pairedSamples} samples
              means some patients contribute more than one sample (bilateral
              eyes or repeat visits). Every split here groups by patient ID
              first — no patient&apos;s data appears in more than one of
              train / validation / test.
            </p>
          </GlassCard>
        </Reveal>
      </section>
    </div>
  );
}
