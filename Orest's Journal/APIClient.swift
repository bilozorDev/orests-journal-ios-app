//
//  APIClient.swift
//  Orest's Journal
//
//  Network client for FastAPI backend with authentication.
//

import Foundation

// MARK: - Configuration

struct APIConfiguration {
    // For local development via ngrok:
    static let baseURL = "https://climbing-helping-hermit.ngrok-free.app/api/v1"
    // For local development on device (use Mac's IP address):
    // static let baseURL = "http://192.168.0.225:8000/api/v1"
    // For simulator:
    // static let baseURL = "http://localhost:8000/api/v1"
    // For production (update when deployed to Railway):
    // static let baseURL = "https://your-app.railway.app/api/v1"
}

// MARK: - API Errors

enum APIError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(statusCode: Int, message: String)
    case decodingError(Error)
    case networkError(Error)
    case unauthorized
    case notFound

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code, let message):
            return "HTTP \(code): \(message)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .unauthorized:
            return "Unauthorized. Please sign in again."
        case .notFound:
            return "Resource not found"
        }
    }
}

// MARK: - API Client

class APIClient: APIClientProtocol {
    static let shared = APIClient()

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    // Auth token for API requests
    var authToken: String?

    // Current organization ID (family)
    var currentOrgId: String?

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)

        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)

            // Try ISO8601 with fractional seconds
            let isoFormatter = ISO8601DateFormatter()
            isoFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = isoFormatter.date(from: dateString) {
                return date
            }

            // Try ISO8601 without fractional seconds
            isoFormatter.formatOptions = [.withInternetDateTime]
            if let date = isoFormatter.date(from: dateString) {
                return date
            }

            // Try without timezone (assume UTC)
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
            formatter.timeZone = TimeZone(identifier: "UTC")
            if let date = formatter.date(from: dateString) {
                return date
            }

            formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
            if let date = formatter.date(from: dateString) {
                return date
            }

            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode date: \(dateString)")
        }
        self.decoder.keyDecodingStrategy = .convertFromSnakeCase

        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
        self.encoder.keyEncodingStrategy = .convertToSnakeCase
    }

    // MARK: - Generic Request Method (used by AuthManager)

    func request<T: Decodable>(
        endpoint: String,
        method: String,
        body: Encodable? = nil
    ) async throws -> T {
        let request = try buildRequest(path: endpoint, method: method, body: body)
        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    // MARK: - Request Builder

    private func buildRequest(
        path: String,
        method: String = "GET",
        queryItems: [URLQueryItem]? = nil,
        body: Encodable? = nil
    ) throws -> URLRequest {
        var components = URLComponents(string: APIConfiguration.baseURL + path)
        components?.queryItems = queryItems

        guard let url = components?.url else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token if available
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = try encoder.encode(body)
        }

        return request
    }

    // MARK: - Response Handler

    private func handleResponse<T: Decodable>(_ data: Data, _ response: URLResponse) throws -> T {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                throw APIError.decodingError(error)
            }
        case 401:
            throw APIError.unauthorized
        case 404:
            throw APIError.notFound
        default:
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: message)
        }
    }

    private func handleEmptyResponse(_ data: Data, _ response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            return
        case 401:
            throw APIError.unauthorized
        case 404:
            throw APIError.notFound
        default:
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: message)
        }
    }

    // MARK: - Generic Request Methods

    func get<T: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem]? = nil
    ) async throws -> T {
        let request = try buildRequest(path: path, queryItems: queryItems)
        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    func post<T: Decodable, B: Encodable>(
        _ path: String,
        body: B,
        queryItems: [URLQueryItem]? = nil
    ) async throws -> T {
        let request = try buildRequest(path: path, method: "POST", queryItems: queryItems, body: body)
        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    func patch<T: Decodable, B: Encodable>(
        _ path: String,
        body: B
    ) async throws -> T {
        let request = try buildRequest(path: path, method: "PATCH", body: body)
        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    func delete(_ path: String) async throws {
        let request = try buildRequest(path: path, method: "DELETE")
        let (data, response) = try await session.data(for: request)
        try handleEmptyResponse(data, response)
    }

    func delete<T: Encodable>(_ path: String, body: T) async throws {
        var request = try buildRequest(path: path, method: "DELETE")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(body)
        let (data, response) = try await session.data(for: request)
        try handleEmptyResponse(data, response)
    }

    func deleteWithResponse<T: Decodable>(_ path: String) async throws -> T {
        let request = try buildRequest(path: path, method: "DELETE")
        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    // MARK: - Pets

    func getPets() async throws -> [Pet] {
        guard let orgId = currentOrgId else {
            throw APIError.unauthorized
        }
        let response: PetListResponse = try await get("/pets", queryItems: [
            URLQueryItem(name: "org_id", value: orgId)
        ])
        return response.pets
    }

    func createPet(_ pet: PetCreate) async throws -> Pet {
        guard let orgId = currentOrgId else {
            throw APIError.unauthorized
        }
        return try await post("/pets", body: pet, queryItems: [
            URLQueryItem(name: "org_id", value: orgId)
        ])
    }

    func updatePet(id: UUID, update: PetUpdate) async throws -> Pet {
        return try await patch("/pets/\(id.uuidString)", body: update)
    }

    func deletePet(id: UUID) async throws -> PetDeleteResponse {
        return try await deleteWithResponse("/pets/\(id.uuidString)")
    }

    func uploadPetPhoto(imageData: Data) async throws -> String {
        guard let url = URL(string: APIConfiguration.baseURL + "/uploads/pet-photo") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        // Add auth token if available
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"pet.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        struct UploadResponse: Decodable {
            let url: String
        }

        let result: UploadResponse = try handleResponse(data, response)
        return result.url
    }

    // MARK: - Health Records

    func createHealthRecord(petId: UUID, weightPounds: Double?, ageYears: Double?, notes: String?) async throws -> HealthRecord {
        let record = HealthRecordCreate(weightPounds: weightPounds, ageYears: ageYears, notes: notes)
        return try await post("/pets/\(petId.uuidString)/health-records", body: record)
    }

    func getHealthRecords(petId: UUID) async throws -> [HealthRecord] {
        return try await get("/pets/\(petId.uuidString)/health-records")
    }

    // MARK: - Foods

    func getFoods(includeArchived: Bool = false) async throws -> [PetFood] {
        guard let orgId = currentOrgId else {
            throw APIError.unauthorized
        }
        var queryItems = [URLQueryItem(name: "org_id", value: orgId)]
        if includeArchived {
            queryItems.append(URLQueryItem(name: "include_archived", value: "true"))
        }
        let response: FoodListResponse = try await get("/foods", queryItems: queryItems)
        return response.foods
    }

    func createFood(_ food: FoodCreate) async throws -> PetFood {
        guard let orgId = currentOrgId else {
            throw APIError.unauthorized
        }
        return try await post("/foods", body: food, queryItems: [
            URLQueryItem(name: "org_id", value: orgId)
        ])
    }

    func updateFood(id: UUID, update: FoodUpdate) async throws -> PetFood {
        return try await patch("/foods/\(id.uuidString)", body: update)
    }

    func deleteFood(id: UUID) async throws -> FoodDeleteResponse {
        let request = try buildRequest(path: "/foods/\(id.uuidString)", method: "DELETE")
        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    // MARK: - Feedings

    func createFeeding(_ feeding: FeedingCreate) async throws -> PetFeeding {
        return try await post("/feedings", body: feeding)
    }

    func getTodayFeedings(petId: UUID) async throws -> FeedingListResponse {
        return try await get("/feedings/pet/\(petId.uuidString)/today")
    }

    func getFeedingHistory(petId: UUID, limit: Int = 50, offset: Int = 0) async throws -> FeedingListResponse {
        return try await get("/feedings/pet/\(petId.uuidString)", queryItems: [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String(offset))
        ])
    }

    func updateFeeding(id: UUID, update: FeedingUpdate) async throws -> PetFeeding {
        return try await patch("/feedings/\(id.uuidString)", body: update)
    }

    func deleteFeeding(id: UUID) async throws {
        try await delete("/feedings/\(id.uuidString)")
    }

    func getCalorieGoal(petId: UUID) async throws -> CalorieGoal? {
        do {
            return try await get("/feedings/pet/\(petId.uuidString)/calorie-goal")
        } catch APIError.notFound {
            return nil
        }
    }

    func setCalorieGoal(petId: UUID, dailyCalories: Double, notes: String?) async throws -> CalorieGoal {
        struct GoalCreate: Encodable {
            let dailyCalories: Double
            let notes: String?
        }
        return try await post("/feedings/pet/\(petId.uuidString)/calorie-goal", body: GoalCreate(
            dailyCalories: dailyCalories,
            notes: notes
        ))
    }

    // MARK: - Medications

    func getMedications(petId: UUID? = nil, activeOnly: Bool = false, includeArchived: Bool = false) async throws -> [PetMedication] {
        guard let orgId = currentOrgId else {
            throw APIError.unauthorized
        }
        var queryItems = [
            URLQueryItem(name: "org_id", value: orgId),
            URLQueryItem(name: "timezone", value: TimeZone.current.identifier)
        ]
        if let petId = petId {
            queryItems.append(URLQueryItem(name: "pet_id", value: petId.uuidString))
        }
        if activeOnly {
            queryItems.append(URLQueryItem(name: "active_only", value: "true"))
        }
        if includeArchived {
            queryItems.append(URLQueryItem(name: "include_archived", value: "true"))
        }
        let response: MedicationListResponse = try await get("/medications", queryItems: queryItems)
        return response.medications
    }

    func getActiveMedications(petId: UUID) async throws -> [PetMedication] {
        let response: MedicationListResponse = try await get("/medications/pet/\(petId.uuidString)/active", queryItems: [
            URLQueryItem(name: "timezone", value: TimeZone.current.identifier)
        ])
        return response.medications
    }

    func createMedication(_ medication: MedicationCreate) async throws -> PetMedication {
        return try await post("/medications", body: medication)
    }

    func updateMedication(id: UUID, update: MedicationUpdate) async throws -> PetMedication {
        return try await patch("/medications/\(id.uuidString)", body: update)
    }

    func deleteMedication(id: UUID) async throws -> MedicationDeleteResponse {
        return try await deleteWithResponse("/medications/\(id.uuidString)")
    }

    // MARK: - Doses

    func recordDose(_ dose: DoseCreate) async throws -> PetMedicationDose {
        return try await post("/doses", body: dose)
    }

    func getTodayDoses(medicationId: UUID) async throws -> [PetMedicationDose] {
        let response: DoseListResponse = try await get("/doses/medication/\(medicationId.uuidString)/today", queryItems: [
            URLQueryItem(name: "timezone", value: TimeZone.current.identifier)
        ])
        return response.doses
    }

    func getLastDose(medicationId: UUID) async throws -> PetMedicationDose? {
        do {
            return try await get("/doses/medication/\(medicationId.uuidString)/last")
        } catch APIError.notFound {
            return nil
        }
    }

    func getDoses(medicationId: UUID, limit: Int = 50) async throws -> [PetMedicationDose] {
        let response: DoseListResponse = try await get("/doses/medication/\(medicationId.uuidString)", queryItems: [
            URLQueryItem(name: "limit", value: String(limit))
        ])
        return response.doses
    }

    func updateDose(id: UUID, update: DoseUpdate) async throws -> PetMedicationDose {
        return try await patch("/doses/\(id.uuidString)", body: update)
    }

    func deleteDose(id: UUID) async throws {
        try await delete("/doses/\(id.uuidString)")
    }

    func getAllDoses(petId: UUID, limit: Int = 50, offset: Int = 0) async throws -> AllDosesListResponse {
        return try await get("/doses/all/\(petId.uuidString)", queryItems: [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String(offset))
        ])
    }

    // MARK: - Family

    func getFamilyMembers(familyId: String) async throws -> FamilyDetailResponse {
        return try await get("/families/\(familyId)")
    }

    func updateMemberRole(familyId: String, memberUserId: String, role: String) async throws -> FamilyMemberResponse {
        struct RoleUpdateRequest: Encodable {
            let role: String
        }
        return try await patch("/families/\(familyId)/members/\(memberUserId)/role", body: RoleUpdateRequest(role: role))
    }

    func removeFamilyMember(familyId: String, memberUserId: String) async throws {
        try await delete("/families/\(familyId)/members/\(memberUserId)")
    }

    func regenerateInviteCode(familyId: String) async throws -> AppFamily {
        return try await post("/families/\(familyId)/regenerate-invite-code", body: EmptyBody())
    }

    // MARK: - Health Events

    func getHealthCategories(petId: UUID) async throws -> [HealthCategory] {
        return try await get("/health/pet/\(petId.uuidString)/categories")
    }

    func createHealthEvent(petId: UUID, event: HealthEventCreate) async throws -> HealthEvent {
        return try await post("/health/pet/\(petId.uuidString)/events", body: event)
    }

    func getHealthEvents(petId: UUID, limit: Int = 100) async throws -> [HealthEventWithCategory] {
        let response: HealthEventListResponse = try await get("/health/pet/\(petId.uuidString)/events", queryItems: [
            URLQueryItem(name: "limit", value: String(limit))
        ])
        return response.events
    }

    func deleteHealthEvent(id: UUID) async throws {
        try await delete("/health/events/\(id.uuidString)")
    }

    // MARK: - Dashboard

    func getDashboardData(petId: UUID) async throws -> DashboardData {
        guard let orgId = currentOrgId else {
            throw APIError.unauthorized
        }
        return try await get("/dashboard/pet/\(petId.uuidString)", queryItems: [
            URLQueryItem(name: "org_id", value: orgId),
            URLQueryItem(name: "timezone", value: TimeZone.current.identifier)
        ])
    }

    // MARK: - Notifications

    func registerDeviceToken(token: String, deviceName: String) async throws -> DeviceTokenResponse {
        let request = DeviceTokenRequest(deviceToken: token, deviceName: deviceName)
        return try await post("/notifications/device-token", body: request)
    }

    func unregisterDeviceToken(token: String) async throws {
        let request = DeviceTokenDeleteRequest(deviceToken: token)
        try await delete("/notifications/device-token", body: request)
    }
}

// MARK: - Request/Response Types

// These match the FastAPI schemas

struct PetCreate: Encodable {
    let name: String
    let kind: String
    let photoUrl: String?
    let currentWeight: Double?
}

struct PetUpdate: Encodable {
    let name: String?
    let kind: String?
    let photoUrl: String?
    let currentWeight: Double?
}

struct PetListResponse: Decodable {
    let pets: [Pet]
}

struct FoodCreate: Encodable {
    let name: String
    let category: String
    let caloriesPerKg: Double
    let containerSize: Double
    let containerSizeUnit: String
    let imageUrl: String?
}

struct FoodUpdate: Encodable {
    let name: String?
    let category: String?
    let caloriesPerKg: Double?
    let containerSize: Double?
    let containerSizeUnit: String?
    let imageUrl: String?
}

struct FoodListResponse: Decodable {
    let foods: [PetFood]
}

struct FeedingCreate: Encodable {
    let petId: UUID
    let foodId: UUID
    let amount: Double
    let amountUnit: String
    let calories: Double
    let notes: String?
    let fedAt: Date?
}

struct FeedingUpdate: Encodable {
    let amount: Double?
    let amountUnit: String?
    let calories: Double?
    let notes: String?
    let fedAt: Date?
    let fedBy: UUID?
}

struct FeedingListResponse: Codable {
    let feedings: [PetFeeding]
    let totalCalories: Double
    let total: Int
}

struct MedicationCreate: Encodable {
    let petId: UUID
    let name: String
    let medicationType: String
    let startDate: Date
    let endDate: Date?
    let timesPerDay: Int
    let notes: String?
    let remindersEnabled: Bool?
    let timezone: String?
    let scheduledTimes: [ScheduledTimeCreate]?
}

struct MedicationListResponse: Decodable {
    let medications: [PetMedication]
}

struct DoseCreate: Encodable {
    let medicationId: UUID
    let notes: String?
    let givenAt: Date?
}

struct DoseUpdate: Encodable {
    let givenAt: Date?
    let givenBy: UUID?
    let notes: String?
}

struct DoseListResponse: Decodable {
    let doses: [PetMedicationDose]
}

struct HealthEventCreate: Encodable {
    let categoryName: String
    let occurredAt: Date?
    let notes: String?
}

struct HealthEventListResponse: Decodable {
    let events: [HealthEventWithCategory]
}

// MARK: - Dashboard Types

struct MedicationWithDoses: Codable {
    let medication: PetMedication
    let lastDose: PetMedicationDose?
    let todayDoseCount: Int
    let dosesRemaining: Int
}

struct DashboardData: Codable {
    let calorieGoal: CalorieGoal?
    let todayFeedings: [PetFeeding]
    let totalCalories: Double
    let foods: [PetFood]
    let medications: [MedicationWithDoses]
}

// MARK: - Family Types

struct EmptyBody: Encodable {}

struct FamilyMemberResponse: Codable, Identifiable {
    let id: String
    let userId: String
    let email: String?
    let firstName: String?
    let lastName: String?
    let role: String
    let joinedAt: Date?

    /// Display name format: "FirstName L." or just "FirstName" if no last name
    var displayName: String {
        if let firstName = firstName, !firstName.isEmpty {
            if let lastName = lastName, !lastName.isEmpty {
                let initial = String(lastName.prefix(1)).uppercased()
                return "\(firstName) \(initial)."
            }
            return firstName
        }
        return email ?? "Unknown"
    }
}

struct FamilyDetailResponse: Decodable {
    let id: String
    let name: String
    let inviteCode: String
    let createdAt: Date
    let members: [FamilyMemberResponse]
}

// MARK: - Notification Types

struct DeviceTokenRequest: Encodable {
    let deviceToken: String
    let deviceName: String
}

struct DeviceTokenDeleteRequest: Encodable {
    let deviceToken: String
}

struct DeviceTokenResponse: Decodable {
    let id: UUID
    let userId: UUID
    let deviceToken: String
    let deviceName: String?
    let platform: String
    let isActive: Bool
    let createdAt: Date
    let updatedAt: Date
}
