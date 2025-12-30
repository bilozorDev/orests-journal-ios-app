//
//  Medication.swift
//  Orest's Journal
//
//  Medication model and related types for medication scheduling.
//

import Foundation

// MARK: - Medication Type

enum MedicationType: String, Codable, CaseIterable {
    case drops = "drops"
    case pill = "pill"
    case inhaler = "inhaler"
    case shot = "shot"
    case liquid = "liquid"
    case tablet = "tablet"
    case capsule = "capsule"
    case topical = "topical"

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

    var icon: String {
        switch self {
        case .drops: return "drop.fill"
        case .pill: return "pills.fill"
        case .inhaler: return "wind"
        case .shot: return "syringe.fill"
        case .liquid: return "flask.fill"
        case .tablet: return "capsule.fill"
        case .capsule: return "capsule.fill"
        case .topical: return "hand.raised.fill"
        }
    }
}

// MARK: - Scheduled Time

struct ScheduledTime: Codable, Identifiable, Hashable {
    let id: UUID
    let medicationId: UUID
    let scheduledHour: Int
    let scheduledMinute: Int

    /// Formatted time string (e.g., "8:00 AM")
    var formattedTime: String {
        let calendar = Calendar.current
        var components = DateComponents()
        components.hour = scheduledHour
        components.minute = scheduledMinute
        guard let date = calendar.date(from: components) else {
            return "\(scheduledHour):\(String(format: "%02d", scheduledMinute))"
        }
        return Formatters.shortTime.string(from: date)
    }
}

// MARK: - Medication Photo

struct MedicationPhoto: Codable, Identifiable, Hashable {
    let id: UUID
    let medicationId: UUID
    let photoUrl: String
    let sortOrder: Int
    let createdAt: Date
}

// MARK: - Medication

struct Medication: Codable, Identifiable, Hashable {
    let id: UUID
    let petId: UUID
    let name: String
    let medicationType: MedicationType
    let dosage: String?
    let intervalDays: Int?
    let isAsNeeded: Bool
    let startDate: Date
    let endDate: Date?
    let timesPerDay: Int
    let notes: String?
    let remindersEnabled: Bool
    let timezone: String
    let isArchived: Bool
    let createdBy: UUID?
    let createdAt: Date
    var scheduledTimes: [ScheduledTime]?
    var photos: [MedicationPhoto]?

    /// Check if medication is currently active based on dates
    var isActive: Bool {
        let now = Date()
        if now < startDate { return false }
        if let end = endDate, now > end { return false }
        return true
    }

    /// Formatted interval description
    var intervalDescription: String {
        if isAsNeeded {
            return "As needed"
        }
        guard let days = intervalDays else { return "Daily" }
        if days == 1 { return "Daily" }
        if days == 7 { return "Weekly" }
        if days == 14 { return "Every 2 weeks" }
        return "Every \(days) days"
    }

    // Custom decoder to handle backwards compatibility
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        petId = try container.decode(UUID.self, forKey: .petId)
        name = try container.decode(String.self, forKey: .name)
        medicationType = try container.decode(MedicationType.self, forKey: .medicationType)
        dosage = try container.decodeIfPresent(String.self, forKey: .dosage)
        intervalDays = try container.decodeIfPresent(Int.self, forKey: .intervalDays)
        isAsNeeded = try container.decodeIfPresent(Bool.self, forKey: .isAsNeeded) ?? false
        startDate = try container.decode(Date.self, forKey: .startDate)
        endDate = try container.decodeIfPresent(Date.self, forKey: .endDate)
        timesPerDay = try container.decodeIfPresent(Int.self, forKey: .timesPerDay) ?? 1
        notes = try container.decodeIfPresent(String.self, forKey: .notes)
        remindersEnabled = try container.decodeIfPresent(Bool.self, forKey: .remindersEnabled) ?? false
        timezone = try container.decodeIfPresent(String.self, forKey: .timezone) ?? "UTC"
        isArchived = try container.decodeIfPresent(Bool.self, forKey: .isArchived) ?? false
        createdBy = try container.decodeIfPresent(UUID.self, forKey: .createdBy)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        scheduledTimes = try container.decodeIfPresent([ScheduledTime].self, forKey: .scheduledTimes)
        photos = try container.decodeIfPresent([MedicationPhoto].self, forKey: .photos)
    }

    // Memberwise initializer
    init(
        id: UUID,
        petId: UUID,
        name: String,
        medicationType: MedicationType,
        dosage: String?,
        intervalDays: Int?,
        isAsNeeded: Bool,
        startDate: Date,
        endDate: Date?,
        timesPerDay: Int,
        notes: String?,
        remindersEnabled: Bool,
        timezone: String,
        isArchived: Bool,
        createdBy: UUID?,
        createdAt: Date,
        scheduledTimes: [ScheduledTime]?,
        photos: [MedicationPhoto]?
    ) {
        self.id = id
        self.petId = petId
        self.name = name
        self.medicationType = medicationType
        self.dosage = dosage
        self.intervalDays = intervalDays
        self.isAsNeeded = isAsNeeded
        self.startDate = startDate
        self.endDate = endDate
        self.timesPerDay = timesPerDay
        self.notes = notes
        self.remindersEnabled = remindersEnabled
        self.timezone = timezone
        self.isArchived = isArchived
        self.createdBy = createdBy
        self.createdAt = createdAt
        self.scheduledTimes = scheduledTimes
        self.photos = photos
    }
}

