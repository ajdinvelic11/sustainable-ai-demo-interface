import { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  children: ReactNode;
}

export default function Button({ variant = "primary", className, children, ...props }: ButtonProps) {
  const classes = {
    primary: "bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-lg shadow-cyan-950/30",
    secondary: "border border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800",
    danger: "bg-red-500 text-white hover:bg-red-400 shadow-lg shadow-red-950/30",
    ghost: "text-slate-300 hover:bg-slate-800/80",
  };
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
        classes[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
