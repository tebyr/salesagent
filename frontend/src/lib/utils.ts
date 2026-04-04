import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCOP(amount: number): string {
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`;
  return `$${amount.toFixed(0)}`;
}

export function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function statusColor(pct: number): string {
  if (pct >= 80) return "green";
  if (pct >= 60) return "yellow";
  return "red";
}

export function statusBadgeClass(color: string): string {
  switch (color) {
    case "green": return "bg-emerald-100 text-emerald-800";
    case "yellow": return "bg-amber-100 text-amber-800";
    case "red": return "bg-red-100 text-red-800";
    default: return "bg-gray-100 text-gray-800";
  }
}
