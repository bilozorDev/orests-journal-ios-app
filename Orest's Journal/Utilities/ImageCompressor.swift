//
//  ImageCompressor.swift
//  Orest's Journal
//
//  Compresses images for upload with adaptive quality to meet size limits.
//

import UIKit

enum ImageCompressionError: LocalizedError {
    case cannotCompressUnderLimit(currentSize: Int, limit: Int)
    case invalidImage

    var errorDescription: String? {
        switch self {
        case .cannotCompressUnderLimit(let current, let limit):
            let currentMB = Double(current) / 1_000_000
            let limitMB = Double(limit) / 1_000_000
            return String(format: "Image too large (%.1fMB). Maximum is %.1fMB. Try a smaller image.", currentMB, limitMB)
        case .invalidImage:
            return "Could not process the image"
        }
    }
}

struct CompressedImage {
    let data: Data
    let mimeType: String
}

final class ImageCompressor {
    static let shared = ImageCompressor()
    private init() {}

    /// Maximum file size for uploads (leaving margin under 5MB limit)
    private let maxSizeBytes = 4_500_000

    /// Maximum dimension before any compression attempts
    private let maxInitialDimension: CGFloat = 1500

    /// Compresses image for upload, choosing best format based on transparency
    func compressForUpload(_ image: UIImage, hasTransparency: Bool) throws -> CompressedImage {
        // First, resize to max dimension
        let resized = resizeIfNeeded(image, maxDimension: maxInitialDimension)

        if hasTransparency {
            return try compressTransparentImage(resized)
        } else {
            return try compressOpaqueImage(resized)
        }
    }

    // MARK: - Private Methods

    private func resizeIfNeeded(_ image: UIImage, maxDimension: CGFloat) -> UIImage {
        let size = image.size
        let maxSide = max(size.width, size.height)

        guard maxSide > maxDimension else { return image }

        let scale = maxDimension / maxSide
        let newSize = CGSize(width: size.width * scale, height: size.height * scale)

        let renderer = UIGraphicsImageRenderer(size: newSize)
        return renderer.image { _ in
            image.draw(in: CGRect(origin: .zero, size: newSize))
        }
    }

    private func compressOpaqueImage(_ image: UIImage) throws -> CompressedImage {
        // Try JPEG with decreasing quality
        var quality: CGFloat = 0.8

        while quality >= 0.1 {
            if let data = image.jpegData(compressionQuality: quality),
               data.count <= maxSizeBytes {
                return CompressedImage(data: data, mimeType: "image/jpeg")
            }
            quality -= 0.1
        }

        // If still too large, resize and retry
        let smallerImage = resizeIfNeeded(image, maxDimension: 1000)
        if smallerImage.size != image.size {
            return try compressOpaqueImage(smallerImage)
        }

        // Last resort: aggressive resize
        let tinyImage = resizeIfNeeded(image, maxDimension: 600)
        if let data = tinyImage.jpegData(compressionQuality: 0.6),
           data.count <= maxSizeBytes {
            return CompressedImage(data: data, mimeType: "image/jpeg")
        }

        let currentSize = image.jpegData(compressionQuality: 0.1)?.count ?? 0
        throw ImageCompressionError.cannotCompressUnderLimit(currentSize: currentSize, limit: maxSizeBytes)
    }

    private func compressTransparentImage(_ image: UIImage) throws -> CompressedImage {
        // For transparent images, use PNG with progressive resizing
        var currentMaxDimension: CGFloat = 1500

        while currentMaxDimension >= 400 {
            let resized = resizeIfNeeded(image, maxDimension: currentMaxDimension)
            if let data = resized.pngData(), data.count <= maxSizeBytes {
                return CompressedImage(data: data, mimeType: "image/png")
            }
            currentMaxDimension -= 200
        }

        // Last resort: very small PNG
        let tinyImage = resizeIfNeeded(image, maxDimension: 300)
        if let data = tinyImage.pngData(), data.count <= maxSizeBytes {
            return CompressedImage(data: data, mimeType: "image/png")
        }

        let currentSize = image.pngData()?.count ?? 0
        throw ImageCompressionError.cannotCompressUnderLimit(currentSize: currentSize, limit: maxSizeBytes)
    }
}
