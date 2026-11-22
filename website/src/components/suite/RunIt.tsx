"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Reveal } from "@/components/Reveal";
import { SUITE_RUN_COMMANDS, SUITE_URL } from "@/lib/suiteContent";

const COMMAND_TEXT = SUITE_RUN_COMMANDS.join("\n");

type CopyState = "idle" | "copied" | "manual";

export function RunIt() {
  const [state, setState] = useState<CopyState>("idle");
  const preRef = useRef<HTMLPreElement>(null);

  function flash(next: CopyState) {
    setState(next);
    window.setTimeout(() => setState("idle"), next === "manual" ? 3200 : 1800);
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(COMMAND_TEXT);
      flash("copied");
    } catch {
      // Clipboard blocked (permissions policy, insecure origin, denied prompt). Select the
      // commands so Ctrl+C works, and say so instead of failing silently.
      const el = preRef.current;
      const sel = window.getSelection();
      if (el && sel) {
        const range = document.createRange();
        range.selectNodeContents(el);
        sel.removeAllRanges();
        sel.addRange(range);
      }
      flash("manual");
    }
  }

  const label = state === "copied" ? "Copied" : state === "manual" ? "Press Ctrl+C" : "Copy";

  return (
    <section id="run" className="relative scroll-mt-24 px-6 py-24">
      <div className="mx-auto grid max-w-6xl items-start gap-10 lg:grid-cols-[1fr_1.1fr]">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-ink-faint">Run it locally</p>
          <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Two commands, one workspace.</h2>
          <p className="mt-4 text-ink-muted">
            The script creates a virtual environment, installs the backend and the app, then starts the API and
            the interface. It falls back to CPU when there is no GPU, though it has only been tested on an RTX
            3060.
          </p>
          <ul className="mt-6 space-y-2 text-sm text-ink-muted">
            <li className="flex gap-3">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-champagne" aria-hidden />
              Needs Python 3.10+ and Node 20+.
            </li>
            <li className="flex gap-3">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-champagne" aria-hidden />
              <span>
                This website already uses port 3000, so the commands start the workspace on port 3100 and its API
                on 8001. Plain <code className="text-ink">.\run.ps1</code> uses 3000 and 8000.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-champagne" aria-hidden />
              API reference at <code className="text-ink">/docs</code> on the backend port.
            </li>
            <li className="flex gap-3">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-champagne" aria-hidden />
              <span>
                Then open{" "}
                <a
                  href={SUITE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-ink underline decoration-white/25 underline-offset-4 hover:decoration-white/60"
                >
                  {SUITE_URL}
                </a>
                .
              </span>
            </li>
          </ul>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="glass-strong overflow-hidden rounded-2xl">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-2.5">
              <div className="flex items-center gap-1.5" aria-hidden>
                <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
                <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
                <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
              </div>
              <span className="text-xs text-ink-faint">PowerShell</span>
              <button
                type="button"
                onClick={copy}
                className="relative min-w-[6.5rem] rounded-full border border-white/10 px-3 py-1 text-xs text-ink-muted transition-colors hover:border-white/25 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne"
              >
                <AnimatePresence mode="wait" initial={false}>
                  <motion.span
                    key={state}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.15 }}
                    className={`block ${state === "idle" ? "" : "text-accent-champagne"}`}
                    aria-live="polite"
                  >
                    {label}
                  </motion.span>
                </AnimatePresence>
              </button>
            </div>
            <pre ref={preRef} className="overflow-x-auto p-5 font-mono text-sm leading-7 text-ink">
              {SUITE_RUN_COMMANDS.map((line, i) => (
                <motion.div
                  key={line}
                  initial={{ opacity: 0, x: -8 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: 0.25 + i * 0.18 }}
                >
                  <span className="select-none text-accent-champagne">PS&gt; </span>
                  {line}
                </motion.div>
              ))}
            </pre>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
