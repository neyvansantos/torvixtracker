// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { PRODUCT_NAME, SITE_DESCRIPTION, SITE_URL } from "@/config/product";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl = new URL(SITE_URL);

export const viewport: Viewport = {
  themeColor: "#00e5ff",
};

export const metadata: Metadata = {
  metadataBase: siteUrl,
  applicationName: PRODUCT_NAME,
  title: {
    default: `${PRODUCT_NAME} | Rastreamento Ocular por Webcam para ETS2 e ATS`,
    template: `%s | ${PRODUCT_NAME}`,
  },
  description: SITE_DESCRIPTION,
  keywords: [
    "Torvix Tracker",
    "eye tracking",
    "rastreamento ocular",
    "rastreamento de cabeça",
    "webcam tracker",
    "ETS2",
    "ATS",
    "TrackIR alternativo",
    "simulador de caminhão",
  ],
  authors: [{ name: PRODUCT_NAME }],
  creator: PRODUCT_NAME,
  publisher: PRODUCT_NAME,
  manifest: "/site.webmanifest",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  alternates: {
    canonical: SITE_URL,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  verification: {
    google: "J8winAvO2OwFah8dSDQhSm1z8ra9cJUERPyyOPTZhBE",
  },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: SITE_URL,
    siteName: PRODUCT_NAME,
    title: `${PRODUCT_NAME} | Rastreamento Ocular por Webcam`,
    description: SITE_DESCRIPTION,
    images: [
      {
        url: "/torvix-logo.png",
        width: 1200,
        height: 630,
        alt: `${PRODUCT_NAME} - rastreamento por webcam para ETS2 e ATS`,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `${PRODUCT_NAME} | Rastreamento Ocular por Webcam`,
    description: SITE_DESCRIPTION,
    images: ["/torvix-logo.png"],
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon-48.png", sizes: "48x48", type: "image/png" },
      { url: "/favicon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/favicon-512.png", sizes: "512x512", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
    apple: "/favicon-192.png",
  },
};

const structuredData = [
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: PRODUCT_NAME,
    url: SITE_URL,
    logo: `${SITE_URL}/torvix-logo.png`,
  },
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: PRODUCT_NAME,
    alternateName: "Torvix",
    url: SITE_URL,
    inLanguage: "pt-BR",
  },
  {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: PRODUCT_NAME,
    url: SITE_URL,
    operatingSystem: "Windows",
    applicationCategory: "GameApplication",
    description: SITE_DESCRIPTION,
    offers: {
      "@type": "Offer",
      price: "19.99",
      priceCurrency: "BRL",
      availability: "https://schema.org/InStock",
      url: `${SITE_URL}/pricing`,
    },
  },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="pt-BR"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background text-foreground">
        <script
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(structuredData),
          }}
          type="application/ld+json"
        />
        <div className="flex min-h-svh flex-col">
          <SiteHeader />
          <div className="flex-1">{children}</div>
          <SiteFooter />
        </div>
      </body>
    </html>
  );
}
