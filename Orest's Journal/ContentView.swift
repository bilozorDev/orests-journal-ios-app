//
//  ContentView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI
import Clerk

struct ContentView: View {
    @ObservedObject private var clerkManager = ClerkManager.shared
    @State private var isLoading = true
    @State private var hasPet = false
    @State private var isCheckingStatus = false
    @State private var showError = false
    @State private var errorMessage = ""

    var body: some View {
        Group {
            if isLoading || !clerkManager.isLoaded {
                ProgressView("Loading...")
            } else if clerkManager.isSignedIn {
                if isCheckingStatus {
                    ProgressView("Setting up...")
                } else if !clerkManager.hasOrganization {
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
            await clerkManager.configure()
            if clerkManager.isSignedIn {
                await checkPetStatus()
            }
            isLoading = false
        }
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("RefreshFamilyStatus"))) { _ in
            Task {
                await clerkManager.loadOrganizations()
                await checkPetStatus()
            }
        }
        .onChange(of: clerkManager.isSignedIn) { _, isSignedIn in
            if isSignedIn {
                Task {
                    await checkPetStatus()
                }
            } else {
                hasPet = false
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

    private func checkPetStatus() async {
        guard clerkManager.hasOrganization else {
            hasPet = false
            return
        }

        isCheckingStatus = true
        do {
            let pets = try await DataService.shared.getPets()
            hasPet = !pets.isEmpty
            print("✅ Pet status loaded: hasPet=\(hasPet)")
        } catch {
            print("❌ Error checking pet status: \(error)")
            print("❌ Error details: \(error.localizedDescription)")

            errorMessage = "Failed to load pet data: \(error.localizedDescription)"
            showError = true

            hasPet = false
        }
        isCheckingStatus = false
    }
}

struct MainTabView: View {
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "house")
                }
                .tag(0)

            FoodView()
                .tabItem {
                    Label("Food", systemImage: "pawprint")
                }
                .tag(1)

            MedicationView()
                .tabItem {
                    Label("Medication", systemImage: "syringe")
                }
                .tag(2)

            HealthView()
                .tabItem {
                    Label("Health", systemImage: "heart")
                }
                .tag(3)

            HealthSearchView()
                .tabItem {
                    Label("Search", systemImage: "magnifyingglass")
                }
                .tag(4)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(5)
        }
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("SwitchToFoodTab"))) { _ in
            selectedTab = 1
        }
    }
}

// MARK: - Skeleton Views
struct SkeletonView: View {
    @State private var isAnimating = false

    var body: some View {
        Rectangle()
            .fill(Color.gray.opacity(0.3))
            .overlay(
                Rectangle()
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: [.clear, .white.opacity(0.4), .clear]),
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .offset(x: isAnimating ? 300 : -300)
            )
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .onAppear {
                withAnimation(Animation.linear(duration: 1.5).repeatForever(autoreverses: false)) {
                    isAnimating = true
                }
            }
    }
}

struct CalorieSkeletonView: View {
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                SkeletonView()
                    .frame(width: 150, height: 20)
                Spacer()
                SkeletonView()
                    .frame(width: 100, height: 20)
            }
            .padding(.horizontal)

            VStack(spacing: 12) {
                VStack(spacing: 8) {
                    HStack {
                        SkeletonView()
                            .frame(width: 120, height: 16)
                        Spacer()
                        SkeletonView()
                            .frame(width: 60, height: 16)
                    }
                    .padding(.horizontal, 12)

                    SkeletonView()
                        .frame(height: 8)
                        .padding(.horizontal, 12)
                }
                .padding(.vertical, 12)

                Divider()
                    .padding(.horizontal, 12)

                VStack(alignment: .leading, spacing: 8) {
                    SkeletonView()
                        .frame(width: 140, height: 14)
                        .padding(.horizontal, 12)

                    ForEach(0..<3, id: \.self) { _ in
                        HStack(spacing: 12) {
                            VStack(alignment: .leading, spacing: 4) {
                                SkeletonView()
                                    .frame(width: 120, height: 14)
                                SkeletonView()
                                    .frame(width: 180, height: 12)
                            }
                            Spacer()
                            SkeletonView()
                                .frame(width: 60, height: 12)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                    }
                }
                .padding(.bottom, 8)
            }
            .background(Color.gray.opacity(0.1))
            .cornerRadius(12)
            .padding(.horizontal)
        }
        .padding(.top, 8)
    }
}

