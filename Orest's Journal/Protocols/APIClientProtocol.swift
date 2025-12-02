//
//  APIClientProtocol.swift
//  Orest's Journal
//
//  Protocol abstraction for APIClient to enable testing with mock implementations.
//

import Foundation

/// Protocol defining the API client interface for network requests.
/// Conforming to this protocol allows for dependency injection and mock implementations in tests.
protocol APIClientProtocol {
    /// Auth token for API requests
    var authToken: String? { get set }

    /// Current organization ID (family)
    var currentOrgId: String? { get set }

    // MARK: - Generic Request Methods

    /// Perform a GET request
    func get<T: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem]?
    ) async throws -> T

    /// Perform a POST request with a body
    func post<T: Decodable, B: Encodable>(
        _ path: String,
        body: B,
        queryItems: [URLQueryItem]?
    ) async throws -> T

    /// Perform a PATCH request with a body
    func patch<T: Decodable, B: Encodable>(
        _ path: String,
        body: B
    ) async throws -> T

    /// Perform a DELETE request
    func delete(_ path: String) async throws

    /// Perform a DELETE request with a response
    func deleteWithResponse<T: Decodable>(_ path: String) async throws -> T
}

// MARK: - Default Parameter Extensions

extension APIClientProtocol {
    func get<T: Decodable>(_ path: String) async throws -> T {
        try await get(path, queryItems: nil)
    }

    func post<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        try await post(path, body: body, queryItems: nil)
    }
}
