// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import { NextRequest, NextResponse } from "next/server";
import {
  createServerAnonClient,
  createServiceRoleClient,
} from "@/lib/supabase-server";

type PurchaseRow = {
  amount: number | null;
  created_at: string | null;
  id: string;
  mercado_pago_status: string | null;
  product_name: string | null;
};

export async function GET(request: NextRequest) {
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
  const { data, error } = await serviceClient
    .from("purchases")
    .select("id, created_at, mercado_pago_status, amount, product_name")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(10);

  if (error) {
    return NextResponse.json({ error: "Não foi possível carregar os pedidos." }, { status: 500 });
  }

  return NextResponse.json({
    orders: ((data || []) as PurchaseRow[]).map((purchase) => ({
      amount: purchase.amount,
      created_at: purchase.created_at,
      id: purchase.id,
      payment_status: purchase.mercado_pago_status,
      product_name: purchase.product_name,
    })),
  });
}
