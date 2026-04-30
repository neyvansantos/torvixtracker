import { NextRequest, NextResponse } from "next/server";
import { PRICE_AMOUNT } from "@/config/product";
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

function isPaymentEvent(request: NextRequest, body: MercadoPagoWebhookBody) {
  const searchParams = request.nextUrl.searchParams;
  const queryType = searchParams.get("type");
  const queryTopic = searchParams.get("topic");
  const queryId = searchParams.get("id") || searchParams.get("data.id");

  return (
    body.type === "payment" ||
    body.topic === "payment" ||
    body.action?.startsWith("payment.") === true ||
    queryType === "payment" ||
    queryTopic === "payment" ||
    Boolean(body.data?.id) ||
    Boolean(queryId)
  );
}

function amountMatchesProduct(amount: number | undefined) {
  if (typeof amount !== "number") {
    return false;
  }

  return Math.abs(amount - PRICE_AMOUNT) < 0.001;
}

export async function POST(request: NextRequest) {
  let body: MercadoPagoWebhookBody = {};

  try {
    body = (await request.json()) as MercadoPagoWebhookBody;
  } catch {
    body = {};
  }

  console.log("[mercado-pago:webhook] recebido", {
    action: body.action,
    type: body.type,
    topic: body.topic,
  });

  if (!isPaymentEvent(request, body)) {
    console.log("[mercado-pago:webhook] evento ignorado: nao e payment");
    return NextResponse.json({ received: true, ignored: "not_payment_event" });
  }

  const paymentId = getPaymentId(request, body);

  if (!paymentId) {
    console.error("[mercado-pago:webhook] payment_id ausente");
    return NextResponse.json({ error: "payment_id ausente." }, { status: 400 });
  }

  console.log("[mercado-pago:webhook] payment_id identificado", { paymentId });

  const signatureIsValid = validateMercadoPagoSignature({
    dataId: paymentId,
    requestId: request.headers.get("x-request-id"),
    signatureHeader: request.headers.get("x-signature"),
  });

  if (!signatureIsValid) {
    console.error("[mercado-pago:webhook] assinatura invalida", { paymentId });
    return NextResponse.json({ error: "Assinatura invalida." }, { status: 400 });
  }

  try {
    const payment = await getMercadoPagoPayment(paymentId);
    const status = payment.status;
    const externalReference = payment.external_reference?.toString() || "";
    const transactionAmount = payment.transaction_amount;
    const payerEmail = payment.payer?.email || null;

    console.log("[mercado-pago:webhook] pagamento consultado", {
      paymentId: String(payment.id),
      status,
      externalReference,
      transactionAmount,
      payerEmail,
    });

    const serviceClient = createServiceRoleClient();
    const { data: purchase, error: purchaseLookupError } = await serviceClient
      .from("purchases")
      .select("id, user_id")
      .eq("mercado_pago_payment_id", paymentId)
      .maybeSingle();

    if (purchaseLookupError) {
      console.error("[mercado-pago:webhook] erro ao buscar purchase", {
        paymentId,
        error: purchaseLookupError.message,
      });
      return NextResponse.json({ error: "Erro ao buscar compra." }, { status: 500 });
    }

    const userId = externalReference || purchase?.user_id || "";

    if (!userId) {
      console.error("[mercado-pago:webhook] usuario nao identificado", {
        paymentId,
        externalReference,
        purchaseFound: Boolean(purchase),
      });
      return NextResponse.json({
        received: true,
        ignored: "user_not_found",
        status,
      });
    }

    console.log("[mercado-pago:webhook] user_id identificado", { userId });

    if (purchase) {
      const { error: purchaseUpdateError } = await serviceClient
        .from("purchases")
        .update({
          mercado_pago_status: status || "unknown",
          updated_at: new Date().toISOString(),
        })
        .eq("id", purchase.id);

      if (purchaseUpdateError) {
        console.error("[mercado-pago:webhook] erro ao atualizar purchase", {
          paymentId,
          purchaseId: purchase.id,
          error: purchaseUpdateError.message,
        });
        return NextResponse.json({ error: "Erro ao atualizar compra." }, { status: 500 });
      }

      console.log("[mercado-pago:webhook] purchase atualizada", {
        paymentId,
        purchaseId: purchase.id,
        status,
      });
    } else {
      console.error("[mercado-pago:webhook] purchase nao encontrada para payment_id", {
        paymentId,
        userId,
      });
    }

    if (status !== "approved") {
      console.log("[mercado-pago:webhook] status sem liberacao Pro", {
        paymentId,
        status,
      });
      return NextResponse.json({ received: true, status });
    }

    if (!amountMatchesProduct(transactionAmount)) {
      console.error("[mercado-pago:webhook] valor divergente, Pro nao liberado", {
        paymentId,
        transactionAmount,
        expectedAmount: PRICE_AMOUNT,
      });
      return NextResponse.json({
        received: true,
        status,
        ignored: "amount_mismatch",
      });
    }

    const { error: profileUpdateError } = await serviceClient
      .from("profiles")
      .update({
        has_pro: true,
        plan: "pro",
      })
      .eq("id", userId);

    if (profileUpdateError) {
      console.error("[mercado-pago:webhook] erro ao atualizar profile", {
        userId,
        error: profileUpdateError.message,
      });
      return NextResponse.json({ error: "Erro ao atualizar perfil." }, { status: 500 });
    }

    console.log("[mercado-pago:webhook] profile atualizado com Pro", {
      userId,
      paymentId,
    });

    return NextResponse.json({ received: true, status });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Erro ao processar webhook.";
    console.error("[mercado-pago:webhook] erro de servidor", {
      paymentId,
      error: message,
    });
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
