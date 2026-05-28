import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertTriangle, BrainCircuit, Loader2, LockKeyhole, RadioTower, ShieldCheck } from "lucide-react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import Button from "../components/ui/button";
import Card from "../components/ui/card";

const JWT_RE = /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;

export default function LoginPage() {
  const { authenticated, loading, login, config } = useAuth();
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = useMemo(() => {
    const state = location.state as { from?: { pathname?: string } } | null;
    return state?.from?.pathname || "/";
  }, [location.state]);

  useEffect(() => {
    if (!loading && authenticated) {
      navigate(redirectTo, { replace: true });
    }
  }, [authenticated, loading, navigate, redirectTo]);

  if (!loading && authenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const trimmed = token.trim();
    if (!trimmed) {
      setError("Paste a JWT / VC-JWT token to continue.");
      return;
    }
    if (!JWT_RE.test(trimmed)) {
      setError("The token must have three JWT segments separated by dots.");
      return;
    }
    setVerifying(true);
    try {
      await login(trimmed);
      setToken("");
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.16),transparent_34%),#020617]">
      <main className="mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-6 py-12 lg:grid-cols-[0.9fr_1.1fr]">
        <section>
          <div className="mb-8 flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-400 text-slate-950">
              <BrainCircuit className="h-6 w-6" />
            </span>
            <div>
              <div className="text-sm font-semibold text-white">Sustainable AI Demo Interface</div>
              <div className="text-xs text-slate-400">Credential-gated training control</div>
            </div>
          </div>

          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1.5 text-xs font-semibold text-cyan-200">
            <ShieldCheck className="h-3.5 w-3.5" />
            VC-JWT validation
          </div>
          <h1 className="mt-6 max-w-3xl text-5xl font-semibold tracking-normal text-white lg:text-6xl">
            Secure control room for a multi-site Sustainable AI demo
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            Log in with a JWT / VC-JWT, start the five-minute training chain, and monitor checkpoint transfer across Wiener Neustadt, Wien and Eisenstadt.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {["No password-based access", "Compliance validation", "HttpOnly app session"].map((item) => (
              <div key={item} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm font-semibold text-slate-200">
                {item}
              </div>
            ))}
          </div>
        </section>

        <Card className="p-7 lg:p-8">
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800 text-cyan-300">
                <LockKeyhole className="h-6 w-6" />
              </div>
              <h2 className="mt-5 text-2xl font-semibold text-white">Verify & Login</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                Paste a Gaia-X compatible VC-JWT or a JWT accepted by your configured validation service.
              </p>
            </div>
            {config?.mock_mode && (
              <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1.5 text-xs font-semibold text-amber-200">
                <RadioTower className="h-3.5 w-3.5" />
                Demo Auth Mode
              </span>
            )}
          </div>

          {error && (
            <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-200">
              <AlertTriangle className="mt-0.5 h-5 w-5 flex-none" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <label>
              <span className="mb-2 block text-sm font-medium text-slate-300">JWT / VC-JWT token</span>
              <textarea
                className="control-input min-h-60 resize-y font-mono text-xs leading-5"
                spellCheck={false}
                value={token}
                onChange={(event) => setToken(event.target.value)}
                placeholder="Paste token here"
              />
            </label>
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm leading-6 text-slate-400">
              The raw token is sent only to the backend for verification. The browser receives a short-lived application session through an HttpOnly cookie.
            </div>
            <Button className="w-full" disabled={verifying}>
              {verifying ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
              Verify & Login
            </Button>
          </form>
        </Card>
      </main>
    </div>
  );
}
