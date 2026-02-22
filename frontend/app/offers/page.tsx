'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { UserButton } from '@clerk/nextjs';
import { Zap, Package, CheckCircle, XCircle, Clock, Printer } from 'lucide-react';
import Link from 'next/link';
import { formatPrice } from '@/lib/utils';

/* ─── Types ──────────────────────────────────────────────────────────────── */

interface OfferResult {
  id: string;
  store_name: string;
  store_address: string;
  store_phone: string;
  store_specialty: string;
  accepted: boolean;
  agreed_price: number | null;
  call_summary: string | null;
}

interface OffersData {
  job_id: string;
  status: string;
  item_name: string;
  image_url: string;
  offers: OfferResult[];
}

type PageState = 'loading' | 'ready' | 'error';

/* ─── Navbar ─────────────────────────────────────────────────────────────── */

function Navbar() {
  return (
    <nav className="sticky top-0 z-40 bg-neutral-white border-b-[3px] border-neutral-black shadow-medium">
      <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 bg-primary border-2 border-neutral-black rounded-md shadow-brutal-sm flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight" style={{ fontFamily: 'var(--font-family-display)' }}>
            FlipKit
          </span>
        </Link>
        <UserButton />
      </div>
    </nav>
  );
}

/* ─── Shipping Label ─────────────────────────────────────────────────────── */

function ShippingLabel({ offer, itemName }: { offer: OfferResult; itemName: string }) {
  const tracking = `MOCK-${offer.id.slice(0, 4).toUpperCase()}-${offer.id.slice(4, 8).toUpperCase()}`;
  return (
    <div className="card p-5 mt-3 border-2 border-dashed border-neutral-black bg-neutral-50 print:shadow-none">
      <p
        className="text-xs font-semibold text-neutral-500 uppercase tracking-widest mb-3"
        style={{ fontFamily: 'var(--font-family-mono)' }}
      >
        Shipping Label (Mock)
      </p>
      <div className="flex flex-col gap-1.5 text-sm mb-4">
        <div className="flex gap-2">
          <span className="text-neutral-500 w-14 shrink-0">From</span>
          <span className="font-semibold">You</span>
        </div>
        <div className="flex gap-2">
          <span className="text-neutral-500 w-14 shrink-0">To</span>
          <div>
            <p className="font-semibold">{offer.store_name}</p>
            <p className="text-neutral-500 text-xs">{offer.store_address}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <span className="text-neutral-500 w-14 shrink-0">Item</span>
          <span className="font-semibold">{itemName}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-neutral-500 w-14 shrink-0">Price</span>
          <span className="font-semibold text-accent-green">{formatPrice(offer.agreed_price ?? 0)}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-neutral-500 w-14 shrink-0">Track #</span>
          <span style={{ fontFamily: 'var(--font-family-mono)' }} className="text-xs">{tracking}</span>
        </div>
      </div>
      <button
        onClick={() => window.print()}
        className="btn btn-secondary w-full py-2.5 justify-center text-sm"
      >
        <Printer className="w-4 h-4" />
        Print Label
      </button>
    </div>
  );
}

/* ─── Main Page ──────────────────────────────────────────────────────────── */

