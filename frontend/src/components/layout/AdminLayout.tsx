"use client";
import { Sidebar } from "./Sidebar";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Cookies from "js-cookie";
import { getTenantSettings } from "@/lib/api";
import { useIdleTimeout } from "@/hooks/useIdleTimeout";
import { SessionTimeoutModal } from "@/components/SessionTimeoutModal";

function logout() {
  Cookies.remove("access_token");
  Cookies.remove("user_name");
  Cookies.remove("user_role");
  window.location.href = "/login";
}

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [showWarning, setShowWarning] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(120);
  const countdownRef = { current: null as ReturnType<typeof setInterval> | null };

  // Cargar configuracion de seguridad del tenant
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: getTenantSettings,
    enabled: !!Cookies.get("access_token"),
    staleTime: 5 * 60 * 1000,
  });

  const timeoutMinutes: number = settings?.security_config?.session_timeout_minutes ?? 30;
  const warningMinutes: number = settings?.security_config?.session_warning_minutes ?? 2;

  const handleWarn = useCallback(() => {
    setSecondsLeft(warningMinutes * 60);
    setShowWarning(true);
  }, [warningMinutes]);

  const handleTimeout = useCallback(() => {
    setShowWarning(false);
    logout();
  }, []);

  const { resetTimer } = useIdleTimeout({
    timeoutMinutes,
    warningMinutes,
    onWarn: handleWarn,
    onTimeout: handleTimeout,
  });

  // Cuenta regresiva visible en el modal
  useEffect(() => {
    if (!showWarning) {
      if (countdownRef.current) clearInterval(countdownRef.current);
      return;
    }
    countdownRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(countdownRef.current!);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [showWarning]);

  // Redirigir si no hay token
  useEffect(() => {
    if (!Cookies.get("access_token")) router.push("/login");
  }, [router]);

  function handleContinue() {
    setShowWarning(false);
    resetTimer();
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="p-6 max-w-7xl mx-auto">{children}</div>
      </main>

      {showWarning && (
        <SessionTimeoutModal
          secondsLeft={secondsLeft}
          onContinue={handleContinue}
          onLogout={logout}
        />
      )}
    </div>
  );
}
