//
//  NextDoseWidget.swift
//  OrestsJournalWidget
//
//  Widget showing next upcoming medication dose.
//

import WidgetKit
import SwiftUI
import AppIntents

// MARK: - Timeline Entry

struct NextDoseEntry: TimelineEntry {
    let date: Date
    let widgetData: WidgetData?

    /// Check if this is placeholder/preview data
    var isPlaceholder: Bool {
        widgetData == nil
    }

    /// The primary dose to display
    var primaryDose: WidgetDoseInfo? {
        widgetData?.primaryDose
    }

    /// Additional doses (for medium/large widgets)
    var additionalDoses: [WidgetDoseInfo] {
        guard let doses = widgetData?.nextDoses, doses.count > 1 else {
            return []
        }
        return Array(doses.dropFirst().prefix(2))
    }
}

// MARK: - Configuration Intent

struct NextDoseWidgetIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Next Dose"
    static var description = IntentDescription("Shows your next upcoming medication dose.")
}

// MARK: - Timeline Provider

struct NextDoseProvider: AppIntentTimelineProvider {
    typealias Entry = NextDoseEntry
    typealias Intent = NextDoseWidgetIntent

    func placeholder(in context: Context) -> NextDoseEntry {
        NextDoseEntry(
            date: Date(),
            widgetData: sampleWidgetData
        )
    }

    func snapshot(for configuration: NextDoseWidgetIntent, in context: Context) async -> NextDoseEntry {
        let widgetData = WidgetDataManager.shared.getWidgetData()
        return NextDoseEntry(
            date: Date(),
            widgetData: widgetData ?? sampleWidgetData
        )
    }

    func timeline(for configuration: NextDoseWidgetIntent, in context: Context) async -> Timeline<NextDoseEntry> {
        let widgetData = WidgetDataManager.shared.getWidgetData()
        let currentDate = Date()

        var entries: [NextDoseEntry] = []

        // Create entry for now
        entries.append(NextDoseEntry(
            date: currentDate,
            widgetData: widgetData
        ))

        // If we have upcoming doses, create entries at those times for countdown update
        if let doses = widgetData?.nextDoses {
            for dose in doses.prefix(3) {
                // Create entry slightly after dose time to show "overdue" state
                let updateTime = dose.scheduledTime.addingTimeInterval(60)
                if updateTime > currentDate {
                    entries.append(NextDoseEntry(
                        date: updateTime,
                        widgetData: widgetData
                    ))
                }
            }
        }

        // Refresh every 15 minutes minimum
        let refreshDate = currentDate.addingTimeInterval(15 * 60)

        return Timeline(entries: entries, policy: .after(refreshDate))
    }

    // Sample data for previews
    private var sampleWidgetData: WidgetData {
        let sampleDose = WidgetDoseInfo(
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
        let sampleDose2 = WidgetDoseInfo(
            medicationId: UUID(),
            medicationName: "Eye Drops",
            dosage: "2 drops",
            iconName: "drop.fill",
            petName: "Orest",
            scheduledTime: Date().addingTimeInterval(6 * 3600),
            isOverdue: false,
            isGiven: false,
            givenBy: nil,
            givenAt: nil
        )
        return WidgetData(
            nextDoses: [sampleDose, sampleDose2],
            lastUpdated: Date()
        )
    }
}

// MARK: - Widget Definition

struct NextDoseWidget: Widget {
    let kind: String = "NextDoseWidget"

    var body: some WidgetConfiguration {
        AppIntentConfiguration(
            kind: kind,
            intent: NextDoseWidgetIntent.self,
            provider: NextDoseProvider()
        ) { entry in
            NextDoseWidgetEntryView(entry: entry)
                .containerBackground(.fill.tertiary, for: .widget)
        }
        .configurationDisplayName("Next Dose")
        .description("Shows your next upcoming medication dose.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
    }
}

// MARK: - Widget Bundle

@main
struct OrestsJournalWidgetBundle: WidgetBundle {
    var body: some Widget {
        NextDoseWidget()
    }
}

// MARK: - Previews

#Preview(as: .systemSmall) {
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

#Preview(as: .systemMedium) {
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
                ),
                WidgetDoseInfo(
                    medicationId: UUID(),
                    medicationName: "Eye Drops",
                    dosage: "2 drops",
                    iconName: "drop.fill",
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
