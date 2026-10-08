# How we work together on Git

Two people, two folders: **backend/** (teammate) and **frontend/** (you). Because you rarely edit the same files, merge conflicts stay rare as long as everyone follows these rules.

## Branches
| Branch | Purpose |
|--------|---------|
| `main` | Always works. Only changed by pull request. |
| `develop` | Where finished features are combined and tested together. |
| `backend/<topic>` | Backend work, e.g. `backend/detection-api` |
| `frontend/<topic>` | Frontend work, e.g. `frontend/history-page` |

## Daily routine
```bash
git checkout develop && git pull          # start from the latest
git checkout -b frontend/history-page     # new branch for one piece of work
# ...work, then:
git add frontend/
git commit -m "frontend: add history page with delete"
git push -u origin frontend/history-page  # then open a Pull Request into develop
```

## Rules
1. **Stay in your folder.** Backend dev edits `backend/`, frontend dev edits `frontend/`. Anything else (`docs/`, `ml/`, root files) goes in its own small PR.
2. **The API contract is `docs/API.md`.** If an endpoint or JSON shape changes, update that file in the same PR and message the other person *before* merging.
3. **Pull requests, not direct pushes** to `main` or `develop`. The other person reviews (even a quick look).
4. **Small PRs.** One feature or fix per PR; merge often.
5. **Commit prefixes:** `backend:`, `frontend:`, `ml:`, `docs:`.
6. **Never commit secrets.** `.env` is ignored; add new variables to `.env.example` (without values).
7. **Migrations:** run `python manage.py makemigrations` and commit the generated files. Two people adding migrations to the same app? Pull first, and tell each other.
8. **Frontend can move first.** Keep `USE_MOCK: true` in `frontend/js/config.js` until the backend endpoint exists, then switch to `false` and test against the real API.

## Protect `main` (GitHub → Settings → Branches)
Require a pull request before merging, and require the "Backend CI" check to pass.
