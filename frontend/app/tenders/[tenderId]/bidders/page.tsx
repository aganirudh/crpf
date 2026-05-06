"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileUp,
  Gavel,
  Loader2,
  Pickaxe,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  ApiError,
  type BidderSummary,
  type FieldAggregate,
  type EvidenceGraph,
} from "@/lib/api";
import { cn, formatINR, shortHash } from "@/lib/utils";

export default function BiddersPage() {
  const { tenderId } = useParams<{ tenderId: string }>();
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [legalName, setLegalName] = React.useState("");
  const fileRef = React.useRef<HTMLInputElement>(null);

  const tenderQ = useQuery({
    queryKey: ["tender", tenderId],
    queryFn: () => api.getTender(tenderId),
  });

  const biddersQ = useQuery({
    queryKey: ["bidders", tenderId],
    queryFn: () => api.listBidders(tenderId),
    enabled: !!tenderQ.data?.has_dsl,
  });

  React.useEffect(() => {
    const list = biddersQ.data;
    if (!list?.length) {
      setSelectedId(null);
      return;
    }
    setSelectedId((cur) => {
      if (cur && list.some((b) => b.id === cur)) return cur;
      return list[0].id;
    });
  }, [biddersQ.data]);

  const docsQ = useQuery({
    queryKey: ["documents", selectedId],
    queryFn: () => api.listDocuments(selectedId as string),
    enabled: !!selectedId,
  });

  const graphQ = useQuery({
    queryKey: ["evidence-graph", selectedId],
    queryFn: () => api.getEvidenceGraph(selectedId as string),
    enabled: !!selectedId,
    retry: (count, err) => {
      if (err instanceof ApiError && err.status === 404) return false;
      return count < 2;
    },
  });

  const createBidder = useMutation({
    mutationFn: () =>
      api.createBidder(tenderId, {
        legal_name: legalName.trim() || null,
      }),
    onSuccess: (b: BidderSummary) => {
      toast.success("Bidder added.");
      setLegalName("");
      setSelectedId(b.id);
      void biddersQ.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const uploadDocs = useMutation({
    mutationFn: async (files: FileList) => {
      if (!selectedId) throw new Error("Select a bidder first.");
      let n = 0;
      for (const file of Array.from(files)) {
        const fd = new FormData();
        fd.append("file", file);
        await api.uploadDocument(selectedId, fd);
        n += 1;
      }
      return n;
    },
    onSuccess: (n) => {
      toast.success(n === 1 ? "Uploaded 1 document." : `Uploaded ${n} documents.`);
      void docsQ.refetch();
      void biddersQ.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const excavateAll = useMutation({
    mutationFn: () => {
      if (!selectedId) throw new Error("Select a bidder first.");
      return api.excavateBidder(selectedId, { foreground: true });
    },
    onSuccess: (res) => {
      toast.success(
        `Excavation finished — ${res.total_nodes} evidence node${res.total_nodes === 1 ? "" : "s"} across ${res.documents.length} document${res.documents.length === 1 ? "" : "s"}.`,
      );
      void docsQ.refetch();
      void graphQ.refetch();
      void biddersQ.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const excavateOne = useMutation({
    mutationFn: (documentId: string) => {
      if (!selectedId) throw new Error("Select a bidder first.");
      return api.excavateDocument(selectedId, documentId);
    },
    onSuccess: (doc) => {
      toast.success(`Excavated — ${doc.n_evidence_nodes} node${doc.n_evidence_nodes === 1 ? "" : "s"} from ${doc.filename}.`);
      void docsQ.refetch();
      void graphQ.refetch();
      void biddersQ.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (tenderQ.isLoading) return <Spinner label="Loading tender…" />;
  if (!tenderQ.data) return <ErrorBox text="Tender not found." />;

  if (!tenderQ.data.has_dsl) {
    return (
      <div className="container mx-auto max-w-lg px-4 py-12">
        <Card>
          <CardHeader>
            <CardTitle>Criteria not ready yet</CardTitle>
            <CardDescription>
              The bidder intake needs a confirmed CriterionDSL. Finish Cartographer extraction and lock
              the criteria first.
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Button asChild variant="outline">
              <Link href={`/tenders/${tenderId}/dsl`}>Go to criteria</Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  const selectedBidder =
    selectedId != null ? biddersQ.data?.find((b) => b.id === selectedId) : undefined;

  return (
    <div className="container mx-auto max-w-5xl space-y-8 px-4 py-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Gavel className="h-5 w-5 text-primary" aria-hidden />
            <h1 className="text-2xl font-semibold">Bidder intake</h1>
          </div>
          <p className="max-w-xl text-sm text-muted-foreground">
            Upload bidder submission PDFs or Office files. Documents are classified and parsed, then the
            Excavator extractor grounds each field with page + bbox provenance and builds a per-bidder
            evidence graph.
          </p>
          <p className="font-mono text-xs text-muted-foreground">
            Tender: {tenderQ.data.reference_no ?? tenderQ.data.filename}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/tenders/${tenderId}/dsl`}>Edit criteria</Link>
          </Button>
        </div>
      </header>

      {/* Add bidder */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-4 w-4" />
            Bidders on this tender
          </CardTitle>
          <CardDescription>
            Each bidder owns a bundle of uploads. Labels are advisory — use the bid price and IDs when you have
            them.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="bn">Legal name (optional)</Label>
              <Input
                id="bn"
                value={legalName}
                placeholder="ABC Construction Pvt Ltd"
                onChange={(e) => setLegalName(e.target.value)}
                className="w-[260px] max-w-full"
              />
            </div>
            <Button
              disabled={createBidder.isPending}
              onClick={() => createBidder.mutate()}
            >
              {createBidder.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Users className="h-4 w-4" />
              )}
              Add bidder
            </Button>
          </div>

          {biddersQ.isLoading ? (
            <Spinner inline label="Loading bidders…" />
          ) : !biddersQ.data?.length ? (
            <p className="text-sm text-muted-foreground">No bidders yet — add one to begin uploads.</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {biddersQ.data.map((b) => (
                <li key={b.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(b.id)}
                    className={cn(
                      "rounded-lg border px-3 py-2 text-left transition-colors hover:bg-secondary/80",
                      b.id === selectedId && "border-primary bg-primary/5 ring-2 ring-primary/20",
                    )}
                  >
                    <div className="text-sm font-medium leading-tight">
                      {b.legal_name ?? "Unnamed bidder"}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                      <Badge variant="secondary" className="font-normal">
                        {b.n_documents} docs
                      </Badge>
                      {b.bid_price_inr != null && (
                        <Badge variant="outline">{formatINR(b.bid_price_inr)}</Badge>
                      )}
                      <span className="font-mono">{shortHash(b.id.replace(/-/g, ""), 6)}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {selectedBidder && (
        <>
          <Card>
            <CardHeader className="space-y-1">
              <CardTitle className="text-lg">
                Documents — {selectedBidder.legal_name ?? "selected bidder"}
              </CardTitle>
              <CardDescription>
                Classification and extraction run per file. Excavator uses foreground mode here so results are
                ready when the button spinner stops.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <input
                ref={fileRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => {
                  const files = e.target.files;
                  e.target.value = "";
                  if (files?.length) uploadDocs.mutate(files);
                }}
              />
              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={uploadDocs.isPending}
                  onClick={() => fileRef.current?.click()}
                >
                  {uploadDocs.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FileUp className="h-4 w-4" />
                  )}
                  Upload documents
                </Button>
                <Button
                  type="button"
                  disabled={
                    excavateAll.isPending || !docsQ.data?.length || uploadDocs.isPending
                  }
                  onClick={() => excavateAll.mutate()}
                >
                  {excavateAll.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Pickaxe className="h-4 w-4" />
                  )}
                  Run Excavator (all docs)
                </Button>
              </div>

              {docsQ.isLoading ? (
                <Spinner inline label="Listing documents…" />
              ) : !docsQ.data?.length ? (
                <p className="text-sm text-muted-foreground">No uploads for this bidder yet.</p>
              ) : (
                <ul className="space-y-3">
                  {docsQ.data.map((d) => (
                    <li
                      key={d.id}
                      className="flex flex-wrap items-start justify-between gap-3 rounded-lg border bg-muted/30 p-3"
                    >
                      <div className="space-y-1">
                        <p className="text-sm font-medium leading-tight">{d.filename}</p>
                        <div className="flex flex-wrap gap-1.5 text-xs">
                          {d.classification && (
                            <Badge variant="outline" className="font-normal">
                              {d.classification}
                            </Badge>
                          )}
                          {d.document_kind && (
                            <Badge variant="secondary" className="font-normal">
                              {d.document_kind}
                            </Badge>
                          )}
                          {typeof d.page_count === "number" && (
                            <span className="text-muted-foreground">{d.page_count} pages</span>
                          )}
                          <span className="font-mono text-muted-foreground">
                            sha {shortHash(d.sha256_hex)}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {d.n_evidence_nodes} grounded field{d.n_evidence_nodes === 1 ? "" : "s"}
                          {d.excavated ? "" : " — not excavated"}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-wrap gap-2">
                        <Button variant="outline" size="sm" asChild>
                          <a href={api.documentSourceUrl(selectedId!, d.id)} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="mr-1 h-3 w-3" />
                            Source
                          </a>
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={excavateOne.isPending}
                          onClick={() => excavateOne.mutate(d.id)}
                        >
                          {excavateOne.isPending ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Pickaxe className="h-3 w-3" />
                          )}
                          Excavate
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <EvidenceGraphSection graph={graphQ.data} loading={graphQ.isLoading} />
        </>
      )}
    </div>
  );
}

function EvidenceGraphSection({
  graph,
  loading,
}: {
  graph: EvidenceGraph | undefined;
  loading: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          Evidence graph (aggregated)
          {typeof graph?.n_nodes === "number" && graph.n_nodes > 0 ? (
            <Badge variant="secondary">{graph.n_nodes} nodes · {graph.fields.length} fields</Badge>
          ) : null}
        </CardTitle>
        <CardDescription>
          Fields are keyed by extractor output (`field` + optional FY window). Sources list every grounded
          node with bbox — building blocks for adjudication + split-pane UX in Week 5.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <Spinner inline label="Loading evidence graph…" />
        ) : !graph?.fields?.length ? (
          <p className="text-sm text-muted-foreground">
            No grounded fields yet — upload documents and run the Excavator.
          </p>
        ) : (
          graph.fields.map((agg) => <FieldAggregateCard key={`${agg.field}-${agg.fy ?? "nofy"}`} agg={agg} />)
        )}
      </CardContent>
    </Card>
  );
}

function FieldAggregateCard({ agg }: { agg: FieldAggregate }) {
  const [open, setOpen] = React.useState(false);
  const fmt = (n: unknown) =>
    typeof n === "number" ? (Number.isInteger(n) ? String(n) : n.toFixed(3)) : String(n);

  return (
    <div className="rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-start gap-3 p-4 text-left hover:bg-muted/40"
      >
        <div className="flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-semibold">{agg.field}</span>
            {agg.fy ? (
              <Badge variant="outline" className="font-normal">
                {agg.fy}
              </Badge>
            ) : null}
            {agg.cross_doc_disagreement ? (
              <Badge variant="manualReview" className="gap-1">
                <AlertTriangle className="h-3 w-3" />
                Cross-doc mismatch
              </Badge>
            ) : (
              <Badge variant="secondary" className="gap-1 font-normal">
                <CheckCircle2 className="h-3 w-3" /> consistent
              </Badge>
            )}
          </div>
          <div className="text-sm">
            Canonical value: <span className="font-medium">{fmt(agg.value)}</span>
          </div>
        </div>
        <div className="hidden shrink-0 text-right text-xs text-muted-foreground sm:block">
          agreement {(agg.agreement_score * 100).toFixed(0)}% · confidence {(agg.final_conf * 100).toFixed(0)}%
        </div>
      </button>
      {open && (
        <div className="space-y-2 border-t bg-muted/20 p-4 text-xs">
          {agg.sources.map((s, i) => (
            <div
              key={s.node_id}
              className="rounded-md border bg-background px-3 py-2 font-mono text-[11px] leading-relaxed"
            >
              <div className="mb-1 flex flex-wrap gap-2">
                <span className="font-semibold text-foreground">{i + 1}. Doc {shortHash(s.document_id.replace(/-/g, ""))}</span>
                <span>
                  page {s.page}
                </span>
                <span>
                  bbox [{s.bbox.map((x) => (typeof x === "number" ? x.toFixed(1) : x)).join(", ")}]
                </span>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground">
                <span>value {fmt(s.value)}</span>
                <span>final {(s.final_conf * 100).toFixed(0)}%</span>
                <span>OCR {(s.ocr_conf * 100).toFixed(0)}%</span>
              </div>
              {s.source_quote && (
                <p className="mt-2 border-l-2 border-primary/40 pl-2 text-[11px] italic text-muted-foreground">
                  “{s.source_quote}”
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Spinner({ label, inline }: { label: string; inline?: boolean }) {
  const wrap = cn(
    "flex flex-col items-center gap-3 text-muted-foreground",
    inline ? "py-6" : "py-24",
  );
  return (
    <div className={wrap}>
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
      <span className="text-sm">{label}</span>
    </div>
  );
}

function ErrorBox({ text }: { text: string }) {
  return (
    <div className="container mx-auto max-w-md px-4 py-24">
      <Card>
        <CardHeader>
          <CardTitle className="text-destructive">Error</CardTitle>
          <CardDescription>{text}</CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
