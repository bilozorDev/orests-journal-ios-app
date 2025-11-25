//
//  AuthView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI
import Clerk

struct AuthView: View {
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Spacer()

                Image(systemName: "pawprint.circle.fill")
                    .font(.system(size: 80))
                    .foregroundColor(.blue)

                Text("Orest's Journal")
                    .font(.largeTitle)
                    .bold()

                Text("Track your pet's health and wellness")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .padding(.bottom, 30)

                // Clerk SignIn component
                SignInView()
                    .frame(maxWidth: .infinity)

                Spacer()
            }
            .padding()
        }
    }
}

#Preview {
    AuthView()
}
