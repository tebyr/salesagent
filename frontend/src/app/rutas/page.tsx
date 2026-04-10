"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getZonas, createZona, updateZona, deleteZona,
  getRutas, createRuta, updateRuta, deleteRuta,
  getVendors,
} from "@/lib/api";
import { AdminLayout } from "@/components/layout/AdminLayout";
import {
  Plus, Edit2, Trash2, Loader2, X, MapPin, Route,
  Users, ChevronDown, ChevronUp,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Zona {
  id: string; name: string; description: string | null;
  is_active: boolean; routes_count: number; clients_count: number;
}

interface Ruta {
  id: string; name: string | null; route_type: string; status: string;
  is_active: boolean; zone_id: string | null; zone_name: string | null;
  salesperson_id: string; salesperson_name: string | null;
  operating_days: number[] | null; delivery_days: number[] | null;
  total_clients: number; visited_count: number; sales_count: number;
}

interface Vendor { id: string; name: string; role: string; is_active: boolean; }

const DIAS_LABEL: Record<number, string> = {
  1: "L", 2: "M", 3: "X", 4: "J", 5: "V", 6: "S",
};
const DIAS_FULL: Record<number, string> = {
  1: "Lunes", 2: "Martes", 3: "Miércoles",
  4: "Jueves", 5: "Viernes", 6: "Sábado",
};

function DayBadges({ days }: { days: number[] | null }) {
  if (!days?.length) return <span className="text-slate-400 text-xs">—</span>;
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5, 6].map((d) => (
        <span
          key={d}
          title={DIAS_FULL[d]}
          className={`w-5 h-5 flex items-center justify-center text-[10px] font-bold rounded ${
            days.includes(d)
              ? "bg-blue-100 text-blue-700"
              : "bg-slate-100 text-slate-300"
          }`}
        >
          {DIAS_LABEL[d]}
        </span>
      ))}
    </div>
  );
}

// ── Zona Modal ────────────────────────────────────────────────────────────────

