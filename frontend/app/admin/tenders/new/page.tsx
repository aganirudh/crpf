"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, Upload, FileText, ArrowLeft, CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";

export default function AdminNewTenderPage() {
  const router = useRouter();
  const [file, setFile] = React.useState<File | null>(null);
  const [referenceNo, setReferenceNo] = React.useState("");
  const [department, setDepartment] = React.useState("");
  const [dragOver, setDragOver] = React.useState(false);
  const fileRef = React.useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Pick a tender PDF first.");
      const form = new FormData();
      form.append("file", file);
      if (referenceNo) form.append("reference_no", referenceNo);
      if (department) form.append("department", department);
      const tender = await api.uploadTender(form);
      try {
        await api.cartograph(tender.id);
      } catch (e) {
        if (!(e instanceof ApiError && e.status === 409)) throw e;
      }
      return tender;
    },
    onSuccess: (tender) => {
      toast.success("Tender uploaded. Criteria extraction complete.");
      router.push(`/admin/tenders/${tender.id}`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === "application/pdf") {
      setFile(dropped);
    } else {
      toast.error("Only PDF files are accepted");
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="animate-fade-in-up">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <h1 className="text-2xl font-bold">Upload New Tender</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload the tender PDF. PRAMAAN will automatically extract all eligibility criteria using AI-powered document intelligence.
        </p>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-6 space-y-5 animate-fade-in-up stagger-1">
        {/* Reference No */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Reference No.</label>
          <input
            type="text"
            placeholder="e.g. CRPF/GC-BLR/ENGG/2025-26/CT-07"
            value={referenceNo}
            onChange={(e) => setReferenceNo(e.target.value)}
            className="w-full h-10 px-4 rounded-lg border border-border bg-background text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all"
          />
        </div>

        {/* Department */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Department</label>
          <input
            type="text"
            placeholder="e.g. Engineering Division, Group Centre Bengaluru"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="w-full h-10 px-4 rounded-lg border border-border bg-background text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all"
          />
        </div>

        {/* File Upload */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Tender Document (PDF)</label>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              dragOver
                ? "border-primary bg-primary/5"
                : file
                  ? "border-emerald-500/50 bg-emerald-500/5"
                  : "border-border/50 hover:border-primary/30 hover:bg-primary/5"
            }`}
          >
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {file ? (
              <div className="space-y-2">
                <CheckCircle2 className="h-10 w-10 mx-auto text-emerald-500" />
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(file.size / 1024 / 1024).toFixed(2)} MB · Click to change
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload className="h-10 w-10 mx-auto text-muted-foreground/40" />
                <p className="text-sm font-medium">Drop PDF here or click to browse</p>
                <p className="text-xs text-muted-foreground">Only .pdf files accepted</p>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2">
          <button
            onClick={() => router.back()}
            className="px-4 py-2.5 text-sm font-medium rounded-lg border border-border hover:bg-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            disabled={!file || upload.isPending}
            onClick={() => upload.mutate()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {upload.isPending ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Extracting Criteria…</>
            ) : (
              <><Upload className="h-4 w-4" /> Upload &amp; Extract</>
            )}
          </button>
        </div>
      </div>

      {/* Info */}
      <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 animate-fade-in-up stagger-2">
        <p className="text-xs text-blue-400 font-medium mb-1">What happens next?</p>
        <ul className="text-xs text-muted-foreground space-y-1">
          <li>1. PRAMAAN parses the PDF using document intelligence</li>
          <li>2. All eligibility criteria are extracted (Financial, Technical, Compliance, Optional)</li>
          <li>3. The document checklist is generated automatically</li>
          <li>4. You review and confirm the criteria before any bidder is evaluated</li>
        </ul>
      </div>
    </div>
  );
}
