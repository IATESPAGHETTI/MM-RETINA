import { HTMLAttributes } from "react";
import clsx from "clsx";

type GlassCardProps = HTMLAttributes<HTMLDivElement> & {
  strong?: boolean;
};

export function GlassCard({ strong, className, children, ...rest }: GlassCardProps) {
  return (
    <div
      className={clsx(
        strong ? "glass-strong" : "glass",
        "rounded-2xl p-6 md:p-8",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
