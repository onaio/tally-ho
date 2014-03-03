from django.utils.cache import add_never_cache_headers


class DisableClientsideCachingMiddleware(object):
    def process_response(self, request, response):
        add_never_cache_headers(response)
        return response
