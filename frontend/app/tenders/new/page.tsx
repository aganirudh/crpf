"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

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
import { api, ApiError } from "@/lib/api";

export default function NewTenderPage() {
  const router = useRouter();
  const [file, setFile] = React.useState<File | null>(null);
  const [referenceNo, setReferenceNo] = React.useState("");
  const [department, setDepartment] = React.useState("");
  const fileRef = React.useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Pick a tender PDF first.");
      const form = new FormData();
      form.append("file", file);
      if (referenceNo) form.append("reference_no", referenceNo);
      if (department) form.append("department", department);
      const tender = await api.uploadTender(form);
      // Trigger Cartographer immediately (the backend also auto-triggers it
      // in the background; this gives us deterministic UI feedback).
      try {
        await api.cartograph(tender.id);
      } catch (e) {
        if (!(e instanceof ApiError && e.status === 409)) throw e;
      }
      return tender;
    },
    onSuccess: (tender) => {
      toast.success("Tender uploaded. Extracting criteria…");
      router.push(`/tenders/${tender.id}/dsl`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="container mx-auto max-w-2xl px-4 py-12">
      <Card>
        <CardHeader>
          <CardTitle>Start a new evaluation</CardTitle>
          <CardDescription>
            Upload the tender PDF. PRAMAAN will extract the eligibility criteria and ask you
            to confirm them before any bidder is judged.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="reference">Reference no.</Label>
            <Input
              id="reference"
              placeholder="T-CRPF-2026-CONST-014"
              value={referenceNo}
              onChange={(e) => setReferenceNo(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="department">Department</Label>
            <Input
              id="department"
              placeholder="Construction Wing, CRPF"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="file">Tender file (PDF)</Label>
            <div className="flex flex-wrap items-center gap-3">
              <Input
                ref={fileRef}
                id="file"
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <Button type="button" variant="secondary" onClick={() => fileRef.current?.click()}>
                Choose PDF…
              </Button>
              <span className="text-xs text-muted-foreground">
                {file ? file.name : "No file selected"}
              </span>
            </div>
            {file && (
              <p className="text-xs text-muted-foreground">
                {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
          </div>
        </CardContent>
        <CardFooter className="justify-end gap-2">
          <Button variant="outline" type="button" onClick={() => router.push("/")}>
            Cancel
          </Button>
          <Button
            disabled={!file || upload.isPending}
            onClick={() => upload.mutate()}
          >
            {upload.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Extracting…
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Upload &amp; extract criteria
              </>
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
