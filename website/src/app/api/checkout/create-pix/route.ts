import { NextRequest, NextResponse } from "next/server";
import { PRICE_AMOUNT, PRODUCT_NAME } from "@/config/product";
import { createPixPayment } from "@/lib/mercadoPago";
import {
  createServerAnonClient,
  createServiceRoleClient,
} from "@/lib/supabase-server";

export async function POST(request: NextRequest) {
  try {
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

    if (userError || !user?.email) {
      return NextResponse.json({ error: "Usuário não autenticado." }, { status: 401 });
    }

    const serviceClient = createServiceRoleClient();
    const { data: profile } = await serviceClient
      .from("profiles")
      .select("id, email, plan, has_pro")
      .eq("id", user.id)
      .maybeSingle();

    if (profile?.has_pro === true) {
      return NextResponse.json({ already_pro: true, status: "approved" });
    }

    if (!profile) {
      await serviceClient.from("profiles").insert({
        id: user.id,
        email: user.email,
        plan: "free",
        has_pro: false,
      });
    }

    const pixPayment = await createPixPayment({
      email: user.email,
      userId: user.id,
    });

    const paymentStatus = pixPayment.status || "pending";
    const { error: purchaseError } = await serviceClient.from("purchases").insert({
      user_id: user.id,
      mercado_pago_payment_id: pixPayment.payment_id,
      mercado_pago_status: paymentStatus,
      amount: PRICE_AMOUNT,
      product_name: PRODUCT_NAME,
    });

    if (purchaseError) {
      return NextResponse.json(
        { error: "Pagamento criado, mas não foi possível salvar a compra." },
        { status: 500 },
      );
    }

    return NextResponse.json(pixPayment);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Erro ao criar pagamento PIX.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
