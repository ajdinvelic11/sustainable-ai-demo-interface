import { BrainCircuit, LogOut, RadioTower, ShieldCheck } from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import Button from "./ui/Button";

export default function NavBar() {
  const { user, config, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
        <Link to="/" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-400 text-slate-950">
            <BrainCircuit className="h-5 w-5" />
          </span>
          <div>
            <div className="text-sm font-semibold text-white">Sustainable AI Demo Interface</div>
            <div className="text-xs text-slate-400">Multi-site training control surface</div>
          </div>
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <nav className="flex items-center gap-1">
            <NavLink to="/" className={({ isActive }) => `rounded-lg px-3 py-2 text-sm ${isActive ? "bg-slate-800 text-cyan-200" : "text-slate-400 hover:text-white"}`}>
              Overview
            </NavLink>
          </nav>
          {config?.mock_mode && (
            <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1.5 text-xs font-semibold text-amber-200">
              <RadioTower className="h-3.5 w-3.5" />
              Demo Auth Mode
            </span>
          )}
          <span className="inline-flex max-w-sm items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-200">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span className="truncate">{user?.subject || "verified session"}</span>
          </span>
          <Button variant="secondary" onClick={handleLogout}>
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </div>
      </div>
    </header>
  );
}
