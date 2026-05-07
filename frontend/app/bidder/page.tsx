"use client";

import * as React from "react";
import Link from "next/link";
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  Upload,
  BarChart3,
  Building2,
  Calendar
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";

const MY_TENDERS = [
  {
    id: "t1",
    reference: "CRPF/GC-BLR/ENGG/2025-26/CT-07",
    title: "Construction of Barrack Complex & Utility Infrastructure",
    status: "evaluating",
    progress: "14/15 documents uploaded",
    deadline: "31 May 2025",
  },
  {
    id: "t2",
    reference: "CRPF/GC-DEL/CIVIL/2025-26/CT-12",
    title: "Renovation of Administrative Block — Group Centre Delhi",
    status: "completed",
    progress: "Eligible (Score: 88/100)",
    deadline: "15 Apr 2025",
  },
];

const statusConfig: Record<string, { label: string; class: string; dotClass: string }> = {
  evaluating: { label: "Under Evaluation", class: "text-amber-400 bg-amber-500/10 border-amber-500/20", dotClass: "review" },
  completed: { label: "Completed", class: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", dotClass: "pass" },
  draft: { label: "Draft", class: "text-muted-foreground bg-secondary border-border", dotClass: "pending" },
};

export default function BidderDashboard() {
  const { user } = useAuth();

  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      {/* Welcome */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold">Welcome, {user?.name}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your tender submissions and track evaluation status.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Active Submissions", value: "1", icon: FileText, color: "text-blue-400", bg: "bg-blue-500/10" },
          { label: "Documents Uploaded", value: "14", icon: Upload, color: "text-emerald-400", bg: "bg-emerald-500/10" },
          { label: "Pending Actions", value: "1", icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-500/10" },
          { label: "Evaluations Passed", value: "4", icon: CheckCircle2, color: "text-violet-400", bg: "bg-violet-500/10" },
        ].map(({ label, value, icon: Icon, color, bg }, i) => (
          <div
            key={label}
            className={`rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5 card-hover animate-fade-in-up stagger-${i + 1}`}
          >
            <div className="flex items-center justify-between">
              <div className={`h-10 w-10 rounded-lg ${bg} flex items-center justify-center`}>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-3xl font-bold animate-count-up">{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Tenders */}
        <div className="lg:col-span-2 rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5 space-y-4 animate-fade-in-up stagger-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              My Tenders
            </h3>
            <Link href="/bidder/tenders" className="text-xs text-emerald-500 hover:underline">
              View all →
            </Link>
          </div>
          <div className="space-y-3">
            {MY_TENDERS.map((tender) => {
              const sc = statusConfig[tender.status];
              return (
                <Link key={tender.id} href={`/bidder/tenders/${tender.id}`}>
                  <div className="flex items-center gap-4 p-3 rounded-lg hover:bg-secondary/50 transition-colors group cursor-pointer border border-border/30">
                    <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
                      <FileText className="h-5 w-5 text-emerald-500/80" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{tender.title}</p>
                      <p className="text-xs text-muted-foreground truncate">{tender.reference}</p>
                      <p className="text-xs font-medium mt-1 text-emerald-500/80">{tender.progress}</p>
                    </div>
                    <div className="text-right shrink-0 space-y-1">
                      <div className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full border ${sc.class}`}>
                        <span className={`status-dot ${sc.dotClass}`} />
                        {sc.label}
                      </div>
                      <p className="text-[10px] text-muted-foreground flex items-center justify-end gap-1">
                        <Calendar className="h-3 w-3" />
                        Due: {tender.deadline}
                      </p>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Quick Actions & To-Do */}
        <div className="space-y-6 animate-fade-in-up stagger-4">
          <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5 space-y-4">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              Pending Actions
            </h3>
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
                <p className="text-sm font-medium text-amber-500/90">Power of Attorney Missing</p>
                <p className="text-xs text-muted-foreground mt-1">
                  CRPF/GC-BLR/ENGG/2025-26/CT-07 requires D-15.
                </p>
                <Link href={`/bidder/tenders/t1/submit`} className="text-xs font-semibold text-amber-500 mt-2 inline-block hover:underline">
                  Upload Now →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
