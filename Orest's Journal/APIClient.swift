//
//  APIClient.swift
//  Orest's Journal
//
//  Network client for FastAPI backend with Clerk authentication.
//

import Foundation

// MARK: - Configuration

struct APIConfiguration {
    // TODO: Update these for your deployment
    static let baseURL = "https://your-app.railway.app/api/v1"  // Railway URL
    // static let baseURL = "http://localhost:8000/api/v1"  // Local development
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

class APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    // Clerk token provider - set this from ClerkSDK
    var getToken: (() async throws -> String)?

    // Current organization ID (family) - set from Clerk
    var currentOrgId: String?

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)

        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
        self.decoder.keyDecodingStrategy = .convertFromSnakeCase

        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
        self.encoder.keyEncodingStrategy = .convertToSnakeCase
    }

    // MARK: - Request Builder

    private func buildRequest(
        path: String,
        method: String = "GET",
        queryItems: [URLQueryItem]? = nil,
        body: Encodable? = nil
    ) async throws -> URLRequest {
        var components = URLComponents(string: APIConfiguration.baseURL + path)
        components?.queryItems = queryItems

        guard let url = components?.url else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token from Clerk
        if let getToken = getToken {
            let token = try await getToken()
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
        let request = try await buildRequest(path: path, queryItems: queryItems)
        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    func post<T: Decodable, B: Encodable>(
        _ path: String,
        body: B,
        queryItems: [URLQueryItem]? = nil
    ) async throws -> T {
        let request = try await buildRequest(path: path, method: "POST", queryItems: queryItems, body: body)
        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    func patch<T: Decodable, B: Encodable>(
        _ path: String,
        body: B
    ) async throws -> T {
        let request = try await buildRequest(path: path, method: "PATCH", body: body)
        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    func delete(_ path: String) async throws {
        let request = try await buildRequest(path: path, method: "DELETE")
        let (data, response) = try await session.data(for: request)
        try handleEmptyResponse(data, response)
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

    func deletePet(id: UUID) async throws {
        try await delete("/pets/\(id.uuidString)")
    }

    // MARK: - Foods

    func getFoods() async throws -> [PetFood] {
        guard let orgId = currentOrgId else {
            throw APIError.unauthorized
        }
        let response: FoodListResponse = try await get("/foods", queryItems: [
            URLQueryItem(name: "org_id", value: orgId)
        ])
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

    func deleteFood(id: UUID) async throws {
        try await delete("/foods/\(id.uuidString)")
    }

    // MARK: - Feedings

    func createFeeding(_ feeding: FeedingCreate) async throws -> PetFeeding {
        return try await post("/feedings", body: feeding)
    }

    func getTodayFeedings(petId: UUID) async throws -> FeedingListResponse {
        return try await get("/feedings/pet/\(petId.uuidString)/today")
    }

    func getFeedingHistory(petId: UUID, limit: Int = 50) async throws -> [PetFeeding] {
        let response: FeedingListResponse = try await get("/feedings/pet/\(petId.uuidString)", queryItems: [
            URLQueryItem(name: "limit", value: String(limit))
        ])
        return response.feedings
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

    func getMedications(petId: UUID? = nil, activeOnly: Bool = false) async throws -> [PetMedication] {
        guard let orgId = currentOrgId else {
            throw APIError.unauthorized
        }
        var queryItems = [URLQueryItem(name: "org_id", value: orgId)]
        if let petId = petId {
            queryItems.append(URLQueryItem(name: "pet_id", value: petId.uuidString))
        }
        if activeOnly {
            queryItems.append(URLQueryItem(name: "active_only", value: "true"))
        }
        let response: MedicationListResponse = try await get("/medications", queryItems: queryItems)
        return response.medications
    }

    func getActiveMedications(petId: UUID) async throws -> [PetMedication] {
        let response: MedicationListResponse = try await get("/medications/pet/\(petId.uuidString)/active")
        return response.medications
    }

    func createMedication(_ medication: MedicationCreate) async throws -> PetMedication {
        return try await post("/medications", body: medication)
    }

    func deleteMedication(id: UUID) async throws {
        try await delete("/medications/\(id.uuidString)")
    }

    // MARK: - Doses

    func recordDose(_ dose: DoseCreate) async throws -> PetMedicationDose {
        return try await post("/doses", body: dose)
    }

    func getTodayDoses(medicationId: UUID) async throws -> [PetMedicationDose] {
        let response: DoseListResponse = try await get("/doses/medication/\(medicationId.uuidString)/today")
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

struct FeedingListResponse: Decodable {
    let feedings: [PetFeeding]
    let totalCalories: Double
}

struct MedicationCreate: Encodable {
    let petId: UUID
    let name: String
    let medicationType: String
    let startDate: Date
    let endDate: Date?
    let timesPerDay: Int
    let notes: String?
}

struct MedicationListResponse: Decodable {
    let medications: [PetMedication]
}

struct DoseCreate: Encodable {
    let medicationId: UUID
    let notes: String?
    let givenAt: Date?
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
