# Changelog

All notable changes to `moderatorim-sdk` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) from `1.0.0` onward.

> **Pre-1.0:** the contract surface is unstable. Breaking changes may land in any `0.0.x` release
> and are noted here.

## [Unreleased]

## [0.3.0] — unreleased

### Added
- **`TableModel.acl`** — permission-based table-ACL base (e.g. `"core.session"`). When set,
  the store gate derives the required permission per op (`{acl}.read` for get/list/count;
  `{acl}.create|update|delete` for writes) and checks the caller's effective permissions —
  the same currency the route layer uses. Supersedes the op-blind role-tuple `role` field
  (retained, deprecated, one release). For the core-table-acl-hardening feature.
- **`ListCard` view descriptor** — a list rendered as one card per row (vs `ListView`'s
  table), with `ListCardField` (labelled facts, optional `datetime`/`browser` formatters) and
  `ListCardAction` (per-card buttons that POST to a fixed owner-declared route, role-gated,
  optional `confirm`/`variant`). `ListCard` carries an `id` (D5) so the same card list mounted
  in two places stays a distinct htmx swap target. Introduced for the sessions view.
- **View-object `id` (ARCHITECTURE D5)** — every element-rendering view descriptor (`ListView`,
  `FormList`, `FormView`, `FormTab`, `CalendarView`, `DashboardView`, `StatCard`, `ScoreCard`,
  `BarChart`) now carries an optional `id: str = ""`. When set, the engine renders it as the
  element's DOM id and uses it as the htmx swap target + CSS/test hook; when empty the engine keeps
  its per-context default. This makes multiple same-kind views on one page uniquely addressable
  (the general form of the cross-page list-search fix). Value-leaf descriptors (`ScoreBand`,
  `ListCardField`, `Filter`, `Field`, …) deliberately have no `id`.

### Changed / Deprecated
- **`FormList.region_id` → `id`.** `region_id` is renamed to the uniform `id` (above). The old
  `region_id=` keyword is still accepted for ONE release — it maps to `id` and emits a
  `DeprecationWarning`. Passing both `id` and `region_id` is an error. Migrate `FormList(region_id=…)`
  to `FormList(id=…)`.

### Added
- **Dashboard-visuals widget descriptors** — `MetricSource` / `SeriesSource` (a widget's table
  binding: `model` names the table like `PageView.model`, `filters` reuse the `Filter`/`FilterOp`
  grammar, `agg`/`group_by`/`bucket` shape the aggregate), plus `StatCard`, `ScoreCard` + `ScoreBand`
  (bounded-scale gauge with ordered threshold bands), `BarChart` and `DashboardView`. Server-rendered
  SVG, no JS charting lib; count-only v1 (sum/avg/min/max and a store-side group-by await a future
  `store.aggregate`). Core renders + resolves these in a follow-up. Also ships the `.mim-dashboard` /
  `.mim-statcard` / `.mim-scorecard` / `.mim-barchart` CSS (all CSS-variable colors).
- **`ModalView` + `ModalAction` + `ListView.select` + `FormTab.editor`** — modal set-editor. A
  `ModalView(view=…, label=…, actions=(ModalAction,…))` renders an inner view in a `<dialog>`; a
  `ModalAction` is like a `FormAction` but CLOSES the modal on completion (opener region refreshes).
  `ListView.select="multi"` renders a leading checkbox column (a set-editor) with `select_key`
  naming the submitted key column. A `FormTab.editor` is the ModalView opened by that tab's
  permission-driven Edit control (a fields tab leaves it None → Edit toggles form-edit mode).
  `FormTab.actions` are now the tab's more_vert OVERFLOW items, not primary buttons. `ModalView.rows` is an optional async resolver supplying the select-mode body's candidate rows (each with `_checked`).
- **`FormTab.actions` + `moderatorim.sdk.FormList`** — tabbed form sub-views: a `FormTab` may carry
  its own `actions` (per-tab header buttons, shown for the active tab), and a `FormList` child
  embeds a list of a RELATED model inside a tab (with a `region_id` for tab-scoped htmx refresh).
  `FormList.link` names the REF column on the related model pointing back at the parent table
  (``""`` = auto-detect the single such REF), so the embedded list scopes to the parent record via
  a reverse-REF relation. Enables master-detail forms — e.g. a role's Permissions tab listing its
  grants with an Add action that refreshes only that tab. Backward compatible: a tab with no
  `actions` and fields-only `views` renders as before.
- **`TableColumn.source`** — the owning unit's manifest name (default `None` = unattributed, NOT
  `"core"`). Core stamps it unconditionally from the declaring manifest at boot; app authors never
  set it. Enables app-owned-column tracking (additive migration, uninstall retire-the-view).
- **`FormView.save` + `moderatorim.sdk.FormSave`** — an optional save delegate (protocol with
  optional `create`/`update`/`delete`). When set, core routes a generated Form's mutations through
  it instead of the generic `ctx.store` write path — the seam for a resource whose create/update/
  delete must run domain logic (e.g. roles reconcile `core_role_permission` grants and refuse
  system-row mutation via `ctx.authz.define_role`/`delete_role`). None (default) keeps the generic
  store path, unchanged.
- **`moderatorim.ui.DataRowActions`** — a per-row action control for `DataTable`: a `more_vert`
  popup menu (BeerCSS, mirroring `DataColumns`) holding Edit + Delete, rendered into a right-fixed
  (sticky) actions column. Delete opens a per-row confirmation modal (`<dialog class="modal">`)
  whose confirm button carries the `hx-delete`, so a destructive action needs an explicit second
  click. Presentation-only; the caller supplies the record id, gate booleans, and display label.
