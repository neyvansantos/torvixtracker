import { NextRequest, NextResponse } from "next/server";
import {
  getMercadoPagoPayment,
  validateMercadoPagoSignature,
} from "@/lib/mercadoPago";
import { createServiceRoleClient } from "@/lib/supabase-server";

type MercadoPagoWebhookBody = {
  action?: string;
  type?: string;
  topic?: string;
  data?: {
    id?: string | number;
  };
};

function getPaymentId(request: NextRequest, body: MercadoPagoWebhookBody) {
  const searchParams = request.nextUrl.searchParams;
  return (
    body.data?.id?.toString() ||
    searchParams.get("data.id") ||
    searchParams.get("id") ||
    ""
  );
}

export async function POST(request: NextRequest) {
  let body: MercadoPagoWebhookBody = {};

  try {
    body = (await request.json()) as MercadoPagoWebhookBody;
  } catch {
    body = {};
  }

  const paymentId = getPaymentId(request, body);

  if (!paymentId) {
    return NextResponse.json({ error: "payment_id ausente." }, { status: 400 });
  }

  const signatureIsValid = validateMercadoPagoSignature({
    dataId: paymentId,
    requestId: request.headers.get("x-request-id"),
    signatureHeader: request.headers.get("x-signature"),
  });

  if (!signatureIsValid) {
    return NextResponse.json({ error: "Assinatura inválida." }, { status: 401 });
  }

  try {
    const payment = await getMercadoPagoPayment(paymentId);
    const status = payment.status;
    const serviceClient = createServiceRoleClient();

    const { data: purchase } = await serviceClient
      .from("purchases")
      .select("id, user_id")
      .eq("mercado_pago_payment_id", paymentId)
      .maybeSingle();

    if (!purchase) {
      return NextResponse.json({ received: true, ignored: "purchase_not_found" });
    }

    await serviceClient
      .from("purchases")
      .update({
        mercado_pago_status: status,
        updated_at: new Date().toISOString(),
      })
      .eq("id", purchase.id);

    if (status === "approved") {
      await serviceClient
        .from("profiles")
        .update({
          has_pro: true,
          plan: "pro",
        })
        .eq("id", purchase.user_id);
    }

    return NextResponse.json({ received: true, status });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Erro ao processar webhook.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
