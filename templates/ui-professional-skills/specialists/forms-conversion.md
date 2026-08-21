# Forms Conversion

This specialist skill focuses on forms, sign-up, checkout, onboarding, intake, and other input-heavy flows.

## Apply when

- The user must enter data, submit a request, or move through a multi-field flow.
- Conversion depends on reducing friction, clarifying errors, or preserving confidence.
- Validation, masking, persistence, or step order are part of the work.

## Decisions to resolve

- What the minimum required fields are.
- When to validate and when to wait.
- Which errors are blocking, recoverable, or informational.
- What the submit, save, retry, and cancel states should do.
- Which inspected live or mature component owns field semantics, combobox and
  date behavior, focus, validation messages, and pending submission states.

## Image-primary augmentation

- Use image-primary when the form needs visual diagnosis or layout tuning.
- Inspect spacing, field grouping, labels, helper text, and error placement.
- Show the form in at least one normal and one error or empty state.

## HTML-primary augmentation

- Use HTML-primary when the flow must be exercised end to end.
- Keep the prototype interactive so the user can feel validation timing and recovery.
- Ask about field order, required data, and submission semantics one question at a time.

## Quality gate

- Pass only when the form is clear, forgiving, and recoverable.
- Verify labels, focus order, keyboard behavior, and error visibility.
- Reject forms that hide critical instructions or punish small mistakes.
- Reject hand-built complex controls when a compatible mature component covers
  keyboard, screen-reader, localization, and mobile input behavior.
