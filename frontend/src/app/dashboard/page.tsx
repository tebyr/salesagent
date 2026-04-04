"use client";
import { useQuery } from "@tanstack/react-query";
import { getDashboardKPIs, getVendorsPerformance } from "@/lib/api";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { formatCOP, formatPct, statusBadgeClass } from "@/lib/utils";
import {
  TrendingUp, TrendingDown, Users, Store, CheckCircle,
  AlertTriangle, ShoppingBag, Target, Loader2,
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

function KPICard({
  title, value, subtitle, icon: Icon, color = "blue", trend,
}: {
  title: string; value: string; subtitle?: string;
  icon: React.ElementType; color?: string; trend?: number;
}) {
  const colors: Record<string, string> = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600",
    red: "bg-red-50 text-red-600",
  };
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
        <div className={`p-2.5 rounded-lg ${colors[color] || colors.blue}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      {trend !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${trend >= 0 ? "text-emerald-600" : "text-red-500"}`}>
          {trend >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
          {trend >= 0 ? "+" : ""}{formatPct(trend)} vs mes anterior
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { data: kpis, isLoading: loadingKpis } = useQuery({
    queryKey: ["dashboard-kpis"],
    queryFn: getDashboardKPIs,
    refetchInterval: 60_000,
  });

  const { data: salespersons, isLoading: loadingVendors } = useQuery({
    queryKey: ["salespersons-performance"],
    queryFn: getVendorsPerformance,
    refetchInterval: 60_000,
  });

  if (loadingKpis) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </AdminLayout>
    );
  }

  const chartData = salespersons?.map((v: { name: string; month_pct: number }) => ({
    name: v.name.split(" ")[0],
    pct: v.month_pct,
  })) || [];

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Rendimiento del equipo comercial en tiempo real
          </p>
        </div>

        {/* Alertas */}
        {(kpis?.salespersons_below_60pct > 0 || kpis?.inactive_clients_30d > 0) && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-amber-800">
              <p className="font-medium">Alertas activas</p>
              <ul className="mt-1 space-y-0.5 text-xs">
                {kpis?.salespersons_below_60pct > 0 && (
                  <li>• {kpis.salespersons_below_60pct} vendedor(es) con menos del 60% de meta</li>
                )}
                {kpis?.inactive_clients_30d > 0 && (
                  <li>• {kpis.inactive_clients_30d} clientes sin compra en los últimos 30 días</li>
                )}
              </ul>
            </div>
          </div>
        )}

        {/* KPIs principales */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Ventas Hoy" value={formatCOP(kpis?.sales_today || 0)}
            subtitle={`${kpis?.active_salespersons_today || 0} vendedores activos`}
            icon={ShoppingBag} color="blue"
          />
          <KPICard
            title="Ventas del Mes" value={formatCOP(kpis?.sales_this_month || 0)}
            subtitle={`${formatPct(kpis?.team_month_pct || 0)} de la meta`}
            icon={TrendingUp} color="green" trend={kpis?.mom_change_pct}
          />
          <KPICard
            title="Meta del Mes" value={formatCOP(kpis?.team_month_goal || 0)}
            subtitle={`Faltan ${formatCOP(Math.max(0, (kpis?.team_month_goal || 0) - (kpis?.sales_this_month || 0)))}`}
            icon={Target} color="amber"
          />
          <KPICard
            title="Efectividad Hoy"
            value={formatPct(kpis?.effectiveness_today || 0)}
            subtitle={`${kpis?.visits_completed_today || 0}/${kpis?.visits_planned_today || 0} visitas`}
            icon={CheckCircle} color="green"
          />
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Vendedores" value={String(kpis?.total_salespersons || 0)}
            subtitle={`${kpis?.active_salespersons_today || 0} con ruta hoy`}
            icon={Users} color="blue"
          />
          <KPICard
            title="Clientes Totales" value={String(kpis?.total_clients || 0)}
            subtitle={`${kpis?.active_clients_this_month || 0} compraron este mes`}
            icon={Store} color="blue"
          />
          <KPICard
            title="Bajo Meta (<60%)" value={String(kpis?.salespersons_below_60pct || 0)}
            subtitle="vendedores en riesgo"
            icon={AlertTriangle} color={kpis?.salespersons_below_60pct > 0 ? "red" : "green"}
          />
          <KPICard
            title="Clientes Inactivos" value={String(kpis?.inactive_clients_30d || 0)}
            subtitle="+30 dias sin compra"
            icon={Store} color={kpis?.inactive_clients_30d > 50 ? "red" : "amber"}
          />
        </div>

        {/* Grafico de cumplimiento */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h3 className="font-semibold text-slate-900 mb-4">% Cumplimiento de Meta por Vendedor</h3>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip
                    formatter={(v: number) => [`${v.toFixed(1)}%`, "Cumplimiento"]}
                    contentStyle={{ fontSize: 12 }}
                  />
                  <Bar dataKey="pct" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry: { pct: number }, i: number) => (
                      <Cell
                        key={i}
                        fill={entry.pct >= 80 ? "#10b981" : entry.pct >= 60 ? "#f59e0b" : "#ef4444"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-56 flex items-center justify-center text-slate-400 text-sm">
                Sin datos disponibles
              </div>
            )}
          </div>

          {/* Tabla de vendedores */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h3 className="font-semibold text-slate-900 mb-4">Rendimiento del Equipo</h3>
            {loadingVendors ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
              </div>
            ) : (
              <div className="space-y-2 overflow-auto max-h-56">
                {salespersons?.map((v: {
                  id: string; name: string; sales_month: number;
                  month_goal: number; month_pct: number; status_color: string;
                  visits_today: number; effectiveness_today: number;
                }) => (
                  <div key={v.id} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${
                        v.status_color === "green" ? "bg-emerald-500" :
                        v.status_color === "yellow" ? "bg-amber-500" : "bg-red-500"
                      }`} />
                      <span className="text-sm font-medium text-slate-800">{v.name}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>{formatCOP(v.sales_month)}</span>
                      <span className={`px-2 py-0.5 rounded-full font-medium ${statusBadgeClass(v.status_color)}`}>
                        {formatPct(v.month_pct)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
