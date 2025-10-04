//
//  ContentView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI
import Supabase

struct ContentView: View {
    @State private var session: Session?
    @State private var isLoading = true

    var body: some View {
        Group {
            if isLoading {
                ProgressView("Loading...")
            } else if session != nil {
                MainTabView()
            } else {
                AuthView()
            }
        }
        .task {
            await observeAuthState()
        }
    }

    private func observeAuthState() async {
        // Get initial session
        do {
            session = try await supabase.auth.session
        } catch {
            session = nil
        }
        isLoading = false

        // Listen for auth state changes
        for await state in supabase.auth.authStateChanges {
            switch state.event {
            case .signedIn:
                session = state.session
            case .signedOut:
                session = nil
            default:
                break
            }
        }
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "house")
                }

            FoodView()
                .tabItem {
                    Label("Food", systemImage: "pawprint")
                }

            MedicationView()
                .tabItem {
                    Label("Medication", systemImage: "syringe")
                }

            HealthView()
                .tabItem {
                    Label("Health", systemImage: "heart")
                }

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
        }
    }
}

struct DashboardView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Dashboard")
                    .font(.largeTitle)
                Text("Placeholder content")
            }
            .navigationTitle("Dashboard")
        }
    }
}

struct FoodView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Food")
                    .font(.largeTitle)
                Text("Placeholder content")
            }
            .navigationTitle("Food")
        }
    }
}

struct MedicationView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Medication")
                    .font(.largeTitle)
                Text("Placeholder content")
            }
            .navigationTitle("Medication")
        }
    }
}

struct HealthView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Health")
                    .font(.largeTitle)
                Text("Placeholder content")
            }
            .navigationTitle("Health")
        }
    }
}

struct SettingsView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Settings")
                    .font(.largeTitle)
                Text("Placeholder content")
            }
            .navigationTitle("Settings")
        }
    }
}

#Preview {
    ContentView()
}
