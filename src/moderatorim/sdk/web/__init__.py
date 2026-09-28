"""The routing-facade contract domain: the App registration surface + the primitives handlers
return/receive. The dispatch adapter that renders these lives in core."""

from moderatorim.sdk.web.app import App, Kind, RouteDef, as_bundle_tuple
from moderatorim.sdk.web.primitives import Ctx, Fragment, Page, Redirect, Rendered, redirect

__all__ = [
    "App",
    "Kind",
    "RouteDef",
    "as_bundle_tuple",
    "Ctx",
    "Fragment",
    "Page",
    "Redirect",
    "Rendered",
    "redirect",
]
