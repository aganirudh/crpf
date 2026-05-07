"use client";

import * as React from "react";
import Link from "next/link";
import {
  FileText,
  Users,
  ClipboardCheck,
  TrendingUp,
  ArrowRight,
  Plus,
  Clock,
  CheckCircle2,
  AlertTriangle,
  BarChart3,
} from "lucide-react";

const STATS = [
  {
    label: "Total Tenders",
    value: "12",
    change: "+3 this month",
    icon: FileText,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    label: "Active Evaluations",
    value: "5",
    change: "2 pending review",
    icon: ClipboardCheck,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    label: "Bidders Evaluated",
    value: "34",
    change: "+8 this week",
    icon: Users,
    color: "text-violet-400",
    bg: "bg-violet-500/10",
  },
  {
    label: "Completion Rate",
    value: "87%",
    change: "↑ 12% from last month",
    icon: TrendingUp,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
];

const RECENT_TENDERS = [
  {
    id: "t1",
    reference: "CRPF/GC-BLR/ENGG/2025-26/CT-07",
    title: "Construction of Barrack Complex & Utility Infrastructure",
    status: "evaluating",
    bidders: 6,
    date: "01 May 2025",
  },
  {
    id: "t2",
    reference: "CRPF/GC-DEL/CIVIL/2025-26/CT-12",
    title: "Renovation of Administrative Block — Group Centre Delhi",
    status: "completed",
    bidders: 4,
    date: "15 Apr 2025",
  },
  {
    id: "t3",
    reference: "CRPF/GC-HYD/ELEC/2025-26/CT-03",
    title: "Electrical Infrastructure Upgrade — Hyderabad Campus",
    status: "pending",
    bidders: 0,
    date: "28 Apr 2025",
  },
];

const statusConfig: Record<string, { label: string; class: string; dotClass: string }> = {
  evaluating: { label: "Evaluating", class: "text-amber-400 bg-amber-500/10 border-amber-500/20", dotClass: "review" },
  completed: { label: "Completed", class: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", dotClass: "pass" },
  pending: { label: "Pending", class: "text-muted-foreground bg-secondary border-border", dotClass: "pending" },
};

export default function AdminDashboard() {
  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      {/* Welcome */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold">Welcome back, Commandant</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Here&apos;s an overview of your tender evaluations
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {STATS.map(({ label, value, change, icon: Icon, color, bg }, i) => (
          <div
            key={label}
            className={`rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5 card-hover animate-fade-in-up stagger-${i + 1}`}
          >
            <div className="flex items-center justify-between">
              <div className={`h-10 w-10 rounded-lg ${bg} flex items-center justify-center`}>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
              <BarChart3 className="h-4 w-4 text-muted-foreground/40" />
            </div>
            <div className="mt-4">
              <p className="text-3xl font-bold animate-count-up">{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{label}</p>
            </div>
            <p className="text-xs text-muted-foreground/80 mt-2">{change}</p>
          </div>
        ))}
      </div>

      {/* Quick Actions + Recent Tenders */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5 space-y-4 animate-fade-in-up stagger-3">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            Quick Actions
          </h3>
          <div className="space-y-2">
            <Link href="/admin/tenders/new">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-primary/5 border border-primary/10 hover:bg-primary/10 transition-colors group cursor-pointer">
                <Plus className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">Upload New Tender</span>
                <ArrowRight className="h-3 w-3 ml-auto text-primary opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>
            <Link href="/admin/tenders">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors group cursor-pointer">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">View All Tenders</span>
                <ArrowRight className="h-3 w-3 ml-auto text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>
            <Link href="/admin/bidders">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors group cursor-pointer">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Manage Bidders</span>
                <ArrowRight className="h-3 w-3 ml-auto text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>
          </div>
        </div>

        {/* Recent Tenders */}
        <div className="lg:col-span-2 rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5 space-y-4 animate-fade-in-up stagger-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              Recent Tenders
            </h3>
            <Link href="/admin/tenders" className="text-xs text-primary hover:underline">
              View all →
            </Link>
          </div>
          <div className="space-y-3">
            {RECENT_TENDERS.map((tender) => {
              const sc = statusConfig[tender.status];
              return (
                <Link key={tender.id} href={`/admin/tenders/${tender.id}`}>
                  <div className="flex items-center gap-4 p-3 rounded-lg hover:bg-secondary/50 transition-colors group cursor-pointer">
                    <div className="h-10 w-10 rounded-lg bg-primary/5 flex items-center justify-center shrink-0">
                      <FileText className="h-5 w-5 text-primary/60" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{tender.title}</p>
                      <p className="text-xs text-muted-foreground truncate">{tender.reference}</p>
                    </div>
                    <div className="text-right shrink-0 space-y-1">
                      <div className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full border ${sc.class}`}>
                        <span className={`status-dot ${sc.dotClass}`} />
                        {sc.label}
                      </div>
                      <p className="text-[10px] text-muted-foreground">{tender.bidders} bidders · {tender.date}</p>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      {/* Pipeline status */}
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5 animate-fade-in-up stagger-5">
        <h3 className="text-sm font-semibold mb-4">Evaluation Pipeline</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { label: "Tender Uploaded", count: 12, icon: FileText, status: "pass" },
            { label: "Criteria Extracted", count: 10, icon: ClipboardCheck, status: "pass" },
            { label: "Documents Parsed", count: 8, icon: BarChart3, status: "review" },
            { label: "Verdicts Generated", count: 5, icon: CheckCircle2, status: "pass" },
            { label: "Reports Signed", count: 3, icon: AlertTriangle, status: "pending" },
          ].map(({ label, count, icon: Icon, status }) => (
            <div key={label} className="text-center p-3 rounded-lg bg-secondary/30">
              <div className={`h-8 w-8 rounded-lg mx-auto flex items-center justify-center mb-2 ${
                status === "pass" ? "bg-emerald-500/10" : status === "review" ? "bg-amber-500/10" : "bg-muted"
              }`}>
                <Icon className={`h-4 w-4 ${
                  status === "pass" ? "text-emerald-400" : status === "review" ? "text-amber-400" : "text-muted-foreground"
                }`} />
              </div>
              <p className="text-xl font-bold">{count}</p>
              <p className="text-[10px] text-muted-foreground mt-1">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
