from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """API contract: `?page=&page_size=` → {count, next, previous, results}."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
