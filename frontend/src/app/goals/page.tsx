"use client";
import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getGoals, createGoal, updateGoal, deleteGoal, bulkCreateGoals, getVendors } from "@/lib/api";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { formatCOP, formatPct } from "@/lib/utils";
import {
  Plus, Edit2, Trash2, Loader2, X, Target, TrendingUp,
  Users, ChevronDown, ChevronUp, Copy,
} from "lucide-react";

interface Goal {
  id: string; salesperson_id: string; salesperson_name: string | null;
  period_type: string; period_start: string; period_end: string;
  target_amount: number; target_visits: number | null;
  target_new_clients: number | null; is_active: boolean;
  progress?: {
    actual_amount: number; actual_visits: number; actual_new_clients: number;
    pct_amount: number; pct_visits: number; projected_amount: number;
  };
}

interface Vendor { id: string; name: string; }

const PERIOD_LABELS: Record<string, string> = {
  daily: "Diaria",
  weekly: "Semanal",
  monthly: "Mensual",
  quarterly: "Trimestral",
};

function GoalModal({
  goal, onClose, salespersons,
}: { goal?: Goal | null; onClose: () => void; salespersons: Vendor[] }) {
  const qc = useQueryClient();
  const today = new Date();
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split("T")[0];
  const lastOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split("T")[0];

  const [form, setForm] = useState({
    salesperson_id: goal?.salesperson_id || "",
    period_type: goal?.period_type || "monthly",
    period_start: goal?.period_start?.split("T")[0] || firstOfMonth,
    period_end: goal?.period_end?.split("T")[0] || lastOfMonth,
    target_amount: goal?.target_amount?.toString() || "",
    target_visits: goal?.target_visits?.toString() || "",
    target_new_clients: goal?.target_new_clients?.toString() || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const payload = {
        salesperson_id: form.salesperson_id,
        period_type: form.period_type,
        period_start: form.period_start,
        period_end: form.period_end,
        target_amount: parseFloat(form.target_amount),
        target_visits: form.target_visits ? parseInt(form.target_visits) : null,
        target_new_clients: form.target_new_clients ? parseInt(form.target_new_clients) : null,
      };
      if (goal) await updateGoal(goal.id, payload);
      else await createGoal(payload);
      qc.invalidateQueries({ queryKey: ["goals"] });
      onClose();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail || "Error guardando");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-semibold text-slate-900">
            {goal ? "Editar Meta" : "Nueva Meta"}
          </h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Vendedor *</label>
            <select
              value={form.salesperson_id}
              onChange={(e) => setForm({ ...form, salesperson_id: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Seleccionar vendedor</option>
              {salespersons.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Tipo de período</label>
            <select
              value={form.period_type}
              onChange={(e) => setForm({ ...form, period_type: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(PERIOD_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Inicio</label>
              <input
                type="date"
                value={form.period_start}
                onChange={(e) => setForm({ ...form, period_start: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Fin</label>
              <input
                type="date"
                value={form.period_end}
                onChange={(e) => setForm({ ...form, period_end: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Meta de ventas (COP) *</label>
            <input
              type="number"
              value={form.target_amount}
              onChange={(e) => setForm({ ...form, target_amount: e.target.value })}
              placeholder="5000000"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Meta de visitas</label>
              <input
                type="number"
                value={form.target_visits}
                onChange={(e) => setForm({ ...form, target_visits: e.target.value })}
                placeholder="Opcional"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Meta clientes nuevos</label>
              <input
                type="number"
                value={form.target_new_clients}
                onChange={(e) => setForm({ ...form, target_new_clients: e.target.value })}
                placeholder="Opcional"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          {error && (
            <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
          )}
        </div>
        <div className="flex justify-end gap-2 p-5 border-t">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !form.salesperson_id || !form.target_amount}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {goal ? "Guardar cambios" : "Crear meta"}
          </button>
        </div>
      </div>
    </div>
  );
}

function BulkGoalModal({
  onClose, salespersons,
}: { onClose: () => void; salespersons: Vendor[] }) {
  const qc = useQueryClient();
  const today = new Date();
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split("T")[0];
  const lastOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split("T")[0];

  const [selectedVendors, setSelectedVendors] = useState<string[]>([]);
  const [form, setForm] = useState({
    period_type: "monthly",
    period_start: firstOfMonth,
    period_end: lastOfMonth,
    target_amount: "",
    target_visits: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function toggleVendor(id: string) {
    setSelectedVendors((prev) =>
      prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]
    );
  }

  function toggleAll() {
    if (selectedVendors.length === salespersons.length) setSelectedVendors([]);
    else setSelectedVendors(salespersons.map((v) => v.id));
  }

  async function handleSave() {
    if (selectedVendors.length === 0) { setError("Selecciona al menos un vendedor"); return; }
    setSaving(true);
    setError("");
    try {
      await bulkCreateGoals({
        salesperson_ids: selectedVendors,
        period_type: form.period_type,
        period_start: form.period_start,
        period_end: form.period_end,
        target_amount: parseFloat(form.target_amount),
        target_visits: form.target_visits ? parseInt(form.target_visits) : null,
      });
      qc.invalidateQueries({ queryKey: ["goals"] });
      onClose();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail || "Error guardando");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-semibold text-slate-900">Asignar meta a varios vendedores</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>
        <div className="p-5 space-y-4">
          {/* Selector de vendedores */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-600">Vendedores *</label>
              <button onClick={toggleAll} className="text-xs text-blue-600 hover:underline">
                {selectedVendors.length === salespersons.length ? "Deseleccionar todos" : "Seleccionar todos"}
              </button>
            </div>
            <div className="border border-slate-200 rounded-lg max-h-40 overflow-y-auto divide-y divide-slate-100">
              {salespersons.map((v) => (
                <label key={v.id} className="flex items-center gap-3 px-3 py-2 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedVendors.includes(v.id)}
                    onChange={() => toggleVendor(v.id)}
                    className="rounded"
                  />
                  <span className="text-sm text-slate-700">{v.name}</span>
                </label>
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-1">{selectedVendors.length} vendedores seleccionados</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Inicio</label>
              <input
                type="date"
                value={form.period_start}
                onChange={(e) => setForm({ ...form, period_start: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Fin</label>
              <input
                type="date"
                value={form.period_end}
                onChange={(e) => setForm({ ...form, period_end: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Meta de ventas (COP) *</label>
            <input
              type="number"
              value={form.target_amount}
              onChange={(e) => setForm({ ...form, target_amount: e.target.value })}
              placeholder="5000000"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Meta de visitas (opcional)</label>
            <input
              type="number"
              value={form.target_visits}
              onChange={(e) => setForm({ ...form, target_visits: e.target.value })}
              placeholder="Ej. 20"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && (
            <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
          )}
        </div>
        <div className="flex justify-end gap-2 p-5 border-t">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !form.target_amount || selectedVendors.length === 0}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Asignar metas ({selectedVendors.length})
          </button>
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="w-full bg-slate-100 rounded-full h-1.5">
      <div
        className={`h-1.5 rounded-full ${color} transition-all`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

export default function GoalsPage() {
  const [showModal, setShowModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [editing, setEditing] = useState<Goal | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const qc = useQueryClient();

  const { data: goals = [], isLoading } = useQuery({
    queryKey: ["goals"],
    queryFn: () => getGoals(),
  });

  const { data: salespersons = [] } = useQuery({
    queryKey: ["salespersons"],
    queryFn: () => getVendors(),
  });

  async function handleDelete(id: string) {
    if (!confirm("¿Eliminar esta meta?")) return;
    await deleteGoal(id);
    qc.invalidateQueries({ queryKey: ["goals"] });
  }

  function toggleRow(id: string) {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // Summary stats
  const activeGoals = (goals as Goal[]).filter((g) => g.is_active);
  const avgPct = activeGoals.length
    ? activeGoals.reduce((sum, g) => sum + (g.progress?.pct_amount || 0), 0) / activeGoals.length
    : 0;
  const totalTarget = activeGoals.reduce((sum, g) => sum + g.target_amount, 0);
  const totalActual = activeGoals.reduce((sum, g) => sum + (g.progress?.actual_amount || 0), 0);

  return (
    <AdminLayout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Metas de Venta</h1>
            <p className="text-sm text-slate-500 mt-0.5">{activeGoals.length} metas activas</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowBulkModal(true)}
              className="flex items-center gap-2 border border-slate-200 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50"
            >
              <Copy className="w-4 h-4" /> Asignación masiva
            </button>
            <button
              onClick={() => { setEditing(null); setShowModal(true); }}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" /> Nueva meta
            </button>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { icon: Target, label: "Total meta del mes", value: formatCOP(totalTarget), color: "bg-blue-50 text-blue-600" },
            { icon: TrendingUp, label: "Total ejecutado", value: formatCOP(totalActual), color: "bg-emerald-50 text-emerald-600" },
            { icon: Users, label: "Cumplimiento promedio", value: formatPct(avgPct), color: avgPct >= 80 ? "bg-emerald-50 text-emerald-600" : avgPct >= 60 ? "bg-amber-50 text-amber-600" : "bg-red-50 text-red-600" },
          ].map(({ icon: Icon, label, value, color }) => (
            <div key={label} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center gap-4">
              <div className={`p-2.5 rounded-lg ${color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="text-xl font-bold text-slate-900 mt-0.5">{value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Tabla */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                {["Vendedor", "Período", "Meta", "Ejecutado", "Cumplimiento", "Proyección", "Estado", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr><td colSpan={8} className="text-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-400 mx-auto" />
                </td></tr>
              ) : (goals as Goal[]).length === 0 ? (
                <tr><td colSpan={8} className="text-center py-12 text-slate-400">Sin metas configuradas</td></tr>
              ) : (goals as Goal[]).map((g) => {
                const pct = g.progress?.pct_amount || 0;
                const isExpanded = expandedRows.has(g.id);
                return (
                  <React.Fragment key={g.id}>
                    <tr className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-medium text-slate-900">{g.salesperson_name || "—"}</td>
                      <td className="px-4 py-3 text-slate-500 text-xs">
                        <span className="px-2 py-0.5 bg-slate-100 rounded-full">{PERIOD_LABELS[g.period_type]}</span>
                        <p className="mt-1 text-slate-400">
                          {new Date(g.period_start).toLocaleDateString("es-CO", { day: "2-digit", month: "short" })}
                          {" – "}
                          {new Date(g.period_end).toLocaleDateString("es-CO", { day: "2-digit", month: "short" })}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-slate-700 font-medium">{formatCOP(g.target_amount)}</td>
                      <td className="px-4 py-3 text-slate-700">{formatCOP(g.progress?.actual_amount || 0)}</td>
                      <td className="px-4 py-3 w-36">
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className={`font-medium ${pct >= 80 ? "text-emerald-600" : pct >= 60 ? "text-amber-600" : "text-red-500"}`}>
                              {formatPct(pct)}
                            </span>
                          </div>
                          <ProgressBar pct={pct} />
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-xs">
                        {g.progress?.projected_amount != null
                          ? formatCOP(g.progress.projected_amount)
                          : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          g.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
                        }`}>
                          {g.is_active ? "Activa" : "Inactiva"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => toggleRow(g.id)}
                            className="p-1.5 hover:bg-slate-100 rounded-lg"
                            title="Ver detalles"
                          >
                            {isExpanded
                              ? <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                              : <ChevronDown className="w-3.5 h-3.5 text-slate-500" />}
                          </button>
                          <button
                            onClick={() => { setEditing(g); setShowModal(true); }}
                            className="p-1.5 hover:bg-slate-100 rounded-lg"
                          >
                            <Edit2 className="w-3.5 h-3.5 text-slate-500" />
                          </button>
                          <button
                            onClick={() => handleDelete(g.id)}
                            className="p-1.5 hover:bg-red-50 rounded-lg"
                          >
                            <Trash2 className="w-3.5 h-3.5 text-red-400" />
                          </button>
                        </div>
                      </td>
                    </tr>
                    {isExpanded && g.progress && (
                      <tr className="bg-slate-50">
                        <td colSpan={8} className="px-4 py-3">
                          <div className="grid grid-cols-3 gap-6 text-sm">
                            <div>
                              <p className="text-xs text-slate-500 mb-1">Visitas</p>
                              <p className="font-medium text-slate-800">
                                {g.progress.actual_visits} / {g.target_visits || "—"}
                              </p>
                              {g.target_visits && (
                                <ProgressBar pct={g.progress.pct_visits} />
                              )}
                            </div>
                            <div>
                              <p className="text-xs text-slate-500 mb-1">Efectividad de visitas</p>
                              <p className="font-medium text-slate-800">
                                {g.progress.actual_visits > 0
                                  ? formatPct((g.progress.actual_amount / g.target_amount) * 100)
                                  : "—"}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-500 mb-1">Brecha proyectada</p>
                              <p className={`font-medium ${
                                g.progress.projected_amount >= g.target_amount
                                  ? "text-emerald-600"
                                  : "text-red-500"
                              }`}>
                                {g.progress.projected_amount >= g.target_amount ? "+" : ""}
                                {formatCOP(g.progress.projected_amount - g.target_amount)}
                              </p>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <GoalModal
          goal={editing}
          salespersons={salespersons as Vendor[]}
          onClose={() => { setShowModal(false); setEditing(null); }}
        />
      )}

      {showBulkModal && (
        <BulkGoalModal
          salespersons={salespersons as Vendor[]}
          onClose={() => setShowBulkModal(false)}
        />
      )}
    </AdminLayout>
  );
}
