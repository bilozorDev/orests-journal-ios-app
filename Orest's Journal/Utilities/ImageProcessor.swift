//
//  ImageProcessor.swift
//  Orest's Journal
//
//  Created by Claude on 12/10/25.
//

import Vision
import CoreImage
import CoreImage.CIFilterBuiltins
import UIKit

/// Actor for processing images, including background removal using Vision Framework.
/// Reusable for pet photos, food photos, medicine photos, etc.
actor ImageProcessor {
    static let shared = ImageProcessor()
    private let context = CIContext()

    /// Maximum image dimension (width or height) for processing.
    /// Images larger than this will be resized to prevent memory issues.
    private let maxImageDimension: CGFloat = 2048

    /// Resizes an image if it exceeds the maximum dimension while preserving aspect ratio.
    private func resizeIfNeeded(_ image: UIImage) -> UIImage {
        let size = image.size
        let maxDim = max(size.width, size.height)

        guard maxDim > maxImageDimension else { return image }

        let scale = maxImageDimension / maxDim
        let newSize = CGSize(width: size.width * scale, height: size.height * scale)

        let renderer = UIGraphicsImageRenderer(size: newSize)
        return renderer.image { _ in
            image.draw(in: CGRect(origin: .zero, size: newSize))
        }
    }

    /// Removes background from an image using Vision Framework subject lifting.
    /// Returns the image with a transparent background.
    /// - Parameter image: The source UIImage (will be resized if too large)
    /// - Returns: UIImage with transparent background
    /// - Throws: ImageProcessingError if processing fails
    @available(iOS 17.0, *)
    func removeBackground(from image: UIImage) async throws -> UIImage {
        // Resize image if too large to prevent memory issues
        let processableImage = resizeIfNeeded(image)

        guard let inputCIImage = CIImage(image: processableImage) else {
            throw ImageProcessingError.invalidInput
        }

        // Create foreground instance mask request
        let request = VNGenerateForegroundInstanceMaskRequest()
        let handler = VNImageRequestHandler(ciImage: inputCIImage)

        // Perform the request (this is synchronous but runs on actor's executor)
        try handler.perform([request])

        guard let result = request.results?.first else {
            throw ImageProcessingError.noMaskGenerated
        }

        // Generate scaled mask for the detected instances
        let mask = try result.generateScaledMaskForImage(
            forInstances: result.allInstances,
            from: handler
        )
        let maskCIImage = CIImage(cvPixelBuffer: mask)

        // Apply the mask with transparent background
        let filter = CIFilter.blendWithMask()
        filter.inputImage = inputCIImage
        filter.maskImage = maskCIImage
        filter.backgroundImage = CIImage.empty()

        guard let outputCIImage = filter.outputImage,
              let cgImage = context.createCGImage(outputCIImage, from: inputCIImage.extent) else {
            throw ImageProcessingError.filterFailed
        }

        return UIImage(cgImage: cgImage, scale: processableImage.scale, orientation: processableImage.imageOrientation)
    }

    enum ImageProcessingError: LocalizedError {
        case invalidInput
        case noMaskGenerated
        case filterFailed

        var errorDescription: String? {
            switch self {
            case .invalidInput:
                return "Could not process this image"
            case .noMaskGenerated:
                return "Could not detect subject in image"
            case .filterFailed:
                return "Failed to process image"
            }
        }
    }
}