- **`moderatorim.ui.Header`** — a generic BeerCSS app-bar component (`header>nav`) with `title` +
  `actions` + `leading` slots (and `class_`/`title_class` passthroughs a host uses for its own
  styling). Apps compose their own top bar: `Header("Members", actions=[Button("Invite")])`.
- **`moderatorim.ui` component library** — the single source of truth for the BeerCSS UI
  components, a top-level peer of `moderatorim.sdk`/`moderatorim.cli` (SDK-owned by convention;
  imports stdlib + SDK contracts only, never `moderatorim.core`). Both core and apps import their
  components from here, so there is one library to maintain instead of a core copy plus per-app
  re-implementations. Exposes the primitives (`tag`, `Raw`, `esc`, `attrs`, `Component`), the
  generic BeerCSS components (`Card`, `Button`, `Input`, `Select`, `Field`, `Alert`, `Avatar`,
  `Icon`, `Stepper`, `Row`/`Grid`/`Nav`, and `Header` — a generic app bar with `title`/`actions`/
  `leading` slots an app composes), and the shipped BeerCSS/MDC/base assets via `ui_asset_dir()` +
  `ui_asset_tags(base_url)` (a host mounts + references them; serving stays a host job).
  ModeratorIM-specific chrome (the nav rail, account menu, content-pane header, footer, screen
  headings, theme toggle) stays in core — `moderatorim.ui` holds generic BeerCSS components only.
- **Validation moved into the SDK** (`Validator`, `Required`, `MinLength`, `MaxLength`, `Min`,
  `Max`, `Pattern`, `Email`, `OneOf`, `PasswordPolicy`, `ValidationError`, `Result`,
  `validate_field`, `validate_form`, `build_validators`). Each validator renders HTML hints AND
  enforces server-side from one declaration; placing it with the field/model contract makes
  server-side enforcement run on the data path regardless of whether a UI is rendered (security by
  default). `moderatorim.ui.Input` renders an SDK `Validator`.

- **`moderatorim` scaffolding CLI** — a console command (`moderatorim.cli:main`) for authoring and
  growing units. Every command is **additive and never overwrites** existing source. Commands are
  grouped by `action_type` (the intent the verb expresses):

  | action | action_type | description |
  |---|---|---|
  | `create app <name>` | create-container | Scaffold a new flat app module in the current directory (manifest + README + tests, no packaging config). Flags: `--display-name` (alias `--name`) → `Manifest.display_name`, `--description` → README summary, `--version` → `Manifest.version` (default `0.0.0`). |
  | `generate model <domain>` (alias `g`) | operate-in-app | Write `<domain>/model.py` and register the model in the manifest's `models=(…)`. Repeatable `--field name:type` (`str`/`int`/`bool`) declares columns; the table name is `{app}_{domain}`. |
  | `generate service <domain>` | operate-in-app | Write `<domain>/service.py` — the domain's service stub. |
  | `generate routes <domain>` | operate-in-app | Write `<domain>/routes.py` — the domain's route registration. **App units only.** |
  | `generate view <domain>` | operate-in-app | Write `<domain>/view.py` — the domain's view/render stub. **App units only.** |
  | `generate test <domain>` | operate-in-app | Write `tests/test_<domain>.py` — the domain's test stub. |

  `create` states the unit **kind** explicitly (nothing exists to infer it from yet). `generate` runs
  **in the unit root** and reads the kind from `./manifest.py` (`Manifest.type`), which **gates the
  valid artifacts**: apps allow all five, backends/platforms allow only `service`/`test` (`routes`/
  `view` are refused with a kind-specific message).
- **`CacheStore` port** — a narrow ephemeral key/value cache contract
  (`get`/`set(ttl=)`/`delete`/`incr`/`expire`/`exists`, string values) that the core caches
  against. Backed by an in-memory default or Redis (chosen by the core from configuration, not the
  setup wizard); the port lives in the SDK so it is a frozen contract a third party can implement.

### Changed
- **Breaking:** `Manifest.default_roles` renamed to `Manifest.roles`.

## [0.2.0] — 2026-09-25

### Added
- `Manifest.system_users` — a unit declares system-user principals (`{app}.{user_name}` → groups)
  that the core seeds for userless (webhook / cron / boot) execution.

### Documentation
- `Model.table` prefix is documented as **mandatory, developer-declared, and boot-validated**
  (`{unit}_{name}`), rather than auto-generated.
- Added a uniform release-notes format: `.github/release.yml` categorizes auto-generated notes by
  PR label, paired with a `RELEASING.md` human-summary template.

## [0.1.0] — 2026-09-24

### Added
- Initial contract kernel, extracted from the ModeratorIM core:
  - `models` — `Model`, `Field`/`FieldType` (+ `ref`/`enum`/`list_of`), `Extends`,
    `ResolvedSchema`/`ResolvedColumn`.
  - `datastore` — the `DataStore` port + `Filter`/`FilterOp`.
  - `bus` — `Event`/`EventKind`, `Action`/`ActionKind`, `EventBus`.
  - `registry` — `Manifest` (with the `routes` hook), `UnitType`, `NavEntry`.
  - `web` — the `App` routing facade + `Ctx`/`Page`/`Fragment`/`Rendered`/`redirect`.
- Domain-driven folder layout mirroring core; flat public API via `from moderatorim.sdk import ...`.
