//
//  SupabaseClient.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation
import Supabase

let supabase: SupabaseClient = {
    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601

    let encoder = JSONEncoder()
    encoder.dateEncodingStrategy = .iso8601

    // Toggle between local (via ngrok), simulator local, and production
    let useLocal = true  // Set to false to use production Supabase

    let url = useLocal
        ? "https://climbing-helping-hermit.ngrok-free.app"  // ngrok tunnel to local Supabase
        // ? "http://127.0.0.1:54321"  // Use this for simulator only
        : "https://mtfuyemqypyqibqthrmc.supabase.co"

    let key = useLocal
        ? "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"  // Local Supabase anon key
        : "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im10ZnV5ZW1xeXB5cWlicXRocm1jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk1NzIzOTQsImV4cCI6MjA3NTE0ODM5NH0.grDMwJ1OAELh4W-6dv7sIkA-reLzMJMI7wauTUkNYFM"

    return SupabaseClient(
        supabaseURL: URL(string: url)!,
        supabaseKey: key,
        options: SupabaseClientOptions(
            db: SupabaseClientOptions.DatabaseOptions(
                encoder: encoder,
                decoder: decoder
            )
        )
    )
}()
