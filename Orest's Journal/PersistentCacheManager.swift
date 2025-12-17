//
//  PersistentCacheManager.swift
//  Orest's Journal
//
//  Manages persistent disk caching for app data to enable instant loading on app launch.
//

import Foundation

/// Manages persistent disk caching with JSON encoding to Application Support directory.
/// Provides stale-while-revalidate pattern support with timestamped cache entries.
@MainActor
final class PersistentCacheManager {
    static let shared = PersistentCacheManager()

    private let cacheDirectory: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    /// Current cache version - increment when data models change
    private let currentCacheVersion = 2

    /// Maximum age for cached data (24 hours)
    private let maxCacheAge: TimeInterval = 24 * 60 * 60

    /// Wrapper for cached data including metadata
    struct CachedData<T: Codable>: Codable {
        let data: T
        let timestamp: Date
        let cacheVersion: Int
    }

    /// Cache keys for different data types
    enum CacheKey {
        case familyMembers(familyId: String)
        case pets
        case calorieGoal(petId: String)
        case healthEvents(petId: String)
        case healthCategories(orgId: String)  // Categories are family-wide, keyed by org_id

        var fileName: String {
            switch self {
            case .familyMembers(let familyId):
                return "family_members_\(familyId).json"
            case .pets:
                return "pets.json"
            case .calorieGoal(let petId):
                return "calorie_goal_\(petId).json"
            case .healthEvents(let petId):
                return "health_events_\(petId).json"
            case .healthCategories(let orgId):
                return "health_categories_\(orgId).json"
            }
        }
    }

    private init() {
        // Use Application Support directory (persists, unlike Caches)
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        cacheDirectory = appSupport.appendingPathComponent("DataCache", isDirectory: true)

        // Configure encoder/decoder for dates
        // Use same date encoding as APIClient for consistency
        encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601

        // Use custom date decoder matching APIClient to handle multiple formats
        decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
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

        // Ensure cache directory exists
        createCacheDirectoryIfNeeded()
    }

    // MARK: - Public Methods

    /// Save data to disk cache
    func save<T: Codable>(_ data: T, forKey key: CacheKey) async {
        let cached = CachedData(data: data, timestamp: Date(), cacheVersion: currentCacheVersion)
        let fileURL = cacheDirectory.appendingPathComponent(key.fileName)

        do {
            let jsonData = try encoder.encode(cached)
            try await Task.detached(priority: .utility) {
                try jsonData.write(to: fileURL, options: .atomic)
            }.value
        } catch {
            print("PersistentCache: Failed to save \(key.fileName): \(error)")
        }
    }

    /// Load data from disk cache
    /// Returns nil if cache doesn't exist, is corrupted, or version mismatches
    func load<T: Codable>(forKey key: CacheKey) async -> CachedData<T>? {
        let fileURL = cacheDirectory.appendingPathComponent(key.fileName)

        do {
            let jsonData = try await Task.detached(priority: .utility) {
                try Data(contentsOf: fileURL)
            }.value

            let cached = try decoder.decode(CachedData<T>.self, from: jsonData)

            // Check cache version
            guard cached.cacheVersion == currentCacheVersion else {
                print("PersistentCache: Version mismatch for \(key.fileName), deleting")
                await delete(forKey: key)
                return nil
            }

            // Check max age
            guard Date().timeIntervalSince(cached.timestamp) < maxCacheAge else {
                print("PersistentCache: Cache expired for \(key.fileName), deleting")
                await delete(forKey: key)
                return nil
            }

            return cached
        } catch {
            // File doesn't exist or is corrupted - this is normal for first run
            if (error as NSError).code != NSFileReadNoSuchFileError {
                print("PersistentCache: Failed to load \(key.fileName): \(error)")
                // Delete corrupted file
                await delete(forKey: key)
            }
            return nil
        }
    }

    /// Delete a specific cache entry
    func delete(forKey key: CacheKey) async {
        let fileURL = cacheDirectory.appendingPathComponent(key.fileName)

        do {
            try await Task.detached(priority: .utility) {
                try FileManager.default.removeItem(at: fileURL)
            }.value
        } catch {
            // Ignore file not found errors
            if (error as NSError).code != NSFileNoSuchFileError {
                print("PersistentCache: Failed to delete \(key.fileName): \(error)")
            }
        }
    }

    /// Clear all cached data
    func clearAll() async {
        do {
            try await Task.detached(priority: .utility) {
                let fileManager = FileManager.default
                if fileManager.fileExists(atPath: self.cacheDirectory.path) {
                    try fileManager.removeItem(at: self.cacheDirectory)
                }
            }.value
            createCacheDirectoryIfNeeded()
        } catch {
            print("PersistentCache: Failed to clear all caches: \(error)")
        }
    }

    /// Get the timestamp of cached data without loading the full data
    func getCacheTimestamp(forKey key: CacheKey) async -> Date? {
        // For efficiency, load minimal wrapper to check timestamp
        struct TimestampOnly: Codable {
            let timestamp: Date
            let cacheVersion: Int
        }

        let fileURL = cacheDirectory.appendingPathComponent(key.fileName)

        do {
            let jsonData = try await Task.detached(priority: .utility) {
                try Data(contentsOf: fileURL)
            }.value

            let wrapper = try decoder.decode(TimestampOnly.self, from: jsonData)

            guard wrapper.cacheVersion == currentCacheVersion else {
                return nil
            }

            return wrapper.timestamp
        } catch {
            return nil
        }
    }

    /// Check if cache exists and is valid (not expired, correct version)
    func hasValidCache(forKey key: CacheKey, maxAge: TimeInterval? = nil) async -> Bool {
        guard let timestamp = await getCacheTimestamp(forKey: key) else {
            return false
        }

        let age = Date().timeIntervalSince(timestamp)
        let effectiveMaxAge = maxAge ?? maxCacheAge

        return age < effectiveMaxAge
    }

    // MARK: - Private Methods

    private func createCacheDirectoryIfNeeded() {
        let fileManager = FileManager.default
        if !fileManager.fileExists(atPath: cacheDirectory.path) {
            do {
                try fileManager.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)
            } catch {
                print("PersistentCache: Failed to create cache directory: \(error)")
            }
        }
    }
}
