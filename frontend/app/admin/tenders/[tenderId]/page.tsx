"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  FileText,
  ClipboardCheck,
  Users,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Eye,
  ChevronDown,
  ChevronRight,
  Shield,
  Award,
  Building2,
  ScrollText,
  BadgeCheck,
  Sparkles,
  Loader2,
  Code2,
  BarChart3,
  Trophy,
} from "lucide-react";
import { PdfViewer } from "@/components/pdf-viewer";

// ─── Sample Criteria (matching the tender images) ─────────────────────
const CRITERIA_SECTIONS = [
  {
    title: "Financial Eligibility",
    type: "financial",
    mandatory: true,
    criteria: [
      { id: "F-1", text: "Average Annual Turnover of the firm in last 3 financial years (FY 2021-22, 2022-23, 2023-24) from construction activities shall be at least Rs. 1 Crore", mandatory: true, status: "pass" },
      { id: "F-2", text: "Net Worth of the firm as on 31 March 2024 must be positive (i.e., total assets must exceed total liabilities as per audited balance sheet)", mandatory: true, status: "pass" },
      { id: "F-3", text: "The firm must not have incurred losses in more than one of the last three financial years (FY 2021-22, 2022-23, 2023-24)", mandatory: true, status: "review" },
    ],
  },
  {
    title: "Technical Eligibility",
    type: "technical",
    mandatory: true,
    criteria: [
      { id: "T-1", text: "The firm must have successfully completed at least 3 (three) similar construction projects in last 7 years (i.e., on or after 01 May 2018)", mandatory: true, status: "pass" },
      { id: "T-2", text: "At least one of the completed similar projects (T-1 above) must have had a contract value of ₹2 Crore or more", mandatory: true, status: "fail" },
      { id: "T-3", text: "The firm must have a registered Civil/Structural Engineer on payroll with a minimum of 5 years post-qualification experience", mandatory: true, status: "pass" },
      { id: "T-4", text: "The firm must own or have assured access to key construction equipment: Tower Crane, Transit Mixer (min 6m³), Batching Plant", mandatory: true, status: "review" },
      { id: "T-5", text: "ISO 9001:2015 Quality Management System certification from an accredited certifying body — certificate must be valid on date of submission", mandatory: true, status: "pass" },
    ],
  },
];

const DOCUMENT_CHECKLIST = [
  { id: "P-01", description: "Main Bid Proposal (Technical + Financial)" },
];

const SAMPLE_BIDDERS = []; // Empty by default for demo

const TENDER_META = {
  reference: "CRPF/GC-BLR/ENGG/2025-26/CT-07",
  title: "Construction of Barrack Complex & Utility Infrastructure",
  issueDate: "01 May 2025",
  submissionDeadline: "31 May 2025 (17:00 hrs IST)",
  projectValue: "Rs. 18,50,00,000/- (Eighteen Crore Fifty Lakh)",
  emd: "Rs. 37,00,000/- (Thirty-Seven Lakh)",
  performanceSecurity: "5% of contract value on award",
  contractDuration: "24 months from date of work order",
  modeOfSubmission: "Physical submission at CRPF Group Centre, Bengaluru",
};

type TabId = "criteria" | "checklist" | "bidders" | "comparative";

