'use client';

import { useRef, useState, useCallback, useEffect } from 'react';
import { UserButton, useAuth } from '@clerk/nextjs';
import { Camera, Upload, X, Zap, ImageIcon, Phone, MapPin } from 'lucide-react';
import Link from 'next/link';
import { formatPrice } from '@/lib/utils';

/* ─── Types ──────────────────────────────────────────────────────────────── */

type UploadState = 'idle' | 'preview' | 'analyzing' | 'results' | 'calling' | 'error';

interface NegotiationStrategy {
  opening_price: number;
  target_price: number;
  walk_away_price: number;
  opening_script: string;
  counter_script: string;
  accept_script: string;
  walk_away_script: string;
}

interface AnalysisResult {
  analysis_id: string;
  image_url: string;
  item_name: string;
  item_description: string;
  estimated_price_range: { low: number; fair: number; high: number; currency: string };
  best_platform: string;
  platforms: Array<{
    name: string;
    avg_price: number;
    demand: string;
    time_to_sell_days: number;
  }>;
  local_stores: Array<{
    name: string;
    address: string;
    phone: string;
    specialty: string;
  }>;
  condition_tips: string[];
  confidence: number;
  negotiation_strategy: NegotiationStrategy | null;
}

/* ─── Navbar ─────────────────────────────────────────────────────────────── */

function Navbar() {
  return (
    <nav className="sticky top-0 z-40 bg-[var(--color-neutral-white)] border-b-[3px] border-[var(--color-neutral-black)] shadow-medium">
      <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 bg-[var(--color-primary)] border-2 border-[var(--color-neutral-black)] rounded-md shadow-brutal-sm flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-white" />
          </div>
          <span
            className="text-lg font-bold tracking-tight"
            style={{ fontFamily: 'var(--font-family-display)' }}
          >
            FlipKit
          </span>
        </Link>
        <UserButton />
      </div>
    </nav>
  );
}

/* ─── Upload Zone ─────────────────────────────────────────────────────────── */

