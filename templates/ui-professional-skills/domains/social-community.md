# Social Community

This domain covers social feeds, community hubs, messaging-like surfaces, creator tools, and people-centered networked experiences.

## Apply when

- The product is about posts, comments, reactions, profiles, communities, channels, or follower-driven interaction.
- The user cares about engagement, identity, activity streams, moderation, or community health.
- The interface has competing conversational, social, and content-discovery pressures.
- The surface must support both reading and participation.

## Decisions to resolve

- What the primary social action is: post, reply, react, follow, share, moderate, or discover.
- How identity should be expressed.
- Which interactions are public, private, or moderated.
- How much algorithmic feed structure the user wants.
- What safety, reporting, or trust signals are required.

## Image-primary augmentation

- Use image-primary when the agent can inspect a feed or social concept.
- Keep the visual result credible for real posts, avatars, reactions, and moderation states.
- Show one primary social loop clearly instead of an entire network at once.
- Use separate images for feed, composer, profile, and moderation states when needed.

## HTML-primary augmentation

- Use HTML-primary when the surface needs live interaction or careful community state handling.
- Ask one question at a time about feed ordering, moderation, or composer behavior.
- Keep the composer, feed, and profile states understandable without relying on placeholder social noise.
- Avoid inventing fake engagement metrics if they are not part of the brief.

## Quality gate

- Pass only when the community loop is obvious and safe enough to use.
- Verify content hierarchy, identity cues, moderation affordances, and responsive behavior.
- Reject noisy layouts that hide the actual social action.
- Escalate to accessibility, forms, or motion specialists for deeper checks on input flow and animated feedback.

