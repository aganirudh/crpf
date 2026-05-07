"use client";

import * as React from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Brain,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  Info
} from "lucide-react";

// Same verdicts as admin, but read-only for bidder
const VERDICT_DETAILS = [
  { id: "F-1", label: "Avg Turnover ≥ ₹1 Cr", status: "pass" },
  { id: "F-2", label: "Positive Net Worth", status: "pass" },
  { id: "F-3", label: "No excess loss years", status: "pass" },
  { id: "T-1", label: "3+ similar projects", status: "pass" },
  { id: "T-2", label: "Project value ≥ ₹2 Cr", status: "pass" },
  { id: "T-3", label: "Registered Engineer", status: "pass" },
  { id: "T-4", label: "Equipment access", status: "review" },
  { id: "T-5", label: "ISO 9001:2015", status: "pass" },
  { id: "C-1", label: "GST active", status: "pass" },
  { id: "C-2", label: "PF registration", status: "pass" },
  { id: "C-3", label: "ESI registration", status: "pass" },
  { id: "C-4", label: "PAN verified", status: "pass" },
  { id: "C-5", label: "Not blacklisted", status: "pass" },
  { id: "C-6", label: "PWD/CPWD registration", status: "review" },
];

const AI_SUMMARY = `## Evaluation Summary
Your submission for Tender CRPF/GC-BLR/ENGG/2025-26/CT-07 is currently **Under Evaluation**.

### Financial Assessment ✅
Your financial documents have been successfully verified. The average annual turnover meets the ₹1 Crore threshold, and net worth is positive.

### Technical Qualification ⏳
Your project experience and personnel qualifications have been verified. However, **Criteria T-4 (Equipment access)** is currently under manual review by the evaluation committee to verify the lease agreement for the Batching Plant.

### Compliance Status ⏳
Statutory registrations (GST, PF, ESI, PAN) are verified and active. **Criteria C-6 (PWD Registration)** is under review pending verification of the registration class against the required threshold.

### Next Steps
No further action is required from you at this time. You will be notified once the manual review is complete and the final verdict is published.`;

export default function BidderTenderStatusPage() {
  const [summaryExpanded, setSummaryExpanded] = React.useState(true);

  const passCount = VERDICT_DETAILS.filter(v => v.status === "pass").length;
  const reviewCount = VERDICT_DETAILS.filter(v => v.status === "review").length;
  const failCount = VERDICT_DETAILS.filter(v => v.status === "fail").length;
  const totalCount = VERDICT_DETAILS.length;

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Overall Status</p>
              <h3 className="text-2xl font-bold text-amber-400 mt-1">Evaluating</h3>
            </div>
            <div className="h-10 w-10 rounded-full bg-amber-500/10 flex items-center justify-center">
              <Clock className="h-5 w-5 text-amber-400" />
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Awaiting manual review on {reviewCount} criteria
          </p>
        </div>

        <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Criteria Passed</p>
              <h3 className="text-2xl font-bold mt-1">
                <span className="text-emerald-500">{passCount}</span>
                <span className="text-muted-foreground text-lg font-medium">/{totalCount}</span>
              </h3>
            </div>
            <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            </div>
          </div>
          <div className="w-full h-1.5 rounded-full bg-secondary mt-4 overflow-hidden">
            <div className="h-full bg-emerald-500" style={{ width: `${(passCount / totalCount) * 100}%` }} />
          </div>
        </div>

        <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-5">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Verification</p>
              <h3 className="text-lg font-bold text-emerald-500 mt-2">Cryptographically Secured</h3>
            </div>
            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
              <ShieldCheck className="h-5 w-5 text-primary" />
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Your evaluation is recorded on an immutable ledger.
          </p>
        </div>
      </div>

      {/* AI Summary */}
      <div className="rounded-xl border border-emerald-500/20 bg-card/60 backdrop-blur-sm overflow-hidden shadow-[0_0_20px_hsl(142,71%,45%,0.05)]">
        <button
          onClick={() => setSummaryExpanded(!summaryExpanded)}
          className="w-full flex items-center justify-between p-4 bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors border-b border-emerald-500/10"
        >
          <div className="flex items-center gap-2 text-emerald-500">
            <Brain className="h-4 w-4" />
            <span className="text-sm font-bold tracking-wide">Pramaan Analysis Engine</span>
          </div>
          {summaryExpanded ? <ChevronDown className="h-4 w-4 text-emerald-500" /> : <ChevronRight className="h-4 w-4 text-emerald-500" />}
        </button>
        
        {summaryExpanded && (
          <div className="p-5">
            <div className="prose prose-sm prose-invert max-w-none prose-p:text-foreground/80 prose-headings:text-foreground prose-strong:text-emerald-400">
              {AI_SUMMARY.split("\n").map((line, i) => {
                if (line.startsWith("## ")) return null; // Skip main title
                if (line.startsWith("### ")) return <h3 key={i} className="text-sm font-bold mt-4 mb-2 text-emerald-500/90">{line.replace("### ", "")}</h3>;
                if (line.trim() === "") return null;
                
                // Bold rendering
                const parts = line.split(/(\*\*[^*]+\*\*)/g);
                return (
                  <p key={i} className="mb-2 last:mb-0 leading-relaxed">
                    {parts.map((p, j) => 
                      p.startsWith("**") && p.endsWith("**") 
                        ? <strong key={j}>{p.slice(2, -2)}</strong> 
                        : p
                    )}
                  </p>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Criteria Breakdown */}
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden">
        <div className="p-4 border-b border-border/30 bg-secondary/10 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Evaluation Breakdown</h3>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Pass ({passCount})</span>
            <span className="flex items-center gap-1.5"><AlertTriangle className="h-3.5 w-3.5 text-amber-500" /> Review ({reviewCount})</span>
            <span className="flex items-center gap-1.5"><XCircle className="h-3.5 w-3.5 text-red-500" /> Fail ({failCount})</span>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-border/30">
          {VERDICT_DETAILS.map((v) => (
            <div key={v.id} className="flex items-center gap-3 p-4 bg-card hover:bg-secondary/20 transition-colors">
              <div className="shrink-0">
                {v.status === "pass" && <CheckCircle2 className="h-5 w-5 text-emerald-500" />}
                {v.status === "fail" && <XCircle className="h-5 w-5 text-red-500" />}
                {v.status === "review" && <AlertTriangle className="h-5 w-5 text-amber-500" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-emerald-500">{v.id}</span>
                  {v.status === "review" && (
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
                      UNDER REVIEW
                    </span>
                  )}
                </div>
                <p className="text-sm text-foreground/90 mt-1 truncate">{v.label}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
