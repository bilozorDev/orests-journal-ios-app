//
//  ContentView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

// MARK: - Extensions

extension UUID: @retroactive Identifiable {
    public var id: UUID { self }
}

// MARK: - Views

struct ContentView: View {
    private var authManager = AuthManager.shared
    @State private var isLoading = true
    @State private var hasPet = false
    @State private var isCheckingStatus = false
    @State private var hasCheckedPetStatus = false  // Prevent duplicate checks
    @State private var showError = false
    @State private var errorMessage = ""

    var body: some View {
        Group {
            if isLoading || !authManager.isLoaded {
                ProgressView("Loading...")
            } else if authManager.isAuthenticated {
                if isCheckingStatus {
                    ProgressView("Setting up...")
                } else if authManager.needsProfileSetup {
                    ProfileSetupView()
                } else if !authManager.hasOrganization {
                    FamilySetupView()
                } else if !hasPet {
                    AddEditPetView(mode: .add) { _ in
                        // Pet was created, refresh status
                        NotificationCenter.default.post(name: NSNotification.Name("RefreshFamilyStatus"), object: nil)
                    }
                } else {
                    MainTabView()
                }
            } else {
                SignInScreen()
            }
        }
        .task {
            await authManager.loadSession()
            // After loading session, check pet status if authenticated
            // onChange won't fire if isAuthenticated was set during loadSession
            // because the view wasn't fully rendered yet
            if authManager.isAuthenticated {
                await checkPetStatus()
            }
            isLoading = false
        }
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("RefreshFamilyStatus"))) { _ in
            Task {
                await checkPetStatus()
            }
        }
        .onChange(of: authManager.isAuthenticated) { _, isAuthenticated in
            // Only handle sign-out here; sign-in is handled by .task
            if !isAuthenticated {
                hasPet = false
            }
        }
        .onChange(of: authManager.hasOrganization) { _, hasOrg in
            // Backup trigger: check pet status when organization state changes
            if hasOrg {
                Task {
                    await checkPetStatus()
                }
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
        // Prevent duplicate calls
        guard !isCheckingStatus else {
            print("⚠️ checkPetStatus already in progress, skipping")
            return
        }

        guard authManager.hasOrganization else {
            hasPet = false
            return
        }

        isCheckingStatus = true
        do {
            let pets = try await DataService.shared.getPets()
            hasPet = !pets.isEmpty
            hasCheckedPetStatus = true
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

            FamilyManagementView()
                .tabItem {
                    Label("Family", systemImage: "figure.2.and.child.holdinghands")
                }
                .tag(4)

            HealthSearchView()
                .tabItem {
                    Label("Search", systemImage: "magnifyingglass")
                }
                .tag(5)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(6)
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
    @State private var allDashboardData: [UUID: DashboardData] = [:]
    @State private var foods: [UUID: PetFood] = [:]
    @State private var isLoading = false
    @State private var hasLoaded = false
    @State private var isRefreshing = false
    @State private var isLoadingDashboard = false
    @State private var recordFeedingPetId: UUID?
    @State private var setGoalPetId: UUID?
    @State private var showToast = false
    @State private var toastMessage = ""
    @State private var feedingHistoryPetId: UUID?
    @State private var medicationHistoryId: UUID?

    // Computed: All active medications from all pets with pet info
    private var allMedicationsWithPet: [(pet: Pet, medication: PetMedication, lastDose: PetMedicationDose?, dosesRemaining: Int)] {
        var result: [(pet: Pet, medication: PetMedication, lastDose: PetMedicationDose?, dosesRemaining: Int)] = []
        for pet in pets {
            if let data = allDashboardData[pet.id] {
                for medWithDoses in data.medications {
                    result.append((pet: pet, medication: medWithDoses.medication, lastDose: medWithDoses.lastDose, dosesRemaining: medWithDoses.dosesRemaining))
                }
            }
        }
        return result
    }

    private func gaugeColor(for petId: UUID) -> Color {
        guard let data = allDashboardData[petId] else { return .blue }
        let goal = data.calorieGoal?.dailyCalories ?? 0
        return data.totalCalories >= goal ? .red : .blue
    }

    @ViewBuilder
    private var dashboardContent: some View {
        Group {
            if pets.isEmpty && hasLoaded {
                VStack {
                    Text("No pets found")
                        .font(.headline)
                }
            } else {
                dashboardScrollContent
            }
        }
        .overlay {
            if isLoading && !hasLoaded {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(uiColor: .systemBackground))
            }
        }
    }

    @ViewBuilder
    private var dashboardScrollContent: some View {
        ScrollView {
            VStack(spacing: 24) {
                if isRefreshing {
                    // Show skeleton loaders while refreshing
                    ForEach(pets) { _ in
                        CalorieSkeletonView()
                    }
                    MedicationSkeletonView()
                } else {
                    // Feeding section for each pet
                    ForEach(pets) { pet in
                        petFeedingSection(pet: pet)
                    }

                    // Unified medication section for all pets
                    allMedicationsSection
                }

                Spacer()
            }
            .padding(.top)
        }
    }

    private func petFeedingSection(pet: Pet) -> some View {
        let data = allDashboardData[pet.id]
        let todayCalories = data?.totalCalories ?? 0
        let calorieGoal = data?.calorieGoal?.dailyCalories ?? 0
        let todayFeedings = data?.todayFeedings ?? []

        return VStack(spacing: 12) {
            HStack {
                Label("\(pet.name)'s Daily Calories", systemImage: "fork.knife.circle.fill")
                    .font(.headline)
                Spacer()
                if calorieGoal > 0 {
                    Button(action: {
                        setGoalPetId = pet.id
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
                            .tint(gaugeColor(for: pet.id))
                            .scaleEffect(y: 2.0)
                            .padding(.horizontal, 12)
                    }
                    .padding(.vertical, 12)

                    // Today's feedings
                    if !todayFeedings.isEmpty {
                        Divider()
                            .padding(.horizontal, 12)

                        Button(action: {
                            feedingHistoryPetId = pet.id
                        }) {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("Today's Feedings")
                                        .font(.subheadline)
                                        .fontWeight(.medium)
                                        .foregroundColor(.secondary)
                                    Spacer()
                                    Image(systemName: "chevron.right")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                .padding(.horizontal, 12)

                                VStack(spacing: 0) {
                                    ForEach(todayFeedings.prefix(5)) { feeding in
                                        HStack(alignment: .top, spacing: 12) {
                                            VStack(alignment: .leading, spacing: 4) {
                                                if let food = foods[feeding.foodId] {
                                                    Text(food.name)
                                                        .font(.subheadline)
                                                        .fontWeight(.medium)
                                                        .foregroundColor(.primary)
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

                                            VStack(alignment: .trailing, spacing: 2) {
                                                Text(relativeTimeString(from: feeding.fedAt))
                                                    .font(.caption)
                                                    .foregroundColor(.green)
                                                Text("by \(feeding.fedBy)")
                                                    .font(.caption2)
                                                    .foregroundColor(.secondary)
                                            }
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
                        .buttonStyle(.plain)
                    }

                    // Record Feeding button for this pet
                    Button(action: {
                        recordFeedingPetId = pet.id
                    }) {
                        Label("Record Feeding", systemImage: "fork.knife")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.blue)
                            .foregroundColor(.white)
                            .cornerRadius(12)
                    }
                    .padding(.horizontal, 12)
                    .padding(.bottom, 12)
                }
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
                .padding(.horizontal)
            } else {
                noGoalView(for: pet)
            }
        }
        .padding(.top, 8)
    }

    private func noGoalView(for pet: Pet) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "target")
                .font(.system(size: 60))
                .foregroundColor(.gray)
            Text("No calorie goal set for \(pet.name)")
                .font(.headline)
                .foregroundColor(.secondary)
            Button("Set Goal") {
                setGoalPetId = pet.id
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
    }

    // MARK: - Unified Medications Section (All Pets)

    private var allMedicationsSection: some View {
        VStack(spacing: 12) {
            HStack {
                Label("Today's Medications", systemImage: "pills.fill")
                    .font(.headline)
                Spacer()
            }
            .padding(.horizontal)

            if allMedicationsWithPet.isEmpty {
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
                VStack(spacing: 12) {
                    ForEach(allMedicationsWithPet, id: \.medication.id) { item in
                        medicationRow(pet: item.pet, medication: item.medication, lastDose: item.lastDose, dosesRemaining: item.dosesRemaining)
                    }
                }
                .padding(.horizontal)
            }
        }
        .padding(.top, 8)
    }

    private func medicationRow(pet: Pet, medication: PetMedication, lastDose: PetMedicationDose?, dosesRemaining: Int) -> some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    // Pet name badge
                    Text(pet.name)
                        .font(.caption)
                        .fontWeight(.medium)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.purple.opacity(0.2))
                        .foregroundColor(.purple)
                        .cornerRadius(4)

                    Button(action: {
                        medicationHistoryId = medication.id
                    }) {
                        HStack(spacing: 6) {
                            Text(medication.name)
                                .font(.subheadline)
                                .fontWeight(.medium)
                            Image(systemName: "chevron.right")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                    }
                    .buttonStyle(.plain)

                    Text(medication.medicationType.displayName)
                        .font(.caption)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.blue.opacity(0.2))
                        .foregroundColor(.blue)
                        .cornerRadius(4)

                    Spacer()
                }

                if dosesRemaining > 0 {
                    Text("\(dosesRemaining) dose\(dosesRemaining == 1 ? "" : "s") left today")
                        .font(.caption)
                        .foregroundColor(.secondary)
                } else {
                    Text("Completed for today")
                        .font(.caption)
                        .foregroundColor(.green)
                }

                if let lastDose = lastDose,
                   Calendar.current.isDateInToday(lastDose.givenAt) {
                    HStack(spacing: 4) {
                        Text(absoluteTimeString(from: lastDose.givenAt))
                            .font(.caption)
                            .foregroundColor(.green)
                        Text("by \(lastDose.givenBy)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                } else if dosesRemaining > 0 {
                    Text("No doses recorded today")
                        .font(.caption)
                        .foregroundColor(.orange)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 12)

            if dosesRemaining > 0 {
                Button(action: {
                    Task {
                        await recordDose(for: medication, petId: pet.id)
                    }
                }) {
                    Label("Record \(medication.name)", systemImage: "pills.fill")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.green)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 12)
            }
        }
        .background(Color.gray.opacity(0.1))
        .cornerRadius(12)
    }

    var body: some View {
        NavigationStack {
            dashboardContent
            .navigationTitle("Dashboard")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(item: $feedingHistoryPetId) { petId in
                FeedingHistoryView(petId: petId)
            }
            .navigationDestination(item: $medicationHistoryId) { medicationId in
                MedicationHistoryView(medicationId: medicationId)
            }
            .sheet(item: $recordFeedingPetId) { petId in
                RecordFeedingView(petId: petId) { feeding in
                    // Optimistic update - add feeding to the pet's data
                    if let data = allDashboardData[petId] {
                        var feedings = data.todayFeedings
                        feedings.insert(feeding, at: 0)
                        let newData = DashboardData(
                            calorieGoal: data.calorieGoal,
                            todayFeedings: feedings,
                            totalCalories: data.totalCalories + feeding.calories,
                            foods: data.foods,
                            medications: data.medications
                        )
                        allDashboardData[petId] = newData
                    }

                    // Show success toast
                    toastMessage = "Feeding recorded"
                    withAnimation {
                        showToast = true
                    }
                }
                .presentationDragIndicator(.visible)
                .presentationBackgroundInteraction(.disabled)
            }
            .sheet(item: $setGoalPetId) { petId in
                let currentGoal = allDashboardData[petId]?.calorieGoal?.dailyCalories ?? 0
                SetCalorieGoalView(petId: petId, currentGoal: currentGoal)
            }
            .overlay(alignment: .top) {
                if showToast {
                    Toast(message: toastMessage)
                        .padding(.top, 50)
                        .transition(.move(edge: .top).combined(with: .opacity))
                }
            }
            .onChange(of: showToast) { _, isShowing in
                if isShowing {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                        withAnimation {
                            showToast = false
                        }
                    }
                }
            }
            .onChange(of: setGoalPetId) { oldValue, newValue in
                // When sheet closes (petId becomes nil), refresh dashboard
                if oldValue != nil && newValue == nil {
                    Task { @MainActor in
                        await loadAllDashboardData(forceRefresh: true)
                    }
                }
            }
            .onAppear {
                // Show memory-cached dashboard data immediately for all pets
                for pet in pets {
                    if let cached = DataService.shared.getCachedDashboardData(for: pet.id) {
                        allDashboardData[pet.id] = cached
                        // Merge foods
                        for food in cached.foods {
                            foods[food.id] = food
                        }
                    }
                }
            }
            .task {
                guard !hasLoaded else { return }

                // Try to show disk-cached data instantly while network loads
                if let cachedPets = await DataService.shared.getCachedPetsFromDisk(), !cachedPets.isEmpty {
                    pets = cachedPets
                    // Load disk-cached dashboard data for all pets
                    for pet in cachedPets {
                        if let cachedDashboard = await DataService.shared.getCachedDashboardDataFromDisk(for: pet.id) {
                            allDashboardData[pet.id] = cachedDashboard
                            for food in cachedDashboard.foods {
                                foods[food.id] = food
                            }
                        }
                    }
                }

                await loadPets()
            }
            .refreshable {
                isRefreshing = true
                await loadAllDashboardData(forceRefresh: true)
                isRefreshing = false
            }
        }
    }

    private func loadPets() async {
        isLoading = true
        do {
            pets = try await DataService.shared.getPets()

            // Load dashboard data for all pets
            await loadAllDashboardData()
            hasLoaded = true
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            // Ignore cancellation - will retry on next appear
            print("Pet load cancelled (this is normal during navigation)")
        } catch {
            print("Error loading pets: \(error)")
        }
        isLoading = false
    }

    @MainActor
    private func loadAllDashboardData(forceRefresh: Bool = false) async {
        // Prevent concurrent loads
        guard !isLoadingDashboard else {
            print("⚠️ Dashboard load already in progress, skipping")
            return
        }

        isLoadingDashboard = true
        defer { isLoadingDashboard = false }

        // Load dashboard data for all pets concurrently
        await withTaskGroup(of: (UUID, DashboardData?).self) { group in
            for pet in pets {
                group.addTask {
                    do {
                        let data = try await DataService.shared.getDashboardData(for: pet.id, forceRefresh: forceRefresh)
                        return (pet.id, data)
                    } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
                        print("Dashboard load cancelled for \(pet.name)")
                        return (pet.id, nil)
                    } catch {
                        print("Error loading dashboard data for \(pet.name): \(error)")
                        return (pet.id, nil)
                    }
                }
            }

            for await (petId, data) in group {
                if let data = data {
                    allDashboardData[petId] = data
                    // Merge foods into the shared foods dictionary
                    for food in data.foods {
                        foods[food.id] = food
                    }
                }
            }
        }
    }

    private func recordDose(for medication: PetMedication, petId: UUID) async {
        // Get previous state for potential rollback
        let previousData = allDashboardData[petId]

        // Get current user name for optimistic display (format: "FirstName L." or just first name)
        let userName = AuthManager.shared.displayName ?? "You"

        // Create optimistic dose entry
        let optimisticDose = PetMedicationDose(
            id: UUID(),
            medicationId: medication.id,
            givenAt: Date(),
            givenBy: userName,
            notes: nil,
            createdAt: Date()
        )

        // Update UI immediately (optimistic update)
        if var data = allDashboardData[petId] {
            let updatedMedications = data.medications.map { medWithDoses -> MedicationWithDoses in
                if medWithDoses.medication.id == medication.id {
                    return MedicationWithDoses(
                        medication: medWithDoses.medication,
                        lastDose: optimisticDose,
                        todayDoseCount: medWithDoses.todayDoseCount + 1,
                        dosesRemaining: max(0, medWithDoses.dosesRemaining - 1)
                    )
                }
                return medWithDoses
            }
            let newData = DashboardData(
                calorieGoal: data.calorieGoal,
                todayFeedings: data.todayFeedings,
                totalCalories: data.totalCalories,
                foods: data.foods,
                medications: updatedMedications
            )
            allDashboardData[petId] = newData
        }

        // Show success toast immediately
        toastMessage = "\(medication.name) recorded"
        withAnimation {
            showToast = true
        }

        // Make API call in background
        do {
            _ = try await DataService.shared.recordDose(medicationId: medication.id, petId: petId)
        } catch {
            // Revert optimistic update on failure
            if let previousData = previousData {
                allDashboardData[petId] = previousData
            }

            // Show error toast
            toastMessage = "Failed to record dose"
            withAnimation {
                showToast = true
            }
            print("Error recording dose: \(error)")
        }
    }

    private func relativeTimeString(from date: Date) -> String {
        let interval = Date().timeIntervalSince(date)
        let minutes = Int(interval / 60)
        let hours = Int(interval / 3600)
        let days = Int(interval / 86400)

        if minutes < 1 {
            return "Just now"
        } else if minutes < 60 {
            return "\(minutes)m ago"
        } else if hours < 48 {
            return "\(hours)h ago"
        } else {
            return "\(days)d ago"
        }
    }

    private func absoluteTimeString(from date: Date) -> String {
        let calendar = Calendar.current
        let timeFormatter = DateFormatter()
        timeFormatter.timeStyle = .short

        let timeString = timeFormatter.string(from: date)

        if calendar.isDateInToday(date) {
            return "\(timeString) Today"
        } else if calendar.isDateInYesterday(date) {
            return "\(timeString) Yesterday"
        } else {
            let dayFormatter = DateFormatter()
            dayFormatter.dateFormat = "EEE"
            return "\(timeString) \(dayFormatter.string(from: date))"
        }
    }

    private func formatAmount(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }
}

struct FoodView: View {
    @State private var foods: [PetFood] = []
    @State private var pets: [Pet] = []
    @State private var selectedPet: Pet?
    @State private var isLoading = false
    @State private var hasLoaded = false
    @State private var showAddFood = false
    @State private var selectedCategory: FoodCategory?
    @State private var errorMessage: String?
    @State private var foodToEdit: PetFood?
    @State private var foodToDelete: PetFood?
    @State private var showDeleteConfirmation = false
    @State private var showDeleteResultAlert = false
    @State private var deleteResultMessage = ""
    @State private var feedingHistoryPetId: UUID?

    var foodsByCategory: [FoodCategory: [PetFood]] {
        Dictionary(grouping: foods, by: { $0.category })
    }

    var body: some View {
        NavigationStack {
            List {
                if foods.isEmpty && hasLoaded {
                    // Empty state inside List for pull-to-refresh support
                    ContentUnavailableView {
                        Label("No Foods Added", systemImage: "fork.knife.circle")
                    } description: {
                        Text("Add pet foods to track feedings")
                    } actions: {
                        Button("Add Food") {
                            showAddFood = true
                        }
                        .buttonStyle(.borderedProminent)
                    }
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                    .frame(maxWidth: .infinity)
                    .listRowInsets(EdgeInsets())
                } else {
                    ForEach(FoodCategory.allCases, id: \.self) { category in
                        if let categoryFoods = foodsByCategory[category] {
                            Section(header: Text(category.displayName)) {
                                ForEach(categoryFoods) { food in
                                    FoodRowView(food: food)
                                        .contextMenu {
                                            Button(action: {
                                                foodToEdit = food
                                            }) {
                                                Label("Edit", systemImage: "pencil")
                                            }

                                            Button(role: .destructive, action: {
                                                foodToDelete = food
                                                showDeleteConfirmation = true
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
            .overlay {
                if isLoading && !hasLoaded {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color(uiColor: .systemBackground))
                }
            }
            .navigationTitle("Food")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button(action: {
                        Task {
                            if pets.isEmpty {
                                await loadPets()
                            }
                            if let pet = selectedPet ?? pets.first {
                                feedingHistoryPetId = pet.id
                            }
                        }
                    }) {
                        Image(systemName: "clock.arrow.circlepath")
                    }
                }
                ToolbarItem(placement: .primaryAction) {
                    Button(action: {
                        selectedCategory = nil
                        showAddFood = true
                    }) {
                        Image(systemName: "plus")
                    }
                }
            }
            .navigationDestination(item: $feedingHistoryPetId) { petId in
                FeedingHistoryView(petId: petId)
            }
            .sheet(isPresented: $showAddFood) {
                AddFoodView(defaultCategory: selectedCategory)
            }
            .sheet(item: $foodToEdit) { food in
                EditFoodView(food: food) { updatedFood in
                    if let index = foods.firstIndex(where: { $0.id == updatedFood.id }) {
                        foods[index] = updatedFood
                    }
                }
            }
            .onChange(of: showAddFood) { _, isShowing in
                if !isShowing {
                    Task {
                        await loadFoods(forceRefresh: false, showLoading: false)
                    }
                }
            }
            .alert("Delete Food", isPresented: $showDeleteConfirmation) {
                Button("Cancel", role: .cancel) {
                    foodToDelete = nil
                }
                Button("Delete", role: .destructive) {
                    if let food = foodToDelete {
                        Task {
                            await deleteFood(food)
                        }
                    }
                }
            } message: {
                Text("Are you sure you want to delete \"\(foodToDelete?.name ?? "")\"? This action cannot be undone.")
            }
            .alert("Food Archived", isPresented: $showDeleteResultAlert) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(deleteResultMessage)
            }
            .onAppear {
                // Show cached foods immediately (synchronous)
                if let cached = DataService.shared.getCachedFoodsData() {
                    foods = cached
                    hasLoaded = true
                }
            }
            .task {
                // Refresh in background (silently if cache already displayed)
                await loadFoods(showLoading: !hasLoaded)
                await loadPets()
            }
            .refreshable {
                await loadFoods(forceRefresh: true, showLoading: false)
            }
            .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("ShowAddFood"))) { _ in
                showAddFood = true
            }
        }
    }

    private func loadFoods(forceRefresh: Bool = false, showLoading: Bool = true) async {
        if showLoading {
            isLoading = true
        }
        do {
            foods = try await DataService.shared.getFoods(forceRefresh: forceRefresh)
            hasLoaded = true
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Food load cancelled (this is normal during navigation)")
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading foods: \(error)")
        }
        isLoading = false
    }

    private func loadPets() async {
        do {
            pets = try await DataService.shared.getPets()
            if selectedPet == nil {
                selectedPet = pets.first
            }
        } catch {
            print("Error loading pets: \(error)")
        }
    }

    private func deleteFood(_ food: PetFood) async {
        do {
            let response = try await DataService.shared.deleteFood(id: food.id)
            foodToDelete = nil
            await loadFoods(forceRefresh: true, showLoading: false)

            if response.archived && !response.deleted {
                deleteResultMessage = response.message
                showDeleteResultAlert = true
            }
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
    @State private var isLoading = false
    @State private var hasLoaded = false
    @State private var showAddMedication = false
    @State private var showRecordDose = false
    @State private var errorMessage: String?

    // Edit/Delete/History state
    @State private var medicationToEdit: PetMedication?
    @State private var medicationToDelete: PetMedication?
    @State private var showDeleteConfirmation = false
    @State private var showDeleteResultAlert = false
    @State private var deleteResultMessage = ""
    @State private var showAllHistory = false

    var activeMedications: [PetMedication] {
        medications.filter { $0.isActive }
    }

    var endedMedications: [PetMedication] {
        medications.filter { !$0.isActive }
    }

    var body: some View {
        NavigationStack {
            Group {
                if medications.isEmpty && hasLoaded {
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
                                        .contextMenu {
                                            Button(action: {
                                                medicationToEdit = medication
                                            }) {
                                                Label("Edit", systemImage: "pencil")
                                            }

                                            Button(role: .destructive, action: {
                                                medicationToDelete = medication
                                                showDeleteConfirmation = true
                                            }) {
                                                Label("Delete", systemImage: "trash")
                                            }
                                        }
                                }
                            }
                        }

                        if !endedMedications.isEmpty {
                            Section(header: Text("Ended Medications")) {
                                ForEach(endedMedications) { medication in
                                    MedicationRowView(medication: medication, pet: pets[medication.petId])
                                        .opacity(0.6)
                                        .contextMenu {
                                            Button(action: {
                                                medicationToEdit = medication
                                            }) {
                                                Label("Edit", systemImage: "pencil")
                                            }

                                            Button(role: .destructive, action: {
                                                medicationToDelete = medication
                                                showDeleteConfirmation = true
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
            .overlay {
                if isLoading && !hasLoaded {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color(uiColor: .systemBackground))
                }
            }
            .navigationTitle("Medication")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button(action: {
                        showAllHistory = true
                    }) {
                        Image(systemName: "clock.arrow.circlepath")
                    }
                }
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
            .sheet(item: $medicationToEdit) { medication in
                EditMedicationView(medication: medication) { updatedMedication in
                    if let index = medications.firstIndex(where: { $0.id == updatedMedication.id }) {
                        medications[index] = updatedMedication
                    }
                }
            }
            .navigationDestination(isPresented: $showAllHistory) {
                AllMedicationHistoryView()
            }
            .alert("Delete Medication", isPresented: $showDeleteConfirmation) {
                Button("Cancel", role: .cancel) {
                    medicationToDelete = nil
                }
                Button("Delete", role: .destructive) {
                    if let medication = medicationToDelete {
                        Task {
                            await deleteMedication(medication)
                        }
                    }
                }
            } message: {
                Text("Are you sure you want to delete \"\(medicationToDelete?.name ?? "")\"? This action cannot be undone.")
            }
            .alert("Medication Archived", isPresented: $showDeleteResultAlert) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(deleteResultMessage)
            }
            .onChange(of: showAddMedication) { _, isShowing in
                if !isShowing {
                    Task {
                        await loadMedications(forceRefresh: false, showLoading: false)
                    }
                }
            }
            .onChange(of: showRecordDose) { _, isShowing in
                if !isShowing {
                    Task {
                        await loadMedications(forceRefresh: true, showLoading: false)
                    }
                }
            }
            .onAppear {
                // Show cached data immediately (synchronous)
                if let cached = DataService.shared.getCachedMedicationsData() {
                    medications = cached
                    hasLoaded = true
                }
            }
            .task {
                // Refresh in background (silently if cache already displayed)
                await loadMedications(showLoading: !hasLoaded)
            }
            .refreshable {
                await loadMedications(forceRefresh: true, showLoading: false)
            }
        }
    }

    private func loadMedications(forceRefresh: Bool = false, showLoading: Bool = true) async {
        if showLoading {
            isLoading = true
        }
        do {
            medications = try await DataService.shared.getMedications(forceRefresh: forceRefresh)

            let allPets = try await DataService.shared.getPets()
            pets = Dictionary(uniqueKeysWithValues: allPets.map { ($0.id, $0) })
            hasLoaded = true
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Medication load cancelled (this is normal during navigation)")
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading medications: \(error)")
        }
        isLoading = false
    }

    private func deleteMedication(_ medication: PetMedication) async {
        do {
            let response = try await DataService.shared.deleteMedication(
                id: medication.id,
                petId: medication.petId
            )
            medicationToDelete = nil
            await loadMedications(forceRefresh: true, showLoading: false)

            if response.archived && !response.deleted {
                deleteResultMessage = response.message
                showDeleteResultAlert = true
            }
        } catch {
            errorMessage = error.localizedDescription
            print("Error deleting medication: \(error)")
        }
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
    @State private var isLoading = false
    @State private var hasLoaded = false
    @State private var showAddEvent = false
    @State private var showRecordWeight = false
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
                if pets.isEmpty && hasLoaded {
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

                        if events.isEmpty && hasLoaded {
                            emptyState
                        } else {
                            eventsList
                        }
                    }
                }
            }
            .overlay {
                if isLoading && !hasLoaded {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color(uiColor: .systemBackground))
                }
            }
            .navigationTitle("Health Journal")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    if !pets.isEmpty {
                        HStack(spacing: 16) {
                            Button(action: {
                                showRecordWeight = true
                            }) {
                                Image(systemName: "gauge.with.needle")
                            }
                            Button(action: {
                                showAddEvent = true
                            }) {
                                Image(systemName: "plus")
                            }
                        }
                    }
                }
            }
            .sheet(isPresented: $showAddEvent) {
                if let pet = selectedPet {
                    AddHealthEventView(petId: pet.id)
                }
            }
            .sheet(isPresented: $showRecordWeight) {
                if let pet = selectedPet {
                    RecordWeightView(petId: pet.id, petName: pet.name, currentWeight: pet.currentWeight)
                }
            }
            .onChange(of: showAddEvent) { _, isShowing in
                if !isShowing {
                    Task {
                        await loadEvents()
                    }
                }
            }
            .onChange(of: showRecordWeight) { _, isShowing in
                if !isShowing {
                    Task {
                        await loadPets(forceRefresh: true)  // Reload to get updated current_weight
                    }
                }
            }
            .onChange(of: selectedPet) { _, _ in
                Task {
                    await loadEvents()
                }
            }
            .task {
                guard !hasLoaded else { return }
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

    private func loadPets(forceRefresh: Bool = false) async {
        isLoading = true
        do {
            pets = try await DataService.shared.getPets(forceRefresh: forceRefresh)
            // Update selectedPet with fresh data (e.g., new currentWeight)
            if let currentId = selectedPet?.id {
                selectedPet = pets.first { $0.id == currentId }
            }
            if selectedPet == nil {
                selectedPet = pets.first
            }
            await loadEvents()
            hasLoaded = true
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Health pets load cancelled (this is normal during navigation)")
        } catch {
            print("Error loading pets: \(error)")
        }
        isLoading = false
    }

    private func loadEvents() async {
        guard let pet = selectedPet else { return }
        do {
            events = try await DataService.shared.getHealthEvents(for: pet.id)
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Health events load cancelled (this is normal during navigation)")
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
    private var authManager = AuthManager.shared
    @State private var pets: [Pet] = []
    @State private var isLoading = false
    @State private var hasLoaded = false
    @State private var errorMessage: String?
    @State private var showSignOutError = false

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Account Section
                    accountSection

                    // Family Section
                    if let family = authManager.currentFamily {
                        familySection(family: family)
                    }

                    // Pets Section
                    petsSection

                    Spacer()

                    // Sign Out Button
                    signOutButton
                }
                .padding()
            }
            .overlay {
                if isLoading && !hasLoaded {
                    ProgressView("Loading...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color(uiColor: .systemBackground))
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                guard !hasLoaded else { return }
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
                        Text(authManager.displayName ?? authManager.userEmail ?? "Unknown")
                            .font(.body)
                            .fontWeight(.medium)

                        if let email = authManager.userEmail, authManager.displayName != nil {
                            Text(email)
                                .font(.caption)
                                .foregroundColor(.secondary)
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

    private func familySection(family: AppFamily) -> some View {
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
                        Text(family.name)
                            .font(.body)
                            .fontWeight(.medium)

                        Text("Role: \(family.role.capitalized)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Spacer()
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)

                // Invite code section
                VStack(alignment: .leading, spacing: 4) {
                    Text("Invite Code")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    HStack {
                        Text(family.inviteCode)
                            .font(.system(.body, design: .monospaced))
                            .fontWeight(.semibold)

                        Spacer()

                        Button(action: {
                            UIPasteboard.general.string = family.inviteCode
                        }) {
                            Image(systemName: "doc.on.doc")
                                .foregroundColor(.blue)
                        }
                    }
                    .padding()
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(8)
                }
                .padding(.top, 4)

                Text("Share this code to invite family members")
                    .font(.caption2)
                    .foregroundColor(.secondary)
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
            hasLoaded = true
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Settings load cancelled (this is normal during navigation)")
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading settings data: \(error)")
        }

        isLoading = false
    }

    private func signOut() {
        authManager.signOut()
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
