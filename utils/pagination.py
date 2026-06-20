def pagination_values(raw_page, total_items, page_size):
    try:
        page = max(int(raw_page), 1)
    except (TypeError, ValueError):
        page = 1

    total_pages = max((total_items + page_size - 1) // page_size, 1)
    page = min(page, total_pages)
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_previous": page > 1,
        "has_next": page < total_pages,
    }
