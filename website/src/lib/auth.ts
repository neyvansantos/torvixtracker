// Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
import type { User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

export type UserProfile = {
  plan: "free" | "pro" | string | null;
  has_pro: boolean | null;
};

export async function getCurrentUser(): Promise<User | null> {
  const { data, error } = await supabase.auth.getUser();

  if (error) {
    return null;
  }

  return data.user;
}

export async function getUserProfile(
  userId: string,
): Promise<UserProfile | null> {
  const { data, error } = await supabase
    .from("profiles")
    .select("plan, has_pro")
    .eq("id", userId)
    .maybeSingle<UserProfile>();

  if (error) {
    return null;
  }

  return data;
}
