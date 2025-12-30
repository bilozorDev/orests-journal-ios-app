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

@MainActor
final class APIClient: APIClientProtocol {
    static let shared = APIClient()

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    var authToken: String?
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

            let isoFormatter = ISO8601DateFormatter()
            isoFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = isoFormatter.date(from: dateString) {
                return date
            }

            isoFormatter.formatOptions = [.withInternetDateTime]
            if let date = isoFormatter.date(from: dateString) {
                return date
            }

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

            // Handle date-only strings (e.g., "2021-05-23" from backend date fields)
            formatter.dateFormat = "yyyy-MM-dd"
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
        // Only override query items if explicitly provided
        if let queryItems = queryItems {
            components?.queryItems = queryItems
        }

        guard let url = components?.url else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

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
        return try await patch("/pets/\(id.uuidString.lowercased())", body: update)
    }

    func deletePet(id: UUID) async throws {
        try await delete("/pets/\(id.uuidString.lowercased())")
    }

    func uploadPetPhoto(imageData: Data, mimeType: String = "image/jpeg") async throws -> String {
        guard let url = URL(string: APIConfiguration.baseURL + "/uploads/pet-photo") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        // Longer timeout for uploads (60 seconds)
        request.timeoutInterval = 60

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        // Determine file extension from mime type
        let fileExtension = mimeType == "image/png" ? "png" : "jpg"
        let filename = "pet.\(fileExtension)"

        var body = Data()
        // These ASCII strings are guaranteed to convert successfully
        body.append(Data("--\(boundary)\r\n".utf8))
        body.append(Data("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".utf8))
        body.append(Data("Content-Type: \(mimeType)\r\n\r\n".utf8))
        body.append(imageData)
        body.append(Data("\r\n--\(boundary)--\r\n".utf8))

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        struct UploadResponse: Decodable {
            let url: String
        }

        let result: UploadResponse = try handleResponse(data, response)
        return result.url
    }

    // MARK: - Calorie Goals

    func getCalorieGoal(petId: UUID) async throws -> CalorieGoal? {
        do {
            return try await get("/feedings/pet/\(petId.uuidString)/calorie-goal")
        } catch APIError.notFound {
            return nil
        }
    }

    func setCalorieGoal(petId: UUID, dailyCalories: Double, notes: String?) async throws -> CalorieGoal {
        let create = CalorieGoalCreate(petId: petId, dailyCalories: dailyCalories, notes: notes)
        return try await post("/feedings/pet/\(petId.uuidString)/calorie-goal", body: create)
    }

    // MARK: - Family

    func getFamilyDetails(familyId: String) async throws -> FamilyDetailResponse {
        return try await get("/families/\(familyId)")
    }

    func updateMemberRole(familyId: String, userId: String, role: String) async throws -> FamilyMember {
        struct RoleUpdateRequest: Encodable {
            let role: String
        }
        let response: FamilyMemberResponse = try await patch("/families/\(familyId)/members/\(userId)/role", body: RoleUpdateRequest(role: role))
        return FamilyMember(
            id: response.id,
            orgId: familyId,
            userId: response.userId,
            role: response.role,
            joinedAt: response.joinedAt,
            email: response.email,
            firstName: response.firstName,
            lastName: response.lastName
        )
    }

    func removeFamilyMember(familyId: String, userId: String) async throws {
        try await delete("/families/\(familyId)/members/\(userId)")
    }

    func updateFamilyName(familyId: String, name: String) async throws -> AppFamily {
        struct UpdateFamilyRequest: Encodable {
            let name: String
        }
        return try await patch("/families/\(familyId)", body: UpdateFamilyRequest(name: name))
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

    func getNotificationPreferences() async throws -> NotificationPreferences {
        return try await get("/notifications/preferences")
    }

    func updateNotificationPreferences(_ update: NotificationPreferencesUpdate) async throws -> NotificationPreferences {
        return try await patch("/notifications/preferences", body: update)
    }

    // MARK: - Health Events

    func getHealthEvents(
        petId: UUID,
        limit: Int = 100,
        offset: Int = 0,
        category: String? = nil,
        since: Date? = nil,
        until: Date? = nil
    ) async throws -> [HealthEventWithCategory] {
        var queryItems = [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String(offset))
        ]
        if let category = category {
            queryItems.append(URLQueryItem(name: "category", value: category))
        }
        if let since = since {
            queryItems.append(URLQueryItem(name: "since", value: Formatters.iso8601.string(from: since)))
        }
        if let until = until {
            queryItems.append(URLQueryItem(name: "until", value: Formatters.iso8601.string(from: until)))
        }
        let response: HealthEventListResponse = try await get("/health/pet/\(petId.uuidString.lowercased())/events", queryItems: queryItems)
        return response.events
    }

    func getHealthEvent(eventId: UUID) async throws -> HealthEventWithCategory {
        return try await get("/health/events/\(eventId.uuidString.lowercased())")
    }

    func createHealthEvent(petId: UUID, event: HealthEventCreate) async throws -> HealthEvent {
        return try await post("/health/pet/\(petId.uuidString.lowercased())/events", body: event)
    }

    func updateHealthEvent(eventId: UUID, update: HealthEventUpdate) async throws -> HealthEventWithCategory {
        return try await patch("/health/events/\(eventId.uuidString.lowercased())", body: update)
    }

    func deleteHealthEvent(eventId: UUID) async throws {
        try await delete("/health/events/\(eventId.uuidString.lowercased())")
    }

    func searchHealthEvents(
        petId: UUID,
        query: String,
        category: String? = nil,
        since: Date? = nil,
        until: Date? = nil,
        limit: Int = 50
    ) async throws -> [HealthEventWithCategory] {
        var queryItems = [
            URLQueryItem(name: "q", value: query),
            URLQueryItem(name: "limit", value: String(limit))
        ]
        if let category = category {
            queryItems.append(URLQueryItem(name: "category", value: category))
        }
        if let since = since {
            queryItems.append(URLQueryItem(name: "since", value: Formatters.iso8601.string(from: since)))
        }
        if let until = until {
            queryItems.append(URLQueryItem(name: "until", value: Formatters.iso8601.string(from: until)))
        }
        let response: HealthEventListResponse = try await get("/health/pet/\(petId.uuidString.lowercased())/search", queryItems: queryItems)
        return response.events
    }

    func getHealthCategories(petId: UUID) async throws -> [HealthCategory] {
        return try await get("/health/pet/\(petId.uuidString.lowercased())/categories")
    }

    func uploadHealthEventPhoto(eventId: UUID, imageData: Data, mimeType: String = "image/jpeg") async throws -> HealthEventPhoto {
        guard let url = URL(string: APIConfiguration.baseURL + "/health/events/\(eventId.uuidString.lowercased())/photo") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 60

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let fileExtension = mimeType == "image/png" ? "png" : "jpg"
        let filename = "health_event.\(fileExtension)"

        var body = Data()
        body.append(Data("--\(boundary)\r\n".utf8))
        body.append(Data("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".utf8))
        body.append(Data("Content-Type: \(mimeType)\r\n\r\n".utf8))
        body.append(imageData)
        body.append(Data("\r\n--\(boundary)--\r\n".utf8))

        request.httpBody = body

        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    func deleteHealthEventPhoto(eventId: UUID, photoId: UUID) async throws {
        try await delete("/health/events/\(eventId.uuidString.lowercased())/photos/\(photoId.uuidString.lowercased())")
    }

    // MARK: - Medications

    func getMedications(
        orgId: UUID,
        petId: UUID? = nil,
        activeOnly: Bool = false,
        includeArchived: Bool = false,
        timezone: String = TimeZone.current.identifier
    ) async throws -> MedicationListResponse {
        var path = "/medications?org_id=\(orgId.uuidString.lowercased())&timezone=\(timezone)"
        if let petId = petId {
            path += "&pet_id=\(petId.uuidString.lowercased())"
        }
        if activeOnly {
            path += "&active_only=true"
        }
        if includeArchived {
            path += "&include_archived=true"
        }
        return try await get(path)
    }

    func getMedication(id: UUID) async throws -> Medication {
        return try await get("/medications/\(id.uuidString.lowercased())")
    }

    func createMedication(_ medication: MedicationCreate) async throws -> Medication {
        return try await post("/medications", body: medication)
    }

    func updateMedication(id: UUID, _ update: MedicationUpdate) async throws -> Medication {
        return try await patch("/medications/\(id.uuidString.lowercased())", body: update)
    }

    func deleteMedication(id: UUID) async throws -> MedicationDeleteResponse {
        return try await deleteWithResponse("/medications/\(id.uuidString.lowercased())")
    }

    func getActiveMedicationsForPet(petId: UUID, timezone: String = TimeZone.current.identifier) async throws -> MedicationListResponse {
        return try await get("/medications/pet/\(petId.uuidString.lowercased())/active?timezone=\(timezone)")
    }

    func uploadMedicationPhoto(medicationId: UUID, imageData: Data, mimeType: String = "image/jpeg") async throws -> MedicationPhoto {
        guard let url = URL(string: APIConfiguration.baseURL + "/medications/\(medicationId.uuidString.lowercased())/photos") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 60

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let fileExtension = mimeType == "image/png" ? "png" : "jpg"
        let filename = "medication.\(fileExtension)"

        var body = Data()
        body.append(Data("--\(boundary)\r\n".utf8))
        body.append(Data("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".utf8))
        body.append(Data("Content-Type: \(mimeType)\r\n\r\n".utf8))
        body.append(imageData)
        body.append(Data("\r\n--\(boundary)--\r\n".utf8))

        request.httpBody = body

        let (data, response) = try await session.data(for: request)
        return try handleResponse(data, response)
    }

    func deleteMedicationPhoto(medicationId: UUID, photoId: UUID) async throws {
        try await delete("/medications/\(medicationId.uuidString.lowercased())/photos/\(photoId.uuidString.lowercased())")
    }

    // MARK: - Doses

    func recordDose(_ dose: DoseCreate) async throws -> MedicationDose {
        return try await post("/doses", body: dose)
    }

    func getDosesForMedication(medicationId: UUID, limit: Int = 50, offset: Int = 0) async throws -> DoseListResponse {
        return try await get("/doses/medication/\(medicationId.uuidString.lowercased())?limit=\(limit)&offset=\(offset)")
    }

    func getTodaysDoses(medicationId: UUID, timezone: String = TimeZone.current.identifier) async throws -> DoseListResponse {
        return try await get("/doses/medication/\(medicationId.uuidString.lowercased())/today?timezone=\(timezone)")
    }

    func getLastDose(medicationId: UUID) async throws -> MedicationDose {
        return try await get("/doses/medication/\(medicationId.uuidString.lowercased())/last")
    }

    func getAllDosesForPet(petId: UUID, limit: Int = 50, offset: Int = 0) async throws -> AllDosesListResponse {
        return try await get("/doses/all/\(petId.uuidString.lowercased())?limit=\(limit)&offset=\(offset)")
    }

    func updateDose(doseId: UUID, _ update: DoseUpdate) async throws -> MedicationDose {
        return try await patch("/doses/\(doseId.uuidString.lowercased())", body: update)
    }

    func deleteDose(doseId: UUID) async throws {
        try await delete("/doses/\(doseId.uuidString.lowercased())")
    }
}

