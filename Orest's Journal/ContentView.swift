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
    @State private var hasFamily = false
    @State private var hasPet = false
    @State private var isCheckingStatus = false
    @State private var showError = false
    @State private var errorMessage = ""

    var body: some View {
        Group {
            if isLoading {
                ProgressView("Loading...")
            } else if session != nil {
                if isCheckingStatus {
                    ProgressView("Setting up...")
                } else if !hasFamily {
                    FamilySetupView()
                } else if !hasPet {
                    AddPetView()
                } else {
                    MainTabView()
                }
            } else {
                AuthView()
            }
        }
        .task {
            await observeAuthState()
        }
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("RefreshFamilyStatus"))) { _ in
            Task {
                await checkFamilyAndPetStatus()
            }
        }
        .alert("Error Loading Data", isPresented: $showError) {
            Button("OK") {
                showError = false
            }
        } message: {
            Text(errorMessage)
        }
    }

    private func observeAuthState() async {
        // Get initial session
        do {
            session = try await supabase.auth.session
            if session != nil {
                await checkFamilyAndPetStatus()
            }
        } catch {
            session = nil
        }
        isLoading = false

        // Listen for auth state changes
        for await state in supabase.auth.authStateChanges {
            switch state.event {
            case .signedIn:
                session = state.session
                await checkFamilyAndPetStatus()
            case .signedOut:
                session = nil
                hasFamily = false
                hasPet = false
            default:
                break
            }
        }
    }

    private func checkFamilyAndPetStatus() async {
        isCheckingStatus = true
        do {
            let status = try await SupabaseService.shared.checkUserFamilyAndPet()
            hasFamily = status.hasFamily
            hasPet = status.hasPet
            print("✅ Family/Pet status loaded: hasFamily=\(hasFamily), hasPet=\(hasPet)")
        } catch {
            print("❌ Error checking family/pet status: \(error)")
            print("❌ Error details: \(error.localizedDescription)")

            // Show error to user for debugging
            errorMessage = "Failed to load family/pet data: \(error.localizedDescription)\n\nThis might be a database permissions issue. Check Xcode console for details."
            showError = true

            hasFamily = false
            hasPet = false
        }
        isCheckingStatus = false
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
    @State private var foods: [PetFood] = []
    @State private var isLoading = true
    @State private var showAddFood = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            ZStack {
                if isLoading {
                    ProgressView()
                } else if foods.isEmpty {
                    // Empty state - show plus button
                    Button(action: {
                        showAddFood = true
                    }) {
                        VStack(spacing: 16) {
                            Image(systemName: "plus.circle.fill")
                                .font(.system(size: 60))
                                .foregroundColor(.blue)
                            Text("Add Pet Food")
                                .font(.headline)
                        }
                    }
                } else {
                    // Show foods in horizontal scroll
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 16) {
                            ForEach(foods) { food in
                                FoodCardView(food: food)
                                    .containerRelativeFrame(.horizontal)
                            }
                        }
                        .scrollTargetLayout()
                    }
                    .scrollTargetBehavior(.viewAligned)
                }
            }
            .navigationTitle("Food")
            .toolbar {
                if !foods.isEmpty {
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Button(action: {
                            showAddFood = true
                        }) {
                            Image(systemName: "plus")
                        }
                    }
                }
            }
            .sheet(isPresented: $showAddFood) {
                AddFoodView()
            }
            .task {
                await loadFoods()
            }
            .refreshable {
                await loadFoods()
            }
        }
    }

    private func loadFoods() async {
        isLoading = true
        do {
            guard let family = try await SupabaseService.shared.getCurrentUserFamily() else {
                errorMessage = "No family found"
                isLoading = false
                return
            }

            foods = try await SupabaseService.shared.getFamilyFoods(familyId: family.id)
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading foods: \(error)")
        }
        isLoading = false
    }
}

struct FoodCardView: View {
    let food: PetFood

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Food Image
            if let imageUrl = food.imageUrl, let url = URL(string: imageUrl) {
                AsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .overlay(ProgressView())
                }
                .frame(height: 200)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            } else {
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 200)
                    .overlay(
                        Image(systemName: "photo")
                            .font(.largeTitle)
                            .foregroundColor(.gray)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            }

            // Food Details
            VStack(alignment: .leading, spacing: 8) {
                Text(food.name)
                    .font(.title2)
                    .fontWeight(.bold)

                HStack {
                    Text(food.category.displayName)
                        .font(.subheadline)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(categoryColor(for: food.category))
                        .foregroundColor(.white)
                        .clipShape(Capsule())

                    Spacer()
                }

                Divider()

                HStack {
                    VStack(alignment: .leading) {
                        Text("Calories")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text("\(Int(food.caloriesPerContainer)) cal")
                            .font(.headline)
                    }

                    Spacer()

                    VStack(alignment: .leading) {
                        Text("Container Size")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text("\(Int(food.containerSizeGrams)) g")
                            .font(.headline)
                    }
                }
            }
            .padding()
            .background(Color(UIColor.systemBackground))

            Spacer()
        }
        .background(Color(UIColor.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(radius: 4)
        .padding(.vertical)
    }

    private func categoryColor(for category: FoodCategory) -> Color {
        switch category {
        case .dry:
            return .orange
        case .wet:
            return .blue
        case .snack:
            return .green
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
