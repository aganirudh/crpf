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
} from "lucide-react";

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
  {
    title: "Compliance & Statutory",
    type: "compliance",
    mandatory: true,
    criteria: [
      { id: "C-1", text: "Valid GST Registration Certificate. The GSTIN must be active and the same as that in financial documents submitted", mandatory: true, status: "pass" },
      { id: "C-2", text: "Valid Provident Fund (PF) registration under Employees Provident Fund Organisation — valid establishment code must be provided", mandatory: true, status: "pass" },
      { id: "C-3", text: "Valid Employees State Insurance (ESI) registration certificate", mandatory: true, status: "pass" },
      { id: "C-4", text: "PAN Card of the firm/company issued by Income Tax Department of India", mandatory: true, status: "pass" },
      { id: "C-5", text: "The firm must not be blacklisted or debarred by any Central/State Government department or autonomous body", mandatory: true, status: "pass" },
      { id: "C-6", text: "Registration with Central/State PWD, CPWD, MES or any equivalent government body as a contractor in the appropriate class", mandatory: true, status: "review" },
    ],
  },
  {
    title: "Optional Criteria (Technical Scoring)",
    type: "optional",
    mandatory: false,
    criteria: [
      { id: "O-1", text: "ISO 14001:2015 Environmental Management System certification — valid on date of submission", mandatory: false, maxMarks: 5, scored: 5 },
      { id: "O-2", text: "OHSAS 45001:2018 Occupational Health & Safety certification — valid on date of submission", mandatory: false, maxMarks: 5, scored: 0 },
      { id: "O-3", text: "Experience in construction projects for Central Government / Defence establishments", mandatory: false, maxMarks: 10, scored: 8 },
      { id: "O-4", text: "LEED or GRIHA rated green building project in portfolio", mandatory: false, maxMarks: 5, scored: 0 },
    ],
  },
];

const DOCUMENT_CHECKLIST = [
  { id: "D-01", description: "Bid Submission Form (Annexure A) on company letterhead, signed & stamped by authorised signatory" },
  { id: "D-02", description: "Audited Balance Sheets and Profit & Loss Accounts for FY 2021-22, 2022-23, 2023-24" },
  { id: "D-03", description: "CA Certificate confirming Average Annual Turnover from construction activities for last 3 FYs" },
  { id: "D-04", description: "Completion Certificates for all similar projects claimed under T-1 and T-2" },
  { id: "D-05", description: "List of key technical staff with qualifications and experience; supported by appointment letters" },
  { id: "D-06", description: "Equipment list with ownership/lease proof for all items claimed under T-4" },
  { id: "D-07", description: "ISO 9001:2015 Certificate (mandatory); ISO 14001 / OHSAS 45001 if applicable" },
  { id: "D-08", description: "GST Registration Certificate (Form REG-06)" },
  { id: "D-09", description: "PF Registration Certificate (EPFO Establishment Code)" },
  { id: "D-10", description: "ESI Registration Certificate" },
  { id: "D-11", description: "PAN Card copy of firm" },
  { id: "D-12", description: "Registration Certificate with PWD / CPWD / MES or equivalent government body" },
  { id: "D-13", description: "Non-Blacklisting / Self-Declaration Certificate (Annexure B) on company letterhead" },
  { id: "D-14", description: "Earnest Money Deposit (EMD) of Rs. 37,00,000/- in the form of Demand Draft / Bank Guarantee" },
  { id: "D-15", description: "Power of Attorney in favour of the authorised signatory, if bid is signed by a person other than the company director" },
];

const SAMPLE_BIDDERS = [
  { id: "b1", name: "Rajesh Kumar & Associates", status: "eligible", score: 87, docs: 14 },
  { id: "b2", name: "National Builders Pvt Ltd", status: "not_eligible", score: 42, docs: 12 },
  { id: "b3", name: "Heritage Construction Co.", status: "manual_review", score: 68, docs: 15 },
  { id: "b4", name: "Modi Infrastructure Ltd", status: "pending", score: 0, docs: 8 },
];

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

type TabId = "criteria" | "checklist" | "bidders";

