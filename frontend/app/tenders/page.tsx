import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function TendersIndexPage() {
  return (
    <div className="container mx-auto max-w-4xl px-4 py-12">
      <Card>
        <CardHeader>
          <CardTitle>Tenders</CardTitle>
          <CardDescription>
            Listing endpoint will surface here once we add it (W3+). For now,
            start a new evaluation to walk the end-to-end flow.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/tenders/new">New evaluation</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
