import Link from "next/link";
import { ArrowRight, FileText, Gavel, Lock, Network, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const PILLARS = [
  {
    icon: Lock,
    title: "Sovereign by default",
    body: "Air-gapped, on-prem, open-weights. Tender data never leaves CRPF's network.",
  },
  {
    icon: Gavel,
    title: "Neuro-symbolic adjudication",
    body:
      "LLMs extract typed evidence. Open Policy Agent (Rego) returns the verdict. The decision is code, not a vibe.",
  },
  {
    icon: FileText,
    title: "Pixel-grounded evidence",
    body:
      "Every value carries doc_hash + page + bbox. One click: report cell to source pixels.",
  },
  {
    icon: Network,
    title: "Adversarial verification",
    body:
      "A Skeptic agent must fail to overturn each verdict before it is finalised. Otherwise: Manual Review.",
  },
  {
    icon: ShieldAlert,
    title: "Cryptographic audit ledger",
    body:
      "Hash-chained events. Signed report bundle. Replay produces a byte-identical bundle.",
  },
];

export default function Home() {
  return (
    <div className="container mx-auto max-w-6xl space-y-12 px-4 py-12">
      <section className="space-y-6">
        <Badge variant="outline" className="text-xs uppercase tracking-wider">
          Round 2 · MVP
        </Badge>
        <h1 className="text-balance text-4xl font-semibold tracking-tight md:text-5xl">
          AI tender evaluation that a procurement officer can{" "}
          <span className="text-primary">sign and defend.</span>
        </h1>
        <p className="max-w-3xl text-balance text-lg text-muted-foreground">
          PRAMAAN never lets a language model say "Eligible" or "Not Eligible." LLMs and
          vision models extract; a symbolic rules engine adjudicates; cryptography preserves
          every decision. Built for the realities of government procurement.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Button asChild size="lg">
            <Link href="/tenders/new">
              Start a new evaluation <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/tenders">Open existing tenders</Link>
          </Button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {PILLARS.map(({ icon: Icon, title, body }) => (
          <Card key={title} className="bg-card/50">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="rounded-md border border-border bg-secondary p-2">
                  <Icon className="h-5 w-5" />
                </div>
                <CardTitle className="text-base">{title}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>{body}</CardDescription>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="rounded-lg border bg-secondary/30 p-6">
        <h2 className="text-lg font-semibold">The three checks PRAMAAN runs that nothing else does</h2>
        <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
          <li>
            <strong className="text-foreground">Adversarial verification</strong> — a Skeptic
            agent actively tries to overturn every draft verdict.
          </li>
          <li>
            <strong className="text-foreground">Cryptographic audit chain</strong> — every
            extraction, rule eval, validator call, and override is hash-chained.
          </li>
          <li>
            <strong className="text-foreground">Cross-bidder integrity layer</strong> — shared
            directors, shared addresses, near-duplicate documents, and bid-price clustering
            surface cartel signals other tools miss.
          </li>
        </ul>
      </section>
    </div>
  );
}
