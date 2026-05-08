"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter, usePathname } from "next/navigation";
import {
  ArrowLeft,
  ClipboardCheck,
  CheckCircle2,
  Building2,
  Shield,
  Award,
  Upload,
  BarChart3,
  Sparkles,
  FileText
} from "lucide-react";

const TENDER_META = {
  reference: "CRPF/GC-BLR/ENGG/2025-26/CT-07",
  title: "Construction of Barrack Complex & Utility Infrastructure",
  issueDate: "01 May 2025",
  submissionDeadline: "31 May 2025 (17:00 hrs IST)",
  projectValue: "Rs. 18,50,00,000/-",
  emd: "Rs. 37,00,000/-",
  status: "evaluating"
};

const CRITERIA_OVERVIEW = [
  { type: "Financial", count: 3, icon: Building2 },
  { type: "Technical", count: 5, icon: Award },
  { type: "Compliance", count: 6, icon: Shield },
  { type: "Optional", count: 4, icon: Sparkles },
];

export default function BidderTenderLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const params = useParams();
  const pathname = usePathname();
  
  const basePath = `/bidder/tenders/${params.tenderId}`;
  
  const tabs = [
    { id: "view", label: "Original Tender", path: `${basePath}/view`, icon: FileText },
    { id: "criteria", label: "Tender Criteria", path: basePath, icon: ClipboardCheck },
    { id: "submit", label: "Document Submission", path: `${basePath}/submit`, icon: Upload },
    { id: "status", label: "Evaluation Status", path: `${basePath}/status`, icon: BarChart3 },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Back + Title */}
      <div className="animate-fade-in-up">
        <button
          onClick={() => router.push("/bidder/tenders")}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back to My Tenders
        </button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold">{TENDER_META.title}</h1>
            <p className="text-sm text-muted-foreground mt-1 font-mono">{TENDER_META.reference}</p>
          </div>
          <div className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border text-amber-400 bg-amber-500/10 border-amber-500/20 shrink-0">
            <span className="status-dot review" />
            Under Evaluation
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border/30 animate-fade-in-up stagger-1">
        <div className="flex items-center gap-1">
          {tabs.map(({ id, label, path, icon: Icon }) => {
            const isActive = pathname === path;
            return (
              <Link key={id} href={path}>
                <div
                  className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all ${
                    isActive
                      ? "border-emerald-500 text-emerald-500"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="animate-fade-in-up stagger-2">
        {children}
      </div>
    </div>
  );
}
