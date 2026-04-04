"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getVendors, createVendor, updateVendor, deleteVendor } from "@/lib/api";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { formatCOP, formatPct, statusBadgeClass } from "@/lib/utils";
import { Plus, Search, Edit2, Trash2, Loader2, X, CheckCircle, XCircle } from "lucide-react";

interface Vendor {
  id: string; name: string; phone: string; email: string | null;
  role: string; zone: string | null; is_active: boolean; whatsapp_opt_in: boolean;
}

function VendorModal({
  salesperson, onClose, tenantVendors,
}: { salesperson?: Vendor | null; onClose: () => void; tenantVendors: Vendor[] }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: salesperson?.name || "",
    phone: salesperson?.phone || "",
    email: salesperson?.email || "",
    zone: salesperson?.zone || "",
    role: salesperson?.role || "salesperson",
    whatsapp_opt_in: salesperson?.whatsapp_opt_in ?? true,
    password: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        name: form.name, phone: form.phone, zone: form.zone || null,
        email: form.email || null, role: form.role,
        whatsapp_opt_in: form.whatsapp_opt_in,
      };
      if (!salesperson && form.password) payload.password = form.password;
      if (salesperson) await updateVendor(salesperson.id, payload);
      else await createVendor(payload);
      qc.invalidateQueries({ queryKey: ["salespersons"] });
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
            {salesperson ? "Editar Vendedor" : "Nuevo Vendedor"}
          </h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>
        <div className="p-5 space-y-4">
          {[
            { label: "Nombre completo *", key: "name", type: "text", placeholder: "Juan García" },
            { label: "Teléfono (WhatsApp) *", key: "phone", type: "tel", placeholder: "3001234567" },
            { label: "Email", key: "email", type: "email", placeholder: "juan@empresa.com" },
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
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Rol</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="salesperson">Vendedor</option>
              <option value="supervisor">Supervisor</option>
              <option value="manager">Gerente</option>
            </select>
          </div>
          {!salesperson && (
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Contraseña (panel admin)
              </label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Solo para gerentes/supervisores"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
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
            {salesperson ? "Guardar cambios" : "Crear vendedor"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function VendorsPage() {
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Vendor | null>(null);
  const qc = useQueryClient();

  const { data: salespersons = [], isLoading } = useQuery({
    queryKey: ["salespersons"],
    queryFn: () => getVendors(),
  });

  const filtered = salespersons.filter((v: Vendor) =>
    v.name.toLowerCase().includes(search.toLowerCase()) ||
    v.phone.includes(search) ||
    (v.zone || "").toLowerCase().includes(search.toLowerCase())
  );

  async function handleDeactivate(id: string) {
    if (!confirm("¿Desactivar este vendedor?")) return;
    await deleteVendor(id);
    qc.invalidateQueries({ queryKey: ["salespersons"] });
  }

  return (
    <AdminLayout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Vendedores</h1>
            <p className="text-sm text-slate-500 mt-0.5">{salespersons.length} vendedores registrados</p>
          </div>
          <button
            onClick={() => { setEditing(null); setShowModal(true); }}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" /> Nuevo vendedor
          </button>
        </div>

        {/* Busqueda */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre, telefono o zona..."
            className="w-full pl-9 pr-4 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Tabla */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                {["Nombre", "Teléfono", "Zona", "Rol", "WhatsApp", "Estado", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr><td colSpan={7} className="text-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-400 mx-auto" />
                </td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-12 text-slate-400">Sin vendedores</td></tr>
              ) : filtered.map((v: Vendor) => (
                <tr key={v.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{v.name}</td>
                  <td className="px-4 py-3 text-slate-600">{v.phone}</td>
                  <td className="px-4 py-3 text-slate-500">{v.zone || "—"}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 text-xs bg-blue-50 text-blue-700 rounded-full capitalize">
                      {v.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {v.whatsapp_opt_in
                      ? <CheckCircle className="w-4 h-4 text-emerald-500" />
                      : <XCircle className="w-4 h-4 text-slate-300" />}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      v.is_active ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"
                    }`}>
                      {v.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => { setEditing(v); setShowModal(true); }}
                        className="p-1.5 hover:bg-slate-100 rounded-lg"
                      >
                        <Edit2 className="w-3.5 h-3.5 text-slate-500" />
                      </button>
                      <button
                        onClick={() => handleDeactivate(v.id)}
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

      {showModal && (
        <VendorModal
          salesperson={editing}
          tenantVendors={salespersons}
          onClose={() => { setShowModal(false); setEditing(null); }}
        />
      )}
    </AdminLayout>
  );
}
