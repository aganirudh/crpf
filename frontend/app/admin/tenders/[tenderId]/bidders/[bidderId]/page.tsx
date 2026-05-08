"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Code2,
  ChevronDown,
  ChevronRight,
  FileText,
  Building2,
  Shield,
  Award,
  Sparkles,
  Brain,
  Loader2,
  Copy,
  Check,
  Gavel,
} from "lucide-react";
import { PdfViewer } from "@/components/pdf-viewer";

// ─── The evaluation payload JSON (transparent reasoning) ─────────────
const EVALUATION_PAYLOAD = {
  bidder: {
    legal_name: "Rajesh Kumar & Associates",
    gstin: "29AABCR1234A1ZP",
    pan: "AABCR1234A",
    bid_price_inr: 165000000,
  },
  criteria_evaluation: [
    {
      criterion_id: "F-1",
      type: "financial",
      requirement: "Average Annual Turnover >= Rs. 1 Crore (last 3 FY)",
      evidence: {
        field: "annual_turnover",
        values: {
          "FY2021-22": 28500000,
          "FY2022-23": 31200000,
          "FY2023-24": 34800000,
        },
        average: 31500000,
        unit: "INR",
        source_documents: ["D-02", "D-03"],
      },
      threshold: 10000000,
      operator: ">=",
      computed_result: true,
      confidence: 0.96,
      verdict: "PASS",
    },
    {
      criterion_id: "F-2",
      type: "financial",
      requirement: "Net Worth must be positive as on 31 March 2024",
      evidence: {
        field: "net_worth",
        value: 45200000,
        unit: "INR",
        as_on: "2024-03-31",
        source_documents: ["D-02"],
      },
      threshold: 0,
      operator: ">",
      computed_result: true,
      confidence: 0.94,
      verdict: "PASS",
    },
    {
      criterion_id: "T-1",
      type: "technical",
      requirement: "At least 3 similar projects completed in last 7 years",
      evidence: {
        field: "similar_projects",
        count: 5,
        projects: [
          { name: "Residential Complex, Whitefield", value_crore: 4.2, year: 2022 },
          { name: "Admin Block, HAL Township", value_crore: 2.8, year: 2021 },
          { name: "Barracks, BSF Campus Yelahanka", value_crore: 3.1, year: 2023 },
          { name: "Community Centre, DRDO Layout", value_crore: 1.9, year: 2020 },
          { name: "Staff Quarters, Army Campus", value_crore: 5.6, year: 2024 },
        ],
        source_documents: ["D-04"],
      },
      threshold: 3,
      operator: "count >=",
      computed_result: true,
      confidence: 0.91,
      verdict: "PASS",
    },
    {
      criterion_id: "T-2",
      type: "technical",
      requirement: "At least one project with contract value >= Rs. 2 Crore",
      evidence: {
        field: "max_project_value",
        value: 56000000,
        unit: "INR",
        source_documents: ["D-04"],
      },
      threshold: 20000000,
      operator: ">=",
      computed_result: true,
      confidence: 0.92,
      verdict: "PASS",
    },
    {
      criterion_id: "C-1",
      type: "compliance",
      requirement: "Valid GST Registration — GSTIN must be active",
      evidence: {
        field: "gstin_status",
        gstin: "29AABCR1234A1ZP",
        status: "Active",
        source_documents: ["D-08"],
      },
      operator: "exists + active",
      computed_result: true,
      confidence: 0.98,
      verdict: "PASS",
    },
  ],
  optional_scoring: {
    "O-1": { max: 5, scored: 5, evidence: "ISO 14001:2015 certificate valid" },
    "O-2": { max: 5, scored: 0, evidence: "OHSAS 45001 certificate not submitted" },
    "O-3": { max: 10, scored: 8, evidence: "3 defence projects found in portfolio" },
    "O-4": { max: 5, scored: 0, evidence: "No LEED/GRIHA certification found" },
  },
  total_optional_score: { scored: 13, max: 25 },
  overall_verdict: "ELIGIBLE",
  mandatory_pass_rate: "100%",
  confidence_mean: 0.94,
  flags: [],
  evaluated_at: "2025-05-07T16:30:00Z",
  engine_version: "pramaan-engine:v1.2",
};

