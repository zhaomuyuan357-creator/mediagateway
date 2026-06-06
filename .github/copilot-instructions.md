<!-- Copilot Instructions: concise workspace bootstrap for AI assistants -->

Purpose
-------
This file gives AI assistants (Copilot-style agents) the minimum, high-signal information needed to be productive in this repository.

Quick Orientation
-----------------
- **Primary services**: backend (FastAPI/Python) and frontend (React+Vite/TypeScript).
- **Top-level commands**: `./setup.sh`, `make dev`, `docker compose -f docker-compose.local.yml up --build`, `npm install && npm run dev`, `pip install -r backend/requirements.txt && python backend/src/run.py`.
- **Primary docs**: [README.md](README.md), [QUICKSTART.md](QUICKSTART.md), [DEPLOYMENT.md](DEPLOYMENT.md), [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md), [CLAUDE.md](CLAUDE.md).

Scope & When To Help
--------------------
- Use this agent for: code navigation, small edits, documentation updates, scaffolding tests, and PR review guidance.
- Avoid making changes to secrets or CI publishing configurations without explicit user approval.

Project Conventions (short)
---------------------------
- Python: follow PEP 8 and add type hints; files live under `backend/src/`.
- TypeScript/React: functional components, hooks, Vite dev server; frontend code under `frontend/src/`.
- Storage: persistent files stored in `storage/` (videos/images/temp).
- Env vars: `DATABASE_URL`, `ENCRYPTION_KEY`, provider API keys — **do not commit secrets**.

Key Files (quick links)
- Backend entry: [backend/src/main.py](backend/src/main.py)
- Backend config: [backend/src/config.py](backend/src/config.py)
- API routes: [backend/src/api/routes.py](backend/src/api/routes.py)
- Core services: [backend/src/services/pipeline.py](backend/src/services/pipeline.py)
- Frontend entry: [frontend/src/main.tsx](frontend/src/main.tsx)
- Frontend API client: [frontend/src/lib/api.ts](frontend/src/lib/api.ts)

Common Tasks & How To Run Them
-----------------------------
- Local dev (recommended):

  - Run backend + frontend locally (source):

    ```bash
    make dev
    ```

  - Build and run containers locally:

    ```bash
    docker compose -f docker-compose.local.yml up --build
    ```

- Quick setup (pull pre-built images):

  ```bash
  ./setup.sh
  ```

What To Check Before Proposing Changes
--------------------------------------
- Read [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) and [CONTRIBUTING.md](CONTRIBUTING.md) for style and testing expectations.
- Prefer linking to existing docs rather than duplicating content.
- When adding endpoints, update both backend routes and the frontend API client.

Example Prompts (use these to start tasks)
-----------------------------------------
- "Locate the task execution pipeline and explain where new analysis steps should be inserted. Link files." 
- "Add a new API endpoint `POST /v1/tasks/retry` that re-queues failed tasks; update backend route, service, and frontend client with a minimal UI change." 
- "Create a short CONTRIBUTING subsection describing how to add a new provider (files to modify and tests to add)." 
- "List environment variables required for production deployment and where they're set in Docker compose files." 

Suggested Next Agent-Customizations
----------------------------------
- `applyTo: backend/**` — a backend-focused agent that can run tests, lint, and apply Python refactors.
- `applyTo: frontend/**` — frontend-focused assistant that runs `npm` scripts, updates React components, and runs type checks.
- `create-hook: pre-commit` — add a lightweight pre-commit hook template to run linters and type checks during PRs.

Feedback & Iteration
--------------------
If something here is unclear or missing, ask for the specific area to expand (examples: testing, CI, provider onboarding). Keep edits small and link-first.
