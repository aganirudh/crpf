"use client";

import * as React from "react";
import {
  type AuthUser,
  type UserRole,
  getStoredAuth,
  setStoredAuth,
  clearStoredAuth,
} from "@/lib/auth";

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string, role: UserRole) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextType>({
  user: null,
  isLoading: true,
  login: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    const stored = getStoredAuth();
    setUser(stored);
    setIsLoading(false);
  }, []);

  const login = React.useCallback(async (email: string, password: string, role: UserRole) => {
    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, role }),
      });
      
      if (!response.ok) {
        const text = await response.text();
        let message = "Authentication failed";
        try {
          const parsed = JSON.parse(text) as { detail?: unknown; message?: unknown };
          const d = parsed.detail ?? parsed.message;
          if (typeof d === "string") message = d;
          else if (d != null) message = JSON.stringify(d);
        } catch {
          if (text?.trim()) message = text.trim();
        }
        // Common dev failure: backend not running / proxy error -> Next returns plain text.
        if (/ECONNREFUSED|connect|refused|Internal Server Error/i.test(message)) {
          message =
            "Backend is not reachable. Start the FastAPI server on port 8000, then retry.";
        }
        throw new Error(message);
      }
      
      const authUser: AuthUser = await response.json();
      setStoredAuth(authUser);
      setUser(authUser);
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    }
  }, []);

  const logout = React.useCallback(() => {
    clearStoredAuth();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return React.useContext(AuthContext);
}
