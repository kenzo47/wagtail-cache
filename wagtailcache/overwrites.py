from django.conf import settings
from django.core.cache import caches
from django.utils.crypto import md5

from django.utils.cache import _i18n_cache_key_suffix, cc_delim_re

def _generate_cache_key(request, method, headerlist, key_prefix):
    """
    Almost direct overwrite of Django's _generate_cache_key function to allow
    for the model_type to be included in the cache key.
    """
    ctx = md5(usedforsecurity=False)
    for header in headerlist:
        value = request.META.get(header)
        if value is not None:
            ctx.update(value.encode())
    url = md5(request.build_absolute_uri().encode("ascii"), usedforsecurity=False)
    # Get the value of the type query parameter if present.
    model_type = request.GET.get("type", "")
    cache_key = "views.decorators.cache.cache_page.%s.%s.%s.%s.[%s]" % (
        key_prefix,
        method,
        url.hexdigest(),
        ctx.hexdigest(),
        model_type
    )

    return _i18n_cache_key_suffix(request, cache_key)


def _generate_cache_header_key(key_prefix, request):
    """Return a cache key for the header cache."""
    url = md5(request.build_absolute_uri().encode("ascii"), usedforsecurity=False)
    cache_key = "views.decorators.cache.cache_header.%s.%s" % (
        key_prefix,
        url.hexdigest(),
    )
    return _i18n_cache_key_suffix(request, cache_key)


def get_cache_key(request, key_prefix=None, method="GET", cache=None):
    """
    Direct overwrite of Django's get_cache_key function to allow for the
    _generate_cache_key function to be overwritten as well.
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    cache_key = _generate_cache_header_key(key_prefix, request)
    if cache is None:
        cache = caches[settings.CACHE_MIDDLEWARE_ALIAS]
    headerlist = cache.get(cache_key)
    if headerlist is not None:
        return _generate_cache_key(request, method, headerlist, key_prefix)
    else:
        return None

def learn_cache_key(request, response, cache_timeout=None, key_prefix=None, cache=None):
    """
    Learn what headers to take into account for some request URL from the
    response object. Store those headers in a global URL registry so that
    later access to that URL will know what headers to take into account
    without building the response object itself. The headers are named in the
    Vary header of the response, but we want to prevent response generation.

    The list of headers to use for cache key generation is stored in the same
    cache as the pages themselves. If the cache ages some data out of the
    cache, this just means that we have to build the response once to get at
    the Vary header and so at the list of headers to use for the cache key.
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    if cache_timeout is None:
        cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
    cache_key = _generate_cache_header_key(key_prefix, request)
    if cache is None:
        cache = caches[settings.CACHE_MIDDLEWARE_ALIAS]
    if response.has_header("Vary"):
        is_accept_language_redundant = settings.USE_I18N
        # If i18n is used, the generated cache key will be suffixed with the
        # current locale. Adding the raw value of Accept-Language is redundant
        # in that case and would result in storing the same content under
        # multiple keys in the cache. See #18191 for details.
        headerlist = []
        for header in cc_delim_re.split(response.headers["Vary"]):
            header = header.upper().replace("-", "_")
            if header != "ACCEPT_LANGUAGE" or not is_accept_language_redundant:
                headerlist.append("HTTP_" + header)
        headerlist.sort()
        cache.set(cache_key, headerlist, cache_timeout)
        return _generate_cache_key(request, request.method, headerlist, key_prefix)
    else:
        # if there is no Vary header, we still need a cache key
        # for the request.build_absolute_uri()
        cache.set(cache_key, [], cache_timeout)
        return _generate_cache_key(request, request.method, [], key_prefix)