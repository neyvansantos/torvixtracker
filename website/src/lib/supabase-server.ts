// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

export function createServerAnonClient() {
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error("Supabase público não está configurado.");
  }

  return createClient(supabaseUrl, supabaseAnonKey);
}

export function createServiceRoleClient() {
  if (!supabaseUrl || !supabaseServiceRoleKey) {
    throw new Error("Supabase service role não está configurado.");
  }

  return createClient(supabaseUrl, supabaseServiceRoleKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}
