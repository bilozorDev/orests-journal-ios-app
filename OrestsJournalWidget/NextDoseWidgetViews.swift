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

    var body: some View {
        if let dose = entry.primaryDose {
            VStack(alignment: .leading, spacing: 4) {
                // Icon and countdown
                HStack {
                    Image(systemName: dose.iconName)
                        .font(.system(size: 24))
                        .foregroundStyle(dose.isOverdue ? .red : .blue)

                    Spacer()

                    // Countdown
                    Text(dose.relativeTimeDescription)
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundStyle(dose.isOverdue ? .red : .secondary)
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

                // Time
                HStack(spacing: 4) {
                    Image(systemName: "clock")
                        .font(.caption2)
                    Text(dose.formattedTime)
                        .font(.caption)
                }
                .foregroundStyle(.secondary)

                // Pet name
                Text(dose.petName)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
            .padding(2)
        }
    }
}

// MARK: - Medium Widget View

struct MediumWidgetView: View {
    let entry: NextDoseEntry

    var body: some View {
        HStack(spacing: 16) {
            // Primary dose (left side)
            if let dose = entry.primaryDose {
                primaryDoseView(dose)
                    .frame(maxWidth: .infinity)
            }

            // Divider and additional doses (right side)
            if !entry.additionalDoses.isEmpty {
                Divider()
                    .padding(.vertical, 8)

                VStack(alignment: .leading, spacing: 8) {
                    Text("Coming Up")
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .foregroundStyle(.secondary)
                        .textCase(.uppercase)

                    ForEach(entry.additionalDoses) { dose in
                        additionalDoseRow(dose)
                    }

                    Spacer()
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding(4)
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

            // Time info
            HStack(spacing: 12) {
                Label(dose.formattedTime, systemImage: "clock")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Text(dose.relativeTimeDescription)
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(dose.isOverdue ? .red : .blue)
            }

            // Pet name
            Label(dose.petName, systemImage: "pawprint.fill")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
    }

    private func additionalDoseRow(_ dose: WidgetDoseInfo) -> some View {
        HStack(spacing: 8) {
            Image(systemName: dose.iconName)
                .font(.system(size: 14))
                .foregroundStyle(dose.isOverdue ? .red : .secondary)
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 1) {
                Text(dose.medicationName)
                    .font(.caption)
                    .fontWeight(.medium)
                    .lineLimit(1)

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

    /// All doses including primary and additional
    private var allDoses: [WidgetDoseInfo] {
        guard let primary = entry.primaryDose else { return [] }
        return [primary] + entry.additionalDoses
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                Image(systemName: "pills.fill")
                    .font(.title2)
                    .foregroundStyle(.blue)
                Text("Medication Schedule")
                    .font(.headline)
                Spacer()
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
                        Text("All caught up!")
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
            // Icon
            ZStack {
                Circle()
                    .fill(dose.isOverdue ? Color.red.opacity(0.15) : Color.blue.opacity(0.15))
                    .frame(width: 40, height: 40)

                Image(systemName: dose.iconName)
                    .font(.system(size: 18))
                    .foregroundStyle(dose.isOverdue ? .red : .blue)
            }

            // Info
            VStack(alignment: .leading, spacing: 2) {
                HStack {
                    Text(dose.medicationName)
                        .font(.subheadline)
                        .fontWeight(.semibold)

                    if dose.isOverdue {
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
            }

            Spacer()

            // Time
            VStack(alignment: .trailing, spacing: 2) {
                Text(dose.formattedTime)
                    .font(.subheadline)
                    .fontWeight(.medium)

                Text(dose.relativeTimeDescription)
                    .font(.caption)
                    .foregroundStyle(dose.isOverdue ? .red : .blue)
            }
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
                    isOverdue: false
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
                    isOverdue: true
                )
            ],
            lastUpdated: Date()
        )
    )
}

#Preview("Medium - Multiple", as: .systemMedium) {
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
                    isOverdue: false
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Eye Drops",
                    dosage: "2 drops",
                    iconName: "drop.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(6 * 3600),
                    isOverdue: false
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Vitamin D",
                    dosage: nil,
                    iconName: "capsule.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(8 * 3600),
                    isOverdue: false
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
                    scheduledTime: Date().addingTimeInterval(-30 * 60),
                    isOverdue: true
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Eye Drops",
                    dosage: "2 drops each eye",
                    iconName: "drop.fill",
                    petName: "Orest",
                    scheduledTime: Date().addingTimeInterval(2 * 3600),
                    isOverdue: false
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Vitamin D",
                    dosage: "1000 IU",
                    iconName: "capsule.fill",
                    petName: "Luna",
                    scheduledTime: Date().addingTimeInterval(4 * 3600),
                    isOverdue: false
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
