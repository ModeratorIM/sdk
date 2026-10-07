# Changelog

All notable changes to `moderatorim-sdk` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) from `1.0.0` onward.

> **Pre-1.0:** the contract surface is unstable. Breaking changes may land in any `0.0.x` release
> and are noted here.

## [Unreleased]

### Added
- **`TableColumn.secret`** — a UI-masking flag: a secret column renders as a password input whose
  stored value is never echoed back (blank submit = leave unchanged). Distinct from `encrypt`
  (at-rest storage). Used by the platform Authentication tab's credential fields. The catalog of
  common named credential fields that reuse this flag lives in CORE (the platform table's concern),
  not in the SDK manifest. `PlatformCapabilities.credentials` accepts a `TableColumn` (an adapter's
  own auth field) alongside the legacy `str` / `(key, secret)` forms.
- **`GridView`** — a `ListView` rendered as a grid of cards instead of a table: same semantics
  (`fields`/`search`/`sort`, table-backed), different UI. A card-click navigates to the record
  (`{base}/{id}`) like a clickable list row — no built-in picker/Continue (any add control is an
  ordinary `FormAction`). Dispatched by `PageView`/`ViewRoute` as a new `Kind.GRID`; core supplies
  the query→render handler. Used for the platform catalog's card view.
- **`ListView.row_clickable`** — opt a READ-ONLY list's rows back into navigation. A read-only list
  (`enable_actions=False`) normally has non-clickable rows (its generated form routes don't exist);
  set this True when the list DOES have a destination form at `{base}/{id}` (e.g. the platform
  catalog → per-platform FormView) so a row-click navigates there while Edit/Delete/New stay
  suppressed. Honours read permission; ignored on actionable or `multiselect` lists.
  Backward-compatible (`False` default). Pairs with a core `render_list` branch.
- **`FormView.edit_only`** — suppress the generated `GET {base}/new` blank-create form AND the
  `POST {base}` create route for a FormView whose "add" entry point is a SIBLING view (e.g. a
  discovery picker) that owns `{base}/new` itself. The form then expands only its edit/mutate
  routes (`{base}/{id}` GET/PATCH/DELETE), so a sibling route at `{base}/new` no longer collides
  with the form's auto-generated create route. Backward-compatible (`False` default keeps the full
  RESTful expansion). Used by the platform catalog, whose `/platforms/new` is the adapter picker.
- **`ListView.href`** — an optional custom path for the toolbar "New" button. When set, New
  navigates there instead of the generated `{base}/new` CRUD form — the entry point for a read-only
  catalog (`enable_actions=False`) whose "add" flow is a bespoke route (e.g. the platform catalog's
  `/platforms/new` picker). Renders independently of `enable_actions` but still honours the
  create-permission gate; never shown on an embedded list. Backward-compatible (`""` default keeps
  generated behaviour). Pairs with a core `render_list` branch.
- **`FormHtml`** — a `FormTab` child that renders bespoke pre-rendered HTML supplied by the handler
  via `subview_data[tab_index]` (the inline-data seam `FormList` already uses). For a tab whose
  content the model-driven renderer cannot express — e.g. a key/value satellite editor (platform
  credentials) rather than the record's own columns. Pairs with a core `render_form` branch that
  places it. Backward-compatible (pure addition).
- **`PlatformCapabilities` + `Manifest.platform`** — a `UnitType.PLATFORM` adapter declares its
  platform-registry capability catalog (auth/ingest shape + event/signal/action/credential tuples)
  as DATA on its manifest, via the optional `platform: PlatformCapabilities | None` field. Core
  reads it off a discovered platform manifest and seeds the registry rows ONLY when an operator ADDS
  the platform (Model B — no boot-time self-seed). `auth_type`/`ingest_mode` are enum-value strings
  so the SDK carries no dependency on core's enums. `None` for non-platform units and for a platform
  with no capabilities yet — zero impact on existing manifests.
- **`operators_for` / `is_filterable` / `FIELD_TYPE_OPERATORS`** — the `FieldType` → operator-token
  vocabulary, lifted to the public surface as the single source of truth. Core's query builder and
  view renderer already derived condition operators from a column's type; this exposes the same
  table so an app building a condition UI (a no-code rule/Designer surface) derives its operator
  pickers from the SDK instead of re-deriving the mapping (a silent-divergence hazard). The token
  strings are abstract (`eq`/`lt`/`contains`); mapping a token onto a concrete store `FilterOp`
  stays the consumer's concern. Backward-compatible (pure additions).
- **`Manifest.api_version`** — optional provider API version a unit's declared capabilities target
  (e.g. a platform adapter publishing against Telegram Bot API 7.0 sets `api_version="7.0"`).
  Distinct from `version` (the unit's own package SemVer): an adapter bugfix release bumps `version`
  without touching `api_version` when the provider contract is unchanged. Backward-compatible
  (default `""` = no provider API; apps and unversioned/send-only platforms leave it empty). The
  platform registry stamps seeded capability rows with it so multiple provider API versions coexist.
- **`ChoiceReference.where`** — optional equality filters `((column, value), ...)` scoping which
  rows a dynamic CHOICE offers (e.g. `where=(("active", True),)` to offer only active catalog rows).
  Backward-compatible (default `()` = no filter); the consuming sink applies it at resolve + save.

### Fixed

- **Filter value controls are no longer `required`** — a `DataFilterCondition`'s value input is
  built via `render_column`, which propagated the column's own `required` (and its implied
  `Required` validator) into the control. For a filter over a required storage column (e.g. a
  default `id`/`code` field) this emitted `<input required>` with an empty value; on a page whose
  active form submits, the browser rejected the submit with *"An invalid form control with
  name='…' is not focusable"* because the empty required input lives on a hidden tab. `render_column`
  now takes an optional `required` override, and the filter condition passes `required=False` (also
  dropping the implied `Required` validator), so a filter value is always optional. Affects every
  embedded list with a filter builder (admin forms + the platform capability tabs).
- **FormView block spacing** — consecutive `FormFields` grids (`.mim-form-grid`) are now separated
  by `margin-bottom` (the grid's own `gap` only spaced fields WITHIN a block, so two stacked blocks
  — e.g. a paired name+platform row then a full-width description — rendered flush together).

## [0.3.0] — unreleased

### Removed
- **`Manifest.store_metadata` and `Manifest.system_users`** (SDK cleanup G1) — two stale
  forward-declared fields with no reader anywhere (src or tests) and no unit declaring them.
  `store_metadata` was never consumed; `system_users` described a boot-seeding path that was never
  built. Both removed. **Kept** after verification: `provides` (load-bearing in the backend-contract
  test — it drives the capability↔adapter check) and `subscriptions` (wired at boot in core's
  registry). A unit still constructing these two now raises `TypeError`; none did.

### Changed
- **`FieldChoice` → `Choice`, `ChoiceSource` → `ChoiceReference`, and `TableColumn.choices_source`
  folded into `choices`** (breaking) — the static pick-list option is now `Choice`; the dynamic
  options source is now `ChoiceReference` and gains an optional `label_column` (store one column's
  value, show another's — e.g. store a language `code`, show its `name`). `TableColumn` no longer
  has a `choices_source` field: the single `choices=` field accepts EITHER a `tuple[Choice, ...]`
  (static) OR a `ChoiceReference(...)` (dynamic), enforced as "one or the other" in
  `__post_init__`. Migrate `FieldChoice(...)` → `Choice(...)` and
  `choices_source=ChoiceSource(...)` → `choices=ChoiceReference(...)`.
- **Config descriptors are now keyword-only** (SDK cleanup G2) — the big declarative "config bag"
  descriptors (`ListView`, `FormView`, `FormTab`, `FormList`, `FormFields`, `FormAction`,
  `StatusBadge`, `ListCard`, `ListCardAction`, `ListCardField`, `ModalView`, `ModalAction`,
  `PageView`, `ViewModel`, `CalendarView`, `ViewExtension`, `FormOverview`, `PageRoute`,
  `StatCard`, `ScoreCard`, `BarChart`, `MetricSource`, `SeriesSource`, `DashboardView`,
  `Manifest`) are built with `@dataclass(kw_only=True)`, so every field must be passed by name
  (`FormView(tabs=…)`, never `FormView(…)` positionally). Invisible to existing keyword call sites;
  positional construction now raises `TypeError`. Ergonomic value objects keep their positional
  first argument (`Field("name")`, `Locale("en")`, `Route(path, …)`, `Translation(key, …)`,
  `ScoreBand(50, "At risk", …)`, `Action(…)`, `NavEntry(…)`, …) and are deliberately left as-is.

### Internal
- **`views/descriptors.py` → `views/descriptors/` package** (SDK cleanup G3) — the ~851-line module
  is split into cohesive modules (`common`/`list_`/`form`/`view`/`route`/`dashboard`), re-exported
  from the package `__init__`. Pure refactor: every public symbol and import path
  (`from moderatorim.sdk.views.descriptors import …`) is unchanged; the public-API snapshot is
  identical. Sibling type references are `TYPE_CHECKING`-only (lazy via future annotations).

### Added
- **i18n declaration contract** — `Locale(code)`, `Translation(key, language, value)`, and
  `TranslationSet(source, dir, entries)` descriptors (a unit DECLARES translatable strings; core's
  engine RENDERS them). `TranslationSet(dir=...)` reads `translations/languages/{code}.json`
  catalogs; `Manifest.locales` declares the languages a unit ships; `Ctx.lang` + `Ctx.t(key,
  **params)` expose the active locale and the translate callable on the request context (engine in
  core). First piece of the i18n feature (Stage 1).
- **`ChoiceSource`** — a render-time options source for a `FieldType.CHOICE` column. Where
  `FieldChoice` is a static pick-list, `ChoiceSource(model, column)` sources a CHOICE field's
  options from the DISTINCT values of a column on an existing table, resolved by core when the form
  renders and validated strictly server-side. For "pick from the values that already exist" fields
  (e.g. a role's `source` picked from the distinct `app` values in the permission catalog) so a
  free-typed value cannot introduce a typo. A CHOICE column now takes **either** `choices` **or**
  `choices_source` (not both, not neither).
- **`FormList.enrich`** — optional ``async (ctx, rows) -> None`` hook on an embedded form list,
  applied by core after the rows are fetched and before render, so a view's ``Field.custom`` cell
  can show a computed value (e.g. a membership's derived role names). For the admin-users-form
  read-only Roles tab.
- **`StatusBadge` form-header chip** — `StatusBadge(label, field, mapping, default, order)`, a
  presentation-only, read-only status chip declared on `FormView.badges`. Reflects a record column
  (`field`) via `mapping` of value → `(text, variant)` where `variant` ∈ `success`/`neutral`/`warn`/
  `danger` is a theme token (not a colour); core renders it beside the Edit button. For the
  admin-users-form feature (Verification / MFA status).
- **View override-facet rule** — `assert_valid_override(delta)` plus `OVERRIDABLE_FACETS`
  (`label`/`help`/`display`/`read_only`/`active`) and `INHERIT_ONLY_FACETS` (`relation`/`choices`/
  `required`/`unique`/`max_length`/`encrypt`/`default`/`source`). A view may re-skin a column it
  references but not redefine its storage shape; a `ViewModel` override that sets an inherit-only
  facet fails loud. Consumed by the core view-column resolver. For view-column-resolution R4.
- **Implicit audit columns** — `CREATED_AT_FIELD` / `CREATED_BY_FIELD` / `UPDATED_AT_FIELD` /
  `UPDATED_BY_FIELD` constants, and these four names reserved on `TableModel` (a model declaring
  one fails loud). The core schema resolver injects them on every table beside `id`/`deleted_at`
  (`created_*`/`updated_*`: DATETIME; `*_by`: TEXT user-id, `""` = system), set by the write path,
  never client-settable. For the view-column-resolution feature.
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

### Removed
- **`FieldType.ENUM` and the `enum()` constructor** — folded into `FieldType.CHOICE` /
  `FieldChoice` / `choice()` (above). Stored values are unchanged (`CHOICE` stores the same
  text), so no data migration; declarations migrate `enum("x", "a", "b")` →
  `choice("x", FieldChoice(value="a", label="A"), FieldChoice(value="b", label="B"))`.

### Changed / Deprecated
- **`FormList.region_id` → `id`.** `region_id` is renamed to the uniform `id` (above). The old
  `region_id=` keyword is still accepted for ONE release — it maps to `id` and emits a
  `DeprecationWarning`. Passing both `id` and `region_id` is an error. Migrate `FormList(region_id=…)`
  to `FormList(id=…)`.

### Added
- **`FieldType.CHOICE` + `FieldChoice` + `choice()`** — a structured static pick-list field,
  replacing the string-only `ENUM`. `TableColumn.choices` is now a `tuple[FieldChoice, …]` where
  each `FieldChoice(value, label, name="", active=True, order=0)` separates the STORED `value` from
  the shown `label` (so a label renames without touching rows), carries a stable machine `name`
  (defaults to `value`), an `active` flag to retire an option without a data migration, and an
  `order` for dropdown sorting. Stored as `text` (the `value`), like the old ENUM. `choice(name,
  *FieldChoice, …)` is the convenience constructor. The `<select>` widget shows `label`, submits
  `value`, hides inactive options from new input (but still renders an already-stored inactive
  value on edit), and `column_validators` emits `OneOf` over the active values.
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
