"use client";

import * as React from "react";
import { FileText, Loader2, Maximize2, Minimize2, Download, ExternalLink } from "lucide-react";

interface PdfViewerProps {
  url: string;
  title?: string;
  className?: string;
}

export function PdfViewer({ url, title, className = "" }: PdfViewerProps) {
  const [loading, setLoading] = React.useState(true);
  const [fullScreen, setFullScreen] = React.useState(false);

  // We use an iframe to leverage the browser's native PDF viewer.
  // In a production app, we'd use something like react-pdf-viewer for more control,
  // but this is the most reliable "sovereign" way without heavy deps.

  return (
    <div 
      className={`relative flex flex-col rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden transition-all ${
        fullScreen ? "fixed inset-4 z-50 bg-background" : "h-full min-h-[500px]"
      } ${className}`}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/30 bg-secondary/10">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold truncate max-w-[200px] md:max-w-md">
            {title || "Document Viewer"}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <a 
            href={url} 
            download
            className="p-1.5 rounded-lg hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
            title="Download PDF"
          >
            <Download className="h-4 w-4" />
          </a>
          <a 
            href={url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
            title="Open in new tab"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
          <button
            onClick={() => setFullScreen(!fullScreen)}
            className="p-1.5 rounded-lg hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
            title={fullScreen ? "Exit Fullscreen" : "Enter Fullscreen"}
          >
            {fullScreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* PDF Container */}
      <div className="flex-1 bg-muted/30 relative">
        {loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-card/80 z-10">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Loading Document...</p>
          </div>
        )}
        <iframe
          src={`${url}#toolbar=0&navpanes=0&scrollbar=0`}
          className="w-full h-full border-none"
          onLoad={() => setLoading(false)}
          title={title || "PDF Viewer"}
        />
      </div>
    </div>
  );
}
