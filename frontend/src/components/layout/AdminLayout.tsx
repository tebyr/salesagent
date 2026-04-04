"use client";
import { Sidebar } from "./Sidebar";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!Cookies.get("access_token")) router.push("/login");
  }, [router]);

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="p-6 max-w-7xl mx-auto">{children}</div>
      </main>
    </div>
  );
}
