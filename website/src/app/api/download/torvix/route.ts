// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import { createHmac, timingSafeEqual } from "node:crypto";
import { createReadStream } from "node:fs";
import { open, stat } from "node:fs/promises";
import path from "node:path";
import { Readable } from "node:stream";
import { NextRequest, NextResponse } from "next/server";
import {
  createServerAnonClient,
  createServiceRoleClient,
} from "@/lib/supabase-server";

export const runtime = "nodejs";

const DEFAULT_DOWNLOAD_URL =
  "https://www.dropbox.com/scl/fi/3apjnkwcx6r71zwoq4xy5/TorvixTracker_Setup.exe?rlkey=836cx4wubb9qe4l5cze5npzh8&st=slpwf6ww&dl=1";
const DOWNLOAD_TOKEN_TTL_MS = 10 * 60 * 1000;
const DEFAULT_INSTALLER_VERSION = "0.1.6";
const MIN_INSTALLER_SIZE_BYTES = 1024 * 1024;

function installerDownloadUrl() {
  const configuredUrl = process.env.TORVIX_INSTALLER_DOWNLOAD_URL?.trim();
  if (!configuredUrl || configuredUrl.includes("/releases/download/Tracker/")) {
    return DEFAULT_DOWNLOAD_URL;
  }
  return configuredUrl;
}

function installerVersion(downloadUrl: string) {
  const versionMatch = downloadUrl.match(/\/releases\/download\/v?([^/]+)\//i);
  const fileVersionMatch = downloadUrl.match(/TorvixTracker_Setup_v([^/.]+(?:\.[^/.]+)*)\.exe/i);
  return versionMatch?.[1] || fileVersionMatch?.[1] || DEFAULT_INSTALLER_VERSION;
}

function downloadTokenSecret() {
  return (
    process.env.TORVIX_DOWNLOAD_SIGNING_SECRET?.trim() ||
    process.env.SUPABASE_SERVICE_ROLE_KEY?.trim() ||
    ""
  );
}

function signDownloadToken(userId: string) {
  const secret = downloadTokenSecret();
  if (!secret) {
    return null;
  }

  const payload = Buffer.from(
    JSON.stringify({
      exp: Date.now() + DOWNLOAD_TOKEN_TTL_MS,
      sub: userId,
    }),
  ).toString("base64url");
  const signature = createHmac("sha256", secret).update(payload).digest("base64url");

  return `${payload}.${signature}`;
}

function verifyDownloadToken(token: string | null) {
  const secret = downloadTokenSecret();
  if (!token || !secret) {
    return null;
  }

  const [payload, signature] = token.split(".");
  if (!payload || !signature) {
    return null;
  }

  const expectedSignature = createHmac("sha256", secret).update(payload).digest("base64url");
  const signatureBuffer = Buffer.from(signature);
  const expectedSignatureBuffer = Buffer.from(expectedSignature);

  if (
    signatureBuffer.length !== expectedSignatureBuffer.length ||
    !timingSafeEqual(signatureBuffer, expectedSignatureBuffer)
  ) {
    return null;
  }

  let data: { exp?: number; sub?: string };

  try {
    data = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as {
      exp?: number;
      sub?: string;
    };
  } catch {
    return null;
  }

  if (!data.sub || !data.exp || data.exp < Date.now()) {
    return null;
  }

  return data.sub;
}

async function hasProAccess(userId: string) {
  const serviceClient = createServiceRoleClient();
  const { data: profile, error: profileError } = await serviceClient
    .from("profiles")
    .select("has_pro")
    .eq("id", userId)
    .maybeSingle();

  return !profileError && profile?.has_pro === true;
}

function installerFileName(version: string) {
  return `TorvixTracker_Setup_v${version}.exe`;
}

async function localInstaller(version: string) {
  const fileName = installerFileName(version);
  const filePath = path.join(/* turbopackIgnore: true */ process.cwd(), "private", fileName);

  try {
    const fileStat = await stat(filePath);
    const file = await open(filePath, "r");
    const buffer = Buffer.alloc(128);
    const { bytesRead } = await file.read(buffer, 0, buffer.length, 0);
    await file.close();
    const header = buffer.subarray(0, bytesRead).toString("utf8");

    if (
      fileStat.size < MIN_INSTALLER_SIZE_BYTES ||
      header.includes("version https://git-lfs.github.com/spec/v1")
    ) {
      return null;
    }

    return {
      fileName,
      filePath,
      size: fileStat.size,
    };
  } catch {
    return null;
  }
}

function githubDownloadHeaders() {
  const githubToken = process.env.GITHUB_TOKEN?.trim() || process.env.GH_TOKEN?.trim();
  const headers: HeadersInit = {
    Accept: "application/octet-stream",
  };

  if (githubToken) {
    headers.Authorization = `Bearer ${githubToken}`;
  }

  return headers;
}

export async function GET(request: NextRequest) {
  const userId = verifyDownloadToken(request.nextUrl.searchParams.get("token"));
  if (!userId) {
    return NextResponse.json({ error: "Link de download inválido ou expirado." }, { status: 401 });
  }

  if (!(await hasProAccess(userId))) {
    return NextResponse.json({ error: "Acesso Pro necessário." }, { status: 403 });
  }

  const downloadUrl = installerDownloadUrl();
  const version = installerVersion(downloadUrl);
  const installer = await localInstaller(version);

  if (installer) {
    const installerStream = Readable.toWeb(createReadStream(installer.filePath)) as unknown as ReadableStream;

    return new NextResponse(installerStream, {
      headers: {
        "Content-Disposition": `attachment; filename="${installer.fileName}"`,
        "Content-Length": installer.size.toString(),
        "Content-Type": "application/octet-stream",
      },
    });
  }

  const installerResponse = await fetch(downloadUrl, {
    headers: githubDownloadHeaders(),
    redirect: "follow",
  });

  if (!installerResponse.ok || !installerResponse.body) {
    return NextResponse.json(
      { error: "Não foi possível carregar o instalador privado." },
      { status: 502 },
    );
  }

  const remoteSize = Number(installerResponse.headers.get("content-length") || 0);
  if (remoteSize > 0 && remoteSize < MIN_INSTALLER_SIZE_BYTES) {
    return NextResponse.json(
      { error: "O arquivo do instalador está incompleto no servidor." },
      { status: 502 },
    );
  }

  return new NextResponse(installerResponse.body, {
    headers: {
      "Content-Disposition": `attachment; filename="${installerFileName(version)}"`,
      "Content-Type": installerResponse.headers.get("content-type") || "application/octet-stream",
    },
  });
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

  if (!(await hasProAccess(user.id))) {
    return NextResponse.json({ error: "Acesso Pro necessário." }, { status: 403 });
  }

  const downloadUrl = installerDownloadUrl();
  const version = installerVersion(downloadUrl);
  const token = signDownloadToken(user.id);

  if (!token) {
    return NextResponse.json(
      { error: "Servidor de download não configurado." },
      { status: 500 },
    );
  }

  return NextResponse.json({
    download_name: `Torvix Tracker Setup v${version}`,
    download_url: `/api/download/torvix?token=${encodeURIComponent(token)}`,
    version,
  });
}