// MARK: - Request/Response Types

struct PetCreate: Encodable {
    let name: String
    let kind: String
    let photoUrl: String?
    let currentWeight: Double?
    let dateOfBirth: Date?

    init(name: String, kind: String, photoUrl: String?, currentWeight: Double? = nil, dateOfBirth: Date? = nil) {
        self.name = name
        self.kind = kind
        self.photoUrl = photoUrl
        self.currentWeight = currentWeight
        self.dateOfBirth = dateOfBirth
    }
}

struct PetUpdate: Encodable {
    let name: String?
    let kind: String?
    let photoUrl: String?
    let currentWeight: Double?
    let dateOfBirth: Date?
}

struct PetListResponse: Decodable {
    let pets: [Pet]
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

    var displayName: String {
        Formatters.formatDisplayName(firstName: firstName, lastName: lastName, fallback: email ?? "Unknown")
    }
}

struct FamilyDetailResponse: Codable {
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

// MARK: - Notification Preferences Types

struct NotificationPreferences: Codable {
    // Family Updates
    var familyMemberJoined: Bool
    var familyRoleChanged: Bool
    var familyMemberLeft: Bool
    var familyMemberLeftPromoted: Bool
    var familyAccountDeleted: Bool
    var familyAccountDeletedPromoted: Bool

