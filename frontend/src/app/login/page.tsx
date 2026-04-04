"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import Cookies from "js-cookie";
import { MessageSquare, Loader2 } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(email, password);
      Cookies.set("access_token", data.access_token, { expires: 1 });
      Cookies.set("user_name", data.user_name, { expires: 1 });
      Cookies.set("user_role", data.user_role, { expires: 1 });
      router.push("/dashboard");
    } catch {
      setError("Email o contraseña incorrectos");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-blue-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="bg-blue-600 p-3 rounded-xl">
            <MessageSquare className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Sales Agent</h1>
            <p className="text-sm text-slate-500">Panel de Administración</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Correo electrónico
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              placeholder="gerente@empresa.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Contraseña
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-4 py-2.5 rounded-lg border border-red-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {loading ? "Ingresando..." : "Ingresar"}
          </button>
        </form>
      </div>
    </div>
  );
}
