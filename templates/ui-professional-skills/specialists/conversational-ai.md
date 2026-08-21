# Conversational AI

This specialist skill focuses on chat UIs, agent surfaces, copilot panels, prompt-driven flows, and other conversational interfaces.

## Apply when

- The user is designing a chat, assistant, copilot, or prompt-led interface.
- The surface needs turn-taking, tool feedback, citations, memory, or confidence states.
- The product must explain what the agent can and cannot do.

## Decisions to resolve

- What the user asks the agent to do first.
- Which responses should stream, summarize, or ask follow-up questions.
- How tool calls, citations, errors, and retries should appear.
- What the user should control versus what the agent should infer.

## Image-primary augmentation

- Use image-primary when the conversation surface needs layout or state exploration.
- Show at least one normal exchange and one error, tool, or waiting state.
- Keep the conversation visually calm and easy to scan.

## HTML-primary augmentation

- Use HTML-primary when the agent interaction must be exercised live.
- Ask one clarifying question at a time so the interface can progress naturally.
- Preserve visible history, tool status, and recovery behavior.

## Quality gate

- Pass only when the conversation is legible, controlled, and trustworthy.
- Verify state transitions, latency feedback, and error recovery.
- Reject chat UIs that hide important agent state or overwhelm the user with noise.

