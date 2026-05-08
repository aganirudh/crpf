/**
 * Typed API client for the FastAPI backend.
 *
 * In dev, requests go to /api/* which Next.js rewrites to the FastAPI
 * server (see next.config.mjs). In prod they hit the same origin.
 */

const BASE = "/api/v1";

async function request<T>(
  method: string,
  path: string,
  init: RequestInit = {},
  body?: unknown,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (body !== undefined && !(body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const rsp = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
    ...init,
  });
  if (!rsp.ok) {
    const text = await rsp.text();
    let message = text || rsp.statusText;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      const d = parsed.detail;
      if (typeof d === "string") {
        message = d;
      } else if (d && typeof d === "object" && "message" in d && typeof (d as { message: unknown }).message === "string") {
        message = (d as { message: string }).message;
      } else if (d !== undefined) {
        message = typeof d === "object" ? JSON.stringify(d) : String(d);
      }
    } catch {
      /* keep raw text */
    }
    throw new ApiError(rsp.status, message);
  }
  if (rsp.status === 204) return undefined as T;
  return (await rsp.json()) as T;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(`API ${status}: ${message}`);
    this.status = status;
  }
}

// ─── Schemas ─────────────────────────────────────────────────────────────

export type TenderSummary = {
  id: string;
  reference_no: string | null;
  department: string | null;
  filename: string;
  sha256_hex: string;
  page_count: number | null;
  classification: string | null;
  has_dsl: boolean;
};

export type DSLEnvelope = {
  dsl: CriterionDSL;
  dsl_sha256_hex: string;
  dsl_version: string;
  source_model: string;
  source_prompt_hash: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
};

export type CriterionType =
  | "technical"
  | "financial"
  | "compliance"
  | "certification"
  | "documentary";

export type ScalarConstraint = {
  kind: "scalar";
  field: string;
  op: string;
  value?: string | number | null;
  unit?: string | null;
  window?: { last_n_fy?: number; last_n_years?: number; aggregator?: string } | null;
};
export type SetConstraint = {
  kind: "set";
  field: string;
  filter: Record<string, unknown>;
  op: string;
  value: number;
};
export type DocConstraint = {
  kind: "doc";
  field: string;
  op: string;
  issuer?: string | null;
};
export type Constraint = ScalarConstraint | SetConstraint | DocConstraint;

export type Criterion = {
  id: string;
  type: CriterionType;
  mandatory: boolean;
  mandatory_confidence: number;
  text: string;
  text_source?: { page: number; bbox: [number, number, number, number] } | null;
  constraint: Constraint | null;
  evidence_required: string[];
  validators: string[];
  cross_check: { against: string; tolerance_pct: number }[];
  escape_hatch: boolean;
  escape_hatch_text?: string | null;
  notes?: string | null;
};

export type CriterionDSL = {
  dsl_version: "v1";
  tender: {
    id: string;
    source_sha256: string;
    classification?: string | null;
    language: string;
    pages?: number | null;
  };
  criteria: Criterion[];
  evidence_vocabulary: Record<
    string,
    { aliases: string[]; expected_fields: string[] }
  >;
};

export type BidderSummary = {
  id: string;
  tender_id: string;
  legal_name: string | null;
  cin: string | null;
  gstin: string | null;
  pan: string | null;
  bid_price_inr: number | null;
  n_documents: number;
};

export type DocumentSummary = {
  id: string;
  bidder_id: string;
  filename: string;
  mime: string;
  sha256_hex: string;
  page_count: number | null;
  classification: string | null;
  n_evidence_nodes: number;
  excavated: boolean;
  document_kind: string | null;
};

export type EvidenceNode = {
  id: string;
  bidder_id: string;
  document_id: string;
  field: string;
  value: unknown;
  unit: string | null;
  fy: string | null;
  page: number;
  bbox: [number, number, number, number];
  ocr_conf: number | null;
  extractor_conf: number | null;
  provenance_match_conf: number | null;
  final_conf: number;
  extractor_model: string;
  source_quote: string | null;
};

