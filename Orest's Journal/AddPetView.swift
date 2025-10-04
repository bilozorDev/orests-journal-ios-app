//
//  AddPetView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI
import PhotosUI
import Supabase

struct AddPetView: View {
    @State private var petName = ""
    @State private var petKind = "Dog"
    @State private var currentWeight = ""
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedImage: UIImage?
    @State private var isLoading = false
    @State private var errorMessage: String?

    let petKinds = ["Dog", "Cat", "Bird", "Rabbit", "Hamster", "Guinea Pig", "Other"]

    var body: some View {
        NavigationView {
            ZStack {
                Form {
                    Section(header: Text("Pet Information")) {
                        TextField("Pet Name", text: $petName)

                        Picker("Kind", selection: $petKind) {
                            ForEach(petKinds, id: \.self) { kind in
                                Text(kind).tag(kind)
                            }
                        }
                    }

                    Section(header: Text("Photo")) {
                        PhotosPicker(
                            selection: $selectedPhoto,
                            matching: .images
                        ) {
                            if let selectedImage {
                                Image(uiImage: selectedImage)
                                    .resizable()
                                    .scaledToFit()
                                    .frame(maxHeight: 200)
                                    .cornerRadius(10)
                            } else {
                                Label("Select Photo", systemImage: "photo")
                            }
                        }
                        .onChange(of: selectedPhoto) { _, newValue in
                            Task {
                                if let data = try? await newValue?.loadTransferable(type: Data.self),
                                   let image = UIImage(data: data) {
                                    selectedImage = image
                                }
                            }
                        }
                    }

                    Section(header: Text("Current Weight (lbs)")) {
                        TextField("Weight", text: $currentWeight)
                            .keyboardType(.decimalPad)
                    }

                    if let error = errorMessage {
                        Section {
                            Text(error)
                                .foregroundColor(.red)
                                .font(.caption)
                        }
                    }

                    Section {
                        if isLoading {
                            HStack {
                                Spacer()
                                ProgressView()
                                Spacer()
                            }
                        } else {
                            Button(action: savePet) {
                                Text("Add Pet")
                                    .frame(maxWidth: .infinity)
                                    .foregroundColor(.blue)
                            }
                            .disabled(!isFormValid)
                        }
                    }
                }
                .navigationTitle("Add Your Pet")
                .navigationBarTitleDisplayMode(.large)
                .task {
                    // Check if family already has pets
                    do {
                        let status = try await SupabaseService.shared.checkUserFamilyAndPet()
                        if status.hasPet {
                            // Family already has pets, trigger refresh to navigate to dashboard
                            NotificationCenter.default.post(name: NSNotification.Name("RefreshFamilyStatus"), object: nil)
                        }
                    } catch {
                        print("Error checking pet status: \(error)")
                    }
                }

                // Dev: Floating Sign Out Button
                VStack {
                    Spacer()
                    HStack {
                        Spacer()
                        Button(action: signOut) {
                            Image(systemName: "rectangle.portrait.and.arrow.right")
                                .foregroundColor(.white)
                                .padding()
                                .background(Color.red)
                                .clipShape(Circle())
                                .shadow(radius: 4)
                        }
                        .padding()
                    }
                }
            }
        }
    }

    private var isFormValid: Bool {
        !petName.isEmpty &&
        !currentWeight.isEmpty &&
        Double(currentWeight) != nil
    }

    private func savePet() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Get current user's family
                guard let family = try await SupabaseService.shared.getCurrentUserFamily() else {
                    throw NSError(domain: "AddPetView", code: 500, userInfo: [NSLocalizedDescriptionKey: "No family found. Please contact support."])
                }

                // Upload photo if selected
                var photoUrl: String?
                if let image = selectedImage {
                    photoUrl = try await SupabaseService.shared.uploadPetPhoto(image)
                }

                // Create pet
                guard let weight = Double(currentWeight) else {
                    throw NSError(domain: "AddPetView", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid weight format"])
                }

                let _ = try await SupabaseService.shared.createPet(
                    familyId: family.id,
                    name: petName,
                    kind: petKind,
                    photoUrl: photoUrl,
                    currentWeight: weight
                )

                // Notify ContentView to refresh
                NotificationCenter.default.post(name: NSNotification.Name("RefreshFamilyStatus"), object: nil)
            } catch {
                errorMessage = error.localizedDescription
                isLoading = false
            }
        }
    }

    private func signOut() {
        Task {
            try? await supabase.auth.signOut()
        }
    }
}

#Preview {
    AddPetView()
}
