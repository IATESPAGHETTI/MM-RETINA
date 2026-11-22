import Link from "next/link";
import { PageHeader } from "@/components/ui/primitives";
import { PatientTimeline } from "@/components/workspace/PatientCases";
import { STUDY_ID } from "@/lib/api";

export default async function PatientPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="space-y-6">
      <PageHeader title={STUDY_ID.test(id) ? id : "Patient timeline"} eyebrow="Study ID"
        description="Review saved cases and download individual reports."
        actions={<Link href="/workspace/patients" className="text-sm text-accent-champagne hover:underline">All patients</Link>} />
      <PatientTimeline key={id} studyId={id} />
    </div>
  );
}
