// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import { NextRequest, NextResponse } from "next/server";
import {
  createServerAnonClient,
  createServiceRoleClient,
} from "@/lib/supabase-server";

const DEFAULT_DOWNLOAD_URL =
  "https://github.com/NeyvanSantos/TorvixTracker/releases/latest/download/TorvixTracker_Setup.rar";
const RELEASES_URL = "https://github.com/NeyvanSantos/TorvixTracker/releases/latest";

function installerDownloadUrl() {
  const configuredUrl = process.env.TORVIX_INSTALLER_DOWNLOAD_URL?.trim();
  if (!configuredUrl || configuredUrl.includes("/releases/download/Tracker/")) {
    return DEFAULT_DOWNLOAD_URL;
  }
  return configuredUrl;
}

export async function POST(request: NextRequest) {
  const authHeader = request.headers.get("authorization");
  const accessToken = authHeader?.replace("Bearer ", "");

  if (!accessToken) {
    return NextResponse.json({ error: "Usuário não autenticado." }, { status: 401 });
  }

  const authClient = createServerAnonClient();
  const {
    data: { user },
    error: userError,
  } = await authClient.auth.getUser(accessToken);

  if (userError || !user) {
    return NextResponse.json({ error: "Usuário não autenticado." }, { status: 401 });
  }

  const serviceClient = createServiceRoleClient();
  const { data: profile, error: profileError } = await serviceClient
    .from("profiles")
    .select("has_pro")
    .eq("id", user.id)
    .maybeSingle();

  if (profileError || profile?.has_pro !== true) {
    return NextResponse.json({ error: "Acesso Pro necessário." }, { status: 403 });
  }

  return NextResponse.json({
    download_url: installerDownloadUrl(),
    releases_url: RELEASES_URL,
  });
}
