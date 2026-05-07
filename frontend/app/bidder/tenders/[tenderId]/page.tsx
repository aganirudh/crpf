"use client";

import * as React from "react";
import {
  ClipboardCheck,
  ChevronDown,
  ChevronRight,
  Shield,
  Award,
  Building2,
  Sparkles,
  BadgeCheck
} from "lucide-react";

// Same criteria as Admin view, but read-only for bidder
const CRITERIA_SECTIONS = [
  {
    title: "Financial Eligibility",
    type: "financial",
    mandatory: true,
    criteria: [
      { id: "F-1", text: "Average Annual Turnover of the firm in last 3 financial years (FY 2021-22, 2022-23, 2023-24) from construction activities shall be at least Rs. 1 Crore", mandatory: true },
      { id: "F-2", text: "Net Worth of the firm as on 31 March 2024 must be positive (i.e., total assets must exceed total liabilities as per audited balance sheet)", mandatory: true },
      { id: "F-3", text: "The firm must not have incurred losses in more than one of the last three financial years (FY 2021-22, 2022-23, 2023-24)", mandatory: true },
    ],
  },
  {
    title: "Technical Eligibility",
    type: "technical",
    mandatory: true,
    criteria: [
      { id: "T-1", text: "The firm must have successfully completed at least 3 (three) similar construction projects in last 7 years (i.e., on or after 01 May 2018)", mandatory: true },
      { id: "T-2", text: "At least one of the completed similar projects (T-1 above) must have had a contract value of ₹2 Crore or more", mandatory: true },
      { id: "T-3", text: "The firm must have a registered Civil/Structural Engineer on payroll with a minimum of 5 years post-qualification experience", mandatory: true },
      { id: "T-4", text: "The firm must own or have assured access to key construction equipment: Tower Crane, Transit Mixer (min 6m³), Batching Plant", mandatory: true },
      { id: "T-5", text: "ISO 9001:2015 Quality Management System certification from an accredited certifying body — certificate must be valid on date of submission", mandatory: true },
    ],
  },
  {
    title: "Compliance & Statutory",
    type: "compliance",
    mandatory: true,
    criteria: [
      { id: "C-1", text: "Valid GST Registration Certificate. The GSTIN must be active and the same as that in financial documents submitted", mandatory: true },
      { id: "C-2", text: "Valid Provident Fund (PF) registration under Employees Provident Fund Organisation — valid establishment code must be provided", mandatory: true },
      { id: "C-3", text: "Valid Employees State Insurance (ESI) registration certificate", mandatory: true },
      { id: "C-4", text: "PAN Card of the firm/company issued by Income Tax Department of India", mandatory: true },
      { id: "C-5", text: "The firm must not be blacklisted or debarred by any Central/State Government department or autonomous body", mandatory: true },
      { id: "C-6", text: "Registration with Central/State PWD, CPWD, MES or any equivalent government body as a contractor in the appropriate class", mandatory: true },
    ],
  },
  {
    title: "Optional Criteria (Technical Scoring)",
    type: "optional",
    mandatory: false,
    criteria: [
      { id: "O-1", text: "ISO 14001:2015 Environmental Management System certification — valid on date of submission", mandatory: false, maxMarks: 5 },
      { id: "O-2", text: "OHSAS 45001:2018 Occupational Health & Safety certification — valid on date of submission", mandatory: false, maxMarks: 5 },
      { id: "O-3", text: "Experience in construction projects for Central Government / Defence establishments", mandatory: false, maxMarks: 10 },
      { id: "O-4", text: "LEED or GRIHA rated green building project in portfolio", mandatory: false, maxMarks: 5 },
    ],
  },
];

export default function BidderTenderCriteriaPage() {
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

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 mb-6">
        <h3 className="text-sm font-semibold text-emerald-500 mb-1">Eligibility Criteria</h3>
        <p className="text-xs text-muted-foreground">
          These criteria have been automatically extracted from the tender document by PRAMAAN. 
          Ensure your submitted documents provide clear evidence for each of these requirements.
        </p>
      </div>

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
                section.mandatory ? "bg-emerald-500/10" : "bg-amber-500/10"
              }`}>
                <SectionIcon className={`h-4 w-4 ${section.mandatory ? "text-emerald-500" : "text-amber-400"}`} />
              </div>
              <div className="flex-1 text-left">
                <p className="text-sm font-semibold">{section.title}</p>
                <p className="text-xs text-muted-foreground">{section.criteria.length} criteria · {section.mandatory ? "MANDATORY" : "OPTIONAL"}</p>
              </div>
              {isExpanded ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
            </button>
            {isExpanded && (
              <div className="border-t border-border/30">
                {section.criteria.map((c) => (
                  <div key={c.id} className="flex items-start gap-3 px-4 py-3 border-b border-border/20 last:border-b-0 hover:bg-secondary/20 transition-colors">
                    <div className="shrink-0 mt-0.5">
                      <BadgeCheck className="h-4 w-4 text-muted-foreground/50" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-emerald-500">{c.id}</span>
                        {c.mandatory && (
                          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                            MANDATORY
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-foreground/90 mt-1 leading-relaxed">{c.text}</p>
                      {"maxMarks" in c && (
                        <div className="flex items-center gap-3 mt-1.5">
                          <span className="text-xs text-muted-foreground font-medium">Max: {c.maxMarks} marks</span>
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
  );
}
