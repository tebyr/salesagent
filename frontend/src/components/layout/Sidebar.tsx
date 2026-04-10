"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Users, Store, Target, Settings,
  MessageSquare, LogOut, Package, MapPin,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

const navItems = [
  { href: "/dashboard",    label: "Dashboard",   icon: LayoutDashboard },
  { href: "/salespersons", label: "Vendedores",  icon: Users },
  { href: "/clients",      label: "Clientes",    icon: Store },
  { href: "/productos",    label: "Productos",   icon: Package },
  { href: "/rutas",        label: "Rutas",       icon: MapPin },
  { href: "/goals",        label: "Metas",       icon: Target },
  { href: "/settings",     label: "Configuracion", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    Cookies.remove("access_token");
    router.push("/login");
  }

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-slate-900 text-white">
      {/* Logo */}
      <div className="flex items-center gap-2 px-6 py-5 border-b border-slate-700">
        <MessageSquare className="w-7 h-7 text-blue-400" />
        <div>
          <p className="font-bold text-sm leading-tight">Sales Agent</p>
          <p className="text-xs text-slate-400">Panel Admin</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              pathname.startsWith(href)
                ? "bg-blue-600 text-white"
                : "text-slate-300 hover:bg-slate-800 hover:text-white"
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </Link>
        ))}
      </nav>

      {/* Logout */}
      <div className="px-3 py-4 border-t border-slate-700">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Cerrar sesion
        </button>
      </div>
    </aside>
  );
}
