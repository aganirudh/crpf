import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatINR(paise: number | null | undefined): string {
  if (paise == null) return "—";
  // Indian numbering (lakhs, crores)
  const rupees = paise;
  if (rupees >= 1_00_00_000) return `Rs. ${(rupees / 1_00_00_000).toFixed(2)} Cr`;
  if (rupees >= 1_00_000) return `Rs. ${(rupees / 1_00_000).toFixed(2)} L`;
  return `Rs. ${rupees.toLocaleString("en-IN")}`;
}

export function shortHash(hex: string | null | undefined, n = 8): string {
  if (!hex) return "—";
  return `${hex.slice(0, n)}…`;
}