export type FieldSource = {
  node_id: string;
  document_id: string;
  value: unknown;
  page: number;
  bbox: [number, number, number, number];
  final_conf: number;
  extractor_conf: number;
  ocr_conf: number;
  provenance_match_conf: number;
  source_quote: string | null;
};

export type FieldAggregate = {
  field: string;
  fy: string | null;
  value: unknown;
  sources: FieldSource[];
  agreement_score: number;
  final_conf: number;
  cross_doc_disagreement: boolean;
};

export type EvidenceGraph = {
  bidder_id: string;
  n_documents: number;
  n_nodes: number;
  fields: FieldAggregate[];
};

export type ExcavateResult = {
  bidder_id: string;
  documents: Array<{
    document_id: string;
    n_nodes: number;
    n_dropped_no_provenance: number;
    document_kind: string;
    model: string;
    prompt_hash: string;
    run_id: string;
  }>;
  total_nodes: number;
};

// ─── Endpoints ───────────────────────────────────────────────────────────

export const api = {
  info: () => request<{ name: string; version: string; mock_llm: boolean }>("GET", "/info"),

  uploadTender: (form: FormData) =>
    request<TenderSummary>("POST", "/tenders", {}, form),

  cartograph: (tenderId: string) =>
    request<{ tender_id: string; n_criteria: number; model: string; prompt_hash: string }>(
      "POST",
      `/tenders/${tenderId}/cartograph`,
    ),

  getTender: (tenderId: string) =>
    request<TenderSummary>("GET", `/tenders/${tenderId}`),

  getDSL: (tenderId: string) =>
    request<DSLEnvelope>("GET", `/tenders/${tenderId}/dsl`),

  patchDSL: (tenderId: string, dsl: CriterionDSL) =>
    request<DSLEnvelope>("PATCH", `/tenders/${tenderId}/dsl`, {}, dsl),

  tenderSourceUrl: (tenderId: string) => `${BASE}/tenders/${tenderId}/source`,

  createBidder: (
    tenderId: string,
    body: Partial<Omit<BidderSummary, "id" | "tender_id" | "n_documents">>,
  ) =>
    request<BidderSummary>("POST", `/tenders/${tenderId}/bidders`, {}, body),

  listBidders: (tenderId: string) =>
    request<BidderSummary[]>("GET", `/tenders/${tenderId}/bidders`),

  getBidder: (bidderId: string) =>
    request<BidderSummary>("GET", `/bidders/${bidderId}`),

  uploadDocument: (bidderId: string, form: FormData) =>
    request<DocumentSummary>("POST", `/bidders/${bidderId}/documents`, {}, form),

  listDocuments: (bidderId: string) =>
    request<DocumentSummary[]>("GET", `/bidders/${bidderId}/documents`),

  documentSourceUrl: (bidderId: string, documentId: string) =>
    `${BASE}/bidders/${bidderId}/documents/${documentId}/source`,

  // ── W3: Excavator + Evidence Graph ─────────────────────────────────────

  excavateBidder: (bidderId: string, opts: { foreground?: boolean } = {}) =>
    request<ExcavateResult>(
      "POST",
      `/bidders/${bidderId}/excavate${opts.foreground ? "?foreground=true" : ""}`,
    ),

  excavateDocument: (bidderId: string, documentId: string) =>
    request<DocumentSummary>(
      "POST",
      `/bidders/${bidderId}/documents/${documentId}/excavate`,
    ),

  getEvidenceGraph: (bidderId: string) =>
    request<EvidenceGraph>("GET", `/bidders/${bidderId}/evidence-graph`),

  listEvidenceNodes: (bidderId: string) =>
    request<EvidenceNode[]>("GET", `/bidders/${bidderId}/evidence-nodes`),
};
