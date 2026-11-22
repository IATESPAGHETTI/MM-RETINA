"use client";

import { useRef, type HTMLAttributes } from "react";
import clsx from "clsx";

/** Glass card with a soft highlight that follows the cursor and a small lift on hover.
 * The pointer position is written to CSS variables on the element, so moving the mouse
 * never re-renders React. */
export function SpotlightCard({ className, children, onMouseMove, ...rest }: HTMLAttributes<HTMLDivElement>) {
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={ref}
      onMouseMove={(e) => {
        const el = ref.current;
        if (el) {
          const r = el.getBoundingClientRect();
          el.style.setProperty("--mx", `${e.clientX - r.left}px`);
          el.style.setProperty("--my", `${e.clientY - r.top}px`);
        }
        onMouseMove?.(e);
      }}
      className={clsx("glass spotlight rounded-2xl p-6", className)}
      {...rest}
    >
      {children}
    </div>
  );
}
