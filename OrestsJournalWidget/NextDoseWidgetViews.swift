//
//  NextDoseWidgetViews.swift
//  OrestsJournalWidget
//
//  SwiftUI views for the Next Dose widget.
//

import SwiftUI
import WidgetKit

// MARK: - Main Entry View

struct NextDoseWidgetEntryView: View {
    @Environment(\.widgetFamily) var widgetFamily
    var entry: NextDoseEntry

    var body: some View {
        Group {
            if entry.isPlaceholder || entry.primaryDose == nil {
                emptyStateView
            } else {
                switch widgetFamily {
                case .systemSmall:
                    SmallWidgetView(entry: entry)
                case .systemMedium:
                    MediumWidgetView(entry: entry)
                case .systemLarge:
                    LargeWidgetView(entry: entry)
                default:
                    SmallWidgetView(entry: entry)
                }
            }
        }
    }

    private var emptyStateView: some View {
        VStack(spacing: 8) {
            Image(systemName: "pills")
                .font(.system(size: 32))
                .foregroundStyle(.secondary)
            Text("No Upcoming Doses")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Small Widget View

struct SmallWidgetView: View {
    let entry: NextDoseEntry

    /// Get the next pending (not given) dose
    private var nextPendingDose: WidgetDoseInfo? {
        if let primary = entry.primaryDose, !primary.isGiven {
            return primary
        }
        return entry.additionalDoses.first { !$0.isGiven }
    }

    var body: some View {
        if let dose = nextPendingDose {
            VStack(alignment: .leading, spacing: 4) {
                // Icon and status
                HStack {
                    Image(systemName: dose.iconName)
                        .font(.system(size: 24))
                        .foregroundStyle(dose.isOverdue ? .red : .blue)

                    Spacer()

                    // Status badge or countdown
                    if dose.isOverdue {
                        Text("OVERDUE")
                            .font(.caption2)
                            .fontWeight(.bold)
                            .foregroundStyle(.white)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 2)
                            .background(.red)
                            .clipShape(Capsule())
                    } else {
                        Text(dose.relativeTimeDescription)
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundStyle(.blue)
                    }
                }

                Spacer()

                // Medication name
                Text(dose.medicationName)
                    .font(.headline)
                    .lineLimit(2)
                    .minimumScaleFactor(0.8)

                // Dosage if available
                if let dosage = dose.dosage {
                    Text(dosage)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                // Time and action button
                HStack {
                    HStack(spacing: 4) {
                        Image(systemName: "clock")
                            .font(.caption2)
                        Text(dose.formattedTime)
                            .font(.caption)
                    }
                    .foregroundStyle(.secondary)

                    Spacer()

                    // Interactive button (iOS 17+)
                    if #available(iOS 18.0, *) {
                        RecordDoseButton(dose: dose, style: .compact)
                    }
                }

                // Pet name
                Text(dose.petName)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
            .padding(2)
        } else if let dose = entry.primaryDose, dose.isGiven {
            // All doses given - show completion state
            VStack(spacing: 8) {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(.green)
                Text("All Done!")
                    .font(.headline)
                Text("Next dose tomorrow")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

// MARK: - Medium Widget View

struct MediumWidgetView: View {
    let entry: NextDoseEntry

    /// All doses sorted by time
    private var allDoses: [WidgetDoseInfo] {
        guard let primary = entry.primaryDose else { return [] }
        return ([primary] + entry.additionalDoses).sorted { $0.scheduledTime < $1.scheduledTime }
    }

    /// Next pending dose
    private var nextPendingDose: WidgetDoseInfo? {
        allDoses.first { !$0.isGiven }
    }

    var body: some View {
        HStack(spacing: 12) {
            // Primary/Next dose (left side)
            if let dose = nextPendingDose {
                primaryDoseView(dose)
                    .frame(maxWidth: .infinity)
            } else if let firstDose = allDoses.first {
                // All done - show last given
                allDoneView(lastDose: firstDose)
                    .frame(maxWidth: .infinity)
            }

            // Divider and schedule (right side)
            if allDoses.count > 1 {
                Divider()
                    .padding(.vertical, 8)

                VStack(alignment: .leading, spacing: 6) {
                    Text("Today's Schedule")
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .foregroundStyle(.secondary)
                        .textCase(.uppercase)

                    ForEach(allDoses.prefix(3)) { dose in
                        scheduleRow(dose)
                    }

                    Spacer()
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding(4)
    }

    private func allDoneView(lastDose: WidgetDoseInfo) -> some View {
        VStack(spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 36))
                .foregroundStyle(.green)
            Text("All Done!")
                .font(.headline)
            Text("Great job today")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func primaryDoseView(_ dose: WidgetDoseInfo) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            // Header with icon and status
            HStack {
                ZStack {
                    Circle()
                        .fill(dose.isOverdue ? Color.red.opacity(0.15) : Color.blue.opacity(0.15))
                        .frame(width: 44, height: 44)

                    Image(systemName: dose.iconName)
                        .font(.system(size: 20))
                        .foregroundStyle(dose.isOverdue ? .red : .blue)
                }

                Spacer()

                // Status badge
                if dose.isOverdue {
                    Text("OVERDUE")
                        .font(.caption2)
                        .fontWeight(.bold)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(.red)
                        .clipShape(Capsule())
                }
            }

            Spacer()

            // Medication info
            Text(dose.medicationName)
                .font(.headline)
                .lineLimit(1)

            if let dosage = dose.dosage {
                Text(dosage)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            // Time info and action
            HStack(spacing: 12) {
                Label(dose.formattedTime, systemImage: "clock")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Text(dose.relativeTimeDescription)
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(dose.isOverdue ? .red : .blue)

                Spacer()

                // Interactive button (iOS 17+)
                if #available(iOS 18.0, *) {
                    RecordDoseButton(dose: dose, style: .standard)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(.green.opacity(0.15))
                        .clipShape(Capsule())
                }
            }

            // Pet name
            Label(dose.petName, systemImage: "pawprint.fill")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
    }

    private func scheduleRow(_ dose: WidgetDoseInfo) -> some View {
        HStack(spacing: 6) {
            // Status icon
            if dose.isGiven {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 14))
                    .foregroundStyle(.green)
                    .frame(width: 18)
            } else if dose.isOverdue {
                Image(systemName: "exclamationmark.circle.fill")
                    .font(.system(size: 14))
                    .foregroundStyle(.red)
                    .frame(width: 18)
            } else {
                Image(systemName: "circle")
                    .font(.system(size: 14))
                    .foregroundStyle(.secondary)
                    .frame(width: 18)
            }

            VStack(alignment: .leading, spacing: 0) {
                Text(dose.medicationName)
                    .font(.caption)
                    .fontWeight(.medium)
                    .lineLimit(1)
                    .foregroundStyle(dose.isGiven ? .secondary : .primary)

                Text(dose.formattedTime)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            Spacer()
        }
    }
}

// MARK: - Large Widget View

struct LargeWidgetView: View {
    let entry: NextDoseEntry

    /// All doses sorted by scheduled time
    private var allDoses: [WidgetDoseInfo] {
        guard let primary = entry.primaryDose else { return [] }
        return ([primary] + entry.additionalDoses).sorted { $0.scheduledTime < $1.scheduledTime }
    }

    /// Count of completed doses
    private var completedCount: Int {
        allDoses.filter { $0.isGiven }.count
    }

    /// Count of pending doses
    private var pendingCount: Int {
        allDoses.filter { !$0.isGiven }.count
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            // Header with progress
            HStack {
                Image(systemName: "pills.fill")
                    .font(.title2)
                    .foregroundStyle(.blue)
                Text("Today's Schedule")
                    .font(.headline)
                Spacer()

                // Progress indicator
                if !allDoses.isEmpty {
                    Text("\(completedCount)/\(allDoses.count)")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(.fill.tertiary)
                        .clipShape(Capsule())
                }
            }

            Divider()

            // Doses list
            if allDoses.isEmpty {
                Spacer()
                HStack {
                    Spacer()
                    VStack(spacing: 8) {
                        Image(systemName: "checkmark.circle")
                            .font(.largeTitle)
                            .foregroundStyle(.green)
                        Text("No medications scheduled")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                Spacer()
            } else {
                ForEach(allDoses) { dose in
                    doseRow(dose)
                    if dose.id != allDoses.last?.id {
                        Divider()
                    }
                }
                Spacer()
            }
        }
        .padding(4)
    }

    private func doseRow(_ dose: WidgetDoseInfo) -> some View {
        HStack(spacing: 12) {
            // Status icon
            ZStack {
                Circle()
                    .fill(statusBackgroundColor(for: dose))
                    .frame(width: 40, height: 40)

                Image(systemName: statusIcon(for: dose))
                    .font(.system(size: 18))
                    .foregroundStyle(statusColor(for: dose))
            }

            // Info
            VStack(alignment: .leading, spacing: 2) {
                HStack {
                    Text(dose.medicationName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundStyle(dose.isGiven ? .secondary : .primary)

                    if dose.isGiven {
                        Text("GIVEN")
                            .font(.caption2)
                            .fontWeight(.bold)
                            .foregroundStyle(.white)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 1)
                            .background(.green)
                            .clipShape(Capsule())
                    } else if dose.isOverdue {
                        Text("OVERDUE")
                            .font(.caption2)
                            .fontWeight(.bold)
                            .foregroundStyle(.white)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 1)
                            .background(.red)
                            .clipShape(Capsule())
                    }
                }

                HStack(spacing: 8) {
                    if let dosage = dose.dosage {
                        Text(dosage)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Label(dose.petName, systemImage: "pawprint.fill")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }

                // Show who gave it (for given doses)
                if dose.isGiven, let givenBy = dose.givenBy {
                    HStack(spacing: 4) {
                        Image(systemName: "person.fill")
                            .font(.caption2)
                        Text("by \(givenBy)")
                            .font(.caption2)
                        if let givenTime = dose.formattedGivenTime {
                            Text("at \(givenTime)")
                                .font(.caption2)
                        }
                    }
                    .foregroundStyle(.green)
                }
            }

            Spacer()

            // Time and action
            VStack(alignment: .trailing, spacing: 4) {
                Text(dose.formattedTime)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundStyle(dose.isGiven ? .secondary : .primary)

                if !dose.isGiven {
                    Text(dose.relativeTimeDescription)
                        .font(.caption)
                        .foregroundStyle(dose.isOverdue ? .red : .blue)

                    // Interactive button (iOS 17+)
                    if #available(iOS 18.0, *) {
                        RecordDoseButton(dose: dose, style: .standard)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(.green.opacity(0.15))
                            .clipShape(Capsule())
                    }
                }
            }
        }
    }

    private func statusIcon(for dose: WidgetDoseInfo) -> String {
        if dose.isGiven {
            return "checkmark"
        } else if dose.isOverdue {
            return dose.iconName
        } else {
            return dose.iconName
        }
    }

    private func statusColor(for dose: WidgetDoseInfo) -> Color {
        if dose.isGiven {
            return .green
        } else if dose.isOverdue {
            return .red
        } else {
            return .blue
        }
    }

    private func statusBackgroundColor(for dose: WidgetDoseInfo) -> Color {
        if dose.isGiven {
            return .green.opacity(0.15)
        } else if dose.isOverdue {
            return .red.opacity(0.15)
        } else {
            return .blue.opacity(0.15)
        }
    }
}

// MARK: - Previews

#Preview("Small - With Dose", as: .systemSmall) {
    NextDoseWidget()
} timeline: {
    NextDoseEntry(
        date: Date(),
        widgetData: WidgetData(
            nextDoses: [
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Gabapentin",
                    dosage: "100mg",
                    iconName: "pills.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(2 * 3600 + 30 * 60),
                    isOverdue: false,
                    isGiven: false,
                    givenBy: nil,
                    givenAt: nil
                )
            ],
            lastUpdated: Date()
        )
    )
}

#Preview("Small - Overdue", as: .systemSmall) {
    NextDoseWidget()
} timeline: {
    NextDoseEntry(
        date: Date(),
        widgetData: WidgetData(
            nextDoses: [
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Eye Drops",
                    dosage: "2 drops each eye",
                    iconName: "drop.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(-30 * 60),
                    isOverdue: true,
                    isGiven: false,
                    givenBy: nil,
                    givenAt: nil
                )
            ],
            lastUpdated: Date()
        )
    )
}

#Preview("Medium - Schedule", as: .systemMedium) {
    NextDoseWidget()
} timeline: {
    NextDoseEntry(
        date: Date(),
        widgetData: WidgetData(
            nextDoses: [
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Gabapentin",
                    dosage: "100mg",
                    iconName: "pills.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(-2 * 3600),
                    isOverdue: false,
                    isGiven: true,
                    givenBy: "Alex",
                    givenAt: Date().addingTimeInterval(-2 * 3600 + 5 * 60)
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Eye Drops",
                    dosage: "2 drops",
                    iconName: "drop.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(2 * 3600),
                    isOverdue: false,
                    isGiven: false,
                    givenBy: nil,
                    givenAt: nil
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Vitamin D",
                    dosage: nil,
                    iconName: "capsule.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(6 * 3600),
                    isOverdue: false,
                    isGiven: false,
                    givenBy: nil,
                    givenAt: nil
                )
            ],
            lastUpdated: Date()
        )
    )
}

#Preview("Large - Full Day", as: .systemLarge) {
    NextDoseWidget()
} timeline: {
    NextDoseEntry(
        date: Date(),
        widgetData: WidgetData(
            nextDoses: [
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Gabapentin",
                    dosage: "100mg",
                    iconName: "pills.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(-4 * 3600),
                    isOverdue: false,
                    isGiven: true,
                    givenBy: "Alex",
                    givenAt: Date().addingTimeInterval(-4 * 3600 + 10 * 60)
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Eye Drops",
                    dosage: "2 drops each eye",
                    iconName: "drop.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(-30 * 60),
                    isOverdue: true,
                    isGiven: false,
                    givenBy: nil,
                    givenAt: nil
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Vitamin D",
                    dosage: "1000 IU",
                    iconName: "capsule.fill",
                    petName: "Luna",
                    scheduledTime: Date().addingTimeInterval(4 * 3600),
                    isOverdue: false,
                    isGiven: false,
                    givenBy: nil,
                    givenAt: nil
                )
            ],
            lastUpdated: Date()
        )
    )
}

#Preview("Large - All Done", as: .systemLarge) {
    NextDoseWidget()
} timeline: {
    NextDoseEntry(
        date: Date(),
        widgetData: WidgetData(
            nextDoses: [
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Gabapentin",
                    dosage: "100mg",
                    iconName: "pills.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(-4 * 3600),
                    isOverdue: false,
                    isGiven: true,
                    givenBy: "Alex",
                    givenAt: Date().addingTimeInterval(-4 * 3600 + 5 * 60)
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Eye Drops",
                    dosage: "2 drops each eye",
                    iconName: "drop.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(-1 * 3600),
                    isOverdue: false,
                    isGiven: true,
                    givenBy: "Sarah",
                    givenAt: Date().addingTimeInterval(-1 * 3600 + 15 * 60)
                )
            ],
            lastUpdated: Date()
        )
    )
}

#Preview("Empty State", as: .systemSmall) {
    NextDoseWidget()
} timeline: {
    NextDoseEntry(
        date: Date(),
        widgetData: nil
    )
}