    // Pet Updates
    var petAdded: Bool
    var petUpdated: Bool
    var petDeleted: Bool

    // Medication Updates
    var medicationCreated: Bool
    var medicationUpdated: Bool
    var medicationArchived: Bool
    var doseAdministered: Bool

    /// All family-related preferences enabled
    var allFamilyUpdatesEnabled: Bool {
        familyMemberJoined && familyRoleChanged && familyMemberLeft &&
        familyMemberLeftPromoted && familyAccountDeleted && familyAccountDeletedPromoted
    }

    /// All pet-related preferences enabled
    var allPetUpdatesEnabled: Bool {
        petAdded && petUpdated && petDeleted
    }

    /// All medication-related preferences enabled
    var allMedicationUpdatesEnabled: Bool {
        medicationCreated && medicationUpdated && medicationArchived && doseAdministered
    }

    /// Default preferences (all enabled)
    static var defaults: NotificationPreferences {
        NotificationPreferences(
            familyMemberJoined: true,
            familyRoleChanged: true,
            familyMemberLeft: true,
            familyMemberLeftPromoted: true,
            familyAccountDeleted: true,
            familyAccountDeletedPromoted: true,
            petAdded: true,
            petUpdated: true,
            petDeleted: true,
            medicationCreated: true,
            medicationUpdated: true,
            medicationArchived: true,
            doseAdministered: true
        )
    }

