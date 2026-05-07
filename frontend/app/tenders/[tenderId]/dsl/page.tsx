"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Lock,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  type Constraint,
  type Criterion,
  type CriterionDSL,
  type CriterionType,
} from "@/lib/api";
import { cn, formatINR, shortHash } from "@/lib/utils";

const TYPE_TONE: Record<CriterionType, string> = {
  financial: "bg-blue-50 text-blue-900 dark:bg-blue-950 dark:text-blue-50",
  technical: "bg-purple-50 text-purple-900 dark:bg-purple-950 dark:text-purple-50",
  compliance: "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-50",
  certification: "bg-amber-50 text-amber-900 dark:bg-amber-950 dark:text-amber-50",
  documentary: "bg-slate-50 text-slate-900 dark:bg-slate-900 dark:text-slate-50",
};

export default function DslReviewPage() {
  const router = useRouter();
  const { tenderId } = useParams<{ tenderId: string }>();
  const [draft, setDraft] = React.useState<CriterionDSL | null>(null);

  const tenderQ = useQuery({
    queryKey: ["tender", tenderId],
    queryFn: () => api.getTender(tenderId),
    refetchInterval: (q) => (q.state.data?.has_dsl ? false : 1500),
  });

  const dslQ = useQuery({
    queryKey: ["dsl", tenderId],
    queryFn: () => api.getDSL(tenderId),
    enabled: !!tenderQ.data?.has_dsl,
    refetchOnMount: true,
  });

  React.useEffect(() => {
    if (dslQ.data?.dsl && !draft) setDraft(dslQ.data.dsl);
  }, [dslQ.data, draft]);

  const reCartograph = useMutation({
    mutationFn: () => api.cartograph(tenderId),
    onSuccess: () => {
      toast.success("Re-extraction triggered.");
      dslQ.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const lock = useMutation({
    mutationFn: () => {
      if (!draft) throw new Error("DSL not loaded.");
      return api.patchDSL(tenderId, draft);
    },
    onSuccess: () => {
      toast.success("Criteria locked. Adjudication will use this DSL.");
      router.push(`/tenders/${tenderId}/bidders`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (tenderQ.isLoading) return <Spinner label="Loading tender…" />;
  if (!tenderQ.data) return <ErrorBox text="Tender not found." />;

  if (!tenderQ.data.has_dsl) {
    return (
      <div className="container mx-auto max-w-2xl px-4 py-12">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> Cartographer is reading the tender…
            </CardTitle>
            <CardDescription>
              The system is extracting the eligibility criteria. This usually takes 30–90 seconds
              for a typical tender. The page will refresh automatically.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              <strong>Tender:</strong> {tenderQ.data.filename}
            </p>
            <p className="font-mono text-xs text-muted-foreground">
              SHA-256: {shortHash(tenderQ.data.sha256_hex, 16)}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (dslQ.isLoading || !draft) return <Spinner label="Loading CriterionDSL…" />;

  return (
    <div className="container mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Review extracted criteria</h1>
          <p className="text-sm text-muted-foreground">
            {tenderQ.data.reference_no ?? tenderQ.data.filename} · {draft.criteria.length} criteria ·
            DSL v{draft.dsl_version} ·{" "}
            <span className="font-mono">sha {shortHash(dslQ.data?.dsl_sha256_hex, 12)}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/tenders/${tenderId}/bidders`}>Bidder intake</Link>
          </Button>
          <Button variant="outline" asChild>
            <a href={api.tenderSourceUrl(tenderId)} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4" />
              View tender PDF
            </a>
          </Button>
          <Button
            variant="outline"
            disabled={reCartograph.isPending}
            onClick={() => reCartograph.mutate()}
          >
            {reCartograph.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCcw className="h-4 w-4" />
            )}
            Re-extract
          </Button>
        </div>
      </div>

      <div className="rounded-lg border bg-secondary/40 p-4 text-sm">
        <p>
          <ShieldCheck className="mr-1 inline-block h-4 w-4 text-primary" />
          These criteria were extracted by the Cartographer LLM. The verdict path will use the
          version you confirm here — not the raw model output. Toggle mandatoriness, adjust
          thresholds, delete hallucinated criteria, or add ones the model missed.
        </p>
      </div>

      <div className="space-y-4">
        {draft.criteria.map((c, idx) => (
          <CriterionCard
            key={c.id}
            criterion={c}
            tone={TYPE_TONE[c.type]}
            onChange={(next) =>
              setDraft((d) => {
                if (!d) return d;
                const criteria = [...d.criteria];
                criteria[idx] = next;
                return { ...d, criteria };
              })
            }
            onDelete={() =>
              setDraft((d) =>
                d
                  ? {
                      ...d,
                      criteria: d.criteria.filter((x) => x.id !== c.id),
                    }
                  : d,
              )
            }
          />
        ))}
      </div>

      <Card>
        <CardFooter className="flex flex-wrap items-center justify-between gap-3 pt-6">
          <p className="text-sm text-muted-foreground">
            Locking the criteria writes a <code className="font-mono">dsl.confirmed</code> event
            to the audit ledger. Any later edit creates another event — the original is never
            erased.
          </p>
          <Button disabled={lock.isPending} onClick={() => lock.mutate()}>
            {lock.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Lock className="h-4 w-4" />
            )}
            Lock criteria &amp; proceed to bidders
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

// ─── Components ──────────────────────────────────────────────────────────

function CriterionCard({
  criterion,
  tone,
  onChange,
  onDelete,
}: {
  criterion: Criterion;
  tone: string;
  onChange: (next: Criterion) => void;
  onDelete: () => void;
}) {
  const lowConf = criterion.mandatory_confidence < 0.85;
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-border bg-muted px-2 py-0.5 font-mono text-xs">
              {criterion.id}
            </span>
            <span className={cn("rounded-md px-2 py-0.5 text-xs font-medium uppercase", tone)}>
              {criterion.type}
            </span>
            {criterion.escape_hatch && (
              <Badge variant="manualReview" className="gap-1">
                <AlertCircle className="h-3 w-3" />
                Manual Review only
              </Badge>
            )}
            {lowConf && (
              <Badge variant="manualReview" className="gap-1">
                <AlertCircle className="h-3 w-3" />
                Low mandatoriness confidence
              </Badge>
            )}
          </div>
          <CardTitle className="text-base">{criterion.text}</CardTitle>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Switch
              id={`m-${criterion.id}`}
              checked={criterion.mandatory}
              onCheckedChange={(v) =>
                onChange({ ...criterion, mandatory: v, mandatory_confidence: 0.99 })
              }
            />
            <Label htmlFor={`m-${criterion.id}`} className="text-xs">
              {criterion.mandatory ? "Mandatory" : "Optional"}
            </Label>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <ConstraintEditor
          constraint={criterion.constraint}
          onChange={(c) => onChange({ ...criterion, constraint: c })}
        />
        {criterion.evidence_required.length > 0 && (
          <Row label="Evidence required">
            <div className="flex flex-wrap gap-1.5">
              {criterion.evidence_required.map((e) => (
                <Badge key={e} variant="secondary" className="text-xs">
                  {e.replaceAll("_", " ")}
                </Badge>
              ))}
            </div>
          </Row>
        )}
        {criterion.validators.length > 0 && (
          <Row label="Validators">
            <div className="flex flex-wrap gap-1.5">
              {criterion.validators.map((v) => (
                <Badge key={v} variant="outline" className="text-xs">
                  <CheckCircle2 className="mr-1 h-3 w-3" /> {v}
                </Badge>
              ))}
            </div>
          </Row>
        )}
        {criterion.text_source && (
          <Row label="Source">
            <span className="font-mono text-xs text-muted-foreground">
              page {criterion.text_source.page} · bbox{" "}
              {criterion.text_source.bbox.map((n) => Math.round(n)).join(", ")}
            </span>
          </Row>
        )}
        {criterion.escape_hatch && criterion.escape_hatch_text && (
          <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
            <strong>Cannot auto-evaluate:</strong> {criterion.escape_hatch_text}
          </div>
        )}
        {criterion.notes && (
          <div className="rounded-md border bg-muted/50 p-3 text-xs text-muted-foreground">
            <strong>Notes:</strong> {criterion.notes}
          </div>
        )}
      </CardContent>
      <CardFooter className="justify-end gap-2 pt-0">
        <Button variant="ghost" size="sm" onClick={onDelete}>
          Delete
        </Button>
      </CardFooter>
    </Card>
  );
}

function ConstraintEditor({
  constraint,
  onChange,
}: {
  constraint: Constraint | null;
  onChange: (c: Constraint | null) => void;
}) {
  if (!constraint) {
    return <p className="text-xs text-muted-foreground">(escape-hatch criterion)</p>;
  }

  if (constraint.kind === "scalar") {
    const isInr = constraint.field.endsWith("_inr") && typeof constraint.value === "number";
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Field">
          <Input
            value={constraint.field}
            onChange={(e) => onChange({ ...constraint, field: e.target.value })}
          />
        </Field>
        <Field label="Op">
          <Input
            value={constraint.op}
            onChange={(e) => onChange({ ...constraint, op: e.target.value as Constraint["op"] })}
          />
        </Field>
        <Field label="Value">
          <Input
            value={constraint.value == null ? "" : String(constraint.value)}
            onChange={(e) => {
              const v = e.target.value;
              const next = Number(v);
              onChange({
                ...constraint,
                value: v === "" ? null : Number.isFinite(next) ? next : v,
              });
            }}
          />
          {isInr && typeof constraint.value === "number" && (
            <p className="mt-1 text-xs text-muted-foreground">{formatINR(constraint.value)}</p>
          )}
        </Field>
        {constraint.window && (
          <Field label="Window">
            <Input
              value={
                constraint.window.last_n_fy != null
                  ? `last ${constraint.window.last_n_fy} FYs (${constraint.window.aggregator ?? "any"})`
                  : constraint.window.last_n_years != null
                    ? `last ${constraint.window.last_n_years} years (${constraint.window.aggregator ?? "any"})`
                    : "—"
              }
              readOnly
              className="font-mono"
            />
          </Field>
        )}
      </div>
    );
  }

  if (constraint.kind === "set") {
    return (
      <div className="space-y-2">
        <Field label="Field">
          <Input
            value={constraint.field}
            onChange={(e) => onChange({ ...constraint, field: e.target.value })}
          />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Op">
            <Input
              value={constraint.op}
              onChange={(e) => onChange({ ...constraint, op: e.target.value as Constraint["op"] })}
            />
          </Field>
          <Field label="Threshold">
            <Input
              value={constraint.value}
              onChange={(e) => onChange({ ...constraint, value: Number(e.target.value) })}
              type="number"
            />
          </Field>
        </div>
        <Field label="Filter">
          <Textarea
            value={JSON.stringify(constraint.filter, null, 2)}
            onChange={(e) => {
              try {
                onChange({ ...constraint, filter: JSON.parse(e.target.value) });
              } catch {
                /* swallow until valid */
              }
            }}
            className="font-mono text-xs"
            rows={5}
          />
        </Field>
      </div>
    );
  }

  // doc constraint
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Field label="Field">
        <Input
          value={constraint.field}
          onChange={(e) => onChange({ ...constraint, field: e.target.value })}
        />
      </Field>
      <Field label="Op">
        <Input
          value={constraint.op}
          onChange={(e) => onChange({ ...constraint, op: e.target.value as Constraint["op"] })}
        />
      </Field>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[140px_1fr] gap-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div>{children}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}

function Spinner({ label }: { label: string }) {
  return (
    <div className="container mx-auto max-w-md px-4 py-24 text-center">
      <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
      <p className="mt-3 text-sm text-muted-foreground">{label}</p>
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
