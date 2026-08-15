# Quiet-mode execution policy

Quiet mode is active while the founder is using the development computer.

It changes execution scheduling, not product quality or acceptance gates.

## Resource limits

- One coding worker is active at a time.
- Independent reviews run sequentially only after a coherent slice is ready.
- No browser automation runs during source-only work.
- At most one browser process is used during an explicit UX checkpoint and is closed afterward.
- No test, type-check, production-build, and browser command runs concurrently with another heavy command.
- Focused tests run after each tracer slice.
- Full web and API suites run once per accepted implementation slice.
- The production build runs only at a coherent promotion gate.
- Long validation commands run at reduced process priority where the operating system supports it.
- Every locally started server, browser, and validation process is tracked and stopped when its evidence is captured.

## Pressure guard

Before a heavy command, inspect current memory pressure and the highest-CPU processes.

If the computer is already under material pressure, defer that command and continue with source, documentation, or test-design work.

The existing web and API servers may remain only while a live review needs them.

## Return to full-speed work

The founder will explicitly say when the computer is free.

At that point, builders may work in parallel, but local browser, test, and build commands remain serialized to prevent another process pile-up.
