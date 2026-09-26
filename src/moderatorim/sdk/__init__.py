"""ModeratorIM app SDK — the contract kernel external apps build against.

An app imports ONLY from this package (``from moderatorim.sdk import Manifest, Model, ...``); it
never imports ``moderatorim.core``. Core implements these contracts and injects live handles (the
``Ctx``) at runtime, so an app reaches core's behavior without depending on it.

``moderatorim`` is a PEP 420 namespace shared with ``moderatorim-core`` — this package owns only
``moderatorim.sdk``.
"""

from moderatorim.sdk.bus import (
    Action,
    ActionKind,
    Event,
    EventBus,
    EventKind,
    Handler,
)
from moderatorim.sdk.cachestore import (
    CacheStore,
)
from moderatorim.sdk.datastore import (
    DataStore,
    Filter,
    FilterList,
    FilterOp,
    Record,
    RecordList,
)
from moderatorim.sdk.models import (
    ID_FIELD,
    SOFT_DELETE_FIELD,
    Extends,
    FieldType,
    ResolvedColumn,
    ResolvedSchema,
    TableColumn,
    TableModel,
    enum,
    listref,
    ref,
    text,
)
from moderatorim.sdk.registry import (
    AuthMethod,
    Manifest,
    NavEntry,
    UnitType,
)
from moderatorim.sdk.validation import (
    Email,
    Max,
    MaxLength,
    Min,
    MinLength,
    OneOf,
    PasswordPolicy,
    Pattern,
    Required,
    Result,
    ValidationError,
    Validator,
    build_validators,
    validate_field,
    validate_form,
)
from moderatorim.sdk.web import (
    App,
    Ctx,
    Fragment,
    Kind,
    Page,
    Redirect,
    Rendered,
    RouteDef,
    redirect,
)

__all__ = [
    # models
    "TableModel",
    "TableColumn",
    "FieldType",
    "Extends",
    "ResolvedColumn",
    "ResolvedSchema",
    "ID_FIELD",
    "SOFT_DELETE_FIELD",
    "ref",
    "enum",
    "listref",
    "text",
    # datastore port
    "DataStore",
    "Filter",
    "FilterList",
    "FilterOp",
    "Record",
    "RecordList",
    # cachestore port
    "CacheStore",
    # bus
    "Event",
    "EventKind",
    "Action",
    "ActionKind",
    "EventBus",
    "Handler",
    # manifest
    "Manifest",
    "UnitType",
    "NavEntry",
    "AuthMethod",
    # validation (declare-once: render HTML hints + enforce server-side)
    "Validator",
    "Required",
    "MinLength",
    "MaxLength",
    "Min",
    "Max",
    "Pattern",
    "Email",
    "OneOf",
    "PasswordPolicy",
    "ValidationError",
    "Result",
    "validate_field",
    "validate_form",
    "build_validators",
    # web facade (dispatch adapter lives in core)
    "App",
    "Ctx",
    "Page",
    "Fragment",
    "Rendered",
    "Redirect",
    "redirect",
    "RouteDef",
    "Kind",
]
