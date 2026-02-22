'use client';

import { useRef, useState, useCallback } from 'react';
import { UserButton } from '@clerk/nextjs';
import { Camera, Upload, X, Zap, ImageIcon } from 'lucide-react';
import Link from 'next/link';

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

type UploadState = 'idle' | 'preview';

export default function HomePage() {
  const [state, setState] = useState<UploadState>('idle');
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
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
    setState('idle');
  };

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

          {state === 'idle' ? (
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
          ) : (
            /* Preview state */
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

              <button className="btn btn-primary w-full text-base py-4 justify-center">
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
        </div>
      </main>
    </div>
  );
}
