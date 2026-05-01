// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import { NextRequest, NextResponse } from "next/server";
import { PRICE_AMOUNT } from "@/config/product";
import { getMercadoPagoPayment } from "@/lib/mercadoPago";
import {
  createServerAnonClient,
  createServiceRoleClient,
} from "@/lib/supabase-server";

type PurchaseRow = {
  id: string;
  user_id: string;
  mercado_pago_payment_id: string | null;
  mercado_pago_status: string | null;
  amount: number | null;
};

function amountMatchesProduct(amount: number | undefined) {
  if (typeof amount !== "number") {
    return false;
  }

  return Math.abs(amount - PRICE_AMOUNT) < 0.001;
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = request.headers.get("authorization");
    const accessToken = authHeader?.replace("Bearer ", "");

    if (!accessToken) {
      return NextResponse.json({ error: "Usuario nao autenticado." }, { status: 401 });
    }

    const authClient = createServerAnonClient();
    const {
      data: { user },
      error: userError,
    } = await authClient.auth.getUser(accessToken);

    if (userError || !user) {
      return NextResponse.json({ error: "Usuario nao autenticado." }, { status: 401 });
    }

    const serviceClient = createServiceRoleClient();
    const { data: purchases, error: purchasesError } = await serviceClient
      .from("purchases")
      .select("id, user_id, mercado_pago_payment_id, mercado_pago_status, amount")
      .eq("user_id", user.id)
      .neq("mercado_pago_status", "approved")
      .order("created_at", { ascending: false })
      .limit(5);

    if (purchasesError) {
      console.error("[checkout:sync-payment] erro ao buscar purchases", {
        userId: user.id,
        error: purchasesError.message,
      });
      return NextResponse.json({ error: "Erro ao buscar compras." }, { status: 500 });
    }

    const rows = (purchases || []) as PurchaseRow[];
    console.log("[checkout:sync-payment] verificando compras", {
      userId: user.id,
      count: rows.length,
    });

    for (const purchase of rows) {
      if (!purchase.mercado_pago_payment_id) {
        continue;
      }

      const payment = await getMercadoPagoPayment(purchase.mercado_pago_payment_id);
      const status = payment.status || "unknown";

      console.log("[checkout:sync-payment] pagamento consultado", {
        userId: user.id,
        paymentId: purchase.mercado_pago_payment_id,
        status,
        amount: payment.transaction_amount,
      });

      const { error: purchaseUpdateError } = await serviceClient
        .from("purchases")
        .update({
          mercado_pago_status: status,
          updated_at: new Date().toISOString(),
        })
        .eq("id", purchase.id);

      if (purchaseUpdateError) {
        console.error("[checkout:sync-payment] erro ao atualizar purchase", {
          purchaseId: purchase.id,
          error: purchaseUpdateError.message,
        });
        return NextResponse.json({ error: "Erro ao atualizar compra." }, { status: 500 });
      }

      if (status !== "approved") {
        continue;
      }

      if (!amountMatchesProduct(payment.transaction_amount)) {
        console.error("[checkout:sync-payment] valor divergente, Pro nao liberado", {
          userId: user.id,
          paymentId: purchase.mercado_pago_payment_id,
          transactionAmount: payment.transaction_amount,
          expectedAmount: PRICE_AMOUNT,
        });
        continue;
      }

      const { error: profileUpdateError } = await serviceClient
        .from("profiles")
        .update({
          has_pro: true,
          plan: "pro",
        })
        .eq("id", user.id);

      if (profileUpdateError) {
        console.error("[checkout:sync-payment] erro ao atualizar profile", {
          userId: user.id,
          error: profileUpdateError.message,
        });
        return NextResponse.json({ error: "Erro ao atualizar perfil." }, { status: 500 });
      }

      console.log("[checkout:sync-payment] Pro liberado", {
        userId: user.id,
        paymentId: purchase.mercado_pago_payment_id,
      });

      return NextResponse.json({
        has_pro: true,
        status: "approved",
        payment_id: purchase.mercado_pago_payment_id,
      });
    }

    return NextResponse.json({ has_pro: false, status: "not_approved" });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Erro ao verificar pagamento.";
    console.error("[checkout:sync-payment] erro de servidor", { error: message });
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
