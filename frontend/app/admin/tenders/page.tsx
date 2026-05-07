"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  Plus,
  Search,
  Filter,
  ChevronRight,
  Calendar,
  Users,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Upload,
} from "lucide-react";
import { api, type TenderSummary } from "@/lib/api";

// Sample data — replaced by real API data when backend is running
const SAMPLE_TENDERS = [
  {
    id: "sample-1",
    reference_no: "CRPF/GC-BLR/ENGG/2025-26/CT-07",
    department: "Engineering Division, Bengaluru",
    filename: "tender_barrack_complex.pdf",
    sha256_hex: "a1b2c3d4e5f6",
    page_count: 15,
    classification: "typed_pdf",
    has_dsl: true,
    status: "evaluating",
    bidders: 6,
    date: "01 May 2025",
    value: "₹18.50 Cr",
  },
  {
    id: "sample-2",
    reference_no: "CRPF/GC-DEL/CIVIL/2025-26/CT-12",
    department: "Construction Wing, Delhi",
    filename: "renovation_admin_block.pdf",
    sha256_hex: "b2c3d4e5f6a1",
    page_count: 22,
    classification: "typed_pdf",
    has_dsl: true,
    status: "completed",
    bidders: 4,
    date: "15 Apr 2025",
    value: "₹5.20 Cr",
  },
  {
    id: "sample-3",
    reference_no: "CRPF/GC-HYD/ELEC/2025-26/CT-03",
    department: "Electrical Division, Hyderabad",
    filename: "electrical_upgrade.pdf",
    sha256_hex: "c3d4e5f6a1b2",
    page_count: 8,
    classification: "typed_pdf",
    has_dsl: false,
    status: "pending",
    bidders: 0,
    date: "28 Apr 2025",
    value: "₹2.80 Cr",
  },
];

const statusConfig: Record<string, { label: string; class: string; dotClass: string; icon: React.ElementType }> = {
  evaluating: { label: "Evaluating", class: "text-amber-400 bg-amber-500/10 border-amber-500/20", dotClass: "review", icon: Clock },
  completed: { label: "Completed", class: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", dotClass: "pass", icon: CheckCircle2 },
  pending: { label: "Pending", class: "text-muted-foreground bg-secondary border-border", dotClass: "pending", icon: AlertTriangle },
};

export default function AdminTendersPage() {
  const [searchQuery, setSearchQuery] = React.useState("");
  const [filterStatus, setFilterStatus] = React.useState<string>("all");

  const filtered = SAMPLE_TENDERS.filter((t) => {
    if (filterStatus !== "all" && t.status !== filterStatus) return false;
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

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold">Tenders</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage and evaluate tender submissions
          </p>
        </div>
        <Link href="/admin/tenders/new">
          <button className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors">
            <Plus className="h-4 w-4" />
            Upload Tender
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
          {["all", "evaluating", "completed", "pending"].map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                filterStatus === s
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Tender Cards */}
      <div className="grid gap-4">
        {filtered.map((tender, i) => {
          const sc = statusConfig[tender.status] || statusConfig.pending;
          const StatusIcon = sc.icon;
          return (
            <Link key={tender.id} href={`/admin/tenders/${tender.id}`}>
              <div className={`rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5 card-hover cursor-pointer animate-fade-in-up stagger-${Math.min(i + 1, 5)}`}>
                <div className="flex items-start gap-4">
                  <div className="h-12 w-12 rounded-xl bg-primary/5 flex items-center justify-center shrink-0">
                    <FileText className="h-6 w-6 text-primary/60" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-base font-semibold">
                          {tender.reference_no || tender.filename}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-0.5">{tender.department}</p>
                      </div>
                      <div className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${sc.class} shrink-0`}>
                        <span className={`status-dot ${sc.dotClass}`} />
                        {sc.label}
                      </div>
                    </div>
                    <div className="flex items-center gap-6 mt-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5" />
                        {tender.date}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Users className="h-3.5 w-3.5" />
                        {tender.bidders} bidders
                      </span>
                      <span className="flex items-center gap-1.5">
                        <FileText className="h-3.5 w-3.5" />
                        {tender.page_count} pages
                      </span>
                      <span className="font-semibold text-foreground">{tender.value}</span>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-muted-foreground/30 shrink-0 self-center" />
                </div>
              </div>
            </Link>
          );
        })}
        {filtered.length === 0 && (
          <div className="text-center py-16 text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-3 text-muted-foreground/30" />
            <p className="text-sm font-medium">No tenders found</p>
            <p className="text-xs mt-1">Try adjusting your search or filters</p>
          </div>
        )}
      </div>
    </div>
  );
}
