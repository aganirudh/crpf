import type { Metadata } from "next";
import "./globals.css";

import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "PRAMAAN — AI Tender Evaluation for CRPF",
  description:
    "Sovereign, neuro-symbolic, auditable tender evaluation. AI extracts. Logic decides. Cryptography proves. Humans approve.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-dvh antialiased">
        <Providers>
          <main>{children}</main>
        </Providers>
      </body>
    </html>
  );
}
