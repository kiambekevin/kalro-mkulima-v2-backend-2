# apps/common/pagination.py
"""
Pagination classes used by DRF views.
"""
from collections import OrderedDict

from rest_framework.pagination import (
    CursorPagination as DRFCursorPagination,
    PageNumberPagination,
)
from rest_framework.response import Response

from .constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class StandardPagination(PageNumberPagination):
    """
    Default paginator: `?page=N&page_size=M`. Capped at MAX_PAGE_SIZE
    so clients can't request 10 000 rows in one call.
    """
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ("count", self.page.paginator.count),
            ("page", self.page.number),
            ("page_size", self.get_page_size(self.request)),
            ("total_pages", self.page.paginator.num_pages),
            ("next", self.get_next_link()),
            ("previous", self.get_previous_link()),
            ("results", data),
        ]))


class LargePagination(StandardPagination):
    """For admin/export-style endpoints."""
    page_size = 100
    max_page_size = 500


class SmallPagination(StandardPagination):
    """For dashboards and lightweight feeds."""
    page_size = 10
    max_page_size = 50


class RecentFirstCursorPagination(DRFCursorPagination):
    """
    Cursor pagination for time-ordered feeds (activity, notifications).
    Requires an `ordering` field on the queryset.
    """
    page_size = DEFAULT_PAGE_SIZE
    ordering = "-created_at"