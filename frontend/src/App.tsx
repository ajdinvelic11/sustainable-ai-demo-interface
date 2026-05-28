import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Skeleton } from "./components/ui/skeleton";
import { useSession } from "./hooks/useSession";
import { DashboardPage } from "./pages/DashboardPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";

export function App() {
  const navigate = useNavigate();
  const session = useSession();

  if (session.loading) {
    return (
      <main className="min-h-screen bg-surface-base p-6">
        <div className="mx-auto grid max-w-5xl gap-5">
          <Skeleton className="h-16" />
          <Skeleton className="h-80" />
          <Skeleton className="h-56" />
        </div>
      </main>
    );
  }

  if (!session.authenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage authConfig={session.authConfig} onLogin={session.login} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  const logout = async () => {
    await session.logout();
    navigate("/login", { replace: true });
  };

  return (
    <AppShell user={session.user} demoAuthMode={session.demoAuthMode} onLogout={logout}>
      <Routes>
        <Route path="/" element={<HomePage user={session.user} />} />
        <Route path="/runs/:demoRunId" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