// MARK: - List Response

struct MedicationListResponse: Codable {
    let medications: [Medication]
}

// MARK: - Create/Update DTOs

struct ScheduledTimeCreate: Encodable {
    let hour: Int
    let minute: Int

    init(hour: Int, minute: Int = 0) {
        self.hour = hour
        self.minute = minute
    }

    /// Create from a Date
    init(from date: Date) {
        let calendar = Calendar.current
        self.hour = calendar.component(.hour, from: date)
        self.minute = calendar.component(.minute, from: date)
    }
}

struct MedicationCreate: Encodable {
    let petId: UUID
    let name: String
    let medicationType: MedicationType
    let dosage: String?
    let intervalDays: Int?
    let isAsNeeded: Bool
    let startDate: Date
    let endDate: Date?
    let timesPerDay: Int
    let notes: String?
    let remindersEnabled: Bool
    let timezone: String
    let scheduledTimes: [ScheduledTimeCreate]?

    init(
        petId: UUID,
        name: String,
        medicationType: MedicationType,
        dosage: String? = nil,
        intervalDays: Int? = 1,
        isAsNeeded: Bool = false,
        startDate: Date,
        endDate: Date? = nil,
        timesPerDay: Int = 1,
        notes: String? = nil,
        remindersEnabled: Bool = false,
        timezone: String = TimeZone.current.identifier,
        scheduledTimes: [ScheduledTimeCreate]? = nil
    ) {
        self.petId = petId
        self.name = name
        self.medicationType = medicationType
        self.dosage = dosage
        self.intervalDays = isAsNeeded ? nil : intervalDays
        self.isAsNeeded = isAsNeeded
        self.startDate = startDate
        self.endDate = isAsNeeded ? nil : endDate
        self.timesPerDay = isAsNeeded ? 1 : timesPerDay
        self.notes = notes
        self.remindersEnabled = isAsNeeded ? false : remindersEnabled
        self.timezone = timezone
        self.scheduledTimes = isAsNeeded ? nil : scheduledTimes
    }
}

struct MedicationUpdate: Encodable {
    var name: String?
    var medicationType: MedicationType?
    var dosage: String?
    var intervalDays: Int?
    var isAsNeeded: Bool?
    var startDate: Date?
    var endDate: Date?
    var timesPerDay: Int?
    var notes: String?
    var remindersEnabled: Bool?
    var timezone: String?
    var scheduledTimes: [ScheduledTimeCreate]?
}

// MARK: - Delete Response

struct MedicationDeleteResponse: Codable {
    let deleted: Bool
    let archived: Bool
    let message: String
}

// MARK: - Dose Types

/// A recorded dose of a medication
struct MedicationDose: Codable, Identifiable, Hashable {
    let id: UUID
    let medicationId: UUID
    let givenAt: Date
    let givenBy: String  // Formatted user name
    let notes: String?
    let createdAt: Date

    /// Formatted relative time string (e.g., "2 hours ago")
    var relativeTimeString: String {
        Formatters.relativeDateTime.localizedString(for: givenAt, relativeTo: Date())
    }

    /// Formatted date and time string
    var formattedDateTime: String {
        Formatters.mediumDateTime.string(from: givenAt)
    }

    /// Short formatted time string
    var formattedTime: String {
        Formatters.shortTime.string(from: givenAt)
    }
}

/// Response containing a list of doses
struct DoseListResponse: Codable {
    let doses: [MedicationDose]
    let total: Int
}

/// Dose with medication info for all-doses endpoint
struct AllDoseDetail: Codable, Identifiable, Hashable {
    let id: UUID
    let medicationId: UUID
    let medicationName: String
    let petId: UUID
    let givenAt: Date
    let givenBy: String
    let notes: String?
    let createdAt: Date
}

/// Response for all doses for a pet
struct AllDosesListResponse: Codable {
    let doses: [AllDoseDetail]
    let total: Int
}

/// DTO for creating a new dose
struct DoseCreate: Encodable {
    let medicationId: UUID
    let notes: String?
    let givenAt: Date?

    init(medicationId: UUID, notes: String? = nil, givenAt: Date? = nil) {
        self.medicationId = medicationId
        self.notes = notes
        self.givenAt = givenAt
    }
}

/// DTO for updating a dose
struct DoseUpdate: Encodable {
    var givenAt: Date?
    var notes: String?
}
