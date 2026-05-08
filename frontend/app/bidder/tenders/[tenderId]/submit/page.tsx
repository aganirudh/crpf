"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Upload, CheckCircle2, FileText, AlertCircle, X, Loader2, Info, Mail, ArrowRight } from "lucide-react";
import { toast } from "sonner";

const DOCUMENT_CHECKLIST = [
  { id: "P-01", description: "Main Bid Proposal (Technical + Financial)", required: true, status: "missing", filename: null },
];

export default function BidderTenderSubmitPage() {
  const params = useParams();
  const [email, setEmail] = React.useState("");
  const [isLoggedIn, setIsLoggedIn] = React.useState(false);
  const [bidder, setBidder] = React.useState<any>(null);
  const [documents, setDocuments] = React.useState(DOCUMENT_CHECKLIST);
  const [uploadingId, setUploadingId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [targetDocId, setTargetDocId] = React.useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      toast.error("Please enter a valid email address");
      return;
    }

    setLoading(true);
    try {
      // For the demo, we search if a bidder with this "email" (legal_name) already exists for this tender
      const listResp = await fetch(`/api/v1/tenders/${params.tenderId}/bidders`);
      const allBidders = await listResp.json();
      
      let currentBidder = Array.isArray(allBidders) ? allBidders.find(b => b.legal_name === email) : null;

      if (!currentBidder) {
        // Create new bidder with email as name
        const createResp = await fetch(`/api/v1/tenders/${params.tenderId}/bidders`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ legal_name: email })
        });
        if (!createResp.ok) throw new Error("Failed to create bidder session");
        currentBidder = await createResp.json();
      }

      setBidder(currentBidder);
      
      // Load documents for THIS specific bidder
      const docsResp = await fetch(`/api/v1/bidders/${currentBidder.id}/documents`);
      const uploadedDocs = await docsResp.json();
      
      if (Array.isArray(uploadedDocs) && uploadedDocs.length > 0) {
        setDocuments([{
          id: "P-01",
          description: "Main Bid Proposal (Technical + Financial)",
          required: true,
          status: "uploaded",
          filename: uploadedDocs[0].filename
        }]);
      } else {
        setDocuments(DOCUMENT_CHECKLIST);
      }

      setIsLoggedIn(true);
      toast.success(`Logged in as ${email}`);
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to initialize session");
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && targetDocId && bidder) {
      setUploadingId(targetDocId);
      
      const formData = new FormData();
      formData.append("file", file);

      try {
        const resp = await fetch(`/api/v1/bidders/${bidder.id}/documents`, {
          method: "POST",
          body: formData,
        });

        if (!resp.ok) throw new Error("Upload failed");

        setDocuments(docs => docs.map(d => 
          d.id === targetDocId 
            ? { ...d, status: "uploaded", filename: file.name }
            : d
        ));
        toast.success("Proposal submitted and AI extraction started!");
      } catch (err) {
        console.error(err);
        toast.error("Upload failed. Please check backend.");
      } finally {
        setUploadingId(null);
        setTargetDocId(null);
        if (fileRef.current) fileRef.current.value = "";
      }
    }
  };

  const triggerUpload = (id: string) => {
    setTargetDocId(id);
    fileRef.current?.click();
  };

  const uploadedCount = documents.filter(d => d.status === "uploaded").length;
  const progress = Math.round((uploadedCount / documents.length) * 100);

  if (!isLoggedIn) {
    return (
      <div className="max-w-md mx-auto py-12 animate-fade-in">
        <div className="rounded-2xl border border-border/50 bg-card/60 backdrop-blur-xl p-8 shadow-2xl">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6">
            <Mail className="h-6 w-6 text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">Bidder Access</h2>
          <p className="text-sm text-muted-foreground mb-8">
            Enter your registered email to access the submission portal for this tender.
          </p>
          
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground ml-1">Email Address</label>
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="vendor@company.com"
                className="w-full h-12 px-4 rounded-xl border border-border bg-secondary/30 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition-all font-medium"
                required
              />
            </div>
            <button 
              type="submit" 
              disabled={loading}
              className="w-full h-12 rounded-xl bg-primary text-primary-foreground font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-all shadow-lg shadow-primary/20 disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <>Access Portal <ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
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
            <h3 className="text-lg font-semibold">Submission Status</h3>
            <p className="text-sm text-muted-foreground">Logged in as: <span className="text-foreground font-semibold">{bidder.legal_name}</span></p>
          </div>
          <div className="text-right">
            <p className={`text-2xl font-bold ${progress === 100 ? "text-emerald-500" : "text-amber-500"}`}>
              {progress === 100 ? "COMPLETE" : "PENDING"}
            </p>
          </div>
        </div>
        <div className="w-full h-2 rounded-full bg-secondary overflow-hidden">
          <div 
            className={`h-full transition-all duration-500 ${progress === 100 ? "bg-emerald-500" : "bg-amber-500"}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden">
        <div className="p-4 border-b border-border/30 bg-secondary/10 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Proposal Submission</h3>
          {progress === 100 && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              RECEIVED BY LEDGER
            </span>
          )}
        </div>
        <div className="divide-y divide-border/20">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between p-4 hover:bg-secondary/20 transition-colors">
              <div className="flex items-start gap-3 flex-1 pr-4">
                <div className="mt-0.5">
                  {doc.status === "uploaded" ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-amber-500" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-primary">REQUIREMENT</span>
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                      MANDATORY
                    </span>
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
                  <button disabled className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-secondary/50 text-xs font-medium opacity-70">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> Uploading...
                  </button>
                ) : doc.status === "uploaded" ? (
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => triggerUpload(doc.id)}
                      className="px-4 py-2 rounded-lg border border-border hover:bg-secondary transition-colors text-xs font-medium"
                    >
                      Update Proposal
                    </button>
                  </div>
                ) : (
                  <button 
                    onClick={() => triggerUpload(doc.id)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 transition-all shadow-lg shadow-primary/20"
                  >
                    <Upload className="h-4 w-4" /> Submit Proposal
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="p-4 rounded-xl border border-blue-500/20 bg-blue-500/5">
        <div className="flex gap-3">
          <Info className="h-5 w-5 text-blue-400 shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-blue-400">What happens next?</h4>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              Once you upload your proposal, our AI engine will automatically verify your documents against the tender criteria. You can track the real-time extraction and evaluation status in the <strong>Evaluation Status</strong> tab.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
