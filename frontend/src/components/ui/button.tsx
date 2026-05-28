import type { ButtonHTMLAttributes, ReactNode } from "react";
import { clsx } from "clsx";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  icon?: ReactNode;
};

const variants = {
  primary:
    "bg-signal-cyan text-slate-950 hover:bg-cyan-300 shadow-[0_0_28px_rgba(24,211,255,0.22)] disabled:bg-slate-600 disabled:text-slate-300",
  secondary: "bg-surface-panel text-slate-100 border border-surface-line hover:border-signal-blue",
  danger: "bg-red-500/14 text-red-100 border border-red-400/40 hover:bg-red-500/22",
  ghost: "bg-transparent text-slate-300 hover:text-white hover:bg-white/6"
};

export function Button({ className, variant = "primary", icon, children, ...props }: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-signal-cyan/70 disabled:cursor-not-allowed disabled:opacity-70",
        variants[variant],
        className
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}