export default function AdminTenderDetailPage() {
  const router = useRouter();
  const params = useParams();
  const [activeTab, setActiveTab] = React.useState<TabId>("criteria");
  const [showPdf, setShowPdf] = React.useState(false);
  const [bidders, setBidders] = React.useState<any[]>([]);
  const [loadingBidders, setLoadingBidders] = React.useState(true);
  const [expandedSections, setExpandedSections] = React.useState<Set<string>>(
    new Set(CRITERIA_SECTIONS.map((s) => s.title))
  );

  const tenderId = params.tenderId as string;
  const pdfUrl = `/api/v1/tenders/${tenderId}/source`;

  const fetchBidders = React.useCallback(async () => {
    try {
      const resp = await fetch(`/api/v1/tenders/${tenderId}/bidders`);
      if (!resp.ok) throw new Error("Failed to fetch bidders");
      const data = await resp.json();
      setBidders(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setBidders([]);
    } finally {
      setLoadingBidders(false);
    }
  }, [tenderId]);

  React.useEffect(() => {
    fetchBidders();
    const interval = setInterval(fetchBidders, 5000);
    return () => clearInterval(interval);
  }, [fetchBidders]);

  const toggleSection = (title: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(title)) next.delete(title);
      else next.add(title);
      return next;
    });
  };

  const tabs: { id: TabId; label: string; icon: React.ElementType; count?: number }[] = [
    { id: "criteria", label: "Criteria", icon: ClipboardCheck, count: CRITERIA_SECTIONS.reduce((a, s) => a + s.criteria.length, 0) },
    { id: "checklist", label: "Document Checklist", icon: ScrollText, count: DOCUMENT_CHECKLIST.length },
    { id: "bidders", label: "Bidders", icon: Users, count: bidders.length },
    { id: "comparative", label: "Comparative Statement", icon: BarChart3 },
  ];

  const displayBidders = (Array.isArray(bidders) ? bidders : []).map(b => ({
    ...b,
    name: b.legal_name || "Unknown Bidder",
    docs: b.n_documents,
    status: b.selection_status === "accepted" ? "eligible" : b.selection_status === "rejected" ? "not_eligible" : (b.n_documents > 0 ? "processing" : "pending"),
    score: b.score || 0
  }));

  const sortedBidders = [...displayBidders].sort((a, b) => (b.score || 0) - (a.score || 0));
  const bestBidder = sortedBidders.length > 0 ? sortedBidders[0] : null;

  return (
    <div className={`p-6 max-w-7xl mx-auto space-y-6 ${showPdf ? "max-w-none" : ""}`}>
      {/* Back + Title */}
      <div className="animate-fade-in-up">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Tenders
        </button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold">{TENDER_META.title}</h1>
            <p className="text-sm text-muted-foreground mt-1 font-mono">{TENDER_META.reference}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowPdf(!showPdf)}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border transition-all text-sm font-semibold ${
                showPdf 
                  ? "bg-blue-600 text-white border-blue-600 shadow-lg shadow-blue-500/20" 
                  : "bg-secondary/50 text-foreground border-border hover:bg-secondary"
              }`}
            >
              <FileText className="h-4 w-4" />
              {showPdf ? "Hide Tender PDF" : "View Tender PDF"}
            </button>
            <div className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border text-amber-400 bg-amber-500/10 border-amber-500/20 shrink-0">
              <span className="status-dot review" />
              Live Evaluation
            </div>
          </div>
        </div>
      </div>

      <div className={`grid gap-6 ${showPdf ? "grid-cols-1 lg:grid-cols-2" : "grid-cols-1"}`}>
        {/* Left Side: PDF Viewer */}
        {showPdf && (
          <div className="h-[calc(100vh-250px)] sticky top-6">
            <PdfViewer 
              url={pdfUrl} 
              title="CRPF Tender Document" 
              className="h-full"
            />
          </div>
        )}

        {/* Right Side: Tab Content */}
        <div className="space-y-6 overflow-y-auto max-h-full">
          {/* Metadata */}
          <div className={`grid gap-3 animate-fade-in-up stagger-1 ${showPdf ? "grid-cols-2" : "grid-cols-2 md:grid-cols-4"}`}>
            {[
              { label: "Project Value", value: "₹18.50 Cr", icon: Building2 },
              { label: "EMD Required", value: "₹37.00 L", icon: Shield },
              { label: "Submission Deadline", value: "31 May 2025", icon: FileText },
              { label: "Duration", value: "24 Months", icon: Award },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-lg border border-border/30 bg-card/40 p-3 space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </div>
                <p className="text-sm font-semibold">{value}</p>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div className="border-b border-border/30">
            <div className="flex items-center gap-1">
              {tabs.map(({ id, label, icon: Icon, count }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all ${
                    activeTab === id
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                  {count !== undefined && (
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                      activeTab === id ? "bg-primary/10 text-primary" : "bg-secondary text-muted-foreground"
                    }`}>
                      {count}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Criteria Tab */}
          {activeTab === "criteria" && (
            <div className="space-y-4 animate-fade-in">
              <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                <h3 className="text-sm font-semibold text-blue-400 mb-1">Criterion Review</h3>
                <p className="text-xs text-muted-foreground">
                  Extracted requirements from the tender document. Bidders must satisfy all MANDATORY fields.
                </p>
              </div>
              {CRITERIA_SECTIONS.map((section) => (
                <div key={section.title} className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden">
                  <button onClick={() => toggleSection(section.title)} className="w-full flex items-center gap-3 p-4 hover:bg-secondary/30 transition-colors">
                    <p className="text-sm font-semibold flex-1 text-left">{section.title}</p>
                    {expandedSections.has(section.title) ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </button>
                  {expandedSections.has(section.title) && (
                    <div className="border-t border-border/30">
                      {section.criteria.map((c) => (
                        <div key={c.id} className="p-4 border-b border-border/20 last:border-b-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-mono font-bold text-primary">{c.id}</span>
                            {c.mandatory && <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">MANDATORY</span>}
                          </div>
                          <p className="text-sm text-foreground/90 leading-relaxed">{c.text}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Checklist Tab */}
          {activeTab === "checklist" && (
            <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden animate-fade-in">
              <div className="p-4 border-b border-border/30">
                <h3 className="text-sm font-semibold text-foreground/80">Submission Requirements</h3>
              </div>
              {DOCUMENT_CHECKLIST.map((doc) => (
                <div key={doc.id} className="p-4 border-b border-border/20 last:border-b-0 flex gap-3">
                  <span className="text-xs font-mono font-bold text-primary mt-0.5">{doc.id}</span>
                  <p className="text-sm text-foreground/90">{doc.description}</p>
                </div>
              ))}
            </div>
          )}

          {/* Bidders Tab */}
          {activeTab === "bidders" && (
            <div className="space-y-3 animate-fade-in">
              {displayBidders.length === 0 ? (
                <div className="text-center py-20 border-2 border-dashed border-border/30 rounded-xl bg-secondary/5">
                  <Users className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
                  <p className="text-sm font-medium text-foreground/70">Awaiting Bidder Submissions</p>
                  <p className="text-xs text-muted-foreground mt-1">Bidders will appear here in real-time as they upload proposals.</p>
                </div>
              ) : displayBidders.map((bidder) => {
                const statusMap: Record<string, { label: string; class: string; dotClass: string }> = {
                  eligible: { label: "Accepted", class: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", dotClass: "pass" },
                  not_eligible: { label: "Rejected", class: "text-red-400 bg-red-500/10 border-red-500/20", dotClass: "fail" },
                  processing: { label: "AI Extracting...", class: "text-blue-400 bg-blue-500/10 border-blue-500/20 animate-pulse", dotClass: "review" },
                  pending: { label: "Waiting for Docs", class: "text-muted-foreground bg-secondary border-border", dotClass: "pending" },
                };
                const sc = statusMap[bidder.status] || statusMap.pending;
                return (
                  <Link key={bidder.id} href={`/admin/tenders/${params.tenderId}/bidders/${bidder.id}`}>
                    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-4 card-hover">
                      <div className="flex items-center gap-4">
                        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                          <Users className="h-5 w-5 text-primary/60" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold">{bidder.name}</p>
                          <p className="text-xs text-muted-foreground">{bidder.docs} documents submitted</p>
                        </div>
                        <div className="text-right shrink-0 space-y-1">
                          <div className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${sc.class}`}>
                            <span className={`status-dot ${sc.dotClass}`} />
                            {sc.label}
                          </div>
                          {bidder.score > 0 && <p className="text-xs text-muted-foreground">Score: {bidder.score}/100</p>}
                        </div>
                        <ChevronRight className="h-5 w-5 text-muted-foreground/30 shrink-0" />
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}

          {/* Comparative Tab */}
          {activeTab === "comparative" && (
            <div className="space-y-6 animate-fade-in">
              {!bestBidder || bestBidder.score === 0 ? (
                <div className="text-center py-20 border-2 border-dashed border-border/30 rounded-xl bg-secondary/5">
                  <BarChart3 className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
                  <p className="text-sm font-medium text-foreground/70">Comparative Analysis Pending</p>
                  <p className="text-xs text-muted-foreground mt-1">Submit and parse at least one bidder proposal to generate rankings.</p>
                </div>
              ) : (
                <>
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-6 flex items-center gap-6 shadow-[0_0_40px_rgba(16,185,129,0.05)]">
                    <div className="h-16 w-16 rounded-full bg-emerald-500 flex items-center justify-center">
                      <Trophy className="h-8 w-8 text-white animate-pulse" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-emerald-500 uppercase tracking-widest mb-1">AI Recommendation: Best Value Bidder</p>
                      <h2 className="text-2xl font-bold text-foreground">{bestBidder.name}</h2>
                      <p className="text-sm text-muted-foreground mt-1">
                        Highest technical score of <strong>{bestBidder.score}/100</strong> and 100% mandatory compliance.
                      </p>
                    </div>
                  </div>
                  <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="bg-secondary/30 border-b border-border/30">
                          <th className="text-left p-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">Bidder Name</th>
                          <th className="text-center p-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">Compliance</th>
                          <th className="text-center p-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">Tech Score</th>
                          <th className="text-right p-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/20">
                        {sortedBidders.map((bidder, idx) => (
                          <tr key={bidder.id} className="hover:bg-secondary/10 transition-colors text-sm">
                            <td className="p-4 font-semibold">{idx + 1}. {bidder.name}</td>
                            <td className="p-4 text-center">
                              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold">100%</span>
                            </td>
                            <td className="p-4 text-center font-bold text-primary">{bidder.score}</td>
                            <td className="p-4 text-right">
                              <Link href={`/admin/tenders/${params.tenderId}/bidders/${bidder.id}`} className="text-xs text-primary hover:underline font-semibold">View Details</Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