struct MedicationSkeletonView: View {
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                SkeletonView()
                    .frame(width: 180, height: 20)
                Spacer()
            }
            .padding(.horizontal)

            VStack(spacing: 0) {
                ForEach(0..<2, id: \.self) { index in
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                SkeletonView()
                                    .frame(width: 100, height: 14)
                                SkeletonView()
                                    .frame(width: 60, height: 20)
                            }
                            SkeletonView()
                                .frame(width: 140, height: 12)
                            SkeletonView()
                                .frame(width: 120, height: 12)
                        }

                        Spacer()

                        SkeletonView()
                            .frame(width: 80, height: 28)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 12)

                    if index < 1 {
                        Divider()
                    }
                }
            }
            .background(Color.gray.opacity(0.1))
            .cornerRadius(12)
            .padding(.horizontal)
        }
        .padding(.top, 8)
    }
}

struct DashboardView: View {
    @State private var pets: [Pet] = []
    @State private var selectedPet: Pet?
    @State private var todayCalories: Double = 0
    @State private var calorieGoal: Double = 0
    @State private var todayFeedings: [PetFeeding] = []
    @State private var foods: [UUID: PetFood] = [:]
    @State private var activeMedications: [PetMedication] = []
    @State private var lastDoses: [UUID: PetMedicationDose] = [:]
    @State private var dosesRemaining: [UUID: Int] = [:]
    @State private var isLoading = true
    @State private var isRefreshing = false
    @State private var showRecordFeeding = false
    @State private var showSetGoal = false
    @State private var showToast = false
    @State private var toastMessage = ""

    private var gaugeColor: Color {
        todayCalories >= calorieGoal ? .red : .blue
    }

    @ViewBuilder
    private var dashboardContent: some View {
        Group {
            if isLoading {
                ProgressView()
            } else if pets.isEmpty {
                VStack {
                    Text("No pets found")
                        .font(.headline)
                }
            } else {
                dashboardScrollContent
            }
        }
    }

    @ViewBuilder
    private var dashboardScrollContent: some View {
        ScrollView {
            VStack(spacing: 24) {
                if pets.count > 1 {
                    petPicker
                }

                if isRefreshing {
                    // Show skeleton loaders while refreshing
                    CalorieSkeletonView()

                    SkeletonView()
                        .frame(height: 50)
                        .padding(.horizontal)

                    SkeletonView()
                        .frame(height: 50)
                        .padding(.horizontal)

                    MedicationSkeletonView()
                } else if let pet = selectedPet {
                    calorieGaugeSection(pet: pet)
                    recordFeedingButton
                    feedingHistoryLink(pet: pet)

                    medicationSection(pet: pet)
                }

                Spacer()
            }
            .padding(.top)
        }
    }

    private var petPicker: some View {
        Picker("Select Pet", selection: $selectedPet) {
            ForEach(pets) { pet in
                Text(pet.name).tag(pet as Pet?)
            }
        }
        .pickerStyle(.segmented)
        .padding(.horizontal)
    }

