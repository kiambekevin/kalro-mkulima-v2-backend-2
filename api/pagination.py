# api/pagination.py
"""
API-layer pagination. Delegates to `apps.common.pagination` for the
implementations so every app uses the same page-size envelope.
Exposes aliases here so DRF settings can reference `api.pagination.*`
without importing from `apps.common` everywhere.
"""
from apps.common.pagination import (  # noqa: F401
    LargePagination,
    RecentFirstCursorPagination,
    SmallPagination,
    StandardPagination,
)

# Semantic aliases for use in DRF settings and views
DefaultPagination = StandardPagination
DashboardPagination = SmallPagination
CataloguePagination = StandardPagination
ReportPagination = LargePagination
FeedPagination = RecentFirstCursorPagination