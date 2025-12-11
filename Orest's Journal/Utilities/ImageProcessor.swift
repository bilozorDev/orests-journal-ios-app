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

    /// Removes background from an image using Vision Framework subject lifting.
    /// Returns the image with a transparent background.
    /// - Parameter image: The source UIImage
    /// - Returns: UIImage with transparent background
    /// - Throws: ImageProcessingError if processing fails
    @available(iOS 17.0, *)
    func removeBackground(from image: UIImage) async throws -> UIImage {
        guard let inputCIImage = CIImage(image: image) else {
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

        return UIImage(cgImage: cgImage, scale: image.scale, orientation: image.imageOrientation)
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
