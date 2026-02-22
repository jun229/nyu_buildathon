"use client";

import {
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
} from "@clerk/nextjs";
import {
  Camera,
  Phone,
  Package,
  Calendar,
  TrendingUp,
  Search,
  Zap,
  CheckCircle,
  Star,
  MapPin,
  Eye,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

/* ─── Nav ────────────────────────────────────────────────────────────────── */

function Navbar() {
  return (
    <nav className="sticky top-0 z-40 bg-[var(--color-neutral-white)] border-b-[3px] border-[var(--color-neutral-black)] shadow-medium">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-[var(--color-primary)] border-2 border-[var(--color-neutral-black)] rounded-md shadow-brutal-sm flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span
            className="text-xl font-bold tracking-tight"
            style={{ fontFamily: "var(--font-family-display)" }}
          >
            FlipKit
          </span>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          <SignedOut>
            <SignInButton mode="modal">
              <button className="btn btn-secondary text-sm px-4 py-2">
                Sign In
              </button>
            </SignInButton>
            <SignUpButton mode="modal">
              <button className="btn btn-primary text-sm px-4 py-2">
                Get Started
              </button>
            </SignUpButton>
          </SignedOut>
          <SignedIn>
            <Link href="/home" className="btn btn-secondary text-sm px-4 py-2">
              Go to App →
            </Link>
            <UserButton />
          </SignedIn>
        </div>
      </div>
    </nav>
  );
}

/* ─── Hero ───────────────────────────────────────────────────────────────── */

function Hero() {
  return (
    <section className="relative overflow-hidden bg-[var(--color-neutral-white)] pt-16 pb-20 px-4">
      {/* background pattern */}
      <div className="absolute inset-0 pattern-dots opacity-40 pointer-events-none" />

      <div className="relative max-w-6xl mx-auto flex flex-col lg:flex-row items-center gap-12">
        {/* Text */}
        <div className="flex-1 text-center lg:text-left">
          <div className="inline-flex items-center gap-2 badge badge-info mb-6 rotate-slight">
            <Sparkles className="w-3 h-3" />
            AI does the selling for you
          </div>

          <h1
            className="text-5xl sm:text-6xl font-extrabold leading-tight mb-6"
            style={{
              fontFamily: "var(--font-family-display)",
              letterSpacing: "-0.03em",
            }}
          >
            Snap. <span className="gradient-text">Sell.</span>
            <br />
            Done.
          </h1>

          <p className="text-lg sm:text-xl text-[var(--color-neutral-700)] max-w-xl mx-auto lg:mx-0 mb-8 leading-relaxed">
            Take <strong>one photo</strong> of your item and our AI handles
            everything — calling local stores, listing on eBay, finding the best
            price, even booking your drop-off appointment.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center lg:justify-start">
            <SignUpButton mode="modal" forceRedirectUrl="/home">
              <button className="btn btn-primary text-base px-8 py-4">
                <Camera className="w-5 h-5" />
                Start Selling Free
              </button>
            </SignUpButton>
            <a
              href="#how-it-works"
              className="btn btn-secondary text-base px-8 py-4"
            >
              See how it works
            </a>
          </div>

          <p className="mt-4 text-sm text-[var(--color-neutral-500)]">
            No credit card required · Set up in 60 seconds
          </p>
        </div>

        {/* Hero Visual */}
        <div className="flex-1 w-full max-w-md">
          <HeroVisual />
        </div>
      </div>
    </section>
  );
}

function HeroVisual() {
  return (
    <div className="relative">
      {/* Main phone card */}
      <div className="card rotate-slight relative z-10">
        <div className="bg-[var(--color-neutral-50)] border-2 border-[var(--color-neutral-300)] rounded-lg aspect-[9/16] max-h-72 flex flex-col items-center justify-center gap-3 pattern-grid">
          <div className="w-16 h-16 rounded-full bg-[var(--color-primary)] border-2 border-[var(--color-neutral-black)] shadow-brutal flex items-center justify-center">
            <Camera className="w-8 h-8 text-white" />
          </div>
          <p
            className="text-sm font-semibold text-[var(--color-neutral-700)]"
            style={{ fontFamily: "var(--font-family-display)" }}
          >
            Take a photo
          </p>
          <p className="text-xs text-[var(--color-neutral-500)]">
            Tap to upload
          </p>
        </div>
      </div>

      {/* Floating agent bubbles */}
      <div className="absolute -right-4 top-4 card p-3 rotate-slight-reverse z-20 min-w-[180px] shadow-brutal-color">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-[var(--color-accent-green)] flex items-center justify-center agent-active">
            <Phone className="w-3 h-3 text-white" />
          </div>
          <span
            className="text-xs font-medium"
            style={{ fontFamily: "var(--font-family-display)" }}
          >
            Calling Joe's Pawn...
          </span>
        </div>
      </div>

      <div className="absolute -left-6 bottom-12 card p-3 rotate-slight z-20 min-w-[190px]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-[var(--color-secondary)] flex items-center justify-center">
            <Package className="w-3 h-3 text-white" />
          </div>
          <span
            className="text-xs font-medium"
            style={{ fontFamily: "var(--font-family-display)" }}
          >
            Listed on eBay · 47 watching 👀
          </span>
        </div>
      </div>

      <div className="absolute -right-2 bottom-2 card p-3 rotate-slight-reverse z-20 min-w-[170px]">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-[var(--color-accent-green)]" />
          <span
            className="text-xs font-bold text-[var(--color-accent-green)]"
            style={{ fontFamily: "var(--font-family-mono)" }}
          >
            Best offer: $450
          </span>
        </div>
      </div>
    </div>
  );
}

/* ─── How It Works ────────────────────────────────────────────────────────── */

function HowItWorks() {
  const steps = [
    {
      emoji: "📸",
      title: "Take a Photo",
      desc: "Snap one pic of whatever you're selling. That's literally it from you.",
      rotate: "rotate-slight",
      color: "bg-[var(--color-primary)]",
    },
    {
      emoji: "🤖",
      title: "AI Does the Work",
      desc: "Our agents search prices, call stores, and list your item everywhere — all at once.",
      rotate: "rotate-slight-reverse",
      color: "bg-[var(--color-secondary)]",
    },
    {
      emoji: "💰",
      title: "Pick Your Best Offer",
      desc: "See all your options side-by-side. Accept the highest offer or list everywhere at once.",
      rotate: "rotate-slight",
      color: "bg-[var(--color-accent-green)]",
    },
  ];

  return (
    <section
      id="how-it-works"
      className="py-20 px-4 bg-[var(--color-neutral-50)]"
    >
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2
            className="text-4xl sm:text-5xl font-extrabold mb-4"
            style={{ fontFamily: "var(--font-family-display)" }}
          >
            Three steps. <span className="gradient-text">Zero hassle.</span>
          </h2>
          <p className="text-lg text-[var(--color-neutral-700)] max-w-xl mx-auto">
            We built the most annoying part of selling into a single button.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, i) => (
            <div
              key={i}
              className={`card card-hover ${step.rotate} flex flex-col gap-4`}
            >
              <div
                className={`w-14 h-14 ${step.color} border-2 border-[var(--color-neutral-black)] rounded-xl flex items-center justify-center text-2xl shadow-brutal-sm`}
              >
                {step.emoji}
              </div>
              <div className="flex items-center gap-2">
                <span
                  className="text-xs font-bold text-[var(--color-neutral-500)] tracking-widest uppercase"
                  style={{ fontFamily: "var(--font-family-mono)" }}
                >
                  Step {i + 1}
                </span>
              </div>
              <h3
                className="text-xl font-bold"
                style={{ fontFamily: "var(--font-family-display)" }}
              >
                {step.title}
              </h3>
              <p className="text-[var(--color-neutral-700)] leading-relaxed">
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Live Agent Demo ─────────────────────────────────────────────────────── */

function AgentDemo() {
  const activities = [
    {
      icon: <Phone className="w-4 h-4 text-white" />,
      bg: "bg-[var(--color-primary)]",
      title: "Calling Joe's Pawn Shop...",
      sub: "ElevenLabs voice AI on the line",
      status: "Connecting",
      statusClass: "badge-warning",
      pulse: true,
    },
    {
      icon: <Package className="w-4 h-4 text-white" />,
      bg: "bg-[var(--color-secondary)]",
      title: "Listed on eBay",
      sub: "47 people watching right now",
      status: "Live",
      statusClass: "badge-success",
      pulse: false,
    },
    {
      icon: <TrendingUp className="w-4 h-4 text-white" />,
      bg: "bg-[var(--color-accent-green)]",
      title: "Found offer: $450 from Best Buy",
      sub: "22% above average market price",
      status: "Best offer",
      statusClass: "badge-success",
      pulse: false,
    },
    {
      icon: <Calendar className="w-4 h-4 text-white" />,
      bg: "bg-[var(--color-accent-purple)]",
      title: "Appointment booked",
      sub: "Tomorrow at 2pm · GameStop nearby",
      status: "Confirmed",
      statusClass: "badge-info",
      pulse: false,
    },
  ];

  return (
    <section className="py-20 px-4 bg-[var(--color-neutral-black)] relative overflow-hidden">
      {/* Subtle grid pattern on dark bg */}
      <div
        className="absolute inset-0 opacity-10 pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="relative max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 badge badge-success mb-4 rotate-slight">
            <span className="w-2 h-2 rounded-full bg-[var(--color-accent-green)] animate-pulse-dot" />
            Live agents working
          </div>
          <h2
            className="text-4xl sm:text-5xl font-extrabold text-white mb-4"
            style={{ fontFamily: "var(--font-family-display)" }}
          >
            Your AI sales team,{" "}
            <span className="gradient-text">always working</span>
          </h2>
          <p className="text-lg text-[var(--color-neutral-300)] max-w-xl mx-auto">
            While you're doing literally anything else, our agents are grinding
            for you.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 max-w-3xl mx-auto">
          {activities.map((a, i) => (
            <div
              key={i}
              className={`bg-[var(--color-neutral-900)] border-2 border-[var(--color-neutral-700)] border-l-[4px] border-l-[var(--color-primary)] rounded-xl p-4 shadow-brutal card-hover flex items-start gap-4 ${i % 2 === 0 ? "rotate-slight" : "rotate-slight-reverse"}`}
            >
              <div
                className={`w-10 h-10 ${a.bg} rounded-lg border-2 border-[var(--color-neutral-black)] flex items-center justify-center shrink-0 ${a.pulse ? "agent-active" : ""}`}
              >
                {a.icon}
              </div>
              <div className="flex-1 min-w-0">
                <p
                  className="text-white font-semibold text-sm truncate"
                  style={{ fontFamily: "var(--font-family-display)" }}
                >
                  {a.title}
                </p>
                <p className="text-[var(--color-neutral-500)] text-xs mt-0.5">
                  {a.sub}
                </p>
              </div>
              <span className={`badge ${a.statusClass} shrink-0 text-xs`}>
                {a.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Price Comparison Preview ───────────────────────────────────────────── */

function PriceComparison() {
  const localOffers = [
    {
      store: "Joe's Pawn Shop",
      address: "0.4 mi · Brooklyn, NY",
      price: 320,
      cash: true,
    },
    {
      store: "GameStop",
      address: "1.2 mi · Brooklyn, NY",
      price: 280,
      cash: false,
    },
    {
      store: "Best Buy Trade-In",
      address: "2.1 mi · Manhattan, NY",
      price: 450,
      cash: true,
      best: true,
    },
  ];

  const onlineOffers = [
    { platform: "eBay (auction)", viewers: 47, price: 410, live: true },
    { platform: "Facebook Marketplace", viewers: 12, price: 390, live: false },
    { platform: "Shopify Store", viewers: 8, price: 480, live: true },
  ];

  return (
    <section className="py-20 px-4 bg-[var(--color-neutral-white)]">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2
            className="text-4xl sm:text-5xl font-extrabold mb-4"
            style={{ fontFamily: "var(--font-family-display)" }}
          >
            Stop leaving{" "}
            <span className="gradient-text">money on the table</span>
          </h2>
          <p className="text-lg text-[var(--color-neutral-700)] max-w-xl mx-auto">
            FlipKit finds <strong>every</strong> option so you can pick the best
            one. Real example: iPhone 13 Pro
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Local offers */}
          <div className="card rotate-slight">
            <h3
              className="font-bold text-lg mb-4 flex items-center gap-2"
              style={{ fontFamily: "var(--font-family-display)" }}
            >
              <MapPin className="w-5 h-5 text-[var(--color-primary)]" />
              Local Stores
            </h3>
            <div className="flex flex-col gap-3">
              {localOffers.map((o, i) => (
                <div
                  key={i}
                  className={`flex items-center justify-between p-3 rounded-lg border-2 ${
                    o.best
                      ? "border-[var(--color-accent-green)] bg-[color-mix(in_srgb,var(--color-accent-green)_8%,transparent)]"
                      : "border-[var(--color-neutral-300)] bg-[var(--color-neutral-50)]"
                  }`}
                >
                  <div>
                    <p
                      className="font-semibold text-sm"
                      style={{ fontFamily: "var(--font-family-display)" }}
                    >
                      {o.store}
                      {o.best && (
                        <span className="ml-2 badge badge-success text-xs">
                          Best offer ⭐
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-[var(--color-neutral-500)] mt-0.5">
                      {o.address}
                    </p>
                    {o.cash && (
                      <span className="badge badge-warning text-xs mt-1">
                        Cash payment
                      </span>
                    )}
                  </div>
                  <span
                    className={`text-2xl font-bold ${o.best ? "text-[var(--color-accent-green)]" : "text-[var(--color-neutral-black)]"}`}
                    style={{ fontFamily: "var(--font-family-mono)" }}
                  >
                    ${o.price}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Online offers */}
          <div className="card rotate-slight-reverse">
            <h3
              className="font-bold text-lg mb-4 flex items-center gap-2"
              style={{ fontFamily: "var(--font-family-display)" }}
            >
              <Package className="w-5 h-5 text-[var(--color-secondary)]" />
              Online Marketplaces
            </h3>
            <div className="flex flex-col gap-3">
              {onlineOffers.map((o, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 rounded-lg border-2 border-[var(--color-neutral-300)] bg-[var(--color-neutral-50)]"
                >
                  <div>
                    <p
                      className="font-semibold text-sm"
                      style={{ fontFamily: "var(--font-family-display)" }}
                    >
                      {o.platform}
                    </p>
                    <p className="text-xs text-[var(--color-neutral-500)] flex items-center gap-1 mt-0.5">
                      <Eye className="w-3 h-3" />
                      {o.viewers} people watching
                    </p>
                    {o.live && (
                      <span className="badge badge-success text-xs mt-1">
                        Listed · Live
                      </span>
                    )}
                  </div>
                  <span
                    className="text-2xl font-bold text-[var(--color-neutral-black)]"
                    style={{ fontFamily: "var(--font-family-mono)" }}
                  >
                    ${o.price}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Summary bar */}
        <div className="mt-8 card border-[var(--color-primary)] border-chunky shadow-brutal-color flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <p
              className="font-bold text-lg"
              style={{ fontFamily: "var(--font-family-display)" }}
            >
              🎯 FlipKit found you 6 offers in under 3 minutes
            </p>
            <p className="text-sm text-[var(--color-neutral-500)]">
              Without FlipKit, you'd spend 2+ hours doing all this manually
            </p>
          </div>
          <div className="text-right shrink-0">
            <p
              className="text-xs text-[var(--color-neutral-500)] uppercase tracking-wider"
              style={{ fontFamily: "var(--font-family-mono)" }}
            >
              Best offer
            </p>
            <p
              className="text-4xl font-bold text-[var(--color-accent-green)]"
              style={{ fontFamily: "var(--font-family-mono)" }}
            >
              $480
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Features Grid ───────────────────────────────────────────────────────── */

function Features() {
  const features = [
    {
      icon: <Search className="w-6 h-6" />,
      emoji: "🔍",
      title: "Web Search",
      desc: "Scours the internet for comparable prices so you know exactly what your item is worth.",
      rotate: "rotate-slight",
      accent: "var(--color-primary)",
    },
    {
      icon: <Phone className="w-6 h-6" />,
      emoji: "☎️",
      title: "AI Phone Calls",
      desc: "Our ElevenLabs voice agent literally calls local stores and gets you real offers. No joke.",
      rotate: "rotate-slight-reverse",
      accent: "var(--color-secondary)",
    },
    {
      icon: <Package className="w-6 h-6" />,
      emoji: "📦",
      title: "Auto-Listing",
      desc: "Writes the description, picks the price, lists on eBay and Shopify. Done while you nap.",
      rotate: "rotate-slight",
      accent: "var(--color-accent-green)",
    },
    {
      icon: <Calendar className="w-6 h-6" />,
      emoji: "📅",
      title: "Smart Scheduling",
      desc: "Books drop-off appointments at the best local stores. You just show up and collect cash.",
      rotate: "rotate-slight-reverse",
      accent: "var(--color-accent-yellow)",
    },
    {
      icon: <TrendingUp className="w-6 h-6" />,
      emoji: "💡",
      title: "Smart Recommendations",
      desc: "Tells you exactly where and how to sell for maximum payout. No second-guessing.",
      rotate: "rotate-slight",
      accent: "var(--color-accent-purple)",
    },
    {
      icon: <Zap className="w-6 h-6" />,
      emoji: "⚡",
      title: "Instant Results",
      desc: "From photo to first offer in under 3 minutes. Speed is the whole point.",
      rotate: "rotate-slight-reverse",
      accent: "var(--color-primary)",
    },
  ];

  return (
    <section className="py-20 px-4 bg-[var(--color-neutral-50)]">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2
            className="text-4xl sm:text-5xl font-extrabold mb-4"
            style={{ fontFamily: "var(--font-family-display)" }}
          >
            Everything you need.{" "}
            <span className="gradient-text">Nothing you don't.</span>
          </h2>
          <p className="text-lg text-[var(--color-neutral-700)]">
            We call the stores so you don't have to.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className={`card card-hover ${f.rotate}`}>
              <div
                className="w-12 h-12 rounded-lg border-2 border-[var(--color-neutral-black)] flex items-center justify-center text-xl mb-4 shadow-brutal-sm"
                style={{ backgroundColor: f.accent + "22", color: f.accent }}
              >
                {f.emoji}
              </div>
              <h3
                className="font-bold text-lg mb-2"
                style={{ fontFamily: "var(--font-family-display)" }}
              >
                {f.title}
              </h3>
              <p className="text-sm text-[var(--color-neutral-700)] leading-relaxed">
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Pain Points / Social Proof ─────────────────────────────────────────── */

function PainPoints() {
  const pains = [
    "No more posting to 10 different marketplaces",
    "No more calling stores for quotes",
    "No more wondering if you got a good deal",
    "No more wasting weekends at yard sales",
    "No more lowball offers with zero context",
    "No more listing photos with bad lighting",
  ];

  const wins = [
    { stat: "$2.4M+", label: "in items sold" },
    { stat: "12,000+", label: "sellers using FlipKit" },
    { stat: "3 min", label: "avg. time to first offer" },
    { stat: "94%", label: "get more than expected" },
  ];

  return (
    <section className="py-20 px-4 bg-[var(--color-neutral-white)] relative overflow-hidden">
      <div className="absolute inset-0 pattern-dots opacity-30 pointer-events-none" />

      <div className="relative max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Pain points */}
          <div>
            <h2
              className="text-4xl font-extrabold mb-8"
              style={{ fontFamily: "var(--font-family-display)" }}
            >
              Selling stuff shouldn't feel like{" "}
              <span className="gradient-text">a second job.</span>
            </h2>
            <div className="flex flex-col gap-3">
              {pains.map((pain, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-3 p-3 bg-[var(--color-neutral-white)] border-2 border-[var(--color-neutral-black)] rounded-lg shadow-brutal-sm ${i % 2 === 0 ? "rotate-slight" : "rotate-slight-reverse"}`}
                >
                  <CheckCircle className="w-5 h-5 text-[var(--color-accent-green)] shrink-0" />
                  <span className="font-medium text-sm">{pain}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Stats */}
          <div>
            <div className="grid grid-cols-2 gap-5">
              {wins.map((w, i) => (
                <div
                  key={i}
                  className={`card card-hover text-center ${i % 2 === 0 ? "rotate-slight" : "rotate-slight-reverse"}`}
                >
                  <p
                    className="text-4xl font-extrabold gradient-text mb-1"
                    style={{ fontFamily: "var(--font-family-display)" }}
                  >
                    {w.stat}
                  </p>
                  <p className="text-sm text-[var(--color-neutral-700)]">
                    {w.label}
                  </p>
                </div>
              ))}
            </div>

            {/* Quote card */}
            <div className="mt-6 card shadow-brutal-color border-[var(--color-primary)] rotate-slight-reverse">
              <div className="flex gap-1 mb-2">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className="w-4 h-4 fill-[var(--color-accent-yellow)] text-[var(--color-accent-yellow)]"
                  />
                ))}
              </div>
              <p className="text-sm italic text-[var(--color-neutral-700)] mb-3">
                "I uploaded a photo of my old PS5. 4 minutes later I had 8
                offers and an appointment booked for tomorrow. This is insane."
              </p>
              <p
                className="text-xs font-bold text-[var(--color-neutral-500)]"
                style={{ fontFamily: "var(--font-family-mono)" }}
              >
                — Marcus T., sold $1,200 in 2 weeks
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Final CTA ───────────────────────────────────────────────────────────── */

function FinalCTA() {
  return (
    <section className="py-24 px-4 bg-[var(--color-neutral-black)] relative overflow-hidden">
      <div className="absolute inset-0 pattern-grid opacity-10 pointer-events-none" />

      {/* Decorative orange blob */}
      <div
        className="absolute top-0 right-0 w-96 h-96 rounded-full opacity-10 pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, var(--color-primary) 0%, transparent 70%)",
        }}
      />

      <div className="relative max-w-3xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 badge badge-success mb-6">
          <Zap className="w-3 h-3" />
          Free to start · No credit card
        </div>

        <h2
          className="text-5xl sm:text-6xl font-extrabold text-white mb-6"
          style={{
            fontFamily: "var(--font-family-display)",
            letterSpacing: "-0.03em",
          }}
        >
          Ready to sell <span className="gradient-text">smarter?</span>
        </h2>

        <p className="text-xl text-[var(--color-neutral-300)] mb-10 max-w-xl mx-auto">
          Join thousands of sellers who stopped leaving money on the table. One
          photo. That's all it takes.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <SignUpButton mode="modal" forceRedirectUrl="/home">
            <button className="btn btn-primary text-lg px-10 py-4">
              <Camera className="w-5 h-5" />
              Get Started Free
              <ArrowRight className="w-5 h-5" />
            </button>
          </SignUpButton>
        </div>

        <p className="mt-6 text-sm text-[var(--color-neutral-500)]">
          Join sellers who've sold{" "}
          <span
            className="text-[var(--color-accent-green)] font-bold"
            style={{ fontFamily: "var(--font-family-mono)" }}
          >
            $2,400,000+
          </span>{" "}
          in items
        </p>
      </div>
    </section>
  );
}

/* ─── Footer ──────────────────────────────────────────────────────────────── */

function Footer() {
  return (
    <footer className="bg-[var(--color-neutral-white)] border-t-2 border-[var(--color-neutral-black)] py-8 px-4">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-[var(--color-primary)] border-2 border-[var(--color-neutral-black)] rounded flex items-center justify-center">
            <Zap className="w-3 h-3 text-white" />
          </div>
          <span
            className="font-bold"
            style={{ fontFamily: "var(--font-family-display)" }}
          >
            FlipKit
          </span>
        </div>
        <p className="text-sm text-[var(--color-neutral-500)]">
          © 2024 FlipKit. Built for hustlers.
        </p>
        <div className="flex gap-4 text-sm text-[var(--color-neutral-500)]">
          <a
            href="#"
            className="hover:text-[var(--color-primary)] transition-colors"
          >
            Privacy
          </a>
          <a
            href="#"
            className="hover:text-[var(--color-primary)] transition-colors"
          >
            Terms
          </a>
          <a
            href="#"
            className="hover:text-[var(--color-primary)] transition-colors"
          >
            Contact
          </a>
        </div>
      </div>
    </footer>
  );
}

/* ─── Page ────────────────────────────────────────────────────────────────── */

export default function Home() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <Hero />
      <HowItWorks />
      <AgentDemo />
      <PriceComparison />
      <Features />
      <PainPoints />
      <FinalCTA />
      <Footer />
    </div>
  );
}
