# Wait-Pattern Rules

When a script polls for a service to become ready (Spring Boot startup, container health, migration finish, etc.), the wait pattern itself can silently fail and burn human attention. This rule captures concrete patterns that are reliable + ones that are NOT.

## The bug we hit

```bash
# BROKEN — minutes silently stuck
until docker logs --tail 30 {service-container} 2>&1 \
        | grep -qE "Started Application|Tomcat started"; do
  sleep 4
done
```

**Root cause:** `--tail 30` is a **sliding window**. The first poll *might* see the success line within the last 30 lines. But within seconds, scheduled-task logs (DB poll, outbox check, etc.) push the success line out of the tail-30 window. The loop then scans newer tails forever — the success signal already happened, but it's gone from the window.

**Symptom:** `docker ps` shows the container `Up N minutes` (healthy), the service IS ready, but the wait loop never returns. The user waits a long time thinking the service is still booting.

## Reliable wait patterns (pick by use case)

### 1. HTTP health probe — most reliable

```bash
until curl -fsS http://localhost:{PORT}/actuator/health 2>/dev/null | grep -q '"status":"UP"'; do
  sleep 4
done
```

Tests **actual readiness**, not log pattern. Spring Boot Actuator (or equivalent) exposes a deterministic endpoint. If 200 + body says UP, service is ready. End of story.

For Go services, expose a `/healthz` endpoint that returns 200 only after migrations + dependency checks pass.

### 2. Container healthcheck — when service has HEALTHCHECK in Dockerfile

```bash
until [ "$(docker inspect -f '{{.State.Health.Status}}' {service-container})" = "healthy" ]; do
  sleep 4
done
```

Idiomatic. The Dockerfile / compose owns the readiness contract; your script just consults Docker's health view.

### 3. No `--tail` clamp — when log signal is the only option

```bash
until docker logs {service-container} 2>&1 | grep -q "Started Application"; do
  sleep 4
done
```

Drops the sliding-window bug. Scans **all** log history. Slower as logs grow but reliable. Use when no health endpoint exists.

### 4. `--since RESTART_TS` — bounded log scan

```bash
ts=$(docker inspect -f '{{.State.StartedAt}}' {service-container})
until docker logs --since "$ts" {service-container} 2>&1 | grep -q "Started"; do
  sleep 4
done
```

Pin scan to the most recent restart. Won't grow unbounded; won't miss old signal.

## Anti-patterns to avoid

- `docker logs --tail N` for **completion-signal grep** — N is a sliding window; will miss signals that scrolled out
- `tail -f log | grep` without timeout — backgrounded, hard to clean up
- Polling with no max iteration count — silent stuck on bad pattern
- Polling with `sleep` < 1s — burns CPU; 4s is fine for service startup
- Pattern on a string that's part of a normal log (`error` matches `error_message: null`) — be specific; quote full messages

## Always include a heartbeat + max timeout

```bash
for i in $(seq 1 60); do
  if curl -fsS http://localhost:{PORT}/actuator/health 2>/dev/null | grep -q UP; then
    echo "ready after $((i*4))s"
    break
  fi
  sleep 4
  [ $((i % 10)) -eq 0 ] && echo "still waiting... ($((i*4))s elapsed)"
done
[ $i -eq 60 ] && { echo "FAIL: not healthy in 240s"; exit 1; }
```

- **Visible heartbeat** every 40s (i % 10) — user sees life
- **Hard timeout** at 60 iterations × 4s = 240s — fails loud
- **Exit code** signals failure to caller

## Lesson learned

When a wait script gets stuck, **don't trust the wait condition**. Run `docker ps` / `curl health` directly to verify whether the service is ALREADY ready and the wait pattern is buggy, OR genuinely still booting.

**A long silent stuck is a bug in the wait pattern, not the service.**

## See also

- `agents/test-builder.md` — for Playwright test wait/expect patterns
- Docker docs: HEALTHCHECK Dockerfile directive
- Spring Boot Actuator: `/actuator/health`
