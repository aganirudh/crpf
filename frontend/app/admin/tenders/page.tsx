"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  Plus,
  Search,
  ChevronRight,
  Calendar,
  Users,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { api, type TenderSummary } from "@/lib/api";

const statusConfig: Record<string, { label: string; class: string; dotClass: string; icon: React.ElementType }> = {
  evaluating: { label: "Evaluating", class: "text-amber-400 bg-amber-500/10 border-amber-500/20", dotClass: "review", icon: Clock },
  completed: { label: "Completed", class: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", dotClass: "pass", icon: CheckCircle2 },
  pending: { label: "Pending", class: "text-muted-foreground bg-secondary border-border", dotClass: "pending", icon: AlertTriangle },
};

export default function AdminTendersPage() {
  const [searchQuery, setSearchQuery] = React.useState("");
  const [filterStatus, setFilterStatus] = React.useState<string>("all");

  const { data: tenders = [], isLoading } = useQuery<TenderSummary[]>({
    queryKey: ["tenders"],
    queryFn: () => api.listTenders(),
    refetchInterval: 5000, // Poll every 5s for demo
  });

  const filtered = tenders.filter((t) => {
    // Determine status based on flags
    const status = t.has_dsl ? "evaluating" : "pending";
    
    if (filterStatus !== "all" && status !== filterStatus) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        t.reference_no?.toLowerCase().includes(q) ||
        t.department?.toLowerCase().includes(q) ||
        t.filename.toLowerCase().includes(q)
      );
    }
    return true;
  });

  if (isLoading && tenders.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground font-medium uppercase tracking-wider">Loading Tenders...</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Tender Management</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Publish new tenders and oversee the automated evaluation process.
          </p>
        </div>
        <Link href="/admin/tenders/new">
          <button className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20">
            <Plus className="h-4 w-4" />
            Upload New Tender
          </button>
        </Link>
      </div>

      {/* Search & Filters */}
      <div className="flex items-center gap-3 animate-fade-in-up stagger-1">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by reference, department, or filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-10 pl-10 pr-4 rounded-lg border border-border bg-card/60 text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all"
          />
        </div>
        <div className="flex items-center gap-1.5 p-1 rounded-lg bg-secondary/50 border border-border/50">
          {["all", "evaluating", "pending"].map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                filterStatus === s
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {s === "all" ? "All Status" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Tender Cards */}
      <div className="grid gap-4">
        {filtered.map((tender, i) => {
          const status = tender.has_dsl ? "evaluating" : "pending";
          const sc = statusConfig[status] || statusConfig.pending;
          return (
            <Link key={tender.id} href={`/admin/tenders/${tender.id}`}>
              <div className={`rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5 card-hover cursor-pointer animate-fade-in-up`}>
                <div className="flex items-start gap-4">
                  <div className="h-12 w-12 rounded-xl bg-primary/5 flex items-center justify-center shrink-0 border border-primary/10">
                    <FileText className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-base font-semibold text-foreground">
                          {tender.reference_no || tender.filename}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-0.5">{tender.department || "General Department"}</p>
                      </div>
                      <div className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${sc.class} shrink-0`}>
                        <span className={`status-dot ${sc.dotClass}`} />
                        {sc.label}
                      </div>
                    </div>
                    <div className="flex items-center gap-6 mt-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5" />
                        Issued: {new Date().toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Users className="h-3.5 w-3.5" />
                        {tender.bidders || 0} Bidders
                      </span>
                      <span className="flex items-center gap-1.5">
                        <FileText className="h-3.5 w-3.5" />
                        {tender.page_count} Pages
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-muted-foreground/30 shrink-0 self-center" />
                </div>
              </div>
            </Link>
          );
        })}
        {filtered.length === 0 && (
          <div className="text-center py-20 border-2 border-dashed border-border/30 rounded-2xl bg-secondary/5">
            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground/20" />
            <h3 className="text-lg font-semibold text-foreground/70">No Active Tenders</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-xs mx-auto">
              Ready for the demo. Upload a tender document to begin the automated evaluation process.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
