# Adding a New App

This workspace is designed to host multiple tools behind one FastAPI backend and one React frontend.
When adding a new app, follow this document so backend routes, frontend entry points, sidebar registration, and tests stay consistent.

Container-first development is the default rule for this repository.
When validating a new app, prefer running commands inside the project containers described in [AGENTS.md](/home/charlie/workspace/md2word/AGENTS.md:1).

## Backend

1. Create a dedicated backend module under `backend/`, for example `backend/example_app/`.
2. Register the app in [backend/main.py](/home/charlie/workspace/md2word/backend/main.py:1) inside `TOOLS`. Each app must provide:
   - `id`: globally unique id, recommended format is lowercase words with hyphens, for example `example-app`
   - `label`: sidebar display name
   - `icon`: public icon path, for example `/icons/example-app.svg`
   - `description`: short description of the tool
3. Expose app-specific routes under `/api/<app-id>/...`. Do not mix multiple tools into the same route namespace.
4. Keep app-specific templates, fixtures, and configuration inside the app's own backend directory instead of extending `backend/md2word/`.
5. Add backend tests for the new app. At minimum cover:
   - one successful read path
   - one successful submit path
   - one explicit error path

## Frontend

1. Create a dedicated frontend app directory under `frontend/src/apps/`, for example `frontend/src/apps/example-app/`.
2. Put the main React entry component there, for example `ExampleApp.tsx`.
3. Import and mount the app in [frontend/src/App.tsx](/home/charlie/workspace/md2word/frontend/src/App.tsx:1).
4. Add a matching icon under `frontend/public/icons/`.
5. Sidebar behavior is fixed:
   - expanded rail: show icon and app name
   - collapsed rail: show icon only
   - text comes from the backend `label` returned by `/api/tools`
6. Reuse shared workspace variables and layout patterns before adding new global CSS. Keep app-specific styles scoped and intentional.

## Suggested Structure

```text
backend/
  main.py
  md2word/
  example_app/
frontend/
  public/icons/
    md2word.svg
    example-app.svg
  src/apps/
    md2word/
    example-app/
      ExampleApp.tsx
```

## Recommended Integration Order

1. Register the app in `TOOLS` and add `/api/<app-id>/...` routes.
2. Add the sidebar icon.
3. Create the frontend app component and mount it in `App.tsx`.
4. Add backend and frontend tests.
5. Verify the new app in containers before considering the work complete.

## Verification

Preferred container commands:

```bash
docker exec md2word-backend-dev sh -lc 'cd /app/backend && uv run pytest -q'
docker exec md2word-frontend-dev sh -lc 'cd /app/frontend && npm test'
docker exec md2word-frontend-dev sh -lc 'cd /app/frontend && npm run build'
```

Fallback host commands:

```bash
cd /home/charlie/workspace/md2word/backend
uv run pytest -q

cd /home/charlie/workspace/md2word/frontend
npm test
npm run build
```

## Current Limitation

The current [frontend/src/App.tsx](/home/charlie/workspace/md2word/frontend/src/App.tsx:1) still renders apps through manual condition branches.
If the number of apps grows, the next step should be a frontend tool registry, for example:

- one registry mapping `id -> React component`
- backend `/api/tools` only returning metadata
- frontend selecting the component through the registry and `activeToolId`

That keeps future app integration to a registration step instead of spreading more conditional rendering through the shell.
