"use client";
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Cookies from "js-cookie";
import {
  getTenantSettings, updateTenantSettings,
  updateWhatsAppConfig, testWhatsAppConnection,
  updateScheduleConfig, updateSecurityConfig,
} from "@/lib/api";
import { AdminLayout } from "@/components/layout/AdminLayout";
import {
  Loader2, Save, CheckCircle, XCircle, Phone, Bell,
  Building2, Settings2, ChevronRight, ShieldCheck,
} from "lucide-react";

type TabId = "general" | "whatsapp" | "schedule" | "notifications" | "security";

const BASE_TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: "general", label: "General", icon: Building2 },
  { id: "whatsapp", label: "WhatsApp", icon: Phone },
  { id: "schedule", label: "Horarios", icon: Bell },
  { id: "notifications", label: "Avanzado", icon: Settings2 },
];
const SECURITY_TAB = { id: "security" as TabId, label: "Seguridad", icon: ShieldCheck };

function SaveButton({ loading, saved }: { loading: boolean; saved: boolean }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
      {saved ? "Guardado" : "Guardar cambios"}
    </button>
  );
}

function FieldGroup({ label, description, children }: {
  label: string; description?: string; children: React.ReactNode;
}) {
  return (
    <div className="py-5 border-b border-slate-100 last:border-0">
      <div className="grid grid-cols-3 gap-6 items-start">
        <div>
          <p className="text-sm font-medium text-slate-900">{label}</p>
          {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
        </div>
        <div className="col-span-2">{children}</div>
      </div>
    </div>
  );
}

function Input({ label, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label?: string }) {
  return (
    <div>
      {label && <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>}
      <input
        {...props}
        className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}

function GeneralTab({ settings }: { settings: Record<string, unknown> }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    company_name: (settings.company_name as string) || "",
    agent_name: (settings.agent_name as string) || "",
    agent_description: (settings.agent_description as string) || "",
    timezone: (settings.timezone as string) || "America/Bogota",
    currency: (settings.currency as string) || "COP",
    contact_email: (settings.contact_email as string) || "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await updateTenantSettings(form);
      qc.invalidateQueries({ queryKey: ["settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Error guardando configuración");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-1">
      <FieldGroup label="Nombre de la empresa" description="Se muestra en reportes y comunicaciones">
        <Input
          value={form.company_name}
          onChange={(e) => setForm({ ...form, company_name: e.target.value })}
          placeholder="Distribuidora El Sol"
        />
      </FieldGroup>
      <FieldGroup label="Nombre del agente" description="Cómo se presenta el agente por WhatsApp">
        <Input
          value={form.agent_name}
          onChange={(e) => setForm({ ...form, agent_name: e.target.value })}
          placeholder="SalesBot"
        />
      </FieldGroup>
      <FieldGroup label="Descripción del agente" description="Frase de presentación del agente">
        <textarea
          value={form.agent_description}
          onChange={(e) => setForm({ ...form, agent_description: e.target.value })}
          rows={2}
          placeholder="Asistente comercial de Distribuidora El Sol"
          className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      </FieldGroup>
      <FieldGroup label="Zona horaria">
        <select
          value={form.timezone}
          onChange={(e) => setForm({ ...form, timezone: e.target.value })}
          className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="America/Bogota">America/Bogota (UTC-5)</option>
          <option value="America/New_York">America/New_York (UTC-5/-4)</option>
          <option value="America/Mexico_City">America/Mexico_City (UTC-6/-5)</option>
        </select>
      </FieldGroup>
      <FieldGroup label="Email de contacto" description="Para reportes gerenciales">
        <Input
          type="email"
          value={form.contact_email}
          onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
          placeholder="gerencia@empresa.com"
        />
      </FieldGroup>
      {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
      <div className="flex justify-end pt-4">
        <SaveButton loading={saving} saved={saved} />
      </div>
    </form>
  );
}

function WhatsAppTab({ settings }: { settings: Record<string, unknown> }) {
  const wa = (settings.whatsapp_config as Record<string, string>) || {};
  const [form, setForm] = useState({
    phone_number_id: "",
    business_account_id: "",
    access_token: "",
    phone_display: "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [error, setError] = useState("");

  // Pre-poblar el formulario cuando llegan los datos del servidor
  useEffect(() => {
    if (wa.phone_number_id || wa.business_account_id || wa.phone_display) {
      setForm({
        phone_number_id: wa.phone_number_id || "",
        business_account_id: wa.business_account_id || "",
        access_token: "",          // El token nunca se devuelve por seguridad
        phone_display: wa.phone_display || "",
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wa.phone_number_id, wa.business_account_id, wa.phone_display]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await updateWhatsAppConfig(form);
      setSaved(true);
      // Limpiar token después de guardar exitosamente
      setForm((f) => ({ ...f, access_token: "" }));
      setTimeout(() => setSaved(false), 3000);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Error guardando configuración de WhatsApp");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testWhatsAppConnection();
      // Meta devuelve { status, phone_info: { verified_name, display_phone_number, quality_rating } }
      const info = res.phone_info;
      const detail = info
        ? `${info.verified_name} · ${info.display_phone_number} · Calidad: ${info.quality_rating}`
        : "Conexión exitosa";
      setTestResult({ ok: true, message: detail });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setTestResult({ ok: false, message: detail || "No se pudo conectar. Verifica las credenciales." });
    } finally {
      setTesting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-1" autoComplete="off">
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
        <p className="text-sm text-blue-800 font-medium">Configuración de Meta WhatsApp Business</p>
        <p className="text-xs text-blue-700 mt-1">
          Obtén estas credenciales desde el{" "}
          <span className="underline cursor-pointer">Meta Business Manager</span>
          {" → WhatsApp → API Setup"}
        </p>
      </div>
      <FieldGroup label="Phone Number ID" description="ID del número de teléfono de WhatsApp Business">
        <Input
          value={form.phone_number_id}
          onChange={(e) => setForm({ ...form, phone_number_id: e.target.value })}
          placeholder="123456789012345"
          autoComplete="off"
        />
      </FieldGroup>
      <FieldGroup label="WABA ID" description="ID de la cuenta de WhatsApp Business">
        <Input
          value={form.business_account_id}
          onChange={(e) => setForm({ ...form, business_account_id: e.target.value })}
          placeholder="987654321098765"
          autoComplete="off"
        />
      </FieldGroup>
      <FieldGroup
        label="Access Token"
        description={
          settings.whatsapp_configured
            ? "Token actual guardado — ingresa uno nuevo solo si necesitas actualizarlo"
            : "Token de acceso de la API (caduca cada 24h en sandbox)"
        }
      >
        <Input
          type="password"
          value={form.access_token}
          onChange={(e) => setForm({ ...form, access_token: e.target.value })}
          placeholder={settings.whatsapp_configured ? "••••••••  (dejar vacío para conservar)" : "EAAxxxxxxxx..."}
          autoComplete="new-password"
        />
      </FieldGroup>
      <FieldGroup label="Número de teléfono" description="Número visible al usuario (ej: +57 300 123 4567)">
        <Input
          value={form.phone_display}
          onChange={(e) => setForm({ ...form, phone_display: e.target.value })}
          placeholder="+57 300 123 4567"
          autoComplete="off"
        />
      </FieldGroup>

      {testResult && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm ${
          testResult.ok ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
        }`}>
          {testResult.ok
            ? <CheckCircle className="w-4 h-4" />
            : <XCircle className="w-4 h-4" />}
          {testResult.message}
        </div>
      )}

      {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
      <div className="flex justify-between items-center pt-4">
        <button
          type="button"
          onClick={handleTest}
          disabled={testing}
          className="flex items-center gap-2 border border-slate-200 text-slate-700 px-4 py-2 rounded-lg text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Phone className="w-4 h-4" />}
          Probar conexión
        </button>
        <SaveButton loading={saving} saved={saved} />
      </div>
    </form>
  );
}

function ScheduleTab({ settings }: { settings: Record<string, unknown> }) {
  const sc = (settings.schedule_config as Record<string, string>) || {};
  const [form, setForm] = useState({
    work_start: sc.work_start || "08:00",
    work_end: sc.work_end || "18:00",
    briefing_time: sc.briefing_time || "06:30",
    summary_time: sc.summary_time || "18:30",
    performance_report_time: sc.performance_report_time || "20:00",
    no_visit_followup_time: sc.no_visit_followup_time || "19:00",
    management_report_time: sc.management_report_time || "07:00",
    pre_visit_interval_minutes: sc.pre_visit_interval_minutes || "60",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await updateScheduleConfig(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Error guardando configuración de horarios");
    } finally {
      setSaving(false);
    }
  }

  const timeField = (label: string, key: keyof typeof form, description?: string) => (
    <FieldGroup key={key} label={label} description={description}>
      <Input
        type="time"
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
      />
    </FieldGroup>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-1">
      <div className="grid grid-cols-2 gap-4 py-5 border-b border-slate-100">
        <div>
          <p className="text-sm font-medium text-slate-900 mb-1">Horario laboral</p>
          <p className="text-xs text-slate-500 mb-3">Ventana de operación del equipo</p>
          <div className="flex gap-3 items-center">
            <Input
              type="time"
              label="Inicio"
              value={form.work_start}
              onChange={(e) => setForm({ ...form, work_start: e.target.value })}
            />
            <span className="text-slate-400 mt-5">—</span>
            <Input
              type="time"
              label="Fin"
              value={form.work_end}
              onChange={(e) => setForm({ ...form, work_end: e.target.value })}
            />
          </div>
        </div>
        <div>
          <p className="text-sm font-medium text-slate-900 mb-1">Intervalo pre-visita</p>
          <p className="text-xs text-slate-500 mb-3">Cada cuántos minutos se notifica a clientes</p>
          <Input
            type="number"
            label="Minutos"
            value={form.pre_visit_interval_minutes}
            onChange={(e) => setForm({ ...form, pre_visit_interval_minutes: e.target.value })}
            min="15"
            max="120"
          />
        </div>
      </div>

      <div className="py-4">
        <p className="text-sm font-semibold text-slate-700 mb-3">Mensajes automáticos a vendedores</p>
      </div>
      {timeField("Briefing matutino", "briefing_time", "Resumen de ruta y recomendaciones del día")}
      {timeField("Resumen diario", "summary_time", "Resultados del día del vendedor")}
      {timeField("Reporte de rendimiento", "performance_report_time", "vs. meta + proyección")}
      {timeField("Seguimiento sin visita", "no_visit_followup_time", "Para clientes no visitados")}

      <div className="py-4">
        <p className="text-sm font-semibold text-slate-700 mb-3">Reportes a gerencia</p>
      </div>
      {timeField("Reporte gerencial diario", "management_report_time", "Consolidado del equipo")}

      {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
      <div className="flex justify-end pt-4">
        <SaveButton loading={saving} saved={saved} />
      </div>
    </form>
  );
}

function AdvancedTab({ settings }: { settings: Record<string, unknown> }) {
  const [form, setForm] = useState({
    max_daily_ai_cost_usd: ((settings.max_daily_ai_cost_usd as number) || 10).toString(),
    affinity_recalc_days: ((settings.affinity_recalc_days as number) || 7).toString(),
    inactive_client_threshold_days: ((settings.inactive_client_threshold_days as number) || 30).toString(),
    low_performance_threshold_pct: ((settings.low_performance_threshold_pct as number) || 60).toString(),
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await updateTenantSettings({
        max_daily_ai_cost_usd: parseFloat(form.max_daily_ai_cost_usd),
        affinity_recalc_days: parseInt(form.affinity_recalc_days),
        inactive_client_threshold_days: parseInt(form.inactive_client_threshold_days),
        low_performance_threshold_pct: parseFloat(form.low_performance_threshold_pct),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Error guardando configuración");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-1">
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
        <p className="text-sm text-amber-800 font-medium">Parámetros avanzados del sistema</p>
        <p className="text-xs text-amber-700 mt-1">
          Modifica estos valores solo si entiendes su impacto en el comportamiento del agente.
        </p>
      </div>
      <FieldGroup
        label="Límite de costo IA diario (USD)"
        description="El sistema se pausa si supera este límite en el día"
      >
        <Input
          type="number"
          value={form.max_daily_ai_cost_usd}
          onChange={(e) => setForm({ ...form, max_daily_ai_cost_usd: e.target.value })}
          step="0.5"
          min="1"
          max="100"
        />
      </FieldGroup>
      <FieldGroup
        label="Recalculo de afinidad (días)"
        description="Cada cuántos días se recalcula el score de afinidad producto-cliente"
      >
        <Input
          type="number"
          value={form.affinity_recalc_days}
          onChange={(e) => setForm({ ...form, affinity_recalc_days: e.target.value })}
          min="1"
          max="30"
        />
      </FieldGroup>
      <FieldGroup
        label="Umbral cliente inactivo (días)"
        description="Días sin compra para marcar cliente como inactivo"
      >
        <Input
          type="number"
          value={form.inactive_client_threshold_days}
          onChange={(e) => setForm({ ...form, inactive_client_threshold_days: e.target.value })}
          min="7"
          max="90"
        />
      </FieldGroup>
      <FieldGroup
        label="Umbral bajo rendimiento (%)"
        description="Porcentaje de meta para disparar alerta de bajo rendimiento"
      >
        <Input
          type="number"
          value={form.low_performance_threshold_pct}
          onChange={(e) => setForm({ ...form, low_performance_threshold_pct: e.target.value })}
          min="10"
          max="90"
        />
      </FieldGroup>
      {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
      <div className="flex justify-end pt-4">
        <SaveButton loading={saving} saved={saved} />
      </div>
    </form>
  );
}

function SecurityTab({ settings }: { settings: Record<string, unknown> }) {
  const qc = useQueryClient();
  const sec = (settings.security_config as Record<string, number>) || {};
  const [form, setForm] = useState({
    session_timeout_minutes: sec.session_timeout_minutes ?? 30,
    session_warning_minutes: sec.session_warning_minutes ?? 2,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (form.session_warning_minutes >= form.session_timeout_minutes) {
      setError("El aviso debe ser menor que el tiempo de cierre.");
      return;
    }
    if (form.session_timeout_minutes < 5) {
      setError("El tiempo mínimo de inactividad es 5 minutos.");
      return;
    }
    setSaving(true);
    try {
      await updateSecurityConfig({
        session_timeout_minutes: form.session_timeout_minutes,
        session_warning_minutes: form.session_warning_minutes,
      });
      qc.invalidateQueries({ queryKey: ["settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Error guardando configuración de seguridad.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="flex items-center gap-3 mb-6 p-3 bg-blue-50 rounded-xl border border-blue-100">
        <ShieldCheck className="w-5 h-5 text-blue-600 flex-shrink-0" />
        <p className="text-sm text-blue-800">
          Controla cuánto tiempo puede estar el panel inactivo antes de cerrar la sesión automáticamente.
        </p>
      </div>

      <FieldGroup
        label="Tiempo de inactividad"
        description="Minutos sin actividad antes de cerrar la sesión (mín. 5)"
      >
        <div className="flex items-center gap-3">
          <input
            type="number"
            min={5}
            max={480}
            value={form.session_timeout_minutes}
            onChange={(e) => setForm({ ...form, session_timeout_minutes: parseInt(e.target.value) || 5 })}
            className="w-24 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-slate-500">minutos</span>
        </div>
      </FieldGroup>

      <FieldGroup
        label="Aviso anticipado"
        description="Minutos antes del cierre en que aparece el modal de aviso (mín. 1)"
      >
        <div className="flex items-center gap-3">
          <input
            type="number"
            min={1}
            max={form.session_timeout_minutes - 1}
            value={form.session_warning_minutes}
            onChange={(e) => setForm({ ...form, session_warning_minutes: parseInt(e.target.value) || 1 })}
            className="w-24 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-slate-500">minutos</span>
        </div>
      </FieldGroup>

      <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-500">
        Con la configuración actual, el aviso aparecerá a los{" "}
        <span className="font-semibold text-slate-700">
          {form.session_timeout_minutes - form.session_warning_minutes} minutos
        </span>{" "}
        de inactividad y la sesión cerrará a los{" "}
        <span className="font-semibold text-slate-700">{form.session_timeout_minutes} minutos</span>.
      </div>

      {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg mt-4">{error}</p>}
      <div className="flex justify-end pt-4">
        <SaveButton loading={saving} saved={saved} />
      </div>
    </form>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("general");

  const userRole = Cookies.get("user_role");
  // "manager" es el rol administrador del tenant; "admin" es el super-admin de plataforma
  const isAdmin = userRole === "admin" || userRole === "manager";
  const TABS = isAdmin ? [...BASE_TABS, SECURITY_TAB] : BASE_TABS;

  const { data: settings = {}, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: getTenantSettings,
  });

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </AdminLayout>
    );
  }

  const renderTab = () => {
    const s = settings as Record<string, unknown>;
    switch (activeTab) {
      case "general": return <GeneralTab settings={s} />;
      case "whatsapp": return <WhatsAppTab settings={s} />;
      case "schedule": return <ScheduleTab settings={s} />;
      case "notifications": return <AdvancedTab settings={s} />;
      case "security": return isAdmin ? <SecurityTab settings={s} /> : null;
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Configuración</h1>
          <p className="text-sm text-slate-500 mt-0.5">Ajusta los parámetros de tu cuenta y del agente</p>
        </div>

        <div className="flex gap-6">
          {/* Sidebar de tabs */}
          <div className="w-52 flex-shrink-0">
            <nav className="space-y-1">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === id
                      ? "bg-blue-600 text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4" />
                    {label}
                  </div>
                  <ChevronRight className={`w-3.5 h-3.5 opacity-50 ${activeTab === id ? "opacity-70" : ""}`} />
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            {renderTab()}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
