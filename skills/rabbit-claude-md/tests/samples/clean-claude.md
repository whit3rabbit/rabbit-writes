# demo-project

CLI tool that converts fixture logs into per-run summaries for the demo suite.

## Commands

```bash
# Build the converter and run the unit battery
make build
make test-unit
```

## Conventions

- Two-space indent in YAML fixtures, tabs everywhere else.
- Branch names carry the ticket number first, then a short slug.

## Gotchas

- The converter reads stdin only when no file argument is given.
