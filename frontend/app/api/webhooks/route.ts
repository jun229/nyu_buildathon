import { verifyWebhook } from "@clerk/nextjs/webhooks";
import { NextRequest } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_SECRET!,
);

export async function POST(req: NextRequest) {
  try {
    const evt = await verifyWebhook(req);

    if (evt.type === "user.created") {
      const { id, email_addresses, first_name, last_name } = evt.data;

      if (!id || !email_addresses || email_addresses.length === 0) {
        console.error("Missing required user data in webhook payload:", {
          id,
          email_addresses,
        });
        return new Response("Invalid webhook payload", { status: 400 });
      }

      const { error } = await supabase.from("users").insert({
        user_id: id,
        email: email_addresses[0].email_address,
        first_name: first_name || null,
        last_name: last_name || null,
      });

      if (error) {
        console.error("Error inserting user into database:", error);
        return new Response("Database error", { status: 500 });
      }
    }

    return new Response("Webhook processed successfully", { status: 200 });
  } catch (err) {
    console.error("Error processing webhook:", err);
    return new Response("Webhook error", { status: 400 });
  }
}
