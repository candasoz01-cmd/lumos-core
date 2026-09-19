# Ring developer onboarding friction log

Observed on September 19, 2026 while connecting the existing Lumos read-only
adapter to the official Ring Developer Playground. These are observations from
one account and browser session, not claims of platform-wide defects. Severity
and recommendations below are the developer's assessment. No credentials,
identity images, personal address or account identifiers are included.

## 1. Customer-facing business name validation

- **Task:** complete Amazon Developer registration to access Ring Playground.
- **Steps:** open developer registration; enter the requested account details;
  enter a customer-facing developer/business name; attempt to continue.
- **Expected:** accept a supported name or explain the exact validation rule.
- **Actual:** the field displayed a generic request for a valid business name.
  The warning did not explain which property of the entered value was invalid.
- **Severity:** medium; blocked onboarding until registration was completed.
  We did not measure the delay.
- **Workaround:** the account holder continued through registration. We did not
  establish a reproducible name-format rule or isolate which change resolved
  the warning, so we do not prescribe a particular name as a fix.
- **Recommendation:** show field-specific validation, permitted characters and
  length rules, and examples for individual developers and organizations.
- **Evidence boundary:** the validation message was visible in the session;
  no HTTP response or backend validation trace was captured.

## 2. HEIC identity-image upload

- **Task:** provide the front and back identity images required by registration.
- **Steps:** use the identity-photo upload alternative; try the supplied HEIC
  photos; convert copies to JPEG and upload the resulting files.
- **Expected:** accepted-format guidance before file selection and a clear
  format-specific error if HEIC is unsupported.
- **Actual:** the account holder reported that the HEIC files were rejected for
  their format. The JPEG copies could be uploaded; the browser subsequently
  returned to the Developer console and Playground access became available.
- **Severity:** medium; interrupted registration, with a local workaround.
- **Workaround:** convert the existing photos to JPEG without changing their
  content; the account holder handles identity authentication when required.
- **Recommendation:** prominently list supported formats and size limits before
  selection, explain HEIC incompatibility, and offer a safe supported capture or
  conversion path.
- **Evidence boundary:** the original format rejection was user-reported. JPEG
  upload and subsequent console/Playground access were observed. We did not
  independently isolate all steps of the account-verification decision.

## 3. Temporary token handling during repeat demos

- **Task:** run device discovery and status from Lumos without exposing secrets.
- **Steps:** generate a Playground token, transfer it through hidden local input
  into process memory, run the read-only registry actions, then clear the token.
- **Expected:** a clear lifetime and a practical way to repeat the demo safely.
- **Actual:** the UI clearly stated a 30-minute lifetime and warned that closing
  the tab would remove the displayed token. Both authenticated requests worked.
  This is workflow feedback, not an authentication failure or a request for
  longer-lived default credentials.
- **Severity:** low; repeat runs need a fresh token after expiry.
- **Workaround:** keep token generation close to the run; never put it into
  command arguments, source, screenshots or public logs.
- **Recommendation:** provide a minimal example that reads a token from hidden
  input, reports expiry clearly, and explains safe renewal for developer demos.
- **Evidence boundary:** the lifetime is the UI's statement, not an independently
  timed expiry experiment. We did not test tab closure against API revocation.

## Successful outcome and reproducibility

The actual remote API recording returned HTTP 200 for device discovery (one
official Playground simulated test device) and HTTP 200 for status
(`online=true`). Physical hardware was not used. These observations do not
establish production authorization readiness.

- [Recorded API demonstration](https://youtu.be/VpC01p-KWfg)
- [Source, request timestamps and reproduction instructions](ring-playground-live-20260919.md)

No equivalent live Alexa+ onboarding claim is made: that demonstration uses the
web-simulation path.
