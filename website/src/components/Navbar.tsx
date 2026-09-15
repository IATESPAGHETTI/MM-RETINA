"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { NAV_LINKS } from "@/lib/content";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="fixed inset-x-0 top-4 z-50 flex justify-center px-4"
    >
      <nav
        className={`flex w-full max-w-3xl items-center justify-between rounded-full border border-white/10 px-4 py-2.5 transition-all duration-300 ${
          scrolled ? "glass-strong" : "glass"
        }`}
        aria-label="Primary"
      >
        <Link href="/" className="flex items-center gap-2 text-sm font-semibold tracking-wide text-ink">
          <span className="h-2 w-2 rounded-full bg-accent-champagne" aria-hidden />
          MM&#8209;RETINA
        </Link>

        <ul className="hidden items-center gap-6 md:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="text-sm text-ink-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        <Link
          href="/demo"
          className="rounded-full bg-white/95 px-4 py-1.5 text-sm font-medium text-black transition-transform hover:-translate-y-0.5 hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
        >
          Launch demo
        </Link>
      </nav>
    </motion.header>
  );
}