    private func calorieGaugeSection(pet: Pet) -> some View {
        VStack(spacing: 12) {
            HStack {
                Label("\(pet.name)'s Daily Calories", systemImage: "fork.knife.circle.fill")
                    .font(.headline)
                Spacer()
                if calorieGoal > 0 {
                    Button(action: {
                        showSetGoal = true
                    }) {
                        Label("Update Goal", systemImage: "target")
                            .font(.subheadline)
                    }
                }
            }
            .padding(.horizontal)

            if calorieGoal > 0 {
                VStack(spacing: 12) {
                    // Progress bar and stats
                    VStack(spacing: 8) {
                        HStack {
                            Text("\(Int(todayCalories)) / \(Int(calorieGoal)) cal")
                                .font(.subheadline)
                                .fontWeight(.medium)
                            Spacer()
                            Text("\(Int((todayCalories / calorieGoal) * 100))%")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        .padding(.horizontal, 12)

                        ProgressView(value: min(todayCalories, calorieGoal), total: calorieGoal)
                            .tint(gaugeColor)
                            .scaleEffect(y: 2.0)
                            .padding(.horizontal, 12)
                    }
                    .padding(.vertical, 12)

                    // Today's feedings
                    if !todayFeedings.isEmpty {
                        Divider()
                            .padding(.horizontal, 12)

                        VStack(alignment: .leading, spacing: 8) {
                            Text("Today's Feedings")
                                .font(.subheadline)
                                .fontWeight(.medium)
                                .foregroundColor(.secondary)
                                .padding(.horizontal, 12)

                            VStack(spacing: 0) {
                                ForEach(todayFeedings.prefix(5)) { feeding in
                                    HStack(alignment: .top, spacing: 12) {
                                        VStack(alignment: .leading, spacing: 4) {
                                            if let food = foods[feeding.foodId] {
                                                Text(food.name)
                                                    .font(.subheadline)
                                                    .fontWeight(.medium)
                                            } else {
                                                Text("Unknown Food")
                                                    .font(.subheadline)
                                                    .fontWeight(.medium)
                                                    .foregroundColor(.secondary)
                                            }

                                            Text("\(Int(feeding.calories)) cal • \(formatAmount(feeding.amount)) \(feeding.amountUnit.abbreviation)")
                                                .font(.caption)
                                                .foregroundColor(.secondary)
                                        }

                                        Spacer()

                                        Text(relativeTimeString(from: feeding.fedAt))
                                            .font(.caption)
                                            .foregroundColor(.green)
                                    }
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 8)

                                    if feeding.id != todayFeedings.prefix(5).last?.id {
                                        Divider()
                                            .padding(.horizontal, 12)
                                    }
                                }
                            }
                        }
                        .padding(.bottom, 8)
                    }
                }
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
                .padding(.horizontal)
            } else {
                noGoalView
            }
        }
        .padding(.top, 8)
    }