function OffersContent() {
  const { getToken } = useAuth();
  const searchParams = useSearchParams();
  const jobId = searchParams.get('job_id');

  const [pageState, setPageState] = useState<PageState>('loading');
  const [data, setData] = useState<OffersData | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [acceptedOfferId, setAcceptedOfferId] = useState<string | null>(null);

  const fetchOffers = useCallback(async () => {
    if (!jobId) {
      setErrorMessage('No job ID provided.');
      setPageState('error');
      return;
    }
    try {
      const token = await getToken();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/offers?job_id=${jobId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(await res.text());
      const json: OffersData = await res.json();
      setData(json);
      setPageState('ready');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Something went wrong');
      setPageState('error');
    }
  }, [jobId, getToken]);

  useEffect(() => { fetchOffers(); }, [fetchOffers]);

  const accepted = (data?.offers.filter((o) => o.accepted) ?? []).slice(0, 2);
  const declined = (data?.offers.filter((o) => !o.accepted) ?? []).slice(0, 1);

  return (
    <div className="min-h-screen bg-neutral-50 flex flex-col">
      <Navbar />

      <main className="flex-1 flex flex-col items-center px-4 py-8">
        <div className="w-full max-w-md flex flex-col gap-4">

          {/* Header */}
          <div className="mb-2">
            <h1
              className="text-2xl font-extrabold"
              style={{ fontFamily: 'var(--font-family-display)', letterSpacing: '-0.03em' }}
            >
              Your <span className="gradient-text">Offers</span>
            </h1>
            {data?.item_name && (
              <p className="text-sm text-neutral-500 mt-0.5">{data.item_name}</p>
            )}
          </div>

          {/* ── Loading ── */}
          {pageState === 'loading' && (
            <div className="card p-6 flex flex-col items-center gap-3 text-center">
              <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="font-semibold" style={{ fontFamily: 'var(--font-family-display)' }}>
                Loading your offers…
              </p>
            </div>
          )}

          {/* ── Error ── */}
          {pageState === 'error' && (
            <div className="card p-4 border-error shadow-[5px_5px_0px_var(--color-error)]">
              <p className="font-semibold text-accent-red mb-1">Something went wrong</p>
              <p className="text-sm text-neutral-700">{errorMessage}</p>
            </div>
          )}

          {/* ── Ready: still in progress ── */}
          {pageState === 'ready' && data?.status !== 'done' && (
            <div className="card p-6 flex flex-col items-center gap-3 text-center">
              <Clock className="w-10 h-10 text-neutral-400" />
              <p className="font-semibold" style={{ fontFamily: 'var(--font-family-display)' }}>
                Calls still in progress
              </p>
              <p className="text-sm text-neutral-500">
                Refresh this page to check for new offers.
              </p>
              <button onClick={fetchOffers} className="btn btn-secondary py-2.5 px-5 text-sm">
                Refresh
              </button>
            </div>
          )}

          {/* ── Ready: done ── */}
          {pageState === 'ready' && data?.status === 'done' && (
            <>
              {/* Accepted offers */}
              {accepted.length > 0 ? (
                <div className="flex flex-col gap-3">
                  <p
                    className="text-xs font-semibold text-neutral-500 uppercase tracking-widest"
                    style={{ fontFamily: 'var(--font-family-mono)' }}
                  >
                    Accepted Offers
                  </p>
                  {accepted.map((offer) => (
                    <div key={offer.id}>
                      <div className="card p-4 flex flex-col gap-2">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="font-semibold text-sm">{offer.store_name}</p>
                            <p className="text-xs text-neutral-500">{offer.store_specialty}</p>
                          </div>
                          <span className="badge badge-success flex items-center gap-1 shrink-0">
                            <CheckCircle className="w-3 h-3" />
                            Offer
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5 mt-1">
                          <Package className="w-4 h-4 text-neutral-400 shrink-0" />
                          <p className="text-base font-extrabold" style={{ fontFamily: 'var(--font-family-display)' }}>
                            {formatPrice(offer.agreed_price ?? 0)}
                          </p>
                          <span className="text-xs text-neutral-500">agreed</span>
                        </div>

                        {offer.call_summary && (
                          <p className="text-xs text-neutral-600 italic border-l-2 border-neutral-200 pl-2">
                            &ldquo;{offer.call_summary}&rdquo;
                          </p>
                        )}

                        <button
                          onClick={() =>
                            setAcceptedOfferId(acceptedOfferId === offer.id ? null : offer.id)
                          }
                          className="btn btn-primary w-full py-2.5 justify-center text-sm mt-1"
                        >
                          {acceptedOfferId === offer.id ? 'Hide label' : 'Accept & Get Shipping Label'}
                        </button>
                      </div>

                      {acceptedOfferId === offer.id && (
                        <ShippingLabel offer={offer} itemName={data.item_name} />
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="card p-5 text-center">
                  <p className="font-semibold text-neutral-700">No stores accepted this time.</p>
                  <p className="text-sm text-neutral-500 mt-1">Try listing on a platform directly.</p>
                </div>
              )}

              {/* Declined offers */}
              {declined.length > 0 && (
                <div className="flex flex-col gap-2 mt-2">
                  <p
                    className="text-xs font-semibold text-neutral-500 uppercase tracking-widest"
                    style={{ fontFamily: 'var(--font-family-mono)' }}
                  >
                    Not Interested
                  </p>
                  {declined.map((offer) => (
                    <div
                      key={offer.id}
                      className="card p-3 flex items-center justify-between opacity-50"
                    >
                      <div>
                        <p className="font-semibold text-sm">{offer.store_name}</p>
                        <p className="text-xs text-neutral-500">{offer.store_specialty}</p>
                      </div>
                      <XCircle className="w-4 h-4 text-neutral-400 shrink-0" />
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          <Link href="/home" className="btn btn-secondary w-full py-3 justify-center text-sm mt-2">
            Back to FlipKit
          </Link>

        </div>
      </main>
    </div>
  );
}

export default function OffersPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <OffersContent />
    </Suspense>
  );
}
