import { type Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import type { Appearance } from "@clerk/types";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FlipKit — Snap. Sell. Done.",
  description:
    "AI-powered reselling. Take one photo and our agents search prices, call stores, list on marketplaces, and book appointments for you.",
};

const clerkAppearance: Appearance = {
  variables: {
    // Brand colors
    colorPrimary: "#FF6B35",
    colorBackground: "#FFFFFF",
    colorInputBackground: "#F5F5F7",
    colorInputText: "#1A1A1D",
    colorText: "#1A1A1D",
    colorTextSecondary: "#4A4A4F",
    colorNeutral: "#1A1A1D",
    colorDanger: "#EF476F",
    colorSuccess: "#06D6A0",
    colorWarning: "#FFD23F",
    // Typography
    fontFamily: "'Space Grotesk', system-ui, sans-serif",
    fontFamilyButtons: "'Space Grotesk', system-ui, sans-serif",
    fontWeight: { normal: 400, medium: 600, bold: 700 },
    fontSize: "15px",
    // Shape — keep it slightly rounded like our cards, not pill-shaped
    borderRadius: "8px",
    // Spacing
    spacingUnit: "16px",
  },
  elements: {
    // Backdrop
    modalBackdrop: "bg-black/60 backdrop-blur-sm",

    // Card — brutalist style
    card: [
      "shadow-none",
      "border-2",
      "border-[#1A1A1D]",
      "[box-shadow:5px_5px_0px_#1A1A1D]",
      "rounded-xl",
    ].join(" "),

    // Header
    headerTitle: "font-bold tracking-tight text-[#1A1A1D]",
    headerSubtitle: "text-[#4A4A4F]",

    // Primary action button (Sign in / Continue)
    formButtonPrimary: [
      "bg-[#FF6B35]",
      "text-white",
      "border-2",
      "border-[#1A1A1D]",
      "[box-shadow:5px_5px_0px_#1A1A1D]",
      "hover:-translate-y-0.5",
      "hover:[box-shadow:7px_7px_0px_#1A1A1D]",
      "active:translate-y-0",
      "active:[box-shadow:3px_3px_0px_#1A1A1D]",
      "transition-all",
      "duration-150",
      "font-semibold",
      "rounded-lg",
    ].join(" "),

    // Social buttons (Google, etc.)
    socialButtonsBlockButton: [
      "bg-white",
      "text-[#1A1A1D]",
      "border-2",
      "border-[#1A1A1D]",
      "[box-shadow:3px_3px_0px_#1A1A1D]",
      "hover:-translate-y-0.5",
      "hover:[box-shadow:5px_5px_0px_#1A1A1D]",
      "transition-all",
      "duration-150",
      "font-semibold",
      "rounded-lg",
    ].join(" "),

    // Input fields
    formFieldInput: [
      "bg-[#F5F5F7]",
      "border-2",
      "border-[#C4C4CC]",
      "focus:border-[#FF6B35]",
      "focus:[box-shadow:3px_3px_0px_#FF6B35]",
      "rounded-lg",
      "transition-all",
      "duration-150",
    ].join(" "),

    formFieldLabel: "text-[#1A1A1D] font-semibold text-sm",

    // Footer links
    footerActionLink: "text-[#FF6B35] font-semibold hover:text-[#E55A2B]",
    footerActionText: "text-[#4A4A4F]",

    // Internal nav links (e.g. "Use email" / "Use phone")
    identityPreviewEditButton: "text-[#FF6B35] hover:text-[#E55A2B]",
    alternativeMethodsBlockButton: [
      "border-2",
      "border-[#C4C4CC]",
      "hover:border-[#1A1A1D]",
      "hover:[box-shadow:3px_3px_0px_#1A1A1D]",
      "transition-all",
      "duration-150",
      "rounded-lg",
    ].join(" "),

    // OTP / code input
    otpCodeFieldInput: [
      "border-2",
      "border-[#C4C4CC]",
      "focus:border-[#FF6B35]",
      "rounded-lg",
    ].join(" "),
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider
      appearance={clerkAppearance}
      afterSignInUrl="/home"
      afterSignUpUrl="/home"
    >
      <html lang="en">
        <head>
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link
            rel="preconnect"
            href="https://fonts.gstatic.com"
            crossOrigin="anonymous"
          />
          <link
            href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
            rel="stylesheet"
          />
        </head>
        <body
          className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        >
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
