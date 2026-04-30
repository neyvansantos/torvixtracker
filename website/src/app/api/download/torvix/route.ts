import { readFile, stat } from "node:fs/promises";
import { NextRequest, NextResponse } from "next/server";
import {
  createServerAnonClient,
  createServiceRoleClient,
} from "@/lib/supabase-server";

function getInstallerPath() {
  return process.env.TORVIX_INSTALLER_PATH || "private/TorvixInstaller.exe";
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

  const installerPath = getInstallerPath();

  try {
    const installerStat = await stat(installerPath);
    const installer = await readFile(installerPath);

    return new NextResponse(installer, {
      headers: {
        "Content-Disposition": 'attachment; filename="TorvixInstaller.exe"',
        "Content-Length": installerStat.size.toString(),
        "Content-Type": "application/vnd.microsoft.portable-executable",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Instalador não encontrado no servidor." },
      { status: 404 },
    );
  }
}
