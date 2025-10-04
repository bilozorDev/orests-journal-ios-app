//
//  SupabaseClient.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation
import Supabase

let supabase = SupabaseClient(
    supabaseURL: URL(string: "https://mtfuyemqypyqibqthrmc.supabase.co")!,
    supabaseKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im10ZnV5ZW1xeXB5cWlicXRocm1jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk1NzIzOTQsImV4cCI6MjA3NTE0ODM5NH0.grDMwJ1OAELh4W-6dv7sIkA-reLzMJMI7wauTUkNYFM"
)
