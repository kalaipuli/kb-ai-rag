import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KB AI RAG — Enterprise Knowledge Base",
  description: "Agentic RAG platform for enterprise knowledge retrieval",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.JSX.Element {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
