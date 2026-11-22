"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { NAV_LINKS } from "@/lib/content";

/** The nav link that best matches the current path. The longest matching href wins, so
 * /research/journey highlights "Journey" rather than "Research". */
function activeHref(pathname: string): string | null {
  let best: string | null = null;
  for (const { href } of NAV_LINKS) {
    const matches = pathname === href || pathname.startsWith(`${href}/`);
    if (matches && (best === null || href.length > best.length)) best = href;
  }
  return best;
}

const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne";

export function Navbar() {
  const pathname = usePathname();
  const active = activeHref(pathname);
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <motion.header
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="fixed inset-x-0 top-4 z-50 flex justify-center px-4"
    >
      <div className="relative w-full max-w-4xl">
        <nav
          className={`flex w-full items-center justify-between gap-3 rounded-full border border-white/10 px-4 py-2.5 transition-all duration-300 ${
            scrolled || open ? "glass-strong" : "glass"
          }`}
          aria-label="Primary"
        >
          <Link href="/" className={`flex shrink-0 items-center gap-2 text-sm font-semibold tracking-wide text-ink ${focusRing}`}>
            <span className="relative flex h-2 w-2" aria-hidden>
              <span className="pulse-ring absolute inline-flex h-full w-full rounded-full bg-accent-champagne" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-champagne" />
            </span>
            MM&#8209;RETINA
          </Link>

          <ul className="hidden items-center gap-1 lg:flex">
            {NAV_LINKS.map((link) => {
              const isActive = active === link.href;
              return (
                <li key={link.href} className="relative">
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-pill"
                      className="absolute inset-0 rounded-full bg-white/10"
                      transition={{ type: "spring", stiffness: 420, damping: 34 }}
                      aria-hidden
                    />
                  )}
                  <Link
                    href={link.href}
                    aria-current={isActive ? "page" : undefined}
                    className={`relative z-10 block rounded-full px-3 py-1.5 text-sm transition-colors hover:text-ink ${
                      isActive ? "text-ink" : "text-ink-muted"
                    } ${focusRing}`}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
          </ul>

          <div className="flex items-center gap-2">
            <Link
              href="/demo"
              className={`shrink-0 whitespace-nowrap rounded-full bg-white/95 px-4 py-1.5 text-sm font-medium text-black transition-transform hover:-translate-y-0.5 hover:shadow-lg ${focusRing}`}
            >
              <span className="hidden min-[400px]:inline">Launch demo</span>
              <span className="min-[400px]:hidden">Demo</span>
            </Link>
            <button
              type="button"
              onClick={() => setOpen((o) => !o)}
              aria-expanded={open}
              aria-controls="mobile-nav"
              aria-label={open ? "Close menu" : "Open menu"}
              className={`flex h-9 w-9 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-white/10 hover:text-ink lg:hidden ${focusRing}`}
            >
              <span className="relative block h-[14px] w-[18px]" aria-hidden>
                <motion.span
                  className="absolute left-0 top-0 h-[1.6px] w-full rounded-full bg-current"
                  animate={open ? { y: 6, rotate: 45 } : { y: 0, rotate: 0 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                />
                <motion.span
                  className="absolute left-0 top-[6px] h-[1.6px] w-full rounded-full bg-current"
                  animate={{ opacity: open ? 0 : 1 }}
                  transition={{ duration: 0.15 }}
                />
                <motion.span
                  className="absolute left-0 top-[12px] h-[1.6px] w-full rounded-full bg-current"
                  animate={open ? { y: -6, rotate: -45 } : { y: 0, rotate: 0 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                />
              </span>
            </button>
          </div>
        </nav>

        <AnimatePresence>
          {open && (
            <motion.ul
              id="mobile-nav"
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="absolute inset-x-0 top-full mt-2 origin-top rounded-3xl border border-white/10 bg-[rgba(22,21,20,0.97)] p-2 shadow-[var(--glass-shadow)] backdrop-blur-xl lg:hidden"
            >
              {NAV_LINKS.map((link, i) => (
                <motion.li
                  key={link.href}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0, transition: { delay: 0.04 * i + 0.05, duration: 0.3 } }}
                >
                  <Link
                    href={link.href}
                    onClick={() => setOpen(false)}
                    aria-current={active === link.href ? "page" : undefined}
                    className={`flex items-center justify-between rounded-2xl px-4 py-3 text-base transition-colors hover:bg-white/5 ${
                      active === link.href ? "bg-white/10 text-ink" : "text-ink-muted"
                    } ${focusRing}`}
                  >
                    {link.label}
                    {active === link.href && <span className="h-1.5 w-1.5 rounded-full bg-accent-champagne" aria-hidden />}
                  </Link>
                </motion.li>
              ))}
            </motion.ul>
          )}
        </AnimatePresence>
      </div>
    </motion.header>
  );
}
