"use client";

import { motion } from "framer-motion";

/** Soft page transition. Templates remount on every navigation (unlike layouts), which
 * is what lets the entrance animation replay for each route. Opacity and a small rise only,
 * so scroll position and sticky/fixed children are unaffected once it settles. */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
