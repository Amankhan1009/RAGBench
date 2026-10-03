import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RAGBench | LLM & Agent Evaluation Platform",
  description: "Production-Grade LLM, RAG & Agent Evaluation Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <head>
        <title>RAGBench</title>
        <meta name="description" content="Production-Grade LLM, RAG & Agent Evaluation Platform" />
      </head>
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}

