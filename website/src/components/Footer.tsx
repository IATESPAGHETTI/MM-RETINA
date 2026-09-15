import Link from "next/link";

export function Footer() {
  return (
    <footer className="relative border-t border-white/10 px-6 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-sm text-ink-faint sm:flex-row">
        <p>MM-RETINA — a research prototype. Not for clinical diagnosis.</p>
        <div className="flex gap-6">
          <Link href="/about" className="hover:text-ink">
            About
          </Link>
          <Link href="/dataset" className="hover:text-ink">
            Dataset & citation
          </Link>
        </div>
      </div>
    </footer>
  );
}
