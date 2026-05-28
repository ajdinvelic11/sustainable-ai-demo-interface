import { FormEvent, useState } from "react";
import { KeyRound, Loader2, ShieldCheck, TerminalSquare } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import type { AuthConfig } from "../types/api";

type LoginPageProps = {
  authConfig: AuthConfig | null;
  onLogin: (token: string) => Promise<void>;
};

export function LoginPage({ authConfig, onLogin }: LoginPageProps) {
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setStatus(null);
    setLoading(true);
    try {
      await onLogin(token);
      setStatus("Token verified. Session created.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Token verification failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-surface-base px-4 py-8 text-slate-100">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl items-center">
        <div className="grid w-full gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <section className="flex flex-col justify-center">
            <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-lg border border-signal-cyan/40 bg-signal-cyan/12 text-signal-cyan">
              <ShieldCheck size={26} />
            </div>
            <h1 className="max-w-xl text-4xl font-semibold leading-tight text-white sm:text-5xl">Sustainable AI Demo Interface</h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-300">
              Multi-site AI training with checkpoint transfer across Wiener Neustadt, Wien and Eisenstadt.
            </p>
            <div className="mt-8 grid gap-3 text-sm text-slate-300">
              <div className="flex items-center gap-3">
                <TerminalSquare size={18} className="text-signal-green" />
                PostgreSQL-coordinated training commands
              </div>
              <div className="flex items-center gap-3">
                <TerminalSquare size={18} className="text-signal-blue" />
                S3 checkpoint transfer and result tracking
              </div>
            </div>
          </section>

          <Card className="p-6">
            <div className="mb-5 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-white">Secure login</h2>
                <p className="mt-1 text-sm text-slate-400">Paste a JWT / VC-JWT token for validation.</p>
              </div>
              {authConfig?.mock_mode && (
                <span className="rounded-full border border-amber-400/40 bg-amber-400/12 px-3 py-1 text-xs font-semibold text-amber-200">
                  Demo Auth Mode
                </span>
              )}
            </div>

            <form onSubmit={submit} className="grid gap-4">
              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-200">JWT / VC-JWT token</span>
                <textarea
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                  className="min-h-56 w-full resize-y rounded-md border border-surface-line bg-slate-950/70 p-4 font-mono text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-signal-cyan focus:ring-2 focus:ring-signal-cyan/20"
                  placeholder="eyJhbGciOi..."
                  spellCheck={false}
                />
              </label>

              {error && <div className="rounded-md border border-red-400/40 bg-red-500/12 p-3 text-sm text-red-100">{error}</div>}
              {status && <div className="rounded-md border border-emerald-400/40 bg-emerald-400/12 p-3 text-sm text-emerald-100">{status}</div>}
              {!authConfig?.validation_url_configured && !authConfig?.mock_mode && (
                <div className="rounded-md border border-amber-400/40 bg-amber-400/12 p-3 text-sm text-amber-100">
                  VC-JWT validation URL is not fully configured.
                </div>
              )}

              <Button type="submit" disabled={loading || token.trim().length < 16} icon={loading ? <Loader2 size={18} className="animate-spin" /> : <KeyRound size={18} />}>
                Verify & Login
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </main>
  );
}

