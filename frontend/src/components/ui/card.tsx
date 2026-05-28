import type { HTMLAttributes, ReactNode } from "react";
import { clsx } from "clsx";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  title?: string;
  action?: ReactNode;
};

export function Card({ className, title, action, children, ...props }: CardProps) {
  return (
    <section
      className={clsx("rounded-lg border border-surface-line bg-surface-raised/88 shadow-panel backdrop-blur", className)}
      {...props}
    >
      {(title || action) && (
        <div className="flex min-h-14 items-center justify-between border-b border-surface-line px-5">
          {title ? <h2 className="text-sm font-semibold text-slate-100">{title}</h2> : <span />}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

