# Opik local setup (Windows)

Opik provides the local tracing and evaluation UI used by this project. It runs
with Docker Compose. The start script is discovered from the repository-root
checkout (`opik/opik.ps1`), falling back to the vendored copy at
`src/back/opik`. Override with `IRINA_OPIK_HOME`.

## Automatic lifecycle

With `IRINA_OPIK_ENABLED=1`, Irina manages the stack at startup:

- a healthy stack is **reused** (no restart, traces continue in the same project);
- a stopped stack is **started** and polled until healthy;
- a listening but unhealthy stack gets **one** stop/start recovery attempt;
- any failure is **fail-open**: Irina runs with tracing disabled and prints one
  warning;
- `IRINA_OPIK_RESTART=1` forces one stop/start on the next run (data volumes are
  preserved; `--clean` is never used).

Relevant variables:

```powershell
$env:IRINA_OPIK_ENABLED="1"
$env:IRINA_OPIK_HOME="D:\AI Engineering LAB\Irina\opik"  # optional
$env:IRINA_OPIK_URL="http://localhost:5173/api"          # optional
$env:IRINA_OPIK_START_TIMEOUT="120"                      # optional, seconds
```

The Python SDK is loaded from the checkout's `sdks/python/src`; no `pip install
opik` is required. A checkout directory named `opik` at the project root would
otherwise shadow the package, so Irina imports it explicitly.

## Manual start

```powershell
Set-Location opik
powershell -ExecutionPolicy Bypass -File .\opik.ps1
```

## Windows PowerShell 5.1 note

The upstream `opik.ps1` is UTF-8 without a BOM. Windows PowerShell 5.1 reads
BOM-less scripts with the system code page, which can break the box-drawing and
emoji characters. Irina's automatic lifecycle adds the BOM before the first run.
For manual runs, use PowerShell 7+:

```powershell
pwsh -ExecutionPolicy Bypass -File .\opik.ps1
```

Or re-save `opik.ps1` as UTF-8 with a BOM:

```powershell
$p = ".\opik.ps1"
$b = [IO.File]::ReadAllBytes($p)
[IO.File]::WriteAllBytes($p, [byte[]](0xEF, 0xBB, 0xBF) + $b)
```

Then run it with Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\opik.ps1
```

## Common commands

```powershell
powershell -ExecutionPolicy Bypass -File .\opik.ps1            # start full stack
powershell -ExecutionPolicy Bypass -File .\opik.ps1 --infra    # infrastructure only
powershell -ExecutionPolicy Bypass -File .\opik.ps1 --verify   # health check
powershell -ExecutionPolicy Bypass -File .\opik.ps1 --stop     # stop services
```

Back to the [project README](../README.md). For upstream Opik documentation,
see [src/back/opik/README.md](../src/back/opik/README.md).
