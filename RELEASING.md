# Releasing (maintainers)

How we cut `moderatorim-sdk` versions. What the version numbers PROMISE consumers is in
[VERSIONING.md](VERSIONING.md); this page is the internal process that produces them.

## Conventional Commits drive the bump

Commits — and, because we **squash-merge**, **pull-request titles** — follow
[Conventional Commits](https://www.conventionalcommits.org):

| Type | Example | Bump |
| --- | --- | --- |
| `fix:` | `fix: reject an empty ENUM choices tuple` | PATCH |
| `feat:` | `feat: add a DATE field type` | MINOR |
| `feat!:` / `fix!:` / a `BREAKING CHANGE:` footer | `feat!: drop the deprecated Ctx.request escape hatch` | MAJOR (pre-1.0: MINOR) |
| `chore:` `docs:` `refactor:` `test:` `ci:` `style:` `build:` `perf:` | `docs: clarify the Manifest.routes hook` | none |

> **Squash-merge caveat.** Squash means the only commit that reaches `main` is the squash commit,
> whose message is the **PR title** — so the **PR title** determines the version bump. A CI check
> (`.github/workflows/pr-title.yml`) enforces a valid Conventional-Commit title. A PR mixing an
> addition and a break takes the strongest type (`feat!:`).

## The mechanical guard

`tests/test_public_api.py` snapshots the exact `moderatorim.sdk.__all__` set. Any add/remove trips
it — forcing a conscious version + CHANGELOG decision before merge. Combined with the PR-title lint,
"you changed the contract" mechanically becomes "the version and changelog reflect it."

## Cutting a release

1. The single source of version truth is `version` in `pyproject.toml`.
2. Every PR that changes the public surface adds a `CHANGELOG.md` entry under `[Unreleased]`,
   classified Added / Changed / Removed / Deprecated / Fixed.
3. To release: bump `version`, rename the CHANGELOG `[Unreleased]` section to `X.Y.Z` + date, tag
   `vX.Y.Z` on `main`, push the tag. (CI publishes the tag once a publish workflow exists.)
4. On a pushed `v*` tag, the `publish-docs` workflow regenerates the SDK API + CLI reference
   Markdown (from docstrings and the CLI parser) and opens a pull request into the docs repo
   (`ModeratorIM/docs`) with the refreshed `sdk/sdk/reference/` and `sdk/cli/reference/` trees.
   The generated Markdown is a build artifact — never hand-edited; to change it, fix the source
   docstrings / CLI help here and re-release. Requires the `DOCS_PUBLISH_TOKEN` repo secret (a
   token that can push a branch and open a PR in the docs repo). It can also be run manually via
   `workflow_dispatch` to test the wiring before a real tag.
5. **(Planned)** `release-please` will read the merged Conventional-Commit PR titles, compute the
   next version, update the CHANGELOG, and open a release PR — deferred until the first tagged
   release; until then, bump by hand per the table above.

## Release notes — uniform format

Every GitHub Release follows the same shape so a reader knows at a glance **what the release is**:

```markdown
## <one-line summary of what this release delivers>

<1-3 sentences: the theme of the release and who it affects. For a pre-1.0 release, restate the
"contract not yet stable - expect breaks in 0.x minors" note.>

**Install:** `pip install git+https://github.com/ModeratorIM/sdk.git@vX.Y.Z`

<!-- the categorized change list below is AUTO-GENERATED from merged PR labels; do not hand-write it -->
```

- The **top block (summary + theme + install)** is written by the releaser - it is the human "what
  is this" that a changelog of PR titles can't convey.
- The **change list below it is generated**, not hand-written: GitHub's "Generate release notes"
  groups the merged PRs by label into the sections defined in
  [`.github/release.yml`](.github/release.yml) (Breaking -> Features -> Fixes -> Documentation ->
  Maintenance -> Other). This is why PRs must be labelled (see CONTRIBUTING).
- Producing it: `gh release create vX.Y.Z --generate-notes --notes "<the top block>"` (the
  `--generate-notes` appends the categorized list under your summary).

## Deprecating a public thing

Follow the window promised in [VERSIONING.md](VERSIONING.md): mark it deprecated first (docstring +
CHANGELOG `Deprecated` + a `DeprecationWarning` naming the replacement and the removal version),
then remove it no earlier than the next MAJOR (pre-1.0: next MINOR), never in a PATCH.

## Core ↔ SDK compatibility

The SDK and the core runtime version **independently** (Terraform / OpenTelemetry-style). Core (and
every app) pins a compatible SDK range (e.g. `moderatorim-sdk>=0.4,<0.5`). An SDK **MAJOR** bump
(pre-1.0: **MINOR**) requires a **coordinated core release** that widens the pin in the same change
set — core must never be published against an SDK range it has not been tested with. A compatibility
matrix (SDK × core) is added once there is more than one line to track.
