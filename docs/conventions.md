# Conventions

## Folder rules

### `app/`
Only route files, layout files, and global CSS belong here.

### `features/`
Each feature owns:
- components
- hooks
- local types

Do not place unrelated feature code together.

### `lib/`
Use for:
- API clients
- environment config
- shared utilities

## Component rules

1. Prefer one component per file
2. Prefer named exports for feature components
3. Use `use client` only where interactivity is needed
4. Keep presentation components as dumb as possible
5. Move stateful logic into hooks when it starts to grow

## Naming

- kebab-case for file names
- PascalCase for React component names
- camelCase for variables and functions
- exported types should be singular and descriptive

## LLM collaboration notes

When editing this repo:
- do not move files without updating imports
- do not add API logic directly into presentational components
- do not put large feature implementations into `app/page.tsx`
- keep backend request/response shapes typed in one place
