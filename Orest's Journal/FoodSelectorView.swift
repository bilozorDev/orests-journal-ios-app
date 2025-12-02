//
//  FoodSelectorView.swift
//  Orest's Journal
//
//  A sheet view for selecting food with category grouping.
//

import SwiftUI

struct FoodSelectorView: View {
    let foods: [PetFood]
    @Binding var selectedFood: PetFood?
    @Environment(\.dismiss) var dismiss

    var foodsByCategory: [FoodCategory: [PetFood]] {
        Dictionary(grouping: foods, by: { $0.category })
    }

    var body: some View {
        NavigationView {
            List {
                ForEach(FoodCategory.allCases, id: \.self) { category in
                    if let categoryFoods = foodsByCategory[category], !categoryFoods.isEmpty {
                        Section(header: Text(category.displayName)) {
                            ForEach(categoryFoods) { food in
                                Button {
                                    selectedFood = food
                                    dismiss()
                                } label: {
                                    HStack {
                                        Text(food.name)
                                        Spacer()
                                        if selectedFood?.id == food.id {
                                            Image(systemName: "checkmark")
                                                .foregroundColor(.blue)
                                        }
                                    }
                                }
                                .foregroundColor(.primary)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Select Food")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }
}
