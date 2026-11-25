# SmartDesk Assistant — Security Policy

## Authentication and authorization

- All chat endpoints require JWT authentication.
- Inactive users are denied access.
- Conversations are private and scoped to their owners.
- Support and administrator roles do not bypass chat ownership.
- Unauthorized conversation access returns HTTP 404.

## Resource protection

- Daily request limits per user.
- Per-user request rate limits.
- Per-user and global generation concurrency limits.
- Generation deadlines and expired reservation recovery.
- Bounded message size, context and response size.

## AI provider security

- Local Ollama provider.
- Explicit model allowlist.
- Paid fallback disabled.
- No autonomous database access or administrative tools.
- No direct execution of operating system commands.
- Ticket creation requires explicit user confirmation
  once the ticket integration is implemented.

## Data protection

- Conversation history is isolated by conversation.
- Successful chat responses use Cache-Control: no-store.
- Domain errors expose predefined safe messages.
- SSE persistence errors do not expose internal exceptions.

## Prompt injection

- Versioned system instructions.
- User messages are treated as untrusted content.
- Prompt instructions are not an authorization boundary.
- Model output must not be trusted as an executable action.

## Known limitations

- Prompt injection cannot be completely prevented.
- Cache protection does not cover every framework error response.
- Real PostgreSQL concurrency requires functional validation.
- End-to-end SSE behavior through Nginx requires validation.
- Frontend Markdown rendering must sanitize untrusted content.
- Automated tests use mocks without a dedicated test database.
