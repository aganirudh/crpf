"use client";

import { useRouter } from "next/navigation";
import * as React from "react";
import { useAuth } from "@/components/auth-provider";
import { ShieldCheck, Lock, Building2, Loader2, KeyRound, User } from "lucide-react";
import { type UserRole } from "@/lib/auth";

export default function Home() {
  const router = useRouter();
  const { user, isLoading, login } = useAuth();
  
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [role, setRole] = React.useState<UserRole>("admin");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    if (!isLoading && user) {
      router.replace(user.role === "admin" ? "/admin" : "/bidder");
    }
  }, [user, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");

    try {
      // For now, this still uses the auth provider which we will update
      // to make a real backend API call.
      await login(email, password, role);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid credentials");
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-dvh flex bg-background">
      {/* Left side — Info & Branding */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 p-12 border-r border-border/50 bg-secondary/20 relative overflow-hidden">
        <div className="absolute inset-0 bg-grid-white/[0.02] bg-[length:32px_32px]" />
        
        <div className="relative z-10 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <ShieldCheck className="h-6 w-6 text-primary" />
          </div>
          <span className="text-xl font-bold tracking-tight">PRAMAAN</span>
        </div>

        <div className="relative z-10 max-w-lg">
          <h1 className="text-4xl font-bold tracking-tight mb-6 leading-tight">
            Next-generation procurement evaluation for the Central Reserve Police Force.
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Pramaan streamlines tender evaluation by accelerating document verification while maintaining strict compliance, cryptographic audibility, and complete data sovereignty.
          </p>
        </div>

        <div className="relative z-10 text-sm text-muted-foreground">
          <p>Government of India — Ministry of Home Affairs</p>
          <p className="font-semibold text-foreground/80 mt-1">CRPF Engineering Division</p>
        </div>
      </div>

      {/* Right side — Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 relative">
        <div className="w-full max-w-md space-y-8 animate-fade-in-up">
          <div className="text-center lg:text-left">
            <h2 className="text-2xl font-bold">Sign in to your account</h2>
            <p className="text-sm text-muted-foreground mt-2">
              Enter your credentials to access the evaluation portal.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Role Toggle */}
            <div className="flex p-1 rounded-xl bg-secondary/50 border border-border/50">
              <button
                type="button"
                onClick={() => setRole("admin")}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
                  role === "admin" 
                    ? "bg-card shadow-sm border border-border text-foreground" 
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Department / Admin
              </button>
              <button
                type="button"
                onClick={() => setRole("bidder")}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
                  role === "bidder" 
                    ? "bg-card shadow-sm border border-border text-foreground" 
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Contractor / Bidder
              </button>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Email Address / User ID</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={role === "admin" ? "officer@crpf.gov.in" : "anirudh@sunriseconstructions.in"}
                    className="w-full h-11 pl-10 pr-4 rounded-xl border border-border bg-card/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Password</label>
                  <a href="#" className="text-xs text-primary hover:underline">Forgot password?</a>
                </div>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full h-11 pl-10 pr-4 rounded-xl border border-border bg-card/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all"
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="p-3 text-sm text-red-500 bg-red-500/10 border border-red-500/20 rounded-lg">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-11 inline-flex items-center justify-center gap-2 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors disabled:opacity-70"
            >
              {isSubmitting ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>Sign In <Lock className="h-4 w-4" /></>
              )}
            </button>
          </form>

          {role === "bidder" && (
            <p className="text-center text-sm text-muted-foreground">
              New contractor? <a href="#" className="text-primary hover:underline font-medium">Register your firm</a>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
