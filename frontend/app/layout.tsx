import type { Metadata } from "next";
import "./globals.css";

import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "PRAMAAN — AI Tender Evaluation for CRPF",
  description:
    "Sovereign, neuro-symbolic, auditable tender evaluation. LLMs read. Symbolic logic decides. Cryptography proves. Humans approve.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-dvh font-sans antialiased">
        <Providers>
          <SiteHeader />
          <main>{children}</main>
        </Providers>
      </body>
    </html>
  );
}
