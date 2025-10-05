// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts";

// Initialize the embedding model (gte-small, 384 dimensions)
const model = new Supabase.ai.Session("gte-small");

interface RequestBody {
  query: string;
}

Deno.serve(async (req) => {
  try {
    // Parse request body
    const { query }: RequestBody = await req.json();

    if (!query || typeof query !== "string" || query.trim() === "") {
      return new Response(
        JSON.stringify({
          success: false,
          error: "Query parameter is required and must be a non-empty string",
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    console.log("Generating embedding for query:", query);

    // Generate embedding using gte-small model
    const embedding = await model.run(query, {
      mean_pool: true, // Pool token embeddings into a single vector
      normalize: true, // Normalize to unit length (required for inner product)
    });

    console.log("Generated embedding with dimension:", embedding.length);

    return new Response(
      JSON.stringify({
        success: true,
        query: query,
        embedding: embedding,
        dimensions: embedding.length,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    console.error("Error generating embedding:", error);
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
