"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { serviceSummary, useHealth } from "@/lib/useHealth";

export const BRAND = "Retina Suite";

const Icon = ({ d }: { d: string }) => (
  <svg viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d={d} />
  </svg>
);

const NAV: { heading: string; items: { href: string; label: string; icon: string; exact?: boolean }[] }[] = [
  {
    heading: "Workspace",
    items: [{ href: "/workspace", label: "Overview", icon: "M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6v-9h-6v9Zm0-16v5h6V4h-6Z", exact: true }],
  },
  {
    heading: "Screening",
    items: [
      { href: "/workspace/glaucoma", label: "Glaucoma", icon: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z", exact: true },
      { href: "/workspace/glaucoma/multimodal", label: "Multimodal (GAMMA)", icon: "M12 3 3 8l9 5 9-5-9-5ZM3 13l9 5 9-5M3 17.5l9 5 9-5" },
      { href: "/workspace/diabetes", label: "Diabetes", icon: "M12 3s6 6.2 6 10.5A6 6 0 0 1 6 13.5C6 9.2 12 3 12 3Z" },
    ],
  },
  {
    heading: "Evidence",
    items: [
      { href: "/workspace/models", label: "Models", icon: "M4 19V9m6 10V5m6 14v-7m4 7H2" },
      { href: "/workspace/data", label: "Data & integrity", icon: "M12 3 4 6v6c0 4.4 3.2 8 8 9 4.8-1 8-4.6 8-9V6l-8-3Zm-3 9 2 2 4-4" },
    ],
  },
];

function StatusPill() {
  const { state, refresh } = useHealth();
  if (state.phase === "loading")
    return <span className="flex items-center gap-2 text-xs text-ink-faint"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-faint" />Connecting…</span>;
  if (state.phase === "offline")
    return (
      <button onClick={refresh} className="flex items-center gap-2 rounded-full border border-bad/30 bg-bad/10 px-3 py-1 text-xs text-bad hover:bg-bad/15" title={state.message}>
        <span className="h-1.5 w-1.5 rounded-full bg-bad" />
        Service offline · retry
      </button>
    );
  const { allOk, okCount, items } = serviceSummary(state.health);
  return (
    <span
      className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs ${allOk ? "border-ok/30 bg-ok/10 text-ok" : "border-warn/30 bg-warn/10 text-warn"}`}
      title={items.map((i) => `${i.label}: ${i.ok ? "ready" : "unavailable"}`).join("\n")}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${allOk ? "bg-ok" : "bg-warn"}`} />
      {allOk ? "All models ready" : `${okCount}/${items.length} models ready`}
    </span>
  );
}

function crumb(path: string) {
  const all = NAV.flatMap((g) => g.items.map((i) => ({ ...i, group: g.heading })));
  const hit = [...all].sort((a, b) => b.href.length - a.href.length).find((i) => (i.exact ? path === i.href : path.startsWith(i.href)));
  return hit ? { group: hit.group, label: hit.label } : { group: "Workspace", label: "Overview" };
}

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const here = crumb(path);

  useEffect(() => {
    const t = setTimeout(() => setOpen(false), 0);
    return () => clearTimeout(t);
  }, [path]);

  const nav = (
    <nav aria-label="Workspace" className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
      {NAV.map((g) => (
        <div key={g.heading}>
          <p className="mb-1.5 px-3 text-[11px] font-medium uppercase tracking-[0.14em] text-ink-faint">{g.heading}</p>
          <ul className="space-y-0.5">
            {g.items.map((i) => {
              const active = i.exact ? path === i.href : path.startsWith(i.href);
              return (
                <li key={i.href}>
                  <Link
                    href={i.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent-champagne ${
                      active ? "bg-white/[0.07] text-ink" : "text-ink-muted hover:bg-white/[0.04] hover:text-ink"
                    }`}
                  >
                    <span className={active ? "text-accent-champagne" : ""}><Icon d={i.icon} /></span>
                    {i.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );

  const brand = (
    <Link href="/workspace" className="flex items-center gap-2.5 px-5 py-4 text-sm font-semibold tracking-tight text-ink">
      <span className="grid h-7 w-7 place-items-center rounded-md bg-accent-champagne/15 text-accent-champagne">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" fill="currentColor" stroke="none" /></svg>
      </span>
      {BRAND}
    </Link>
  );

  const footer = (
    <div className="space-y-1 border-t border-line px-5 py-4 text-xs text-ink-faint">
      <Link href="/" className="block hover:text-ink-muted">About the research →</Link>
      <p>Research prototype. Not a medical device.</p>
    </div>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <a href="#content" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[100] focus:rounded-md focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:text-black">
        Skip to content
      </a>

      <aside className="sticky top-0 hidden h-screen flex-col border-r border-line bg-sidebar lg:flex">
        {brand}
        {nav}
        {footer}
      </aside>

      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button className="absolute inset-0 bg-black/60" aria-label="Close menu" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-72 max-w-[85%] flex-col border-r border-line bg-sidebar">
            {brand}
            {nav}
            {footer}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-line bg-bg/90 px-4 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button className="-ml-1 grid h-9 w-9 place-items-center rounded-md text-ink-muted hover:bg-white/5 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden><path d="M4 7h16M4 12h16M4 17h16" /></svg>
            </button>
            <p className="truncate text-sm text-ink-faint">
              {here.group} <span className="mx-1.5 text-ink-faint/60">/</span> <span className="text-ink">{here.label}</span>
            </p>
          </div>
          <StatusPill />
        </header>
        <main id="content" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