const AI_SUMMARY = `## Bidder Evaluation Summary — Rajesh Kumar & Associates

### Overview
Rajesh Kumar & Associates is a Bengaluru-based construction firm that has demonstrated strong credentials across all mandatory evaluation categories for Tender CRPF/GC-BLR/ENGG/2025-26/CT-07 (Construction of Barrack Complex & Utility Infrastructure).

### Financial Assessment ✅
The firm reports a healthy financial trajectory with an average annual turnover of **₹3.15 Crore** over the last three financial years — well above the minimum threshold of ₹1 Crore. The net worth is positive at **₹4.52 Crore** as on 31 March 2024. No loss years have been identified in the evaluation window. All financial figures are corroborated by audited balance sheets and a CA certificate.

### Technical Qualification ✅
The firm has completed **5 similar construction projects** in the last 7 years, exceeding the minimum requirement of 3. Notably, the "Staff Quarters, Army Campus" project (₹5.6 Cr, 2024) demonstrates direct experience with defence establishment construction. The highest single project value of ₹5.6 Crore comfortably meets the ₹2 Crore minimum threshold under T-2.

A registered Civil Engineer with 8 years of post-qualification experience is confirmed on payroll. Equipment access documentation has been verified for Tower Crane, Transit Mixer, and Batching Plant.

### Compliance Status ✅
All statutory registrations are verified and active:
- **GST**: 29AABCR1234A1ZP (Active)
- **PF**: Establishment code verified
- **ESI**: Registration current
- **PAN**: AABCR1234A (verified against GST records)
- **Non-blacklisting**: Self-declaration submitted on company letterhead

### Optional Technical Score: 13/25
- ISO 14001:2015 — **5/5** (valid certificate)
- OHSAS 45001:2018 — **0/5** (not submitted)
- Defence/Govt Experience — **8/10** (3 qualifying projects)
- Green Building — **0/5** (no LEED/GRIHA certification)

### Recommendation
**ELIGIBLE** — The bidder satisfies all mandatory criteria across Financial, Technical, and Compliance categories with a mean confidence of **94%**. The optional technical score of 13/25 places them in the upper-mid tier. No integrity flags were raised. Recommended to proceed to commercial bid opening.`;

// ─── Per-criterion verdict data ─────────────────────────────────────
const VERDICT_DETAILS = [
  { id: "F-1", label: "Avg Turnover ≥ ₹1 Cr", status: "pass", confidence: 96 },
  { id: "F-2", label: "Positive Net Worth", status: "pass", confidence: 94 },
  { id: "F-3", label: "No excess loss years", status: "pass", confidence: 89 },
  { id: "T-1", label: "3+ similar projects", status: "pass", confidence: 91 },
  { id: "T-2", label: "Project value ≥ ₹2 Cr", status: "pass", confidence: 92 },
  { id: "T-3", label: "Registered Engineer", status: "pass", confidence: 90 },
  { id: "T-4", label: "Equipment access", status: "review", confidence: 72 },
  { id: "T-5", label: "ISO 9001:2015", status: "pass", confidence: 97 },
  { id: "C-1", label: "GST active", status: "pass", confidence: 98 },
  { id: "C-2", label: "PF registration", status: "pass", confidence: 95 },
  { id: "C-3", label: "ESI registration", status: "pass", confidence: 93 },
  { id: "C-4", label: "PAN verified", status: "pass", confidence: 97 },
  { id: "C-5", label: "Not blacklisted", status: "pass", confidence: 88 },
  { id: "C-6", label: "PWD/CPWD registration", status: "review", confidence: 70 },
];