function ZonaModal({ zona, onClose }: { zona?: Zona | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ name: zona?.name || "", description: zona?.description || "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    if (!form.name.trim()) { setError("El nombre es obligatorio"); return; }
    setSaving(true); setError("");
    try {
      const payload = { name: form.name.trim(), description: form.description || null };
      if (zona) await updateZona(zona.id, payload);
      else await createZona(payload);
      qc.invalidateQueries({ queryKey: ["zonas"] });
      onClose();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail || "Error guardando");
    } finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-semibold text-slate-900">{zona ? "Editar Zona" : "Nueva Zona"}</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Nombre *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Zona Norte Magangué"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Descripción</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Barrios y sectores que cubre esta zona..."
              rows={3}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
          {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 p-5 border-t">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancelar</button>
          <button
            onClick={handleSave}
            disabled={saving || !form.name.trim()}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {zona ? "Guardar" : "Crear zona"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Ruta Modal ────────────────────────────────────────────────────────────────

function RutaModal({
  ruta, zonas, vendors, onClose,
}: { ruta?: Ruta | null; zonas: Zona[]; vendors: Vendor[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: ruta?.name || "",
    zone_id: ruta?.zone_id || "",
    salesperson_id: ruta?.salesperson_id || "",
    route_type: ruta?.route_type || "presential",
    operating_days: ruta?.operating_days || [] as number[],
    delivery_days: ruta?.delivery_days || [] as number[],
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function toggleDay(list: "operating_days" | "delivery_days", day: number) {
    const current = form[list] as number[];
    const updated = current.includes(day) ? current.filter((d) => d !== day) : [...current, day].sort();
    setForm((f) => ({ ...f, [list]: updated }));
  }

  async function handleSave() {
    if (!form.salesperson_id) { setError("El vendedor es obligatorio"); return; }
    if (!form.operating_days.length) { setError("Selecciona al menos un día de operación"); return; }
    setSaving(true); setError("");
    try {
      const payload: Record<string, unknown> = {
        salesperson_id: form.salesperson_id,
        zone_id: form.zone_id || null,
        name: form.name || null,
        route_type: form.route_type,
        operating_days: form.operating_days,
        delivery_days: form.delivery_days.length ? form.delivery_days : null,
        notes: form.notes || null,
      };
      if (ruta) await updateRuta(ruta.id, payload);
      else await createRuta(payload);
      qc.invalidateQueries({ queryKey: ["rutas"] });
      onClose();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail || "Error guardando");
    } finally { setSaving(false); }
  }

  const activeVendors = vendors.filter(
    (v) => v.is_active && (v.role === "salesperson" || v.role === "agent")
  );

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-semibold text-slate-900">{ruta ? "Editar Ruta" : "Nueva Ruta"}</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Nombre (opcional)</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Ruta Zona Norte - Lunes"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Zona</label>
              <select
                value={form.zone_id}
                onChange={(e) => setForm({ ...form, zone_id: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">Sin zona</option>
                {zonas.filter((z) => z.is_active).map((z) => (
                  <option key={z.id} value={z.id}>{z.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Tipo</label>
              <select
                value={form.route_type}
                onChange={(e) => setForm({ ...form, route_type: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="presential">Presencial</option>
                <option value="agent_wa">Agente IA (WhatsApp)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Vendedor / Agente *</label>
            <select
              value={form.salesperson_id}
              onChange={(e) => setForm({ ...form, salesperson_id: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="">Seleccionar...</option>
              {activeVendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} {v.role === "agent" ? "(Agente IA)" : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-2">Días de operación *</label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5, 6].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => toggleDay("operating_days", d)}
                  className={`w-10 h-10 text-xs font-bold rounded-lg transition-colors ${
                    form.operating_days.includes(d)
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                  }`}
                >
                  {DIAS_LABEL[d]}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-2">Días de entrega</label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5, 6].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => toggleDay("delivery_days", d)}
                  className={`w-10 h-10 text-xs font-bold rounded-lg transition-colors ${
                    form.delivery_days.includes(d)
                      ? "bg-emerald-600 text-white"
                      : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                  }`}
                >
                  {DIAS_LABEL[d]}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
        </div>

        <div className="flex justify-end gap-2 p-5 border-t">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancelar</button>
          <button
            onClick={handleSave}
            disabled={saving || !form.salesperson_id || !form.operating_days.length}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {ruta ? "Guardar" : "Crear ruta"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RutasPage() {
  const [zonasExpanded, setZonasExpanded] = useState(true);
  const [filterZona, setFilterZona] = useState("");
  const [filterType, setFilterType] = useState("");
  const [showZonaModal, setShowZonaModal] = useState(false);
  const [showRutaModal, setShowRutaModal] = useState(false);
  const [editingZona, setEditingZona] = useState<Zona | null>(null);
  const [editingRuta, setEditingRuta] = useState<Ruta | null>(null);
  const qc = useQueryClient();

  const { data: zonas = [], isLoading: loadingZonas } = useQuery<Zona[]>({
    queryKey: ["zonas"],
    queryFn: () => getZonas({ is_active: true }),
  });

  const { data: rutas = [], isLoading: loadingRutas } = useQuery<Ruta[]>({
    queryKey: ["rutas"],
    queryFn: () => getRutas({ is_active: true }),
  });

  const { data: vendors = [] } = useQuery<Vendor[]>({
    queryKey: ["salespersons"],
    queryFn: () => getVendors(),
  });

  const deleteZonaMutation = useMutation({
    mutationFn: (id: string) => deleteZona(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zonas"] }),
  });

  const deleteRutaMutation = useMutation({
    mutationFn: (id: string) => deleteRuta(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rutas"] }),
  });

  const filteredRutas = (rutas as Ruta[]).filter((r) => {
    const matchZona = !filterZona || r.zone_id === filterZona;
    const matchType = !filterType || r.route_type === filterType;
    return matchZona && matchType;
  });

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ── Zonas ── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div
            className="flex items-center justify-between p-4 cursor-pointer select-none"
            onClick={() => setZonasExpanded((v) => !v)}
          >
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-slate-500" />
              <span className="font-semibold text-slate-900">Zonas</span>
              <span className="text-xs text-slate-400 ml-1">{(zonas as Zona[]).length} zonas activas</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={(e) => { e.stopPropagation(); setEditingZona(null); setShowZonaModal(true); }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Plus className="w-3 h-3" /> Nueva zona
              </button>
              {zonasExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
            </div>
          </div>

          {zonasExpanded && (
            <div className="border-t border-slate-100">
              {loadingZonas ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
                </div>
              ) : (zonas as Zona[]).length === 0 ? (
                <p className="text-center text-slate-400 text-sm py-8">Sin zonas configuradas</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4">
                  {(zonas as Zona[]).map((z) => (
                    <div key={z.id} className="flex items-start justify-between p-3 rounded-lg border border-slate-100 hover:border-slate-200 hover:bg-slate-50">
                      <div>
                        <p className="font-medium text-sm text-slate-900">{z.name}</p>
                        {z.description && <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{z.description}</p>}
                        <div className="flex gap-3 mt-1.5">
                          <span className="text-xs text-slate-500 flex items-center gap-1">
                            <Route className="w-3 h-3" /> {z.routes_count} rutas
                          </span>
                          <span className="text-xs text-slate-500 flex items-center gap-1">
                            <Users className="w-3 h-3" /> {z.clients_count} clientes
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-1 ml-2 shrink-0">
                        <button onClick={() => { setEditingZona(z); setShowZonaModal(true); }} className="p-1.5 hover:bg-slate-100 rounded-lg">
                          <Edit2 className="w-3.5 h-3.5 text-slate-500" />
                        </button>
                        <button
                          onClick={() => { if (confirm("¿Desactivar esta zona?")) deleteZonaMutation.mutate(z.id); }}
                          className="p-1.5 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-red-400" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Rutas ── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Rutas</h1>
              <p className="text-sm text-slate-500 mt-0.5">{(rutas as Ruta[]).length} rutas activas</p>
            </div>
            <button
              onClick={() => { setEditingRuta(null); setShowRutaModal(true); }}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" /> Nueva ruta
            </button>
          </div>

          {/* Filtros */}
          <div className="flex gap-3">
            <select
              value={filterZona}
              onChange={(e) => setFilterZona(e.target.value)}
              className="px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="">Todas las zonas</option>
              {(zonas as Zona[]).map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}
            </select>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="">Todos los tipos</option>
              <option value="presential">Presencial</option>
              <option value="agent_wa">Agente IA</option>
            </select>
          </div>

          {/* Tabla */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  {["Ruta", "Zona", "Vendedor", "Tipo", "Días op.", "Días ent.", "Clientes", ""].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loadingRutas ? (
                  <tr><td colSpan={8} className="text-center py-12">
                    <Loader2 className="w-6 h-6 animate-spin text-blue-400 mx-auto" />
                  </td></tr>
                ) : filteredRutas.length === 0 ? (
                  <tr><td colSpan={8} className="text-center py-12 text-slate-400">Sin rutas</td></tr>
                ) : filteredRutas.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900">{r.name || "Sin nombre"}</p>
                      <p className="text-xs text-slate-400">ID: {r.id.slice(0, 8)}…</p>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{r.zone_name || "—"}</td>
                    <td className="px-4 py-3 text-slate-700">{r.salesperson_name || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                        r.route_type === "agent_wa"
                          ? "bg-violet-50 text-violet-700"
                          : "bg-blue-50 text-blue-700"
                      }`}>
                        {r.route_type === "agent_wa" ? "Agente IA" : "Presencial"}
                      </span>
                    </td>
                    <td className="px-4 py-3"><DayBadges days={r.operating_days} /></td>
                    <td className="px-4 py-3"><DayBadges days={r.delivery_days} /></td>
                    <td className="px-4 py-3 text-slate-600">{r.total_clients}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => { setEditingRuta(r); setShowRutaModal(true); }} className="p-1.5 hover:bg-slate-100 rounded-lg">
                          <Edit2 className="w-3.5 h-3.5 text-slate-500" />
                        </button>
                        <button
                          onClick={() => { if (confirm("¿Desactivar esta ruta?")) deleteRutaMutation.mutate(r.id); }}
                          className="p-1.5 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-red-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showZonaModal && (
        <ZonaModal
          zona={editingZona}
          onClose={() => { setShowZonaModal(false); setEditingZona(null); }}
        />
      )}
      {showRutaModal && (
        <RutaModal
          ruta={editingRuta}
          zonas={zonas as Zona[]}
          vendors={vendors as Vendor[]}
          onClose={() => { setShowRutaModal(false); setEditingRuta(null); }}
        />
      )}
    </AdminLayout>
  );
}
