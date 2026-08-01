"""Instance-owned manifest for tooling that is safe to vendor into child repositories.

This is the single source of truth for bootstrap and resource sync.  Child sync
downloads this module from the selected instance ref on every run; it never
uses the child's vendored copy to decide what to update.
"""

LOCAL_TOOLING_MODULES = (
    "__init__.py",
    "callers.py",
    "config.py",
    "providers.py",
    "dependencies.py",
    "docs.py",
    "index.py",
    "init_repo.py",
    "sync.py",
    "org_diagram_link.py",
    "recovery.py",
    "local_tooling.py",
)
