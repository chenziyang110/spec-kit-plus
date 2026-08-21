# Commerce Service

This domain covers checkout, order flow, pricing, subscriptions, service purchases, bookings, and transaction-oriented customer surfaces.

## Apply when

- The user wants to sell, book, quote, subscribe, or convert through the interface.
- The work includes pricing tiers, product selection, cart-like steps, payment, confirmation, or service scheduling.
- Trust, clarity, and error recovery matter more than decorative style.
- The user needs a clean path from interest to completion with low friction.

## Decisions to resolve

- What the customer is buying and what the primary conversion step is.
- Which price, fee, term, or commitment details must be visible before commitment.
- What can be saved, edited, or recovered after an error.
- Whether the flow is single-step, multi-step, or assisted.
- How to surface trust signals without cluttering the path.

## Image-primary augmentation

- Use image-primary for service or commerce screens when image generation is available.
- Keep the layout grounded in real checkout or booking behavior, not a fictional storefront.
- Show price, commitment, and confirmation states clearly.
- Use inspection to catch trust issues, clutter, and misleading hierarchy.

## HTML-primary augmentation

- Use HTML-primary when the flow needs to be tested interactively or image generation is not available.
- Keep the prototype close to the actual transaction path and avoid dead-end UI.
- Ask the user only the questions that affect pricing, commitments, or recovery behavior.
- Keep legal and confirmation copy visible where it changes user trust or responsibility.

## Quality gate

- Pass only when the flow is obvious, recoverable, and trustworthy.
- Verify that totals, terms, and confirmation states are explicit.
- Reject flows that hide critical cost or commitment details.
- Escalate to the forms, accessibility, or product-workspace specialists for deeper treatment of inputs, validation, and state handling.

