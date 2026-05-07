/**
 * Authentication context for role-based access control.
 * Supports Admin and Bidder roles with localStorage persistence.
 */

export type UserRole = "admin" | "bidder";

export interface AuthUser {
  id: string;
  name: string;
  role: UserRole;
  email: string;
}

const AUTH_KEY = "pramaan_auth";

export function getStoredAuth(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setStoredAuth(user: AuthUser): void {
  localStorage.setItem(AUTH_KEY, JSON.stringify(user));
}

export function clearStoredAuth(): void {
  localStorage.removeItem(AUTH_KEY);
}

// Mock users for development
export const MOCK_USERS: Record<UserRole, AuthUser> = {
  admin: {
    id: "admin-001",
    name: "Commandant R. K. Sharma",
    role: "admin",
    email: "commandant@crpf.gov.in",
  },
  bidder: {
    id: "bidder-001",
    name: "Rajesh Kumar & Associates",
    role: "bidder",
    email: "rajesh@buildcorp.in",
  },
};
