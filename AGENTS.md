# AGENTS

## Development Mode

This repository follows a container-first development model.
Future development, debugging, testing, and verification should prefer running inside the project containers instead of relying on the host machine environment.

## Core Rules

1. Treat Docker Compose as the default development entry point.
2. Prefer running backend commands inside the backend container.
3. Prefer running frontend commands inside the frontend container.
4. Do not assume the host machine has the required Python, Node.js, npm, or system-level dependencies installed.
5. When host and container behavior differ, treat container behavior as the source of truth for this project.

## Expected Workflow

### Start Services

Use the project compose files to bring up the workspace before making runtime changes:

```bash
docker compose up --build
```

If the development workflow uses a dedicated dev compose file, prefer that variant for local iteration.

### Backend Work

Run backend tasks inside the backend container, for example:

```bash
docker exec md2word-backend-dev sh -lc 'cd /app/backend && uv run pytest -q'
```

Use the backend container for:

- `uv sync`
- `uv run pytest`
- API debugging
- dependency validation
- conversion pipeline checks

### Frontend Work

Run frontend tasks inside the frontend container, for example:

```bash
docker exec md2word-frontend-dev sh -lc 'cd /app/frontend && npm test'
docker exec md2word-frontend-dev sh -lc 'cd /app/frontend && npm run build'
```

Use the frontend container for:

- `npm install`
- `npm test`
- `npm run build`
- Vite-related debugging

## Dependency Policy

1. Add and verify dependencies in containers first.
2. If a new dependency is needed, confirm it works in the relevant service container before considering the task complete.
3. Avoid documenting host-only fixes when the actual application runs in containers.

## Testing Policy

Before closing meaningful application changes, prefer verifying in containers:

- backend tests in the backend container
- frontend tests in the frontend container
- frontend production build in the frontend container

If a task cannot be validated in containers, document the gap explicitly.

## Documentation Policy

When adding future setup or run instructions:

1. Prefer container commands first.
2. If host-machine commands are included, mark them as secondary or convenience-only.
3. Keep service names and working directories aligned with the actual compose setup.

## Decision Rule

If there is any ambiguity about whether to use host tooling or container tooling, choose container tooling by default.
