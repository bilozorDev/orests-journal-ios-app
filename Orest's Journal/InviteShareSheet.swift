//
//  InviteShareSheet.swift
//  Orest's Journal
//
//  Created by Claude on 11/26/25.
//

import SwiftUI

struct InviteShareSheet: View {
    @Environment(\.dismiss) var dismiss
    let inviteCode: String

    @State private var showCopied = false
    @State private var resetTask: Task<Void, Never>?

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()

                // Icon
                Image(systemName: "person.badge.plus")
                    .font(.system(size: 60))
                    .foregroundColor(.blue)

                // Title
                Text("Invite Family Members")
                    .font(.title2)
                    .fontWeight(.bold)

                // Description
                Text("Share this code with family members so they can join your family and help track your pets.")
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)

                // Invite Code Display
                VStack(spacing: 8) {
                    Text("Invite Code")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Text(inviteCode)
                        .font(.system(size: 32, weight: .bold, design: .monospaced))
                        .padding(.horizontal, 24)
                        .padding(.vertical, 16)
                        .background(Color.blue.opacity(0.1))
                        .cornerRadius(12)
                }
                .padding(.vertical)

                // Action Buttons
                VStack(spacing: 12) {
                    // Copy Button
                    Button(action: copyCode) {
                        HStack {
                            Image(systemName: showCopied ? "checkmark" : "doc.on.doc")
                            Text(showCopied ? "Copied!" : "Copy Code")
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.gray.opacity(0.1))
                        .foregroundColor(showCopied ? .green : .primary)
                        .cornerRadius(12)
                    }
                    .accessibilityIdentifier(AccessibilityIdentifier.copyInviteCodeButton)
                    .accessibilityLabel(showCopied ? "Invite code copied" : "Copy invite code \(inviteCode)")

                    // Share Button
                    Button(action: shareCode) {
                        HStack {
                            Image(systemName: "square.and.arrow.up")
                            Text("Share Code")
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                    }
                    .accessibilityIdentifier(AccessibilityIdentifier.shareInviteCodeButton)
                    .accessibilityLabel("Share invite code \(inviteCode)")
                }
                .padding(.horizontal)

                Spacer()
            }
            .padding()
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
            .onDisappear {
                resetTask?.cancel()
            }
        }
    }

    private func copyCode() {
        UIPasteboard.general.string = inviteCode
        withAnimation {
            showCopied = true
        }

        // Cancel any existing reset task
        resetTask?.cancel()
        resetTask = Task {
            try? await Task.sleep(for: .seconds(2))
            guard !Task.isCancelled else { return }
            withAnimation {
                showCopied = false
            }
        }
    }

    private func shareCode() {
        let message = "Join my family on Orest's Journal! Use invite code: \(inviteCode)"

        let activityVC = UIActivityViewController(
            activityItems: [message],
            applicationActivities: nil
        )

        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first,
           let rootVC = window.rootViewController {
            // Find the topmost presented view controller
            var topVC = rootVC
            while let presented = topVC.presentedViewController {
                topVC = presented
            }
            topVC.present(activityVC, animated: true)
        }
    }
}

#Preview {
    InviteShareSheet(inviteCode: "ABC123")
}
