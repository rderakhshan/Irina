# Skills

Each skill is a directory with a `SKILL.md` and optional assets or scripts:

```text
skills/
  release-notes/
    SKILL.md
  application/
    SKILL.md
    assets/cover_letter_template.tex
    scripts/finalize.py
```

Example `SKILL.md`:

```markdown
---
name: release-notes
description: Write concise release notes from git history.
---

# Release Notes

When asked for release notes:
1. Read commits since the last tag.
2. Group by feature, fix, and breaking change.
3. Keep each bullet under 120 characters.
```

## Skill rules

- The directory name is the skill ID (`A-Z a-z 0-9 . _ -`, max 64 characters).
- `description` is the only field shown in the system prompt.
- The full file loads only when the agent calls `use_skill("<name>")`.
- Skills are lower-trust instructions and cannot grant permissions.
- Files over 4,000 lines or 200,000 characters are ignored.
- Symlinks and invalid names are ignored.

On startup, the CLI uploads the complete skill directory, including assets and scripts, into the OpenShell sandbox and adds the catalog to the system prompt.

Use `--skills-dir` to point elsewhere, or `--skills-dir ""` to disable loading.

## Input files and artifact exports

Skills that need input files or produce artifacts use explicit transfers.

**There is no host filesystem mount inside OpenShell.** The sandbox cannot directly access arbitrary local host directories. Instead, Irina's trusted CLI host handles configured uploads and exports.

For example, to prepare an application and export the resulting files:

```powershell
uv run python main.py `
  --skills-dir .\skills `
  --input .\input-cv\resume.tex `
  --export application `
  --export-contents `
  --artifacts-dir "D:\Application" `
  --sandbox-image irina/irina-tools:1 `
  --mode yolo -p "Prepare the application"
```

The transfer options work as follows:

- `--input` uploads host files or directories into the sandbox's `input/` directory.
- `--export` identifies a workspace path to download from the sandbox on clean shutdown.
- `--export-contents` exports the contents of the specified directory rather than the directory itself.
- `--artifacts-dir` specifies the local host directory that receives exported files.
- `--sandbox-image` selects an approved image containing additional tools.

**Exporting does not require creating a ZIP or TAR archive.** The trusted CLI host can transfer configured workspace directories directly.

A successful file creation inside OpenShell is not the same as a successful export to the local machine. The export must be configured, and the host must complete the transfer.

## Application skill

The included `application` skill needs the TeX/Poppler/pypdf image described in [images/application](../images/application/README.md).

Its `SKILL.md` expects:

```text
input/
  resume.tex
  reference.pdf       # optional
  examples/           # optional
```

The application skill is responsible for preparing and validating application artifacts inside the sandbox.

Depending on the instructions in its `SKILL.md`, these may include:

- The original job description.
- A tailored cover letter in LaTeX.
- A compiled cover letter PDF.
- A compiled CV PDF.
- A merged application PDF.
- Compilation and validation results.

Final application files should be organized under the workspace path configured for export, for example:

```text
application/
  IFF/
    ...
```

When `--export application` is configured, the trusted CLI host can export that workspace directory on clean shutdown.

When `--export-contents` is also specified, the contents of `application/` are exported to the configured artifacts destination.

### Application skill: required export behavior

The following instructions should also be included in `skills/application/SKILL.md`, so Irina receives them when the skill is loaded:

1. **Prepare files in the exportable workspace.** Create the final application folder under `application/<application-name>/`, unless the task explicitly specifies another configured workspace path.
2. **Validate before finishing.** Complete the required compilation, merging, and quality checks before reporting the application as ready.
3. **Understand host-managed exports.** Irina's trusted CLI host supports exporting configured workspace paths to the user's local machine. The sandbox does not need direct access to host directories.
4. **Do not invent a manual download requirement.** Do not claim that the user must create or download an archive simply because the sandbox cannot directly access the host filesystem.
5. **Do not create unnecessary archives.** ZIP or TAR files are only needed when explicitly requested or required for another purpose.
6. **Do not claim export success prematurely.** Creating files inside the sandbox does not prove that the host has downloaded them.
7. **Report the correct status.** Clearly distinguish between an application prepared inside OpenShell, an application configured for export, and an application successfully exported.
8. **Explain missing configuration.** If export configuration is absent or unknown, tell the user that export can be enabled with `--export` and `--artifacts-dir`, or through the supported `.env` settings.
9. **Do not attempt to bypass OpenShell isolation.** Host file transfers must use the trusted CLI's supported mechanisms.

### Correct completion messages

When files are prepared but export status is unknown:

> The application files have been created and validated in `application/IFF/` inside the OpenShell workspace. Irina supports exporting this directory through the trusted CLI host. If `application` is configured as an export path, the files will be transferred to the configured local artifacts directory on clean shutdown. I cannot confirm that the host transfer has completed yet.

When export is not configured:

> The application files are ready inside `application/IFF/`. To transfer them to your local machine, configure `--export application` and `--artifacts-dir`, or the equivalent `.env` settings, for a run that performs the export. Creating a ZIP or TAR archive is not required.

When the trusted host has confirmed successful export:

> The application files were exported successfully to the configured local artifacts directory.

**Important:** The application skill creates and validates the artifacts. The trusted CLI host performs the configured transfer. Loading a skill does not itself enable export flags or grant host filesystem access.

## Skill drafts and promotion

Skills created or edited by Irina during a run are captured as drafts under:

```text
<state>/skill-drafts/<workspace-key>/
```

Review them before promoting:

```powershell
uv run python main.py skills list
uv run python main.py skills promote <name>
uv run python main.py skills discard <name>
```

Promotion refuses to overwrite an existing trusted skill unless `--force` is used.

This review gate prevents one run from rewriting the instructions for every later run.

## Environment configuration

For a flag-free launch:

```powershell
uv run python main.py
```

Set the corresponding values in the ignored `.env` file:

```dotenv
IRINA_SANDBOX_IMAGE=...
IRINA_INPUTS=...
IRINA_OPTIONAL_INPUTS=...
IRINA_EXPORT_PATHS=...
IRINA_ARTIFACTS_DIR=...
IRINA_AUTO_EXPORT=...
IRINA_MODE=...
```

Explicit CLI flags override the corresponding environment settings.

For automatic artifact export, ensure that the appropriate export paths, destination directory, and automatic-export behavior are configured.

### Important distinction

The application skill cannot retroactively enable an export that was not configured for the current run.

If a run finishes without an applicable export configuration, the files may remain in the sandbox workspace without having been transferred to the host.

Irina must never present sandbox file creation as proof of successful local export.

## Responsibility boundaries

| Component | Responsibility |
|---|---|
| `SKILL.md` | Defines how the agent performs the skill and prepares artifacts. |
| OpenShell sandbox | Executes skill instructions and holds generated workspace files. |
| Trusted CLI host | Uploads configured inputs and exports configured outputs. |
| `.env` / CLI flags | Configure paths, image, execution mode, and export behavior. |
| Skill draft promotion | Controls which newly created or modified skills become trusted. |

The intended workflow is:

**Configure transfers → Load skill → Generate artifacts in OpenShell → Validate outputs → Finish run → Trusted host exports configured paths.**

No additional download tool, archive mechanism, host mount, or new memory component is required.