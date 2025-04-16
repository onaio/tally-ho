from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger


def paging(objects_list, request, page_kwarg='page'):
    """Return the appropriate page for this list and request.

    :param objects_list: The list of objects to paginate.
    :param request: The request to retrieve a page from.
    :param page_kwarg: The name of the query parameter for the page number.

    :returns: A page for this list and request.
    """
    paginator = Paginator(objects_list, 10)
    page = request.GET.get(page_kwarg)

    return paginate(paginator, page)


def paginate(paginator, page):
    """Get the pages for this paginator and page.

    :param paginator: The paginator to fetch pages from
    :param page: The page to fetch.

    :returns: A list of records for this paginator and page.
    """
    try:
        return paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        return paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page.
        return paginator.page(paginator.num_pages)
