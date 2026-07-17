/** Elektronik Uzmanı (Electronics Expert) pilot copy (English) — Phase 1 scope.
 * Out of scope (this release): camera-based automatic diagnosis, OCR, device
 * control, programmer writing, automatic ordering. See
 * docs/analysis/electronics-expert-pilot-design.md
 */
import type electronicsTr from "./tr";

const electronicsEn: typeof electronicsTr = {
  pilotAccess: {
    programName: "Electronics Expert Pilot Program",
    statusInvited: "Invited",
    statusActive: "Active",
    statusRevoked: "Revoked",
    quotaLabel: "Case quota",
    quotaExceeded: "Your pilot case quota is exhausted.",
    consentRequired: "You must accept the consent agreement to join the pilot program.",
    scopeNote: "This pilot only provides analysis and suggestions; it never controls a device or acts on your behalf.",
  },
  faultCase: {
    title: "Fault Case",
    statusOpen: "Open",
    statusInProgress: "In progress",
    statusResolved: "Resolved",
    statusArchived: "Archived",
    titleLabel: "Case title",
    symptomLabel: "Symptom description",
    deviceTypeLabel: "Device type",
    brandLabel: "Brand",
    modelLabel: "Model",
    boardIdLabel: "Board / part number",
  },
  measurement: {
    title: "Measurement Entry",
    typeVoltage: "Voltage",
    typeResistance: "Resistance",
    typeCurrent: "Current",
    typeCapacitance: "Capacitance",
    typeContinuity: "Continuity",
    typeFrequency: "Frequency",
    typeOther: "Other",
    testPointLabel: "Test point",
    measuredValueLabel: "Measured value",
    expectedValueLabel: "Expected value",
    deviationWarning: "The measured value deviates from the expected value — this is only an arithmetic aid, not a definitive fault indicator.",
    manualEntryNote: "Measurements are entered manually only; automatic device read-in is not part of this release.",
  },
  finding: {
    title: "Finding",
    confidenceLow: "Low confidence",
    confidenceMedium: "Medium confidence",
    confidenceHigh: "High confidence",
    evidenceRequired: "Every finding must be backed by at least one piece of evidence (a measurement).",
    disclaimer: "This is not a definitive fault diagnosis; it is a possible finding.",
    createdByUser: "User",
    createdByLumosAssist: "With Lumos assistance",
  },
  risk: {
    title: "High-Risk Warning",
    severityWarn: "Warning",
    severityHigh: "High risk",
    severityCritical: "Critical risk",
    categoryMainsVoltage: "Mains voltage",
    categoryCapacitorStoredCharge: "Stored charge in capacitor",
    categoryFireSmokeSmell: "Burning / smoke smell",
    categoryBatterySwelling: "Battery swelling",
    categoryHighCurrent: "High current",
    categoryUnknownHighVoltage: "Unknown high voltage",
    categoryOther: "Other",
    ackRequired: "You must acknowledge this safety warning before continuing.",
    neverAutoNote: "This warning is never auto-dismissed or suppressed.",
  },
  paidFeatureStatus: {
    title: "Feature Status",
    closed: "Closed",
    pilot: "Pilot",
    validated: "Validated",
    paid: "Paid",
    transitionNote: "Status transitions are never automatic; each one requires a separate decision record (ADR/OD).",
  },
  scopeNotice: {
    outOfScope: "This release does not include camera-based automatic diagnosis, OCR, device control, programmer writing, or automatic ordering.",
  },
};

export default electronicsEn;
