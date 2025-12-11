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

class APIClient: APIClientProtocol {
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
        components?.queryItems = queryItems

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
