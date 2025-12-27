//
//  LeftFamilyView.swift
//  Orest's Journal
//
//  Shown when a user voluntarily leaves their family.
//

import SwiftUI

struct LeftFamilyView: View {
    let familyName: String?

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "rectangle.portrait.and.arrow.right")
                .font(.system(size: 80))
                .foregroundStyle(.orange)
                .accessibilityLabel("Left family")

            VStack(spacing: 12) {
                Text("You left the family")
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
        AuthManager.shared.resetLeftFamilyState()
    }
}

#Preview {
    LeftFamilyView(familyName: "Smith Family")
}
