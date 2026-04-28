import { useEffect, useRef, useCallback } from "react";

interface UseIdleTimeoutOptions {
  /** Minutos de inactividad antes de mostrar el aviso */
  timeoutMinutes: number;
  /** Minutos de aviso antes del cierre definitivo */
  warningMinutes: number;
  /** Callback al entrar en estado de aviso */
  onWarn: () => void;
  /** Callback al cerrar sesión por inactividad */
  onTimeout: () => void;
}

const ACTIVITY_EVENTS = [
  "mousemove",
  "mousedown",
  "keydown",
  "scroll",
  "touchstart",
  "click",
];

export function useIdleTimeout({
  timeoutMinutes,
  warningMinutes,
  onWarn,
  onTimeout,
}: UseIdleTimeoutOptions) {
  const warnTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const logoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isWarningRef = useRef(false);

  const clearTimers = useCallback(() => {
    if (warnTimerRef.current) clearTimeout(warnTimerRef.current);
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
  }, []);

  const startTimers = useCallback(() => {
    clearTimers();
    isWarningRef.current = false;

    const warnMs = (timeoutMinutes - warningMinutes) * 60 * 1000;
    const logoutMs = timeoutMinutes * 60 * 1000;

    warnTimerRef.current = setTimeout(() => {
      isWarningRef.current = true;
      onWarn();
    }, warnMs);

    logoutTimerRef.current = setTimeout(() => {
      onTimeout();
    }, logoutMs);
  }, [timeoutMinutes, warningMinutes, onWarn, onTimeout, clearTimers]);

  // Resetear timers al detectar actividad (solo si no estamos en modal de aviso)
  const handleActivity = useCallback(() => {
    if (!isWarningRef.current) {
      startTimers();
    }
  }, [startTimers]);

  useEffect(() => {
    startTimers();

    ACTIVITY_EVENTS.forEach((event) =>
      window.addEventListener(event, handleActivity, { passive: true })
    );

    return () => {
      clearTimers();
      ACTIVITY_EVENTS.forEach((event) =>
        window.removeEventListener(event, handleActivity)
      );
    };
  }, [startTimers, handleActivity, clearTimers]);

  /** Llamar desde el modal "Seguir conectado" para resetear */
  const resetTimer = useCallback(() => {
    isWarningRef.current = false;
    startTimers();
  }, [startTimers]);

  return { resetTimer };
}
