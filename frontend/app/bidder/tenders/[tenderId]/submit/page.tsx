"use client";

import * as React from "react";
import { Upload, CheckCircle2, FileText, AlertCircle, X, Loader2 } from "lucide-react";
import { toast } from "sonner";

const DOCUMENT_CHECKLIST = [
  { id: "D-01", description: "Bid Submission Form (Annexure A) on company letterhead", required: true, status: "uploaded", filename: "annexure_a_signed.pdf" },
  { id: "D-02", description: "Audited Balance Sheets (FY 21-22, 22-23, 23-24)", required: true, status: "uploaded", filename: "balance_sheets_3yrs.pdf" },
  { id: "D-03", description: "CA Certificate for Turnover", required: true, status: "uploaded", filename: "ca_certificate_turnover.pdf" },
  { id: "D-04", description: "Completion Certificates for similar projects", required: true, status: "uploaded", filename: "project_completion_certs.pdf" },
  { id: "D-05", description: "List of key technical staff with qualifications", required: true, status: "uploaded", filename: "technical_staff_details.pdf" },
  { id: "D-06", description: "Equipment list with ownership proof", required: true, status: "uploaded", filename: "equipment_ownership.pdf" },
  { id: "D-07", description: "ISO 9001:2015 Certificate", required: true, status: "uploaded", filename: "iso_9001_cert.pdf" },
  { id: "D-08", description: "GST Registration Certificate", required: true, status: "uploaded", filename: "gst_certificate.pdf" },
  { id: "D-09", description: "PF Registration Certificate", required: true, status: "uploaded", filename: "pf_registration.pdf" },
  { id: "D-10", description: "ESI Registration Certificate", required: true, status: "uploaded", filename: "esi_certificate.pdf" },
  { id: "D-11", description: "PAN Card copy", required: true, status: "uploaded", filename: "pan_card_copy.pdf" },
  { id: "D-12", description: "Registration with PWD / CPWD / MES", required: true, status: "uploaded", filename: "cpwd_registration.pdf" },
  { id: "D-13", description: "Non-Blacklisting Certificate", required: true, status: "uploaded", filename: "non_blacklisting_decl.pdf" },
  { id: "D-14", description: "Earnest Money Deposit (EMD)", required: true, status: "uploaded", filename: "emd_bg_scan.pdf" },
  { id: "D-15", description: "Power of Attorney (if applicable)", required: false, status: "missing", filename: null },
];

export default function BidderTenderSubmitPage() {
  const [documents, setDocuments] = React.useState(DOCUMENT_CHECKLIST);
  const [uploadingId, setUploadingId] = React.useState<string | null>(null);
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [targetDocId, setTargetDocId] = React.useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && targetDocId) {
      setUploadingId(targetDocId);
      // Simulate upload delay
      setTimeout(() => {
        setDocuments(docs => docs.map(d => 
          d.id === targetDocId 
            ? { ...d, status: "uploaded", filename: file.name }
            : d
        ));
        setUploadingId(null);
        setTargetDocId(null);
        toast.success("Document uploaded successfully");
        if (fileRef.current) fileRef.current.value = "";
      }, 1500);
    }
  };

  const triggerUpload = (id: string) => {
    setTargetDocId(id);
    fileRef.current?.click();
  };

  const removeDoc = (id: string) => {
    setDocuments(docs => docs.map(d => 
      d.id === id ? { ...d, status: "missing", filename: null } : d
    ));
  };

  const uploadedCount = documents.filter(d => d.status === "uploaded").length;
  const requiredCount = documents.filter(d => d.required).length;
  const progress = Math.round((uploadedCount / documents.length) * 100);

  return (
    <div className="space-y-6">
      <input 
        type="file" 
        className="hidden" 
        ref={fileRef} 
        accept="application/pdf"
        onChange={handleFileChange}
      />

      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-6">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="text-lg font-semibold">Submission Progress</h3>
            <p className="text-sm text-muted-foreground">{uploadedCount} of {documents.length} documents uploaded</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-emerald-500">{progress}%</p>
          </div>
        </div>
        <div className="w-full h-2 rounded-full bg-secondary overflow-hidden">
          <div 
            className="h-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        {uploadedCount < requiredCount && (
          <div className="mt-4 flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-500/90 text-sm">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <p>You still need to upload {requiredCount - documents.filter(d => d.required && d.status === "uploaded").length} mandatory documents before final submission.</p>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden">
        <div className="p-4 border-b border-border/30 bg-secondary/10">
          <h3 className="text-sm font-semibold">Document Checklist</h3>
        </div>
        <div className="divide-y divide-border/20">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between p-4 hover:bg-secondary/20 transition-colors">
              <div className="flex items-start gap-3 flex-1 pr-4">
                <div className="mt-0.5">
                  {doc.status === "uploaded" ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                  ) : doc.required ? (
                    <AlertCircle className="h-5 w-5 text-amber-500" />
                  ) : (
                    <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-emerald-500">{doc.id}</span>
                    {doc.required && (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                        MANDATORY
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-foreground/90 mt-1">{doc.description}</p>
                  {doc.status === "uploaded" && doc.filename && (
                    <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1.5">
                      <FileText className="h-3.5 w-3.5" />
                      {doc.filename}
                    </p>
                  )}
                </div>
              </div>
              <div className="shrink-0">
                {uploadingId === doc.id ? (
                  <button disabled className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-secondary/50 text-xs font-medium opacity-70">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> Uploading...
                  </button>
                ) : doc.status === "uploaded" ? (
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => triggerUpload(doc.id)}
                      className="px-3 py-1.5 rounded-lg border border-border hover:bg-secondary transition-colors text-xs font-medium"
                    >
                      Replace
                    </button>
                    <button 
                      onClick={() => removeDoc(doc.id)}
                      className="p-1.5 rounded-lg border border-transparent hover:bg-red-500/10 hover:text-red-400 transition-colors"
                      title="Remove document"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <button 
                    onClick={() => triggerUpload(doc.id)}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors text-xs font-medium"
                  >
                    <Upload className="h-3.5 w-3.5" /> Upload
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
