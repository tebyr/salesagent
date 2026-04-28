"use client";
import { useEffect, useState } from "react";
import { Clock, LogOut, RefreshCw } from "lucide-react";

interface SessionTimeoutModalProps {
  /** Segundos restantes antes del cierre automático */
  secondsLeft: number;
  onContinue: () => void;
  onLogout: () => void;
}

export function SessionTimeoutModal({
  secondsLeft,
  onContinue,
  onLogout,
}: SessionTimeoutModalProps) {
  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const countdown =
    minutes > 0
      ? `${minutes}:${String(seconds).padStart(2, "0")}`
      : `${seconds}s`;

  const isUrgent = secondsLeft <= 30;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[9999] p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden">
        {/* Header */}
        <div className={`px-6 pt-6 pb-4 text-center ${isUrgent ? "bg-red-50" : "bg-amber-50"}`}>
          <div className={`inline-flex items-center justify-center w-14 h-14 rounded-full mb-3 ${
            isUrgent ? "bg-red-100" : "bg-amber-100"
          }`}>
            <Clock className={`w-7 h-7 ${isUrgent ? "text-red-600" : "text-amber-600"}`} />
          </div>
          <h2 className="text-lg font-semibold text-slate-900">
            Sesión por expirar
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Tu sesión cerrará por inactividad en
          </p>
          <p className={`text-4xl font-bold mt-2 tabular-nums ${
            isUrgent ? "text-red-600" : "text-amber-600"
          }`}>
            {countdown}
          </p>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-3">
          <button
            onClick={onContinue}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Seguir conectado
          </button>
          <button
            onClick={onLogout}
            className="w-full flex items-center justify-center gap-2 text-slate-600 px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-slate-100 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Cerrar sesión ahora
          </button>
        </div>
      </div>
    </div>
  );
}
