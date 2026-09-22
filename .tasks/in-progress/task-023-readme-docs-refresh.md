# Ticket: Refresh README for Human-Facing Setup Guidance

## User Story

As a project contributor, I want the README to clearly explain the app, how to set it up, and how to create client access without including operational or AI-agent details so that new humans can get started quickly and confidently.

## Scope

- Simplify the project README to only the information humans need to run and use the app.
- Keep the README short, scannable, and focused on setup and usage.
- Document how to create a client account via the registration page and/or Django shell.
- Ensure instructions match the current project behavior and setup flow.
- Remove internal workflow, agent policy, and repository-process details that are not relevant to end users.

## Acceptance Criteria

- [ ] The README clearly explains what the project does in a few sentences.
- [ ] Setup steps for local development are concise and accurate.
- [ ] Instructions include how to create a client via the registration page.
- [ ] The README includes the Django shell method for assigning a user to the `Client` group when needed.
- [ ] The README no longer includes AI-agent instructions, workflow policy, or AGENTS.md-specific content.
- [ ] The README stays short and user-friendly rather than acting as a full project policy document.
- [ ] The app run URL(s) and basic usage flow are included.
- [ ] Docker and validation commands remain brief and useful for developers.

## Status

Ready for implementation.
