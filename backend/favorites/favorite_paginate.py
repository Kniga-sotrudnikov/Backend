from core.pagination import StandardPagination


def paginate_queryset(queryset, request, pagination_class=StandardPagination):
    """Возвращает пагенированый кверисет."""
    paginator = pagination_class()
    page = paginator.paginate_queryset(queryset=queryset, request=request)
    return page, paginator
