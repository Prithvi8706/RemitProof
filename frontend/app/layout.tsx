import type { Metadata } from "next";
import { Fragment_Mono, Inter, Space_Grotesk, STIX_Two_Text } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const stix = STIX_Two_Text({ subsets: ["latin"], variable: "--font-stix", display: "swap" });
const fragment = Fragment_Mono({ weight: "400", subsets: ["latin"], variable: "--font-fragment", display: "swap" });
const space = Space_Grotesk({ subsets: ["latin"], variable: "--font-space", display: "swap" });

export const metadata: Metadata = {
  title: {
    default: "RemitProof",
    template: "%s | RemitProof",
  },
  description: "Evidence-grounded investigation for unresolved cross-border receivables.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${stix.variable} ${fragment.variable} ${space.variable}`}>{children}</body>
    </html>
  );
}
