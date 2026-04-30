import crypto from "node:crypto";
import { PRICE_AMOUNT, PRODUCT_NAME } from "../config/product";

const mercadoPagoApiUrl = "https://api.mercadopago.com/v1";

type MercadoPagoPaymentResponse = {
  id: number | string;
  status: string;
  external_reference?: string | null;
  transaction_amount?: number;
  point_of_interaction?: {
    transaction_data?: {
      qr_code?: string;
      qr_code_base64?: string;
      ticket_url?: string;
    };
  };
};

export type PixPaymentResult = {
  payment_id: string;
  status: string;
  qr_code: string | null;
  qr_code_base64: string | null;
  ticket_url: string | null;
};

function getAccessToken() {
  const accessToken = process.env.MERCADO_PAGO_ACCESS_TOKEN;

  if (!accessToken) {
    throw new Error("MERCADO_PAGO_ACCESS_TOKEN não está configurado.");
  }

  return accessToken;
}

export async function createPixPayment({
  email,
  userId,
}: {
  email: string;
  userId: string;
}): Promise<PixPaymentResult> {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  const response = await fetch(`${mercadoPagoApiUrl}/payments`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      "Content-Type": "application/json",
      "X-Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify({
      transaction_amount: PRICE_AMOUNT,
      description: `${PRODUCT_NAME} Pro`,
      payment_method_id: "pix",
      payer: { email },
      external_reference: userId,
      notification_url: `${siteUrl}/api/webhooks/mercado-pago`,
    }),
  });

  const payment = (await response.json()) as MercadoPagoPaymentResponse & {
    message?: string;
  };

  if (!response.ok) {
    throw new Error(payment.message || "Erro ao criar pagamento PIX.");
  }

  const transactionData = payment.point_of_interaction?.transaction_data;

  return {
    payment_id: String(payment.id),
    status: payment.status,
    qr_code: transactionData?.qr_code ?? null,
    qr_code_base64: transactionData?.qr_code_base64 ?? null,
    ticket_url: transactionData?.ticket_url ?? null,
  };
}

export async function getMercadoPagoPayment(paymentId: string) {
  const response = await fetch(`${mercadoPagoApiUrl}/payments/${paymentId}`, {
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
    },
  });

  const payment = (await response.json()) as MercadoPagoPaymentResponse & {
    message?: string;
  };

  if (!response.ok) {
    throw new Error(payment.message || "Erro ao consultar pagamento.");
  }

  return payment;
}

export function validateMercadoPagoSignature({
  dataId,
  requestId,
  signatureHeader,
}: {
  dataId: string;
  requestId: string | null;
  signatureHeader: string | null;
}) {
  const secret = process.env.MERCADO_PAGO_WEBHOOK_SECRET;

  if (!secret) {
    if (process.env.NODE_ENV === "production") {
      console.error("ERRO CRÍTICO: MERCADO_PAGO_WEBHOOK_SECRET não configurado em produção!");
      return false;
    }
    return true;
  }

  if (!requestId || !signatureHeader) {
    return false;
  }

  const signatureParts = Object.fromEntries(
    signatureHeader.split(",").map((part) => {
      const [key, value] = part.trim().split("=");
      return [key, value];
    }),
  );
  const timestamp = signatureParts.ts;
  const signature = signatureParts.v1;

  if (!timestamp || !signature) {
    return false;
  }

  const manifest = `id:${dataId};request-id:${requestId};ts:${timestamp};`;
  const expectedSignature = crypto
    .createHmac("sha256", secret)
    .update(manifest)
    .digest("hex");

  const expectedBuffer = Buffer.from(expectedSignature);
  const receivedBuffer = Buffer.from(signature);

  if (expectedBuffer.length !== receivedBuffer.length) {
    return false;
  }

  return crypto.timingSafeEqual(expectedBuffer, receivedBuffer);
}
