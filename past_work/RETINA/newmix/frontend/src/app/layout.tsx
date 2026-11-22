import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// Use the Geist files from the locked Next.js release for offline demo builds.
const geistSans = localFont({
  src: "../../node_modules/next/dist/next-devtools/server/font/geist-latin.woff2",
  variable: "--font-geist-sans",
  weight: "100 900",
});

const geistMono = localFont({
  src: "../../node_modules/next/dist/next-devtools/server/font/geist-mono-latin.woff2",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: {
    default: "Retina Suite — Retinal screening workspace",
    template: "%s · Retina Suite",
  },
  description:
    "A retinal screening workspace for glaucoma (OCT, clinical measurements, multimodal) and diabetes (vessels, fractal, HbA1c), with the evidence behind every model.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-bg text-ink">{children}</body>
    </html>
  );
}
