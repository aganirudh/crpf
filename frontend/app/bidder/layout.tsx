"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import {
  FileText,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Moon,
  Sun,
  Bell,
  Building2,
  FolderOpen
} from "lucide-react";
import { useTheme } from "next-themes";

const NAV_ITEMS = [
  { href: "/bidder", label: "Dashboard", icon: Building2 },
  { href: "/bidder/tenders", label: "My Tenders", icon: FolderOpen },
];

export default function BidderLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = React.useState(false);

  React.useEffect(() => {
    if (!isLoading && (!user || user.role !== "bidder")) {
      router.replace("/");
    }
  }, [user, isLoading, router]);

  if (isLoading || !user) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const isActive = (href: string) => {
    if (href === "/bidder") return pathname === "/bidder";
    return pathname.startsWith(href);
  };

  return (
    <div className="flex h-dvh overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`relative flex flex-col border-r border-border/50 bg-card/80 backdrop-blur-xl transition-all duration-300 ${
          collapsed ? "w-[68px]" : "w-[260px]"
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 p-4 border-b border-border/30">
          <div className="h-9 w-9 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
            <FileText className="h-5 w-5 text-emerald-500" />
          </div>
          {!collapsed && (
            <div className="animate-fade-in">
              <p className="text-sm font-bold tracking-tight">PRAMAAN</p>
              <p className="text-[10px] text-muted-foreground">Bidder Portal</p>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href}>
              <div
                className={`sidebar-nav-item ${isActive(href) ? "active !text-emerald-500 !bg-emerald-500/10" : ""} ${
                  collapsed ? "justify-center px-0" : ""
                }`}
                title={collapsed ? label : undefined}
              >
                <Icon className="h-[18px] w-[18px] shrink-0" />
                {!collapsed && <span>{label}</span>}
              </div>
            </Link>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-border/30 p-3 space-y-2">
          {!collapsed && (
            <div className="px-3 py-2">
              <p className="text-xs font-semibold truncate">{user.name}</p>
              <p className="text-[10px] text-muted-foreground truncate">{user.email}</p>
            </div>
          )}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className={`sidebar-nav-item ${collapsed ? "justify-center px-0" : ""}`}
            title="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
            {!collapsed && <span>Toggle Theme</span>}
          </button>
          <button
            onClick={() => { logout(); router.replace("/"); }}
            className={`sidebar-nav-item text-destructive hover:!text-destructive hover:!bg-destructive/10 ${
              collapsed ? "justify-center px-0" : ""
            }`}
          >
            <LogOut className="h-[18px] w-[18px]" />
            {!collapsed && <span>Sign Out</span>}
          </button>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -right-3 top-20 h-6 w-6 rounded-full border border-border bg-card flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors z-10"
        >
          {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
        </button>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 border-b border-border/30 bg-card/40 backdrop-blur-sm flex items-center justify-between px-6 shrink-0">
          <div>
            <h2 className="text-sm font-semibold">
              {NAV_ITEMS.find(n => isActive(n.href))?.label || "Dashboard"}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <button className="relative h-8 w-8 rounded-lg bg-secondary/50 flex items-center justify-center hover:bg-secondary transition-colors">
              <Bell className="h-4 w-4 text-muted-foreground" />
            </button>
            <div className="h-8 w-8 rounded-lg bg-emerald-500/20 flex items-center justify-center text-xs font-bold text-emerald-500">
              {user.name.charAt(0)}
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
