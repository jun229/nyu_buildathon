'use client'
import { useSession } from '@clerk/nextjs'
import { createClient, SupabaseClient } from '@supabase/supabase-js'

export function createSupabaseClient(): SupabaseClient {
  const { session } = useSession()

  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      async accessToken() {
        return session?.getToken() ?? null
      },
    },
  )
}