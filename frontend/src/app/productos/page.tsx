"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getProductos, createProducto, updateProducto, deleteProducto } from "@/lib/api";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { formatCOP } from "@/lib/utils";
import {
  Plus, Search, Edit2, Trash2, Loader2, X,
  CheckCircle, XCircle, Cpu,
} from "lucide-react";

interface Producto {
  id: string;
  sku: string;
  name: string;
  brand: string | null;
  category: string;
  subcategory: string | null;
  unit: string | null;
  unit_content: string | null;
  price: number;
  price_promo: number | null;
  is_active: boolean;
  is_featured: boolean;
  is_indexed: boolean;
  external_id: string | null;
}

const DIAS = ["", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

function ProductoModal({
  producto,
  onClose,
}: {
  producto?: Producto | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    sku: producto?.sku || "",
    name: producto?.name || "",
    brand: producto?.brand || "",
    category: producto?.category || "",
    subcategory: producto?.subcategory || "",
    unit: producto?.unit || "",
    unit_content: producto?.unit_content || "",
    price: producto?.price?.toString() || "",
    price_promo: producto?.price_promo?.toString() || "",
    is_active: producto?.is_active ?? true,
    is_featured: producto?.is_featured ?? false,
    external_id: producto?.external_id || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const set = (k: string, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  async function handleSave() {
    if (!form.sku || !form.name || !form.category || !form.price) {
      setError("SKU, nombre, categoría y precio son obligatorios");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        sku: form.sku,
        name: form.name,
        brand: form.brand || null,
        category: form.category,
        subcategory: form.subcategory || null,
        unit: form.unit || null,
        unit_content: form.unit_content || null,
        price: parseFloat(form.price),
        price_promo: form.price_promo ? parseFloat(form.price_promo) : null,
        is_active: form.is_active,
        is_featured: form.is_featured,
        external_id: form.external_id || null,
      };
      if (producto) await updateProducto(producto.id, payload);
      else await createProducto(payload);
      qc.invalidateQueries({ queryKey: ["productos"] });
      onClose();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail || "Error guardando producto");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-semibold text-slate-900">
            {producto ? "Editar Producto" : "Nuevo Producto"}
          </h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto">
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "SKU *", key: "sku", placeholder: "COD-001" },
              { label: "ID externo (ERP)", key: "external_id", placeholder: "ERP-12345" },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
                <input
                  type="text"
                  value={form[key as keyof typeof form] as string}
                  onChange={(e) => set(key, e.target.value)}
                  placeholder={placeholder}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Nombre *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="Arroz Diana x 500g"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Marca", key: "brand", placeholder: "Diana" },
              { label: "Categoría *", key: "category", placeholder: "Granos" },
              { label: "Subcategoría", key: "subcategory", placeholder: "Arroz" },
              { label: "Unidad", key: "unit", placeholder: "Caja, Unidad..." },
              { label: "Contenido", key: "unit_content", placeholder: "12 unidades, 500g..." },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
                <input
                  type="text"
                  value={form[key as keyof typeof form] as string}
                  onChange={(e) => set(key, e.target.value)}
                  placeholder={placeholder}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Precio lista (COP) *</label>
              <input
                type="number"
                value={form.price}
                onChange={(e) => set("price", e.target.value)}
                placeholder="12500"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Precio promo (COP)</label>
              <input
                type="number"
                value={form.price_promo}
                onChange={(e) => set("price_promo", e.target.value)}
                placeholder="Opcional"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex gap-5">
            {[
              { key: "is_active", label: "Producto activo" },
              { key: "is_featured", label: "Producto destacado" },
            ].map(({ key, label }) => (
              <label key={key} className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form[key as keyof typeof form] as boolean}
                  onChange={(e) => set(key, e.target.checked)}
                  className="rounded"
                />
                {label}
              </label>
            ))}
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
            disabled={saving || !form.sku || !form.name || !form.category || !form.price}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {producto ? "Guardar cambios" : "Crear producto"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ProductosPage() {
  const [search, setSearch] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Producto | null>(null);
  const qc = useQueryClient();

  const { data: productos = [], isLoading } = useQuery({
    queryKey: ["productos"],
    queryFn: () => getProductos(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProducto(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["productos"] }),
  });

  const categories = [...new Set((productos as Producto[]).map((p) => p.category))].sort();

  const filtered = (productos as Producto[]).filter((p) => {
    const matchSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.sku.toLowerCase().includes(search.toLowerCase()) ||
      (p.brand || "").toLowerCase().includes(search.toLowerCase());
    const matchCategory = !filterCategory || p.category === filterCategory;
    return matchSearch && matchCategory;
  });

  const indexed = (productos as Producto[]).filter((p) => p.is_indexed).length;

  return (
    <AdminLayout>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Productos</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              {(productos as Producto[]).length} productos ·{" "}
              <span className="text-blue-600 font-medium">{indexed} indexados</span> para búsqueda semántica
            </p>
          </div>
          <button
            onClick={() => { setEditing(null); setShowModal(true); }}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" /> Nuevo producto
          </button>
        </div>

        {/* Filtros */}
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre, SKU o marca..."
              className="w-full pl-9 pr-4 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-3 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">Todas las categorías</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* Tabla */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                {["SKU", "Nombre", "Marca", "Categoría", "Precio", "IA", "Estado", ""].map((h) => (
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
              ) : filtered.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-12 text-slate-400">Sin productos</td></tr>
              ) : filtered.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{p.sku}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{p.name}</div>
                    {p.unit && (
                      <div className="text-xs text-slate-400">
                        {p.unit}{p.unit_content ? ` · ${p.unit_content}` : ""}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{p.brand || "—"}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-slate-600">{p.category}</span>
                    {p.subcategory && (
                      <div className="text-xs text-slate-400">{p.subcategory}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {formatCOP(p.price)}
                    {p.price_promo && (
                      <div className="text-xs text-emerald-600">{formatCOP(p.price_promo)} promo</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span title={p.is_indexed ? "Indexado — búsqueda semántica activa" : "Pendiente de indexar"}>
                      {p.is_indexed
                        ? <Cpu className="w-4 h-4 text-blue-500" />
                        : <Cpu className="w-4 h-4 text-slate-300" />}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      p.is_active ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"
                    }`}>
                      {p.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => { setEditing(p); setShowModal(true); }}
                        className="p-1.5 hover:bg-slate-100 rounded-lg"
                      >
                        <Edit2 className="w-3.5 h-3.5 text-slate-500" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm("¿Desactivar este producto?"))
                            deleteMutation.mutate(p.id);
                        }}
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
        <ProductoModal
          producto={editing}
          onClose={() => { setShowModal(false); setEditing(null); }}
        />
      )}
    </AdminLayout>
  );
}