export default function AdminTenderDetailPage() {
  const router = useRouter();
  const params = useParams();
  const [activeTab, setActiveTab] = React.useState<TabId>("criteria");
  const [expandedSections, setExpandedSections] = React.useState<Set<string>>(
    new Set(CRITERIA_SECTIONS.map((s) => s.title))
  );

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
    { id: "bidders", label: "Bidders", icon: Users, count: SAMPLE_BIDDERS.length },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
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
          <div className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border text-amber-400 bg-amber-500/10 border-amber-500/20 shrink-0">
            <span className="status-dot review" />
            Evaluating
          </div>
        </div>
      </div>

      {/* Tender Metadata */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-fade-in-up stagger-1">
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
      <div className="border-b border-border/30 animate-fade-in-up stagger-2">
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

      {/* Tab Content */}
      {activeTab === "criteria" && (
        <div className="space-y-4 animate-fade-in">
          {CRITERIA_SECTIONS.map((section) => {
            const isExpanded = expandedSections.has(section.title);
            const typeIcons: Record<string, React.ElementType> = {
              financial: Building2,
              technical: Award,
              compliance: Shield,
              optional: Sparkles,
            };
            const SectionIcon = typeIcons[section.type] || ClipboardCheck;

            return (
              <div key={section.title} className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden">
                <button
                  onClick={() => toggleSection(section.title)}
                  className="w-full flex items-center gap-3 p-4 hover:bg-secondary/30 transition-colors"
                >
                  <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${
                    section.mandatory ? "bg-primary/10" : "bg-amber-500/10"
                  }`}>
                    <SectionIcon className={`h-4 w-4 ${section.mandatory ? "text-primary" : "text-amber-400"}`} />
                  </div>
                  <div className="flex-1 text-left">
                    <p className="text-sm font-semibold">{section.title}</p>
                    <p className="text-xs text-muted-foreground">{section.criteria.length} criteria · {section.mandatory ? "MANDATORY" : "OPTIONAL"}</p>
                  </div>
                  {isExpanded ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                </button>
                {isExpanded && (
                  <div className="border-t border-border/30">
                    {section.criteria.map((c, i) => (
                      <div key={c.id} className="flex items-start gap-3 px-4 py-3 border-b border-border/20 last:border-b-0 hover:bg-secondary/20 transition-colors">
                        <div className="shrink-0 mt-0.5">
                          {"status" in c && c.status === "pass" && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                          {"status" in c && c.status === "fail" && <XCircle className="h-4 w-4 text-red-400" />}
                          {"status" in c && c.status === "review" && <AlertTriangle className="h-4 w-4 text-amber-400" />}
                          {!("status" in c) && <BadgeCheck className="h-4 w-4 text-muted-foreground" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-bold text-primary">{c.id}</span>
                            {c.mandatory && (
                              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                                MANDATORY
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-foreground/90 mt-1 leading-relaxed">{c.text}</p>
                          {"maxMarks" in c && (
                            <div className="flex items-center gap-3 mt-1.5">
                              <span className="text-xs text-muted-foreground">Max: {c.maxMarks} marks</span>
                              {"scored" in c && typeof c.scored === "number" && (
                                <span className={`text-xs font-semibold ${c.scored > 0 ? "text-emerald-400" : "text-muted-foreground"}`}>
                                  Scored: {c.scored}/{c.maxMarks}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {activeTab === "checklist" && (
        <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden animate-fade-in">
          <div className="p-4 border-b border-border/30">
            <h3 className="text-sm font-semibold">Mandatory Submission Documents</h3>
            <p className="text-xs text-muted-foreground mt-0.5">{DOCUMENT_CHECKLIST.length} documents required</p>
          </div>
          {DOCUMENT_CHECKLIST.map((doc, i) => (
            <div key={doc.id} className="flex items-start gap-3 px-4 py-3 border-b border-border/20 last:border-b-0 hover:bg-secondary/20 transition-colors">
              <span className="text-xs font-mono font-bold text-primary shrink-0 w-10 mt-0.5">{doc.id}</span>
              <p className="text-sm text-foreground/90 leading-relaxed">{doc.description}</p>
            </div>
          ))}
        </div>
      )}

      {activeTab === "bidders" && (
        <div className="space-y-3 animate-fade-in">
          {SAMPLE_BIDDERS.map((bidder) => {
            const statusMap: Record<string, { label: string; class: string; dotClass: string }> = {
              eligible: { label: "Eligible", class: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", dotClass: "pass" },
              not_eligible: { label: "Not Eligible", class: "text-red-400 bg-red-500/10 border-red-500/20", dotClass: "fail" },
              manual_review: { label: "Under Review", class: "text-amber-400 bg-amber-500/10 border-amber-500/20", dotClass: "review" },
              pending: { label: "Pending", class: "text-muted-foreground bg-secondary border-border", dotClass: "pending" },
            };
            const sc = statusMap[bidder.status] || statusMap.pending;
            return (
              <Link key={bidder.id} href={`/admin/tenders/${params.tenderId}/bidders/${bidder.id}`}>
                <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-4 card-hover cursor-pointer">
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
                      {bidder.score > 0 && (
                        <p className="text-xs text-muted-foreground">Score: {bidder.score}/100</p>
                      )}
                    </div>
                    <ChevronRight className="h-5 w-5 text-muted-foreground/30 shrink-0" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
