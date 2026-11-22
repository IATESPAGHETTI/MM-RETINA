import { redirect } from "next/navigation";
import { SUITE_URL } from "@/lib/suiteContent";

/**
 * The standalone inference demo now lives in the Retina Suite workspace, which runs the same
 * fundus / OCT / fusion checkpoints and adds model comparison, explanations, saved patients and PDFs.
 * Keeping /demo as a redirect means old links and the nav entry still work, and the website no longer
 * needs its own backend on :8000.
 */
export default function DemoPage() {
  redirect(`${SUITE_URL}/glaucoma/multimodal`);
}