    private var noGoalView: some View {
        VStack(spacing: 12) {
            Image(systemName: "target")
                .font(.system(size: 60))
                .foregroundColor(.gray)
            Text("No calorie goal set")
                .font(.headline)
                .foregroundColor(.secondary)
            Button("Set Goal") {
                showSetGoal = true
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
    }

    private var recordFeedingButton: some View {
        Button(action: {
            showRecordFeeding = true
        }) {
            Label("Record Feeding", systemImage: "fork.knife")
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(12)
        }
        .padding(.horizontal)
    }

    private func feedingHistoryLink(pet: Pet) -> some View {
        NavigationLink(destination: FeedingHistoryView(petId: pet.id)) {
            Label("View Feeding History", systemImage: "list.bullet")
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.gray.opacity(0.2))
                .foregroundColor(.primary)
                .cornerRadius(12)
        }
        .padding(.horizontal)
    }

    private func medicationSection(pet: Pet) -> some View {
        VStack(spacing: 12) {
            HStack {
                Label("Today's Medications", systemImage: "pills.fill")
                    .font(.headline)
                Spacer()
            }
            .padding(.horizontal)

            if activeMedications.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "pills")
                        .font(.system(size: 40))
                        .foregroundColor(.gray)
                    Text("No active medications")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
                .padding(.horizontal)
            } else {
                VStack(spacing: 0) {
                    ForEach(activeMedications.prefix(3)) { medication in
                        HStack(alignment: .top, spacing: 12) {
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(medication.name)
                                        .font(.subheadline)
                                        .fontWeight(.medium)

                                    Text(medication.medicationType.displayName)
                                        .font(.caption)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(Color.blue.opacity(0.2))
                                        .foregroundColor(.blue)
                                        .cornerRadius(4)
                                }

                                let remaining = dosesRemaining[medication.id] ?? medication.timesPerDay
                                if remaining > 0 {
                                    Text("\(remaining) dose\(remaining == 1 ? "" : "s") left today")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                } else {
                                    Text("Completed for today ✓")
                                        .font(.caption)
                                        .foregroundColor(.green)
                                }

                                if let lastDose = lastDoses[medication.id] {
                                    Text("Last dose: \(relativeTimeString(from: lastDose.givenAt))")
                                        .font(.caption)
                                        .foregroundColor(.green)
                                } else {
                                    Text("No doses recorded")
                                        .font(.caption)
                                        .foregroundColor(.orange)
                                }
                            }

                            Spacer()

                            let remaining = dosesRemaining[medication.id] ?? medication.timesPerDay
                            if remaining > 0 {
                                Button(action: {
                                    Task {
                                        await recordDose(for: medication)
                                    }
                                }) {
                                    HStack(spacing: 4) {
                                        Image(systemName: "checkmark.circle.fill")
                                            .font(.caption)
                                        Text("Record")
                                            .font(.caption)
                                            .fontWeight(.medium)
                                    }
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 6)
                                    .background(Color.green)
                                    .foregroundColor(.white)
                                    .cornerRadius(8)
                                }
                            }
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 12)

                        if medication.id != activeMedications.prefix(3).last?.id {
                            Divider()
                        }
                    }
                }
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
                .padding(.horizontal)
            }
        }
        .padding(.top, 8)
    }

    var body: some View {
        NavigationView {
            dashboardContent
            .navigationTitle("Dashboard")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $showRecordFeeding) {
                if let pet = selectedPet {
                    RecordFeedingView(petId: pet.id)
                }
            }
            .sheet(isPresented: $showSetGoal) {
                if let pet = selectedPet {
                    SetCalorieGoalView(petId: pet.id, currentGoal: calorieGoal)
                }
            }
            .overlay(alignment: .top) {
                if showToast {
                    Toast(message: toastMessage)
                        .padding(.top, 50)
                        .transition(.move(edge: .top).combined(with: .opacity))
                        .onAppear {
                            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                withAnimation {
                                    showToast = false
                                }
                            }
                        }
                }
            }
            .onChange(of: showRecordFeeding) { _, isShowing in
                if !isShowing {
                    Task { @MainActor in
                        await loadTodayCalories()
                        await loadTodayFeedings()
                    }
                }
            }
            .onChange(of: showSetGoal) { _, isShowing in
                if !isShowing {
                    Task { @MainActor in
                        await loadCalorieGoal()
                        await loadTodayCalories()
                        await loadTodayFeedings()
                    }
                }
            }
            .onChange(of: selectedPet) { _, _ in
                Task { @MainActor in
                    await loadCalorieGoal()
                    await loadTodayCalories()
                    await loadTodayFeedings()
                    await loadActiveMedications()
                }
            }
            .task {
                await loadPets()
            }
            .refreshable {
                isRefreshing = true
                await loadPets()
                await loadCalorieGoal()
                await loadTodayCalories()
                await loadTodayFeedings()
                await loadFoods()
                await loadActiveMedications()
                isRefreshing = false
            }
        }
    }

    private func loadPets() async {
        isLoading = true
        do {
            pets = try await DataService.shared.getPets()
            if selectedPet == nil {
                selectedPet = pets.first
            }
            await loadCalorieGoal()
            await loadTodayCalories()
            await loadTodayFeedings()
            await loadFoods()
            await loadActiveMedications()
        } catch {
            print("Error loading pets: \(error)")
        }
        isLoading = false
    }

    @MainActor
    private func loadCalorieGoal() async {
        guard let pet = selectedPet else { return }
        do {
            let goal = try await DataService.shared.getActiveCalorieGoal(for: pet.id)
            calorieGoal = goal?.dailyCalories ?? 0
        } catch {
            print("Error loading calorie goal: \(error)")
            calorieGoal = 0
        }
    }

    @MainActor
    private func loadTodayCalories() async {
        guard let pet = selectedPet else { return }
        do {
            todayCalories = try await DataService.shared.getTodayCalories(for: pet.id)
        } catch {
            print("Error loading today's calories: \(error)")
            todayCalories = 0
        }
    }

    private func loadActiveMedications() async {
        guard let pet = selectedPet else { return }
        do {
            activeMedications = try await DataService.shared.getActiveMedications(for: pet.id)
            await loadLastDoses()
            await loadDosesRemaining()
        } catch {
            print("Error loading active medications: \(error)")
            activeMedications = []
        }
    }

    private func loadLastDoses() async {
        var doses: [UUID: PetMedicationDose] = [:]
        for medication in activeMedications {
            if let lastDose = try? await DataService.shared.getLastDose(for: medication.id) {
                doses[medication.id] = lastDose
            }
        }
        lastDoses = doses
    }

    private func loadDosesRemaining() async {
        var remaining: [UUID: Int] = [:]
        for medication in activeMedications {
            if let todayDoses = try? await DataService.shared.getTodayDoses(for: medication.id) {
                let dosesLeft = medication.timesPerDay - todayDoses.count
                remaining[medication.id] = max(0, dosesLeft)
            } else {
                remaining[medication.id] = medication.timesPerDay
            }
        }
        dosesRemaining = remaining
    }

    private func recordDose(for medication: PetMedication) async {
        do {
            _ = try await DataService.shared.recordDose(medicationId: medication.id)
            await loadLastDoses()
            await loadDosesRemaining()
            toastMessage = "\(medication.name) recorded"
            withAnimation {
                showToast = true
            }
        } catch {
            print("Error recording dose: \(error)")
        }
    }

    private func relativeTimeString(from date: Date) -> String {
        let interval = Date().timeIntervalSince(date)
        let hours = Int(interval / 3600)
        let days = Int(interval / 86400)

        if hours < 48 {
            return hours == 0 ? "Just now" : "\(hours)h ago"
        } else {
            return "\(days)d ago"
        }
    }

    private func formatAmount(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }

    private func loadTodayFeedings() async {
        guard let pet = selectedPet else { return }
        do {
            todayFeedings = try await DataService.shared.getTodayFeedings(for: pet.id)
        } catch {
            print("Error loading today's feedings: \(error)")
            todayFeedings = []
        }
    }

    private func loadFoods() async {
        do {
            let allFoods = try await DataService.shared.getFoods()
            foods = Dictionary(uniqueKeysWithValues: allFoods.map { ($0.id, $0) })
        } catch {
            print("Error loading foods: \(error)")
            foods = [:]
        }
    }
}

