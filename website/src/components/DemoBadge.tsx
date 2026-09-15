export function DemoBadge({ text = "Demo values — not real results" }: { text?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300/25 bg-amber-300/10 px-2.5 py-1 text-[11px] font-medium tracking-wide text-amber-200 uppercase">
      <span className="h-1.5 w-1.5 rounded-full bg-amber-300" aria-hidden />
      {text}
    </span>
  );
}