    // Custom decoder to handle backwards compatibility with cached data missing medication fields
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        familyMemberJoined = try container.decode(Bool.self, forKey: .familyMemberJoined)
        familyRoleChanged = try container.decode(Bool.self, forKey: .familyRoleChanged)
        familyMemberLeft = try container.decode(Bool.self, forKey: .familyMemberLeft)
        familyMemberLeftPromoted = try container.decode(Bool.self, forKey: .familyMemberLeftPromoted)
        familyAccountDeleted = try container.decode(Bool.self, forKey: .familyAccountDeleted)
        familyAccountDeletedPromoted = try container.decode(Bool.self, forKey: .familyAccountDeletedPromoted)
        petAdded = try container.decode(Bool.self, forKey: .petAdded)
        petUpdated = try container.decode(Bool.self, forKey: .petUpdated)
        petDeleted = try container.decode(Bool.self, forKey: .petDeleted)
        // Medication fields with defaults for backwards compatibility
        medicationCreated = try container.decodeIfPresent(Bool.self, forKey: .medicationCreated) ?? true
        medicationUpdated = try container.decodeIfPresent(Bool.self, forKey: .medicationUpdated) ?? true
        medicationArchived = try container.decodeIfPresent(Bool.self, forKey: .medicationArchived) ?? true
        doseAdministered = try container.decodeIfPresent(Bool.self, forKey: .doseAdministered) ?? true
    }

    // Memberwise initializer
    init(
        familyMemberJoined: Bool,
        familyRoleChanged: Bool,
        familyMemberLeft: Bool,
        familyMemberLeftPromoted: Bool,
        familyAccountDeleted: Bool,
        familyAccountDeletedPromoted: Bool,
        petAdded: Bool,
        petUpdated: Bool,
        petDeleted: Bool,
        medicationCreated: Bool,
        medicationUpdated: Bool,
        medicationArchived: Bool,
        doseAdministered: Bool
    ) {
        self.familyMemberJoined = familyMemberJoined
        self.familyRoleChanged = familyRoleChanged
        self.familyMemberLeft = familyMemberLeft
        self.familyMemberLeftPromoted = familyMemberLeftPromoted
        self.familyAccountDeleted = familyAccountDeleted
        self.familyAccountDeletedPromoted = familyAccountDeletedPromoted
        self.petAdded = petAdded
        self.petUpdated = petUpdated
        self.petDeleted = petDeleted
        self.medicationCreated = medicationCreated
        self.medicationUpdated = medicationUpdated
        self.medicationArchived = medicationArchived
        self.doseAdministered = doseAdministered
    }
}

struct NotificationPreferencesUpdate: Encodable {
    var familyMemberJoined: Bool?
    var familyRoleChanged: Bool?
    var familyMemberLeft: Bool?
    var familyMemberLeftPromoted: Bool?
    var familyAccountDeleted: Bool?
    var familyAccountDeletedPromoted: Bool?
    var petAdded: Bool?
    var petUpdated: Bool?
    var petDeleted: Bool?
    var medicationCreated: Bool?
    var medicationUpdated: Bool?
    var medicationArchived: Bool?
    var doseAdministered: Bool?
}
