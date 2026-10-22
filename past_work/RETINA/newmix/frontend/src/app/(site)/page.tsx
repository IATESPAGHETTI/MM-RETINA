import { Hero } from "@/components/Hero";
import { WhyMultimodal } from "@/components/WhyMultimodal";
import { ArchitecturePipeline } from "@/components/ArchitecturePipeline";
import { DatasetFacts } from "@/components/DatasetFacts";
import { ResultsPreview } from "@/components/ResultsPreview";
import { ResearchIntegrity } from "@/components/ResearchIntegrity";

export default function Home() {
  return (
    <>
      <Hero />
      <WhyMultimodal />
      <ArchitecturePipeline />
      <DatasetFacts />
      <ResultsPreview />
      <ResearchIntegrity />
    </>
  );
}
