// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

// Type for database webhook payload
interface WebhookPayload {
  type: "INSERT" | "UPDATE" | "DELETE";
  table: string;
  schema: string;
  record: {
    id: string;
    category_id?: string; // for events
    name?: string; // for categories
    notes?: string | null; // for events
    pet_id?: string; // for categories
  };
  old_record: Record<string, unknown> | null;
}

// Initialize the Supabase client
const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
const supabaseServiceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const supabase = createClient(supabaseUrl, supabaseServiceRoleKey);

// Initialize the embedding model (gte-small, 384 dimensions)
const model = new Supabase.ai.Session("gte-small");

Deno.serve(async (req) => {
  try {
    const payload: WebhookPayload = await req.json();
    console.log("Webhook received:", {
      type: payload.type,
      table: payload.table,
      id: payload.record.id,
    });

    // Only process INSERT and UPDATE events
    if (payload.type === "DELETE") {
      return new Response("Skipping DELETE event", { status: 200 });
    }

    const { table, record } = payload;
    let textToEmbed: string;

    if (table === "pet_health_categories") {
      // For categories, embed the category name
      textToEmbed = record.name || "";
      console.log("Embedding category:", textToEmbed);
    } else if (table === "pet_health_events") {
      // For events, get the category name and combine with notes
      const { data: category, error: categoryError } = await supabase
        .from("pet_health_categories")
        .select("name")
        .eq("id", record.category_id!)
        .single();

      if (categoryError) {
        console.error("Error fetching category:", categoryError);
        throw categoryError;
      }

      // Combine category name with notes
      textToEmbed = category.name;
      if (record.notes && record.notes.trim() !== "") {
        textToEmbed += ". " + record.notes;
      }
      console.log("Embedding event:", textToEmbed);
    } else {
      return new Response("Unknown table: " + table, { status: 400 });
    }

    // Generate embedding using gte-small model
    const embedding = await model.run(textToEmbed, {
      mean_pool: true, // Pool token embeddings into a single vector
      normalize: true, // Normalize to unit length (required for inner product)
    });

    console.log("Generated embedding with dimension:", embedding.length);

    // Update the record with the embedding
    const { error: updateError } = await supabase
      .from(table)
      .update({ embedding: JSON.stringify(embedding) })
      .eq("id", record.id);

    if (updateError) {
      console.error("Error updating embedding:", updateError);
      throw updateError;
    }

    console.log("Successfully updated embedding for:", record.id);

    return new Response(
      JSON.stringify({
        success: true,
        id: record.id,
        table: table,
        embeddingDimensions: embedding.length,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    console.error("Error processing webhook:", error);
    return new Response(
      JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : String(error),
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
});