struct FoodView: View {
    @State private var foods: [PetFood] = []
    @State private var isLoading = true
    @State private var showAddFood = false
    @State private var selectedCategory: FoodCategory?
    @State private var errorMessage: String?

    var foodsByCategory: [FoodCategory: [PetFood]] {
        Dictionary(grouping: foods, by: { $0.category })
    }

    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    ProgressView()
                } else if foods.isEmpty {
                    // Empty state - show plus button
                    VStack(spacing: 16) {
                        Image(systemName: "plus.circle.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.blue)
                        Button("Add Pet Food") {
                            showAddFood = true
                        }
                        .font(.headline)
                    }
                } else {
                    List {
                        ForEach(FoodCategory.allCases, id: \.self) { category in
                            if let categoryFoods = foodsByCategory[category] {
                                Section(header: Text(category.displayName)) {
                                    ForEach(categoryFoods) { food in
                                        FoodRowView(food: food)
                                            .contextMenu {
                                                Button(action: {
                                                    // TODO: Edit food
                                                }) {
                                                    Label("Edit", systemImage: "pencil")
                                                }

                                                Button(action: {
                                                    // TODO: Archive food
                                                }) {
                                                    Label("Archive", systemImage: "archivebox")
                                                }

                                                Button(role: .destructive, action: {
                                                    Task {
                                                        await deleteFood(food)
                                                    }
                                                }) {
                                                    Label("Delete", systemImage: "trash")
                                                }
                                            }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Food")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button(action: {
                        selectedCategory = nil
                        showAddFood = true
                    }) {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showAddFood) {
                AddFoodView(defaultCategory: selectedCategory)
            }
            .onChange(of: showAddFood) { _, isShowing in
                if !isShowing {
                    Task {
                        await loadFoods()
                    }
                }
            }
            .task {
                await loadFoods()
            }
            .refreshable {
                await loadFoods()
            }
            .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("ShowAddFood"))) { _ in
                showAddFood = true
            }
        }
    }

    private func loadFoods() async {
        isLoading = true
        do {
            foods = try await DataService.shared.getFoods()
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading foods: \(error)")
        }
        isLoading = false
    }

    private func deleteFood(_ food: PetFood) async {
        do {
            try await DataService.shared.deleteFood(id: food.id)
            await loadFoods()
        } catch {
            errorMessage = error.localizedDescription
            print("Error deleting food: \(error)")
        }
    }
}

struct FoodRowView: View {
    let food: PetFood

