# Architecture

## Frontend shape

This project uses a feature-based structure on top of Next.js App Router.

- `app/` contains only route files and global CSS
- `features/` contains domain-specific UI and state
- `lib/` contains infrastructure code such as API clients and environment helpers
- `docs/` contains project conventions and contracts

## Current features

### Auth
Responsible for:
- landing page composition
- Steam sign-in button
- temporary local signed-in state for UI testing

### Chat
Responsible for:
- chat layout
- starter prompts
- input state
- local placeholder assistant responses

## Planned backend integrations

### Steam auth
Replace the placeholder click handler in `steam-login-button.tsx` or `landing-page.tsx` with a redirect to the real backend auth route.

### Recommendation API
Replace the local placeholder assistant message in `use-chat.ts` with a call to `lib/api/client.ts`.

## Design principles

1. Keep route files thin
2. Keep interactive state inside feature hooks/components
3. Keep API contracts typed
4. Keep reusable UI primitives in shadcn `components/ui`
5. Prefer small focused components over one large page file
