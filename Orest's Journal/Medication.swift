//
//  Medication.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

enum MedicationType: String, Codable, CaseIterable {
    case drops
    case pill
    case inhaler
    case shot
    case liquid
    case tablet
    case capsule
    case topical

    var displayName: String {
        switch self {
        case .drops: return "Drops"
        case .pill: return "Pill"
        case .inhaler: return "Inhaler"
        case .shot: return "Shot"
        case .liquid: return "Liquid"
        case .tablet: return "Tablet"
        case .capsule: return "Capsule"
        case .topical: return "Topical"
        }
    }
}

struct ScheduledTime: Codable, Identifiable, Hashable {
    let id: UUID
    let medicationId: UUID
    let scheduledHour: Int
    let scheduledMinute: Int

    var displayTime: String {
        let hour = scheduledHour % 12 == 0 ? 12 : scheduledHour % 12
        let period = scheduledHour < 12 ? "AM" : "PM"
        if scheduledMinute == 0 {
            return "\(hour) \(period)"
        } else {
            return "\(hour):\(String(format: "%02d", scheduledMinute)) \(period)"
        }
    }

    var asDate: Date {
        var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
        components.hour = scheduledHour
        components.minute = scheduledMinute
        return Calendar.current.date(from: components) ?? Date()
    }
}

struct ScheduledTimeCreate: Codable, Hashable {
    let hour: Int
    let minute: Int

    init(hour: Int, minute: Int = 0) {
        self.hour = hour
        self.minute = minute
    }

    init(from date: Date) {
        let components = Calendar.current.dateComponents([.hour, .minute], from: date)
        self.hour = components.hour ?? 0
        self.minute = components.minute ?? 0
    }
}

struct PetMedication: Codable, Identifiable, Hashable {
    let id: UUID
    let petId: UUID
    let name: String
    let medicationType: MedicationType
    let startDate: Date
    let endDate: Date?
    let timesPerDay: Int
    let notes: String?
    let remindersEnabled: Bool
    let timezone: String
    let isArchived: Bool
    let createdAt: Date
    let createdBy: String?
    var scheduledTimes: [ScheduledTime]?

    var isActive: Bool {
        let today = Calendar.current.startOfDay(for: Date())
        let start = Calendar.current.startOfDay(for: startDate)

        guard today >= start else { return false }

        if let end = endDate {
            let endDay = Calendar.current.startOfDay(for: end)
            return today <= endDay
        }

        return true
    }

    // Memberwise initializer for programmatic creation
    init(
        id: UUID,
        petId: UUID,
        name: String,
        medicationType: MedicationType,
        startDate: Date,
        endDate: Date?,
        timesPerDay: Int,
        notes: String?,
        remindersEnabled: Bool,
        timezone: String,
        isArchived: Bool,
        createdAt: Date,
        createdBy: String?,
        scheduledTimes: [ScheduledTime]?
    ) {
        self.id = id
        self.petId = petId
        self.name = name
        self.medicationType = medicationType
        self.startDate = startDate
        self.endDate = endDate
        self.timesPerDay = timesPerDay
        self.notes = notes
        self.remindersEnabled = remindersEnabled
        self.timezone = timezone
        self.isArchived = isArchived
        self.createdAt = createdAt
        self.createdBy = createdBy
        self.scheduledTimes = scheduledTimes
    }

    // Default initializer for decoding
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        petId = try container.decode(UUID.self, forKey: .petId)
        name = try container.decode(String.self, forKey: .name)
        medicationType = try container.decode(MedicationType.self, forKey: .medicationType)
        startDate = try container.decode(Date.self, forKey: .startDate)
        endDate = try container.decodeIfPresent(Date.self, forKey: .endDate)
        timesPerDay = try container.decode(Int.self, forKey: .timesPerDay)
        notes = try container.decodeIfPresent(String.self, forKey: .notes)
        remindersEnabled = try container.decodeIfPresent(Bool.self, forKey: .remindersEnabled) ?? false
        timezone = try container.decodeIfPresent(String.self, forKey: .timezone) ?? TimeZone.current.identifier
        isArchived = try container.decodeIfPresent(Bool.self, forKey: .isArchived) ?? false
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        createdBy = try container.decodeIfPresent(String.self, forKey: .createdBy)
        scheduledTimes = try container.decodeIfPresent([ScheduledTime].self, forKey: .scheduledTimes)
    }
}

struct PetMedicationDose: Codable, Identifiable {
    let id: UUID
    let medicationId: UUID
    let givenAt: Date
    let givenBy: String
    let notes: String?
    let createdAt: Date
}

// MARK: - Medication Management Types

struct MedicationDeleteResponse: Codable {
    let deleted: Bool
    let archived: Bool
    let message: String
}

struct MedicationUpdate: Codable {
    var name: String?
    var medicationType: String?
    var startDate: Date?
    var endDate: Date?
    var timesPerDay: Int?
    var notes: String?
    var remindersEnabled: Bool?
    var timezone: String?
    var scheduledTimes: [ScheduledTimeCreate]?
}

// MARK: - All Doses History Types

struct AllMedicationDose: Codable, Identifiable {
    let id: UUID
    let medicationId: UUID
    let medicationName: String
    let petId: UUID
    let givenAt: Date
    let givenBy: String
    let notes: String?
    let createdAt: Date
}

struct AllDosesListResponse: Codable {
    let doses: [AllMedicationDose]
    let total: Int
}
