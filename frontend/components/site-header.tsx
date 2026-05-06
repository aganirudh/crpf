import Link from "next/link";
import { ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-14 items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <div className="flex items-baseline gap-2">
            <span className="text-base font-bold tracking-tight">PRAMAAN</span>
            <span className="text-xs text-muted-foreground">
              Procurement Review &amp; Audit Network
            </span>
          </div>
        </Link>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="hidden sm:inline-flex">
            CRPF · Theme 3
          </Badge>
          <Badge variant="secondary">v0.1.0</Badge>
        </div>
      </div>
    </header>
  );
}
