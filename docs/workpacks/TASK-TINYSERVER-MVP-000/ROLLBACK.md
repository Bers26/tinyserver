# TASK-TINYSERVER-MVP-000 — Rollback

## General rule

Rollback must match task risk.

```text
docs-only change -> revert commit
code change -> revert commit + rerun tests
runtime wiring -> disable new registry entry + verify previous streams still run
deploy -> separate rollback task with explicit pre-state
```

## Docs-only rollback

```text
git revert <commit>
git diff --check
git push
```

## Framework contract rollback

If `tiny-agent-framework` numeric semantics causes conflict:

```text
revert framework docs/spec commit
remove or update tinyserver adoption reference
record reason in project-log/ERRORS.md or DECISIONS.md
```

## Collector rollback

If collector implementation fails after merge but before runtime adoption:

```text
revert collector commit
run tests
verify registry unchanged
```

If collector was wired into runtime:

```text
disable collector in registry
restore previous registry file
run full registry proof for previous known-good streams
commit rollback notes
```

## Runtime rollback

Before runtime wiring, record:

```text
registry path
modules dir
latest snapshot paths
history paths
timer/service state
current git HEAD
```

Rollback must restore previous registry/module state before claiming success.

## Forbidden rollback shortcuts

```text
no history rewrite on main without explicit approval
no deleting evidence logs
no removing project-log errors because they are ugly
no touching secrets or env during docs rollback
```
