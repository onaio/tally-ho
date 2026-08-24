# Agent guidance

Conventions for automated agents working in this repository. Keep entries
evergreen — describe the rule and its rationale, not the change that
introduced it.

## Comments

- **Never write a `#` comment in a code file.** Code is self-documenting;
  a comment explaining it is a signal to rename something or split a
  function, not to annotate it. This covers every non-Markdown file.

- **Keep docstrings short.** A docstring earns its place only by carrying
  what the code cannot. Remove anything determinable by reading the code,
  anything not evergreen, and any reference to how the code used to
  behave or why it changed.

- Rationale that is genuinely worth recording — a security boundary, a
  cross-system constraint, a decision and its alternatives — belongs in
  `docs/`, where it can be read whole instead of in fragments.

## Migrations

- **Never write a migration that makes application code required to stay
  importable.** A migration must not reference a module-level callable
  (e.g. an `upload_to` / `default` function) by import path, because
  Django imports every migration module to build its history — so that
  callable can never be deleted or moved without breaking `migrate` and
  `makemigrations`, long after the field it served is gone.

  Prefer a value that carries no code dependency:
  - For `upload_to`, use a string path. If a dynamic path is genuinely
    needed, compute it in the model's `save()` (or a signal) rather than
    a callable the migration will pin forever.
  - For `default`, use a literal, or a stdlib callable already imported
    by Django's migration serializer (`dict`, `list`), not a project
    function.

  When a migration would otherwise reference a project callable, the
  callable outlives its usefulness as dead code kept alive solely for the
  migration graph. Avoid creating that debt in the first place.
