import { ResearchIntegrity } from "@/components/ResearchIntegrity";
import { Reveal } from "@/components/Reveal";

export const metadata = { title: "Research — MM-RETINA" };

export default function ResearchPage() {
  return (
    <div className="pt-20">
      <section className="mx-auto max-w-3xl px-6 pt-24 pb-8 text-center">
        <Reveal>
          <p className="mb-4 text-xs uppercase tracking-[0.3em] text-ink-faint">Research</p>
          <h1 className="text-5xl font-semibold tracking-tight text-ink sm:text-6xl">
            The project,
            <br />
            explained simply
          </h1>
        </Reveal>
      </section>

      <section className="mx-auto max-w-2xl px-6 py-8">
        <Reveal>
          <div className="space-y-4 border-t border-white/10 pt-8 text-base leading-relaxed text-ink-muted">
            <p>
              An <strong className="text-ink">OCT scan</strong> is a detailed
              scan showing the structure inside the eye. A{" "}
              <strong className="text-ink">fundus photo</strong> is a broader
              picture of the back of the eye. Instead of asking an AI model to
              look at only one image, this project gives it both views of the
              same eye.
            </p>
            <p>
              Separate neural networks first turn the two images into useful
              numerical information (called <em>embeddings</em>). A
              cross-modal transformer then learns how information from the OCT
              and the fundus relates to each other. Finally, the combined
              information is used to predict a glaucoma grade: Normal, Early,
              or Progressive.
            </p>
            <p>
              The research question is not &quot;can a CNN classify these
              images&quot; — it&apos;s whether combining the two views actually
              improves grading over using either one alone. That&apos;s what
              the ablation study on the{" "}
              <a href="/results" className="text-ink underline underline-offset-4">
                results page
              </a>{" "}
              is designed to answer, once real experiments are run.
            </p>
          </div>
        </Reveal>
      </section>

      <section className="mx-auto max-w-2xl px-6 py-8">
        <Reveal>
          <h2 className="mb-2 text-2xl font-semibold tracking-tight text-ink">A short glossary</h2>
        </Reveal>
        <Reveal delay={0.1}>
          <dl className="mt-6 space-y-5 border-t border-white/10 pt-8 text-sm text-ink-muted">
            <div>
              <dt className="font-medium text-ink">B-scan</dt>
              <dd className="mt-1">One cross-sectional slice of an OCT volume — like one page of a flip-book showing a slice through the retina.</dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Embedding</dt>
              <dd className="mt-1">A list of numbers a neural network produces to summarize an image&apos;s important features, in a form a computer can compare and combine.</dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Cross-attention</dt>
              <dd className="mt-1">A mechanism that lets one type of data (e.g. OCT) inform how much weight to give parts of another type of data (e.g. fundus), instead of just averaging them.</dd>
            </div>
            <div>
              <dt className="font-medium text-ink">Patient-level split</dt>
              <dd className="mt-1">Dividing data into train/validation/test by patient, not by individual image — so the model is never tested on a patient it has already partly seen.</dd>
            </div>
          </dl>
        </Reveal>
      </section>

      <ResearchIntegrity />
    </div>
  );
}
