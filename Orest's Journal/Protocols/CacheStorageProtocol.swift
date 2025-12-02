//
//  CacheStorageProtocol.swift
//  Orest's Journal
//
//  Protocol abstraction for cache storage to enable testing with mock implementations.
//

import Foundation

/// Protocol defining the cache storage interface for persistent caching.
/// Conforming to this protocol allows for dependency injection and mock implementations in tests.
protocol CacheStorageProtocol {
    /// Save data to cache with a given key
    func save<T: Encodable>(_ data: T, forKey key: String) throws

    /// Load data from cache for a given key
    func load<T: Decodable>(forKey key: String) throws -> T?

    /// Delete cached data for a given key
    func delete(forKey key: String) throws

    /// Clear all cached data
    func clearAll() throws

    /// Check if cache exists and is valid for a given key
    func isValid(forKey key: String) -> Bool
}
