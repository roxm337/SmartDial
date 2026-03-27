import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ArteFact Calling Console",
  description: "Manage Retell AI agents, outbound campaigns, and call results.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
