import { LogOut, ShieldCheck, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./ui/button";
import type { SessionUser } from "../types/api";

type AppShellProps = {
  user: SessionUser | null;
  demoAuthMode: boolean;
  onLogout: () => void;
  children: ReactNode;
};

export function AppShell({ user, demoAuthMode, onLogout, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-surface-base text-slate-100">
      <header className="sticky top-0 z-20 border-b border-surface-line bg-surface-base/88 backdrop-blur">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-signal-cyan/40 bg-signal-cyan/12 text-signal-cyan">
              <ShieldCheck size={20} />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Sustainable AI Demo Interface</p>
              <p className="text-xs text-slate-400">Multi-site training control</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {demoAuthMode && (
              <span className="rounded-full border border-amber-400/40 bg-amber-400/12 px-3 py-1 text-xs font-semibold text-amber-200">
                Demo Auth Mode
              </span>
            )}
            <div className="hidden items-center gap-2 rounded-md border border-surface-line bg-surface-raised px-3 py-2 text-xs text-slate-300 sm:flex">
              <UserRound size={15} />
              <span className="max-w-52 truncate">{user?.email ?? user?.name ?? user?.subject ?? "session"}</span>
            </div>
            <Button variant="ghost" icon={<LogOut size={17} />} onClick={onLogout} aria-label="Logout">
              Logout
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}
