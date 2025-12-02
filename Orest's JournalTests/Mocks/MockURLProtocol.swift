//
//  MockURLProtocol.swift
//  Orest's JournalTests
//
//  Custom URLProtocol for intercepting network requests in tests.
//

import Foundation

/// A mock URL protocol that intercepts all URL requests for testing.
/// This allows testing network code without making actual network calls.
final class MockURLProtocol: URLProtocol {
    /// Handler for processing requests and returning mock responses
    static var requestHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    /// Dictionary of mock responses keyed by URL path
    static var mockResponses: [String: (statusCode: Int, data: Data)] = [:]

    /// Captured requests for verification
    static var capturedRequests: [URLRequest] = []

    override class func canInit(with request: URLRequest) -> Bool {
        // Handle all requests
        return true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        return request
    }

    override func startLoading() {
        MockURLProtocol.capturedRequests.append(request)

        // Check if we have a request handler
        if let handler = MockURLProtocol.requestHandler {
            do {
                let (response, data) = try handler(request)
                client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
                client?.urlProtocol(self, didLoad: data)
                client?.urlProtocolDidFinishLoading(self)
            } catch {
                client?.urlProtocol(self, didFailWithError: error)
            }
            return
        }

        // Check mock responses dictionary
        if let path = request.url?.path,
           let mockResponse = MockURLProtocol.mockResponses[path] {
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: mockResponse.statusCode,
                httpVersion: "HTTP/1.1",
                headerFields: ["Content-Type": "application/json"]
            )!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: mockResponse.data)
            client?.urlProtocolDidFinishLoading(self)
            return
        }

        // No mock configured - fail with error
        let error = NSError(
            domain: "MockURLProtocol",
            code: -1,
            userInfo: [NSLocalizedDescriptionKey: "No mock response configured for \(request.url?.absoluteString ?? "unknown URL")"]
        )
        client?.urlProtocol(self, didFailWithError: error)
    }

    override func stopLoading() {
        // Nothing to clean up
    }

    // MARK: - Helper Methods

    /// Reset all mock data
    static func reset() {
        requestHandler = nil
        mockResponses.removeAll()
        capturedRequests.removeAll()
    }

    /// Create a URLSession configured to use this mock protocol
    static func mockURLSession() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        return URLSession(configuration: config)
    }

    /// Helper to create JSON data from an Encodable object
    static func jsonData<T: Encodable>(from object: T) throws -> Data {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        return try encoder.encode(object)
    }
}
