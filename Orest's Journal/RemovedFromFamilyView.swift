//
//  RemovedFromFamilyView.swift
//  Orest's Journal
//
//  Shown when a user has been removed from their family.
//

import SwiftUI

struct RemovedFromFamilyView: View {
    let familyName: String?

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "person.crop.circle.badge.xmark")
                .font(.system(size: 80))
                .foregroundStyle(.red)
                .accessibilityLabel("Removed from family")

            VStack(spacing: 12) {
                Text("You were removed")
                    .font(.title)
                    .fontWeight(.bold)

                if let name = familyName {
                    Text("You are no longer a member of \(name)")
                        .font(.body)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                } else {
                    Text("You are no longer a member of this family")
                        .font(.body)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
            }

            Spacer()

            Button(action: startOver) {
                Text("Start Over")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundStyle(.white)
                    .clipShape(.rect(cornerRadius: 12))
            }
            .accessibilityIdentifier(AccessibilityIdentifier.startOverButton)
            .padding(.horizontal, 40)
            .padding(.bottom, 40)
        }
        .padding()
    }

    private func startOver() {
        AuthManager.shared.resetRemovedState()
    }
}

#Preview {
    RemovedFromFamilyView(familyName: "Smith Family")
}
