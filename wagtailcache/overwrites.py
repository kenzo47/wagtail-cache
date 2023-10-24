from django.conf import settings
from django.core.cache import caches
from django.utils.crypto import md5

from django.utils.cache import _i18n_cache_key_suffix, _generate_cache_header_key

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