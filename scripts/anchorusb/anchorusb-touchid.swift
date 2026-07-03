#!/usr/bin/env swift
// AnchorUSB POC — Touch ID user-presence gate via LocalAuthentication.
// Does NOT unlock the vault (KDF still needs passphrase). Exit 0 = biometric OK.

import Foundation
import LocalAuthentication

let reason = CommandLine.arguments.dropFirst().first
    ?? "AnchorUSB: authenticate to unlock vault"

let context = LAContext()
context.localizedCancelTitle = "Cancel"

var policyError: NSError?
guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &policyError) else {
    let msg = policyError?.localizedDescription ?? "biometrics unavailable"
    fputs("TOUCHID_UNAVAILABLE: \(msg)\n", stderr)
    exit(2)
}

let sem = DispatchSemaphore(value: 0)
var exitCode = 1

context.evaluatePolicy(
    .deviceOwnerAuthenticationWithBiometrics,
    localizedReason: reason
) { success, error in
    if success {
        fputs("TOUCHID_OK\n", stderr)
        exitCode = 0
    } else if let error = error as NSError? {
        if error.code == LAError.userCancel.rawValue {
            fputs("TOUCHID_CANCEL\n", stderr)
            exitCode = 3
        } else {
            fputs("TOUCHID_FAIL: \(error.localizedDescription)\n", stderr)
            exitCode = 1
        }
    }
    sem.signal()
}

sem.wait()
exit(Int32(exitCode))
