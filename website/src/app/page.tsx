import { Hero } from "@/components/Hero";
import { WhyMultimodal } from "@/components/WhyMultimodal";
import { ArchitecturePipeline } from "@/components/ArchitecturePipeline";
import { DatasetFacts } from "@/components/DatasetFacts";
import { ResultsPreview } from "@/components/ResultsPreview";
import { ResearchIntegrity } from "@/components/ResearchIntegrity";
import { SuiteTeaser } from "@/components/suite/SuiteTeaser";

export default function Home() {
  return (
    <>
      <Hero />
      <WhyMultimodal />
      <ArchitecturePipeline />
      <DatasetFacts />
      <ResultsPreview />
      <SuiteTeaser />
      <ResearchIntegrity />
    </>
  );
}