type ViewTab = "verdicts" | "payload" | "summary";

export default function AdminBidderDetailPage() {
  const router = useRouter();
  const params = useParams();
  const [activeView, setActiveView] = React.useState<ViewTab>("verdicts");
  const [isJudging, setIsJudging] = React.useState(false);
  const [docToView, setDocToView] = React.useState<"tender" | "bidder">("tender");
  const [summaryLoading, setSummaryLoading] = React.useState(false);
  const [summaryGenerated, setSummaryGenerated] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [jsonExpanded, setJsonExpanded] = React.useState(false);
  const [updatingStatus, setUpdatingStatus] = React.useState(false);

  const tenderId = params.tenderId as string;
  const bidderId = params.bidderId as string;

  const handleUpdateStatus = async (newStatus: "accepted" | "rejected") => {
    setUpdatingStatus(true);
    try {
      const resp = await fetch(`/api/v1/bidders/${bidderId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!resp.ok) throw new Error("Failed to update status");
      router.refresh();
      // In a real app we'd use a toast here
    } catch (err) {
      console.error(err);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const tenderPdfUrl = `/api/v1/tenders/${tenderId}/source`;
  // Assuming a similar endpoint for bidder documents, or just reuse tender for now
  const bidderPdfUrl = `/api/v1/tenders/${tenderId}/source`; 

  const handleGenerateSummary = () => {
    setSummaryLoading(true);
    setTimeout(() => {
      setSummaryLoading(false);
      setSummaryGenerated(true);
      setActiveView("summary");
    }, 2500);
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(EVALUATION_PAYLOAD, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const passCount = VERDICT_DETAILS.filter((v) => v.status === "pass").length;
  const totalCount = VERDICT_DETAILS.length;

  return (
    <div className={`p-6 max-w-7xl mx-auto space-y-6 ${isJudging ? "max-w-none" : ""}`}>
      {/* Header */}
      <div className="animate-fade-in-up">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold">Rajesh Kumar &amp; Associates</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Tender: CRPF/GC-BLR/ENGG/2025-26/CT-07
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => handleUpdateStatus("accepted")}
              disabled={updatingStatus}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 transition-colors disabled:opacity-50"
            >
              <CheckCircle2 className="h-4 w-4" />
              Accept Bid
            </button>
            <button
              onClick={() => handleUpdateStatus("rejected")}
              disabled={updatingStatus}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700 transition-colors disabled:opacity-50"
            >
              <XCircle className="h-4 w-4" />
              Reject Bid
            </button>
            <div className="w-px h-8 bg-border/50 mx-1" />
            <button
              onClick={() => setIsJudging(!isJudging)}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border transition-all text-sm font-semibold ${
                isJudging 
                  ? "bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/20" 
                  : "bg-secondary/50 text-foreground border-border hover:bg-secondary"
              }`}
            >
              <Gavel className={`h-4 w-4 ${isJudging ? "animate-bounce" : ""}`} />
              {isJudging ? "Exit Judging" : "Judge with PDF"}
            </button>
            <div className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full border text-emerald-400 bg-emerald-500/10 border-emerald-500/20">
              <span className="status-dot pass" />
              Eligible
            </div>
          </div>
        </div>
      </div>

      <div className={`grid gap-6 ${isJudging ? "grid-cols-1 lg:grid-cols-2" : "grid-cols-1"}`}>
        {/* Left Side: PDF Viewer (only in Judging mode) */}
        {isJudging && (
          <div className="space-y-4 h-[calc(100vh-250px)] sticky top-6">
            <div className="flex items-center gap-2 p-1 rounded-lg bg-secondary/50 border border-border/50 w-fit">
              <button
                onClick={() => setDocToView("tender")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  docToView === "tender" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Tender PDF
              </button>
              <button
                onClick={() => setDocToView("bidder")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  docToView === "bidder" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Bidder Documents
              </button>
            </div>
            <PdfViewer 
              url={docToView === "tender" ? tenderPdfUrl : bidderPdfUrl} 
              title={docToView === "tender" ? "Tender: CRPF/GC-BLR/ENGG/2025-26/CT-07" : "Bidder: Rajesh Kumar & Associates (Full Bundle)"}
              className="h-full"
            />
          </div>
        )}

        {/* Right Side: Evaluation Details */}
        <div className="space-y-6 overflow-y-auto max-h-full">
          {!isJudging && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-fade-in-up stagger-1">
              <div className="rounded-lg border border-border/30 bg-card/40 p-4 text-center">
                <p className="text-3xl font-bold text-emerald-400">{passCount}/{totalCount}</p>
                <p className="text-xs text-muted-foreground mt-1">Criteria Passed</p>
              </div>
              <div className="rounded-lg border border-border/30 bg-card/40 p-4 text-center">
                <p className="text-3xl font-bold">94%</p>
                <p className="text-xs text-muted-foreground mt-1">Avg Confidence</p>
              </div>
              <div className="rounded-lg border border-border/30 bg-card/40 p-4 text-center">
                <p className="text-3xl font-bold text-amber-400">13/25</p>
                <p className="text-xs text-muted-foreground mt-1">Optional Score</p>
              </div>
              <div className="rounded-lg border border-border/30 bg-card/40 p-4 text-center">
                <p className="text-3xl font-bold text-primary">14</p>
                <p className="text-xs text-muted-foreground mt-1">Documents</p>
              </div>
            </div>
          )}

          {/* View Tabs */}
          <div className="border-b border-border/30">
            <div className="flex items-center gap-1">
              {([
                { id: "verdicts" as ViewTab, label: "Verdict Details", icon: CheckCircle2 },
                { id: "payload" as ViewTab, label: "Evaluation Payload", icon: Code2 },
                { id: "summary" as ViewTab, label: "AI Summary", icon: Brain },
              ]).map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveView(id)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all ${
                    activeView === id
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Verdicts Tab */}
          {activeView === "verdicts" && (
            <div className="space-y-2">
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 mb-4">
                <h3 className="text-sm font-semibold text-emerald-500 mb-1">Judging Instructions</h3>
                <p className="text-xs text-muted-foreground">
                  Verify the AI-extracted values against the PDF on the left. Click on a criterion to see the specific source pages and quotes used for the verdict.
                </p>
              </div>
              {VERDICT_DETAILS.map((v) => (
                <div key={v.id} className="flex items-center gap-3 px-4 py-3 rounded-lg border border-border/30 bg-card/40 hover:bg-secondary/20 transition-colors cursor-pointer group">
                  <div className="shrink-0">
                    {v.status === "pass" && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                    {v.status === "fail" && <XCircle className="h-4 w-4 text-red-400" />}
                    {v.status === "review" && <AlertTriangle className="h-4 w-4 text-amber-400" />}
                  </div>
                  <span className="text-xs font-mono font-bold text-primary w-10">{v.id}</span>
                  <span className="text-sm flex-1">{v.label}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-24 h-1.5 rounded-full bg-secondary overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-1000 ${
                          v.confidence >= 90 ? "bg-emerald-400" : v.confidence >= 75 ? "bg-amber-400" : "bg-red-400"
                        }`}
                        style={{ width: `${v.confidence}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-muted-foreground w-10 text-right">{v.confidence}%</span>
                  </div>
                </div>
              ))}
              {/* Generate Summary Button */}
              {!summaryGenerated && (
                <div className="pt-4">
                  <button
                    onClick={handleGenerateSummary}
                    disabled={summaryLoading}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-primary to-blue-600 text-primary-foreground text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-60"
                  >
                    {summaryLoading ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Generating Analysis…</>
                    ) : (
                      <><Brain className="h-4 w-4" /> Generate Pramaan Analysis</>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Payload Tab (JSON) */}
          {activeView === "payload" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  Exact structured data computed by the Pramaan Reasoning Engine.
                </p>
                <button
                  onClick={handleCopyJson}
                  className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? "Copied!" : "Copy JSON"}
                </button>
              </div>
              <div className="json-viewer max-h-[600px] overflow-y-auto">
                <pre className="whitespace-pre-wrap">
                  <JsonHighlight data={EVALUATION_PAYLOAD} />
                </pre>
              </div>
            </div>
          )}

          {/* Summary Tab */}
          {activeView === "summary" && (
            <div>
              {summaryGenerated ? (
                <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-6 space-y-4">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground pb-3 border-b border-border/30">
                    <Brain className="h-3.5 w-3.5 text-primary" />
                    <span>Generated by Pramaan Analysis Engine · {new Date().toLocaleDateString()}</span>
                  </div>
                  <div className="prose prose-sm prose-invert max-w-none">
                    {AI_SUMMARY.split("\n").map((line, i) => {
                      if (line.startsWith("## ")) return <h2 key={i} className="text-lg font-bold mt-4 mb-2">{line.replace("## ", "")}</h2>;
                      if (line.startsWith("### ")) return <h3 key={i} className="text-sm font-bold mt-3 mb-1 text-primary">{line.replace("### ", "")}</h3>;
                      if (line.startsWith("- ")) return <li key={i} className="text-sm text-foreground/90 ml-4">{renderBold(line.replace("- ", ""))}</li>;
                      if (line.trim() === "") return <div key={i} className="h-2" />;
                      return <p key={i} className="text-sm text-foreground/90 leading-relaxed">{renderBold(line)}</p>;
                    })}
                  </div>
                </div>
              ) : (
                <div className="text-center py-16 text-muted-foreground">
                  <Brain className="h-12 w-12 mx-auto mb-3 text-muted-foreground/30" />
                  <p className="text-sm font-medium">Summary not yet generated</p>
                  <p className="text-xs mt-1">Go to Verdict Details tab and click &quot;Generate Pramaan Analysis&quot;</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── JSON Syntax Highlighting ─────────────────────────────────────────
function JsonHighlight({ data }: { data: unknown }) {
  const json = JSON.stringify(data, null, 2);
  const parts = json.split(/("(?:[^"\\]|\\.)*")\s*:/g);

  return (
    <code>
      {json.split("\n").map((line, i) => (
        <div key={i} className="hover:bg-white/5 px-1 -mx-1 rounded">
          {highlightLine(line)}
        </div>
      ))}
    </code>
  );
}

function highlightLine(line: string): React.ReactNode {
  // Highlight JSON keys, strings, numbers, booleans
  return line.split(/("(?:[^"\\]|\\.)*")/).map((part, i) => {
    if (part.startsWith('"') && part.endsWith('"')) {
      // Check if it's a key (followed by ':') or a value
      const isKey = line.indexOf(part + ":") !== -1 || line.indexOf(part + " :") !== -1;
      return (
        <span key={i} className={isKey ? "json-key" : "json-string"}>
          {part}
        </span>
      );
    }
    // Highlight numbers and booleans in non-string parts
    return part.split(/(\b\d+\.?\d*\b|true|false|null)/g).map((sub, j) => {
      if (/^\d+\.?\d*$/.test(sub)) return <span key={`${i}-${j}`} className="json-number">{sub}</span>;
      if (sub === "true" || sub === "false") return <span key={`${i}-${j}`} className="json-boolean">{sub}</span>;
      if (sub === "null") return <span key={`${i}-${j}`} className="json-null">{sub}</span>;
      return <span key={`${i}-${j}`}>{sub}</span>;
    });
  });
}

function renderBold(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? (
      <strong key={i} className="font-semibold text-foreground">{p.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{p}</span>
    )
  );
}
