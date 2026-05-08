"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { PdfViewer } from "@/components/pdf-viewer";

export default function BidderTenderViewPage() {
  const params = useParams();
  const tenderId = params.tenderId as string;
  
  // Use the direct backend endpoint for the PDF source
  const pdfUrl = `/api/v1/tenders/${tenderId}/source`;

  return (
    <div className="space-y-4 h-[calc(100vh-280px)]">
      <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 mb-2">
        <h3 className="text-sm font-semibold text-blue-400 mb-1">Original Tender Document</h3>
        <p className="text-xs text-muted-foreground">
          View the full tender document as issued by the department. Use this to verify all requirements and submission instructions.
        </p>
      </div>
      
      <PdfViewer 
        url={pdfUrl} 
        title="CRPF Tender Document" 
        className="h-full border border-border/50" 
      />
    </div>
  );
}
