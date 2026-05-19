---
name: prd-to-scaffold
description: >-
  Reads any PRD or spec file (Project_PRD.md or similar), asks the minimum
  necessary clarifying questions, produces a structured plan with actionable
  todos, then implements the full project scaffold end-to-end without stopping.
  Use when the user provides a requirements document, spec, or PRD and wants a
  complete runnable project scaffold created from it.
---

# PRD → Scaffold

Read the PRD, ask only what's ambiguous, create a plan with todos, implement everything.

---

## Step 1 — Read the PRD thoroughly

Before anything else, read the full PRD. Extract:

- **What the system does** — core purpose and workflow
- **Stages / pipeline** — ordered steps, dependencies between them, state transitions
- **Inputs** — files or data the system reads from disk
- **Outputs / artifacts** — every file the system must produce
- **External integrations** — APIs, LLMs, browsers, databases, third-party services
- **Controlled values** — any enumerated vocabularies that must be validated
- **Must / Should / Stretch** — which features are required vs optional
- **Validation requirements** — what a `validate` command must verify
- **Tech constraints** — languages, tools, or runtimes explicitly required

---

## Step 2 — Ask targeted clarifying questions

Only ask what cannot be inferred from the PRD. Common gaps:

| Gap | Default | Example question |
|---|---|---|
| Backend framework | **FastAPI (Python)** — use unless PRD specifies otherwise | "Prefer a different backend?" |
| LLM provider | None — must ask | "Which LLM provider — OpenAI, Anthropic, Gemini, other?" |
| Frontend framework | **React + Vite + TypeScript + shadcn/ui + Tailwind** — use unless user prefers otherwise | "Preferred frontend stack?" |
| Database | **SQLite** — use unless scale or PRD requires otherwise | "SQLite sufficient, or do you need Postgres/Mongo?" |
| Auth | None — only add if PRD mentions it | "Does this need authentication?" |

Skip asking about anything that has a default — only ask when the PRD is genuinely ambiguous or the user has hinted at a preference.

Use `AskQuestion` for structured multiple-choice. Ask at most 1–2 questions at a time.

---

## Step 3 — Create the plan using `CreatePlan`

Call `CreatePlan` with:

- **`name`** — short project name
- **`overview`** — 2-3 sentence summary of what is being built and the tech stack chosen
- **`plan`** — structured Markdown covering:
  - Full directory tree with a comment on each file's role
  - Backend details: state machine states, DB schema, key utilities
  - Frontend details: pages, components, data-fetching strategy
  - CLI / Makefile targets
  - Explicit list of what is NOT included (out of scope per the PRD)
- **`todos`** — a flat ordered list of todos that collectively cover the entire implementation

### How to write todos

Todos are the implementation checklist. Write them so that completing all of them = the project is done. Each todo should be:

- **One cohesive unit of work** — not a single file, not the entire project
- **Independently verifiable** — you can tell when it's done
- **Ordered** — later todos may depend on earlier ones

Typical todo set for a full-stack project:

```
1. Backend scaffolding — directory structure, requirements, .env.example, config, DB models
2. Pydantic / schema models — all request/response and artifact schemas
3. Core utilities — LLM client, external API wrappers, validators
4. Pipeline / business logic — all stages or processing steps
5. API routes — all endpoints wired to business logic
6. Input files and CLI — sample inputs, CLI entry points, validate script, Makefile
7. Frontend scaffolding — framework init, package installs, config files
8. Frontend types and API client — TypeScript types mirroring backend schemas, fetch wrapper
9. Frontend components — UI primitives, domain-specific components
10. Frontend pages — all routes wired to components and API client
11. Build verification — run build, fix all type/lint errors
```

Adapt the list to the actual PRD — fewer todos for simpler projects, more for complex ones.

---

## Step 4 — Implement

Work through todos **in order**. For each:

1. Mark it `in_progress` before starting
2. Complete all work for that todo
3. Mark it `completed` immediately after finishing
4. Move to the next — do not stop until all todos are `completed`

### General implementation principles

**Foundation first** — config, DB, schemas, utilities before business logic; business logic before API routes; API routes before frontend.

**No static precomputed outputs** — if the PRD says the system runs a pipeline, it must actually run. Hardcoded fixture outputs are not acceptable.

**Downstream stages consume structured outputs** — pass parsed objects between stages, not raw strings.

**Validate controlled vocabularies** — if the PRD defines enumerated values, write a validator and call it on every external response before persisting.

**Security defaults** — all secrets via environment variables, sanitise path inputs in API routes, no hardcoded credentials.

**Frontend must build with zero errors** — run the build command at the end of the frontend todos and fix every error before marking done.

### Installation and dependency notes

- Create a virtual environment (`python -m venv .venv`) before installing Python packages
- Check for platform-specific binary packages that may need `--only-binary=:all:` on newer Python versions
- Use `>=` version constraints (not `==`) for packages with compiled extensions to avoid build failures
- For Playwright scrapers targeting modern SPAs: use `wait_until="domcontentloaded"` + `page.wait_for_timeout(3000)` instead of `wait_until="networkidle"` — SPAs fire continuous background XHRs and never reach true network idle, causing 45s timeouts. Also block image/font/media routes with `page.route(...)` to speed up loads. Use a realistic browser user-agent string, not a bot string, to avoid bot-detection blocks
- After `npm create vite`, always run `npm install` before adding further packages
- When using path aliases (e.g. `@/`) in TypeScript, add both the `paths` config and the vite alias — and verify with a build, not just the dev server

### Makefile / entrypoints

Every project must have:

```makefile
install   # set up venv, install deps, install any browser/tool binaries
run       # execute the main pipeline / entry point
dev       # start the dev server(s)
validate  # run the validation command; exit non-zero on failure
clean     # remove generated artifacts and temp files
```

---

## Step 5 — Verify and summarise

After all todos are completed:

1. Confirm the frontend (if any) builds without errors
2. Confirm the backend starts without import errors
3. Confirm the sample input files are in place
4. Tell the user what to do next (e.g. add API keys to `.env`, then run `make run`)
