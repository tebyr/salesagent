"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getClients, createClient, updateClient, deleteClient, getVendors } from "@/lib/api";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { formatCOP } from "@/lib/utils";
import {
  Plus, Search, Edit2, Trash2, Loader2, X,
  CheckCircle, XCircle, ChevronDown, Filter,
} from "lucide-react";

interface Client {
  id: string; name: string; phone: string; address: string | null;
  zone: string | null; segment: string | null; salesperson_id: string | null;
  salesperson_name: string | null; is_active: boolean; whatsapp_opt_in: boolean;
  credit_limit: number | null; overdue_balance: number | null;
  last_purchase_date: string | null; purchase_frequency_days: number | null;
  days_since_last_purchase: number | null;
}

interface Vendor { id: string; name: string; }

function ClientModal({
  client, onClose, salespersons,
}: { client?: Client | null; onClose: () => void; salespersons: Vendor[] }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: client?.name || "",
    phone: client?.phone || "",
    address: client?.address || "",
    zone: client?.zone || "",
    segment: client?.segment || "regular",
    salesperson_id: client?.salesperson_id || "",
    credit_limit: client?.credit_limit?.toString() || "",
    whatsapp_opt_in: client?.whatsapp_opt_in ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        phone: form.phone,
        address: form.address || null,
        zone: form.zone || null,
        segment: form.segment,
        salesperson_id: form.salesperson_id || null,
        credit_limit: form.credit_limit ? parseFloat(form.credit_limit) : null,
        whatsapp_opt_in: form.whatsapp_opt_in,
      };
      if (client) await updateClient(client.id, payload);
      else await createClient(payload);
      qc.invalidateQueries({ queryKey: ["clients"] });
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
          <h2 className="font-semibold text-slate-900">
            {client ? "Editar Cliente" : "Nuevo Cliente"}
          </h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>
        <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
          {[
            { label: "Nombre del negocio *", key: "name", type: "text", placeholder: "Tienda El Progreso" },
            { label: "Teléfono (WhatsApp) *", key: "phone", type: "tel", placeholder: "3001234567" },
            { label: "Dirección", key: "address", type: "text", placeholder: "Cra 15 #23-45" },
            { label: "Zona", key: "zone", type: "text", placeholder: "Norte, Sur, Centro..." },
          ].map(({ label, key, type, placeholder }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
              <input
                type={type}
                value={form[key as keyof typeof form] as string}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                placeholder={placeholder}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ))}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Segmento</label>
              <select
                value={form.segment}
                onChange={(e) => setForm({ ...form, segment: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="vip">VIP</option>
                <option value="regular">Regular</option>
                <option value="occasional">Ocasional</option>
                <option value="inactive">Inactivo</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Límite de crédito</label>
              <input
                type="number"
                value={form.credit_limit}
                onChange={(e) => setForm({ ...form, credit_limit: e.target.value })}
                placeholder="0"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Vendedor asignado</label>
            <select
              value={form.salesperson_id}
              onChange={(e) => setForm({ ...form, salesperson_id: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Sin asignar</option>
              {salespersons.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={form.whatsapp_opt_in}
              onChange={(e) => setForm({ ...form, whatsapp_opt_in: e.target.checked })}
              className="rounded"
            />
            Recibir mensajes por WhatsApp
          </label>
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
            disabled={saving || !form.name || !form.phone}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {client ? "Guardar cambios" : "Crear cliente"}
          </button>
        </div>
      </div>
    </div>
  );
}

const SEGMENT_LABELS: Record<string, { label: string; color: string }> = {
  vip: { label: "VIP", color: "bg-purple-50 text-purple-700" },
  regular: { label: "Regular", color: "bg-blue-50 text-blue-700" },
  occasional: { label: "Ocasional", color: "bg-amber-50 text-amber-700" },
  inactive: { label: "Inactivo", color: "bg-slate-100 text-slate-500" },
};

export default function ClientsPage() {
  const [search, setSearch] = useState("");
  const [filterVendor, setFilterVendor] = useState("");
  const [filterSegment, setFilterSegment] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Client | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const qc = useQueryClient();

  const { data: clients = [], isLoading } = useQuery({
    queryKey: ["clients", filterVendor, filterSegment],
    queryFn: () => getClients({
      salesperson_id: filterVendor || undefined,
      segment: filterSegment || undefined,
    }),
  });

  const { data: salespersons = [] } = useQuery({
    queryKey: ["salespersons"],
    queryFn: () => getVendors(),
  });

  const filtered = clients.filter((c: Client) =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.phone.includes(search) ||
    (c.address || "").toLowerCase().includes(search.toLowerCase()) ||
    (c.zone || "").toLowerCase().includes(search.toLowerCase())
  );

  async function handleDeactivate(id: string) {
    if (!confirm("¿Desactivar este cliente?")) return;
    await deleteClient(id);
    qc.invalidateQueries({ queryKey: ["clients"] });
  }

  const activeFilters = [filterVendor, filterSegment].filter(Boolean).length;

  return (
    <AdminLayout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Clientes</h1>
            <p className="text-sm text-slate-500 mt-0.5">{clients.length} clientes registrados</p>
          </div>
          <button
            onClick={() => { setEditing(null); setShowModal(true); }}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" /> Nuevo cliente
          </button>
        </div>

        {/* Busqueda y filtros */}
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre, teléfono, zona o dirección..."
              className="w-full pl-9 pr-4 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-2 text-sm border rounded-lg transition-colors ${
              activeFilters > 0
                ? "border-blue-500 bg-blue-50 text-blue-700"
                : "border-slate-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            <Filter className="w-4 h-4" />
            Filtros
            {activeFilters > 0 && (
              <span className="bg-blue-600 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                {activeFilters}
              </span>
            )}
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showFilters ? "rotate-180" : ""}`} />
          </button>
        </div>

        {showFilters && (
          <div className="flex gap-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 mb-1">Vendedor</label>
              <select
                value={filterVendor}
                onChange={(e) => setFilterVendor(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">Todos los vendedores</option>
                {(salespersons as Vendor[]).map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 mb-1">Segmento</label>
              <select
                value={filterSegment}
                onChange={(e) => setFilterSegment(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">Todos los segmentos</option>
                <option value="vip">VIP</option>
                <option value="regular">Regular</option>
                <option value="occasional">Ocasional</option>
                <option value="inactive">Inactivo</option>
              </select>
            </div>
            {activeFilters > 0 && (
              <div className="flex items-end">
                <button
                  onClick={() => { setFilterVendor(""); setFilterSegment(""); }}
                  className="px-3 py-2 text-xs text-slate-500 hover:text-slate-700 hover:bg-slate-200 rounded-lg"
                >
                  Limpiar filtros
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tabla */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                {["Cliente", "Teléfono", "Zona", "Vendedor", "Segmento", "Última compra", "WhatsApp", "Estado", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr><td colSpan={9} className="text-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-400 mx-auto" />
                </td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={9} className="text-center py-12 text-slate-400">Sin clientes</td></tr>
              ) : filtered.map((c: Client) => {
                const seg = SEGMENT_LABELS[c.segment || "regular"] || SEGMENT_LABELS.regular;
                const isOverdue = c.days_since_last_purchase !== null && c.days_since_last_purchase > 30;
                return (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900">{c.name}</p>
                      {c.address && <p className="text-xs text-slate-400 mt-0.5">{c.address}</p>}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{c.phone}</td>
                    <td className="px-4 py-3 text-slate-500">{c.zone || "—"}</td>
                    <td className="px-4 py-3 text-slate-600 text-xs">{c.salesperson_name || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${seg.color}`}>
                        {seg.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {c.last_purchase_date ? (
                        <div>
                          <p className={`text-xs font-medium ${isOverdue ? "text-red-600" : "text-slate-600"}`}>
                            {c.days_since_last_purchase}d atrás
                          </p>
                          <p className="text-xs text-slate-400">
                            {new Date(c.last_purchase_date).toLocaleDateString("es-CO")}
                          </p>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">Sin compras</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {c.whatsapp_opt_in
                        ? <CheckCircle className="w-4 h-4 text-emerald-500" />
                        : <XCircle className="w-4 h-4 text-slate-300" />}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${
                        c.is_active ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"
                      }`}>
                        {c.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => { setEditing(c); setShowModal(true); }}
                          className="p-1.5 hover:bg-slate-100 rounded-lg"
                        >
                          <Edit2 className="w-3.5 h-3.5 text-slate-500" />
                        </button>
                        <button
                          onClick={() => handleDeactivate(c.id)}
                          className="p-1.5 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-red-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <ClientModal
          client={editing}
          salespersons={salespersons as Vendor[]}
          onClose={() => { setShowModal(false); setEditing(null); }}
        />
      )}
    </AdminLayout>
  );
}