    var body: some View {
        HStack(spacing: 12) {
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
                .frame(width: 80, height: 80)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            } else {
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(width: 80, height: 80)
                    .overlay(
                        Image(systemName: "photo")
                            .foregroundColor(.gray)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            // Food Details
            VStack(alignment: .leading, spacing: 4) {
                Text(food.name)
                    .font(.headline)
                    .lineLimit(2)

                Text("\(Int(food.caloriesPerKg)) kcal/kg")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                Text("\(formatNumber(food.containerSize)) \(food.containerSizeUnit.abbreviation) • \(Int(food.caloriesPerContainer)) cal")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 8)
    }

    private func formatNumber(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }
}

struct MedicationView: View {
    @State private var medications: [PetMedication] = []
    @State private var pets: [UUID: Pet] = [:]
    @State private var isLoading = true
    @State private var showAddMedication = false
    @State private var showRecordDose = false
    @State private var errorMessage: String?

    var activeMedications: [PetMedication] {
        medications.filter { $0.isActive }
    }

    var endedMedications: [PetMedication] {
        medications.filter { !$0.isActive }
    }

    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    ProgressView()
                } else if medications.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "pills.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.blue)
                        Text("No medications yet")
                            .font(.headline)
                        Button("Add Medication") {
                            showAddMedication = true
                        }
                        .buttonStyle(.borderedProminent)
                    }
                } else {
                    List {
                        if !activeMedications.isEmpty {
                            Section(header: Text("Active Medications")) {
                                ForEach(activeMedications) { medication in
                                    MedicationRowView(medication: medication, pet: pets[medication.petId])
                                }
                            }
                        }

                        if !endedMedications.isEmpty {
                            Section(header: Text("Ended Medications")) {
                                ForEach(endedMedications) { medication in
                                    MedicationRowView(medication: medication, pet: pets[medication.petId])
                                        .opacity(0.6)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Medication")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Menu {
                        Button(action: {
                            showAddMedication = true
                        }) {
                            Label("Add Medication", systemImage: "plus.circle")
                        }
                        Button(action: {
                            showRecordDose = true
                        }) {
                            Label("Record Dose", systemImage: "checkmark.circle")
                        }
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showAddMedication) {
                AddMedicationView()
            }
            .sheet(isPresented: $showRecordDose) {
                RecordDoseView()
            }
            .onChange(of: showAddMedication) { _, isShowing in
                if !isShowing {
                    Task {
                        await loadMedications()
                    }
                }
            }
            .onChange(of: showRecordDose) { _, isShowing in
                if !isShowing {
                    Task {
                        await loadMedications()
                    }
                }
            }
            .task {
                await loadMedications()
            }
            .refreshable {
                await loadMedications()
            }
        }
    }

    private func loadMedications() async {
        isLoading = true
        do {
            medications = try await DataService.shared.getMedications()

            let allPets = try await DataService.shared.getPets()
            pets = Dictionary(uniqueKeysWithValues: allPets.map { ($0.id, $0) })
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading medications: \(error)")
        }
        isLoading = false
    }
}

struct MedicationRowView: View {
    let medication: PetMedication
    let pet: Pet?

    var body: some View {
        NavigationLink(destination: MedicationHistoryView(medicationId: medication.id)) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(medication.name)
                            .font(.headline)
                        if let pet = pet {
                            Text(pet.name)
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                    }

                    Spacer()

                    VStack(alignment: .trailing, spacing: 4) {
                        Text(medication.medicationType.displayName)
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.blue.opacity(0.2))
                            .foregroundColor(.blue)
                            .cornerRadius(8)

                        Text("\(medication.timesPerDay)x per day")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                HStack {
                    Label(formatDate(medication.startDate), systemImage: "calendar")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    if let endDate = medication.endDate {
                        Image(systemName: "arrow.right")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text(formatDate(endDate))
                            .font(.caption)
                            .foregroundColor(.secondary)
                    } else {
                        Text("• Ongoing")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                if let notes = medication.notes, !notes.isEmpty {
                    Text(notes)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(2)
                }
            }
            .padding(.vertical, 4)
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        return formatter.string(from: date)
    }
}

struct HealthView: View {
    @State private var pets: [Pet] = []
    @State private var selectedPet: Pet?
    @State private var events: [HealthEventWithCategory] = []
    @State private var isLoading = true
    @State private var showAddEvent = false
    @State private var errorMessage: String?

    var eventsByDate: [Date: [HealthEventWithCategory]] {
        let calendar = Calendar.current
        let grouped = Dictionary(grouping: events) { event in
            calendar.startOfDay(for: event.event.occurredAt)
        }
        return grouped
    }

    var sortedDates: [Date] {
        eventsByDate.keys.sorted(by: >)
    }

    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    ProgressView()
                } else if pets.isEmpty {
                    VStack(spacing: 16) {
                        Text("No pets found")
                            .font(.headline)
                            .foregroundColor(.secondary)
                    }
                } else {
                    VStack(spacing: 0) {
                        if pets.count > 1 {
                            petPicker
                                .padding(.horizontal)
                                .padding(.top)
                        }

                        if events.isEmpty {
                            emptyState
                        } else {
                            eventsList
                        }
                    }
                }
            }
            .navigationTitle("Health Journal")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    if !pets.isEmpty {
                        Button(action: {
                            showAddEvent = true
                        }) {
                            Image(systemName: "plus")
                        }
                    }
                }
            }
            .sheet(isPresented: $showAddEvent) {
                if let pet = selectedPet {
                    AddHealthEventView(petId: pet.id)
                }
            }
            .onChange(of: showAddEvent) { _, isShowing in
                if !isShowing {
                    Task {
                        await loadEvents()
                    }
                }
            }
            .onChange(of: selectedPet) { _, _ in
                Task {
                    await loadEvents()
                }
            }
            .task {
                await loadPets()
            }
            .refreshable {
                await loadEvents()
            }
        }
    }

    private var petPicker: some View {
        Picker("Select Pet", selection: $selectedPet) {
            ForEach(pets) { pet in
                Text(pet.name).tag(pet as Pet?)
            }
        }
        .pickerStyle(.segmented)
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "heart.text.square")
                .font(.system(size: 60))
                .foregroundColor(.gray)
            Text("No health events yet")
                .font(.headline)
                .foregroundColor(.secondary)
            Button("Add Event") {
                showAddEvent = true
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var eventsList: some View {
        List {
            ForEach(sortedDates, id: \.self) { date in
                Section(header: Text(formatDate(date))) {
                    if let dayEvents = eventsByDate[date] {
                        ForEach(dayEvents.sorted(by: { $0.event.occurredAt > $1.event.occurredAt })) { eventWithCategory in
                            HealthEventRowView(
                                eventWithCategory: eventWithCategory,
                                petId: selectedPet?.id ?? UUID()
                            )
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    Task {
                                        await deleteEvent(eventWithCategory.event.id)
                                    }
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    private func loadPets() async {
        isLoading = true
        do {
            pets = try await DataService.shared.getPets()
            if selectedPet == nil {
                selectedPet = pets.first
            }
            await loadEvents()
        } catch {
            print("Error loading pets: \(error)")
        }
        isLoading = false
    }

    private func loadEvents() async {
        guard let pet = selectedPet else { return }
        do {
            events = try await DataService.shared.getHealthEvents(for: pet.id)
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading health events: \(error)")
        }
    }

    private func deleteEvent(_ eventId: UUID) async {
        do {
            try await DataService.shared.deleteHealthEvent(id: eventId)
            await loadEvents()
        } catch {
            errorMessage = error.localizedDescription
            print("Error deleting health event: \(error)")
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none

        if Calendar.current.isDateInToday(date) {
            return "Today"
        } else if Calendar.current.isDateInYesterday(date) {
            return "Yesterday"
        } else {
            return formatter.string(from: date)
        }
    }
}

struct HealthEventRowView: View {
    let eventWithCategory: HealthEventWithCategory
    let petId: UUID

    var body: some View {
        NavigationLink(destination: HealthEventDetailView(eventWithCategory: eventWithCategory, petId: petId)) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(eventWithCategory.category.name)
                            .font(.headline)

                        Text(formatTime(eventWithCategory.event.occurredAt))
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    Image(systemName: "heart.circle.fill")
                        .font(.title2)
                        .foregroundColor(.red.opacity(0.7))
                }

                if let notes = eventWithCategory.event.notes, !notes.isEmpty {
                    Text(notes)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .padding(.top, 2)
                        .lineLimit(2)
                }
            }
            .padding(.vertical, 4)
        }
    }

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

struct SettingsView: View {
    @ObservedObject private var clerkManager = ClerkManager.shared
    @State private var pets: [Pet] = []
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var showSignOutError = false

    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    ProgressView("Loading...")
                } else {
                    ScrollView {
                        VStack(spacing: 20) {
                            // Account Section
                            accountSection

                            // Family Section
                            if let org = clerkManager.currentOrganization {
                                familySection(org: org)
                            }

                            // Pets Section
                            petsSection

                            Spacer()

                            // Sign Out Button
                            signOutButton
                        }
                        .padding()
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                await loadData()
            }
            .refreshable {
                await loadData()
            }
            .alert("Sign Out Error", isPresented: $showSignOutError) {
                Button("OK") {
                    showSignOutError = false
                }
            } message: {
                Text(errorMessage ?? "Failed to sign out")
            }
        }
    }

    private var accountSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Account")
                .font(.headline)
                .foregroundColor(.secondary)

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "person.circle.fill")
                        .font(.title2)
                        .foregroundColor(.blue)

                    VStack(alignment: .leading, spacing: 4) {
                        Text(clerkManager.userEmail ?? "No email")
                            .font(.body)
                            .fontWeight(.medium)

                        if let userId = clerkManager.userId {
                            Text("ID: \(userId)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .lineLimit(1)
                                .truncationMode(.middle)
                        }
                    }
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
            }
        }
    }

    private func familySection(org: Organization) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Family")
                .font(.headline)
                .foregroundColor(.secondary)

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "house.circle.fill")
                        .font(.title2)
                        .foregroundColor(.green)

                    VStack(alignment: .leading, spacing: 4) {
                        Text(org.name)
                            .font(.body)
                            .fontWeight(.medium)

                        Text("Organization ID: \(org.id)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
            }
        }
    }

    private var petsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Pets")
                .font(.headline)
                .foregroundColor(.secondary)

            if pets.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "pawprint.circle")
                        .font(.system(size: 40))
                        .foregroundColor(.gray)
                    Text("No pets in family")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
            } else {
                VStack(spacing: 12) {
                    ForEach(pets) { pet in
                        HStack(spacing: 12) {
                            // Pet Photo
                            if let photoUrl = pet.photoUrl, let url = URL(string: photoUrl) {
                                AsyncImage(url: url) { image in
                                    image
                                        .resizable()
                                        .scaledToFill()
                                } placeholder: {
                                    Rectangle()
                                        .fill(Color.gray.opacity(0.2))
                                        .overlay(ProgressView())
                                }
                                .frame(width: 60, height: 60)
                                .clipShape(Circle())
                            } else {
                                Circle()
                                    .fill(Color.gray.opacity(0.2))
                                    .frame(width: 60, height: 60)
                                    .overlay(
                                        Image(systemName: "pawprint.fill")
                                            .foregroundColor(.gray)
                                    )
                            }

                            // Pet Info
                            VStack(alignment: .leading, spacing: 4) {
                                Text(pet.name)
                                    .font(.body)
                                    .fontWeight(.medium)

                                Text(pet.kind)
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)

                                if let weight = pet.currentWeight {
                                    Text("\(formatWeight(weight)) lbs")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }

                            Spacer()
                        }
                        .padding()
                        .background(Color.gray.opacity(0.1))
                        .cornerRadius(12)
                    }
                }
            }
        }
    }

    private var signOutButton: some View {
        Button(action: signOut) {
            HStack {
                Image(systemName: "arrow.right.square.fill")
                Text("Sign Out")
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.red)
            .foregroundColor(.white)
            .cornerRadius(12)
        }
        .padding(.top, 20)
    }

    private func loadData() async {
        isLoading = true
        errorMessage = nil

        do {
            pets = try await DataService.shared.getPets()
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading settings data: \(error)")
        }

        isLoading = false
    }

    private func signOut() {
        Task {
            await clerkManager.signOut()
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        return formatter.string(from: date)
    }

    private func formatWeight(_ weight: Double) -> String {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 1
        return formatter.string(from: NSNumber(value: weight)) ?? "\(weight)"
    }
}

struct Toast: View {
    let message: String

    var body: some View {
        Text(message)
            .font(.subheadline)
            .fontWeight(.medium)
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
            .background(Color.green)
            .foregroundColor(.white)
            .cornerRadius(12)
            .shadow(radius: 4)
    }
}

#Preview {
    ContentView()
}
