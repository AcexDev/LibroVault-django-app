# Library Filters
"""
Query-string filtering for a user's library, kept in one place so the ordering
choices can also be advertised through the metadata endpoint.
"""

ORDER_CHOICES = [
    ("title_asc", "Title (A–Z)"),
    ("title_desc", "Title (Z–A)"),
    ("date_old", "Date added (Oldest first)"),
    ("date_new", "Date added (Newest first)"),
]

ORDER_VALUES = {
    "title_asc": "book__title",
    "title_desc": "-book__title",
    "date_old": "added_at",
    "date_new": "-added_at",
}

DEFAULT_ORDER = "-added_at"

TRUTHY = ("1", "true", "yes", "on")


def filter_library_queryset(queryset, params):
    """
    Applies `status`, `favourite` and `sort` from the query string. Each is
    independent, so they can be combined freely.
    """
    status = params.get('status')
    if status:
        queryset = queryset.filter(status=status)

    favourite = params.get('favourite')
    if favourite:
        queryset = queryset.filter(favourite=str(favourite).lower() in TRUTHY)

    order = ORDER_VALUES.get(params.get('sort'), DEFAULT_ORDER)
    return queryset.order_by(order)
