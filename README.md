# ModeratorIM SDK

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/ModeratorIM/sdk/releases)
[![CI](https://github.com/ModeratorIM/sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/ModeratorIM/sdk/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

The **ModeratorIM SDK** — the contract kernel you build ModeratorIM apps against.

> **Pre-1.0:** the contract surface is still moving. Expect breaking changes between `0.0.x`
> releases until it stabilizes.

## What it is

An app depends on **this package alone** — never the ModeratorIM core runtime. The SDK gives you
the types you author with:

```python
from moderatorim.sdk import Manifest, UnitType, NavEntry, App, Ctx, Page, redirect, Model, Field
```

At runtime, the ModeratorIM core implements these contracts and hands your handlers a live `Ctx`
(the data store, the current user, a permission check) — so your app reaches core's behavior
**without importing core**. This is the same shape as VS Code extensions, Backstage plugins, or
OpenTelemetry's API/SDK split: a small public contract package both the runtime and the plugins
depend on.

`moderatorim` is a shared namespace — this package provides `moderatorim.sdk` (the contract
kernel), `moderatorim.cli` (the scaffolding command), and `moderatorim.ui` (the component
library); the core runtime provides `moderatorim.core`. Installing this SDK does **not** install
the core runtime.

## Scaffolding CLI

Installing the SDK also installs the `moderatorim` command — it scaffolds apps so the conventions
the runtime validates (the flat module layout, the `{app}_` table prefix, manifest registration,
importing only the SDK) are correct by construction.

**Create an app** — runs in any directory, creates `./<name>/`:

```bash
moderatorim create app my_shop --display-name "My Shop" --description "A storefront app"
```

produces a flat app module:

```
my_shop/
  __init__.py        # exposes `manifest`
  manifest.py        # Manifest(name="my_shop", type=UnitType.APP, …)
  README.md
  tests/test_manifest.py
```

**Generate domain components** — run from inside the app (its directory holds `manifest.py`). The
argument names a **domain**; each component lands in that domain's package, so apps fold by domain:

```bash
cd my_shop
moderatorim generate model products --field title:str --field price:int
moderatorim generate service products      # -> products/service.py
moderatorim generate routes products       # -> products/routes.py
moderatorim generate view products         # -> products/view.py
moderatorim generate test products         # -> tests/test_products.py
```

`generate model` also declares the table as `my_shop_products` and registers the model in the
manifest. Field types: `str` / `int` / `bool` / `float` / `text` / `datetime`. `generate` is
aliased `g`. Backends and platforms have no web surface, so `routes`/`view` are only offered in
an app. The commands only ever add files (and one manifest line for a model) — they never overwrite
existing source.

## Install

```bash
pip install moderatorim-sdk   # once published
# or, from source:
pip install git+https://github.com/ModeratorIM/sdk.git
```

## What's in it

| Domain | Contents |
| --- | --- |
| `models` | `Model`, `Field`/`FieldType`, `Extends`, `ResolvedSchema` |
| `datastore` | the `DataStore` port, `Filter`/`FilterOp` |
| `bus` | `Event`/`EventKind`, `Action`/`ActionKind`, `EventBus` |
| `registry` | `Manifest`, `UnitType`, `NavEntry` |
| `web` | the `App` router facade, `Ctx`, `Page`, `Fragment`, `redirect` |

It is **contracts only** — no runtime, no I/O, no heavy dependencies.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and
[SECURITY.md](SECURITY.md). Changes are tracked in [CHANGELOG.md](CHANGELOG.md); versioning + deprecation + core/SDK compatibility rules are in [VERSIONING.md](VERSIONING.md).

## License

[AGPL-3.0-or-later](LICENSE). ModeratorIM is dual-licensed (AGPL-3.0 + a commercial license); see
the main project for details.