export default function HomePage() {
  const { getToken } = useAuth();
  const [state, setState] = useState<UploadState>('idle');
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    navigator.geolocation.getCurrentPosition(
      (pos) => setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
    );
  }, []);

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    setCurrentFile(file);
    setState('preview');
  }, []);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // reset so same file can be re-selected
    e.target.value = '';
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const reset = () => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setCurrentFile(null);
    setAnalysisResult(null);
    setErrorMessage(null);
    setState('idle');
  };

  const handleAnalyze = useCallback(async () => {
    if (!currentFile) return;
    setState('analyzing');
    setErrorMessage(null);
    try {
      const formData = new FormData();
      formData.append('file', currentFile);
      if (coords) {
        formData.append('ll', `@${coords.lat},${coords.lng}`);
      }

      const token = await getToken();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/analyze`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!response.ok) throw new Error(`Analysis failed: ${await response.text()}`);

      const result: AnalysisResult = await response.json();
      setAnalysisResult(result);
      setState('results');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Something went wrong');
      setState('error');
    }
  }, [currentFile, getToken]);

  const handleNegotiate = useCallback(async () => {
    if (!analysisResult?.analysis_id) return;
    try {
      const token = await getToken();
      const apiUrl = const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/negotiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ analysis_id: analysisResult.analysis_id }),
      });
      if (!res.ok) throw new Error(await res.text());
      const { job_id } = await res.json();
      setJobId(job_id);
      setState('calling');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Something went wrong');
      setState('error');
    }
  }, [analysisResult, getToken]);

  return (
    <div className="min-h-screen bg-[var(--color-neutral-50)] flex flex-col">
      <Navbar />

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">

          {/* Header */}
          <div className="text-center mb-8">
            <h1
              className="text-3xl sm:text-4xl font-extrabold mb-2"
              style={{ fontFamily: 'var(--font-family-display)', letterSpacing: '-0.03em' }}
            >
              What are you{' '}
              <span className="gradient-text">selling?</span>
            </h1>
            <p className="text-[var(--color-neutral-700)] text-sm sm:text-base">
              Snap or upload a photo — our AI handles the rest.
            </p>
          </div>

          {/* ── Idle: upload zone ── */}
          {state === 'idle' && (
            <div className="flex flex-col gap-4">
              {/* Drop zone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`
                  card cursor-pointer select-none transition-all duration-150
                  flex flex-col items-center justify-center gap-4
                  min-h-[220px] sm:min-h-[260px]
                  ${dragging
                    ? 'border-[var(--color-primary)] shadow-brutal-color bg-[color-mix(in_srgb,var(--color-primary)_5%,white)]'
                    : 'card-hover border-dashed'
                  }
                `}
              >
                <div className={`
                  w-16 h-16 rounded-2xl border-2 border-[var(--color-neutral-black)] flex items-center justify-center shadow-brutal-sm transition-colors duration-150
                  ${dragging ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-neutral-100)]'}
                `}>
                  <ImageIcon className={`w-7 h-7 ${dragging ? 'text-white' : 'text-[var(--color-neutral-500)]'}`} />
                </div>
                <div className="text-center">
                  <p
                    className="font-semibold text-[var(--color-neutral-black)] mb-1"
                    style={{ fontFamily: 'var(--font-family-display)' }}
                  >
                    {dragging ? 'Drop it!' : 'Upload a photo'}
                  </p>
                  <p className="text-xs text-[var(--color-neutral-500)]">
                    Drag & drop or tap to browse
                  </p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={onFileChange}
                />
              </div>

              {/* Divider */}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-[2px] bg-[var(--color-neutral-200)]" />
                <span className="text-xs font-semibold text-[var(--color-neutral-500)] uppercase tracking-widest" style={{ fontFamily: 'var(--font-family-mono)' }}>or</span>
                <div className="flex-1 h-[2px] bg-[var(--color-neutral-200)]" />
              </div>

              {/* Camera button */}
              <button
                onClick={() => cameraInputRef.current?.click()}
                className="btn btn-primary w-full text-base py-4 justify-center"
              >
                <Camera className="w-5 h-5" />
                Take a Photo
              </button>
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={onFileChange}
              />

              {/* Helper text */}
              <p className="text-center text-xs text-[var(--color-neutral-500)]">
                Works best with clear, well-lit photos · JPG, PNG, WEBP
              </p>
            </div>
          )}

          {/* ── Preview ── */}
          {state === 'preview' && (
            <div className="flex flex-col gap-4">
              <div className="card p-3 relative">
                {/* Remove button */}
                <button
                  onClick={reset}
                  className="absolute top-3 right-3 z-10 w-8 h-8 bg-[var(--color-neutral-black)] text-white rounded-full flex items-center justify-center shadow-brutal-sm hover:bg-[var(--color-neutral-700)] transition-colors"
                  aria-label="Remove photo"
                >
                  <X className="w-4 h-4" />
                </button>

                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={preview!}
                  alt="Your item"
                  className="w-full rounded-lg border-2 border-[var(--color-neutral-black)] object-cover max-h-72 sm:max-h-96"
                />
              </div>

              <button
                onClick={handleAnalyze}
                className="btn btn-primary w-full text-base py-4 justify-center"
              >
                <Zap className="w-5 h-5" />
                Analyze &amp; Find Best Price
              </button>

              <button
                onClick={reset}
                className="btn btn-secondary w-full text-sm py-3 justify-center"
              >
                <Upload className="w-4 h-4" />
                Use a different photo
              </button>
            </div>
          )}

          {/* ── Analyzing ── */}
          {state === 'analyzing' && (
            <div className="flex flex-col gap-4">
              <div className="card p-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={preview!}
                  alt="Your item"
                  className="w-full rounded-lg border-2 border-[var(--color-neutral-black)] object-cover max-h-48 opacity-60"
                />
              </div>
              <div className="card p-6 flex flex-col items-center gap-3 text-center">
                <div className="w-10 h-10 border-4 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
                <p className="font-semibold" style={{ fontFamily: 'var(--font-family-display)' }}>
                  Analyzing with AI...
                </p>
                <p className="text-xs text-[var(--color-neutral-500)]">
                  Identifying item and checking marketplace prices
                </p>
              </div>
            </div>
          )}

          {/* ── Results ── */}
          {state === 'results' && analysisResult && (
            <div className="flex flex-col gap-4">
              <div className="card p-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={preview!}
                  alt="Your item"
                  className="w-full rounded-lg border-2 border-[var(--color-neutral-black)] object-cover max-h-48"
                />
              </div>

              <div className="card p-4">
                <p
                  className="text-xs font-semibold text-[var(--color-neutral-500)] uppercase tracking-widest mb-1"
                  style={{ fontFamily: 'var(--font-family-mono)' }}
                >
                  Estimated Value
                </p>
                <p className="text-3xl font-extrabold" style={{ fontFamily: 'var(--font-family-display)' }}>
                  {formatPrice(analysisResult.estimated_price_range.low)} – {formatPrice(analysisResult.estimated_price_range.high)}
                </p>
                <p className="text-sm text-[var(--color-neutral-500)] mt-1">
                  Best on{' '}
                  <span className="font-semibold text-[var(--color-primary)]">
                    {analysisResult.best_platform}
                  </span>
                </p>
              </div>

              <div className="card p-4 flex flex-col gap-2">
                <p
                  className="text-xs font-semibold text-[var(--color-neutral-500)] uppercase tracking-widest mb-2"
                  style={{ fontFamily: 'var(--font-family-mono)' }}
                >
                  Platform Comparison
                </p>
                {analysisResult.platforms.map((p) => (
                  <div
                    key={p.name}
                    className="flex items-center justify-between py-2 border-b border-[var(--color-neutral-200)] last:border-0"
                  >
                    <span className="font-semibold text-sm">{p.name}</span>
                    <div className="flex items-center gap-3 text-sm">
                      <span>{formatPrice(p.avg_price)}</span>
                      <span className={`font-semibold ${
                        p.demand === 'high' ? 'text-(--color-accent-green)' :
                        p.demand === 'medium' ? 'text-(--color-accent-yellow)' : 'text-(--color-accent-red)'
                      }`}>
                        {p.demand}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="card p-4 flex flex-col gap-3">
                <p
                  className="text-xs font-semibold text-[var(--color-neutral-500)] uppercase tracking-widest"
                  style={{ fontFamily: 'var(--font-family-mono)' }}
                >
                  Local Stores Nearby
                </p>
                {analysisResult.local_stores.map((store) => (
                  <div
                    key={store.name}
                    className="flex flex-col gap-1 py-3 border-b border-neutral-200 last:border-0 last:pb-0"
                  >
                    <div className="flex flex-col gap-0.5">
                      <p className="font-semibold text-sm">{store.name}</p>
                      <p className="text-xs text-neutral-500">{store.specialty}</p>
                    </div>
                    <div className="flex items-center gap-4 mt-1">
                      <a
                        href={`https://maps.google.com/?q=${encodeURIComponent(store.address)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-neutral-500 hover:text-primary transition-colors"
                      >
                        <MapPin className="w-3 h-3" />
                        {store.address}
                      </a>
                    </div>
                    <a
                      href={`tel:${store.phone}`}
                      className="flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary-dark transition-colors w-fit"
                    >
                      <Phone className="w-3 h-3" />
                      {store.phone}
                    </a>
                  </div>
                ))}
              </div>

              <div className="card p-4 flex flex-col gap-3">
                <p className="font-semibold text-sm" style={{ fontFamily: 'var(--font-family-display)' }}>
                  Want us to call these stores for you?
                </p>
                <p className="text-xs text-neutral-500">
                  We'll reach out to each store, share your item details, and find out who's interested before you make the trip.
                </p>
                <div className="flex gap-3 mt-1">
                  <button
                    onClick={handleNegotiate}
                    className="btn btn-primary flex-1 py-3 justify-center text-sm"
                  >
                    <Phone className="w-4 h-4" />
                    Yes, call them
                  </button>
                  <button className="btn btn-secondary flex-1 py-3 justify-center text-sm">
                    No thanks
                  </button>
                </div>
              </div>

              <button onClick={reset} className="btn btn-secondary w-full text-sm py-3 justify-center">
                <Upload className="w-4 h-4" />
                Analyze another item
              </button>
            </div>
          )}

          {/* ── Calling ── */}
          {state === 'calling' && (
            <div className="flex flex-col gap-4">
              <div className="card p-6 flex flex-col items-center gap-4 text-center">
                <div className="relative flex items-center justify-center w-16 h-16">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-25 animate-ping" />
                  <div className="w-14 h-14 rounded-full bg-primary border-2 border-neutral-black flex items-center justify-center shadow-brutal-sm">
                    <Phone className="w-6 h-6 text-white" />
                  </div>
                </div>
                <div>
                  <p
                    className="font-extrabold text-lg mb-1"
                    style={{ fontFamily: 'var(--font-family-display)' }}
                  >
                    Our AI is calling stores
                  </p>
                  <p className="text-sm text-neutral-500">
                    We&apos;ll negotiate the best deal for you.<br />
                    Come back in about an hour.
                  </p>
                </div>
              </div>

              <Link
                href={`/offers?job_id=${jobId}`}
                className="btn btn-primary w-full text-sm py-3 justify-center"
              >
                Check my offers
              </Link>

              <button onClick={reset} className="btn btn-secondary w-full text-sm py-3 justify-center">
                <Upload className="w-4 h-4" />
                Analyze another item
              </button>
            </div>
          )}

          {/* ── Error ── */}
          {state === 'error' && (
            <div className="flex flex-col gap-4">
              <div className="card p-4 border-(--color-error) shadow-[5px_5px_0px_var(--color-error)]">
                <p className="font-semibold text-(--color-accent-red) mb-1">Something went wrong</p>
                <p className="text-sm text-neutral-700">{errorMessage}</p>
              </div>
              <button
                onClick={() => setState('preview')}
                className="btn btn-primary w-full py-3 justify-center"
              >
                Try again
              </button>
              <button onClick={reset} className="btn btn-secondary w-full py-3 justify-center">
                <Upload className="w-4 h-4" />
                Use a different photo
              </button>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
