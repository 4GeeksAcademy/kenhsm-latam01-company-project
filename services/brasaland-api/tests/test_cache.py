from brasaland_api.core.cache import TTLCache


def test_cache_hits_until_ttl_expires():
    cache = TTLCache()
    loads = 0

    def load():
        nonlocal loads
        loads += 1
        return {"value": loads}

    assert cache.get_or_set("user-a", load, ttl_seconds=30) == {"value": 1}
    assert cache.get_or_set("user-a", load, ttl_seconds=30) == {"value": 1}
    assert loads == 1

    assert cache.get_or_set("expired", load, ttl_seconds=0) == {"value": 2}
    assert cache.get_or_set("expired", load, ttl_seconds=0) == {"value": 3}


def test_cache_keys_are_isolated_and_prefix_invalidation_is_scoped():
    cache = TTLCache()
    loads = 0

    def load():
        nonlocal loads
        loads += 1
        return [loads]

    assert cache.get_or_set("hr:employees:user-a", load, ttl_seconds=30) == [1]
    assert cache.get_or_set("hr:employees:user-b", load, ttl_seconds=30) == [2]
    cache.invalidate_prefix("hr:employees:user-a")

    assert cache.get_or_set("hr:employees:user-a", load, ttl_seconds=30) == [3]
    assert cache.get_or_set("hr:employees:user-b", load, ttl_seconds=30) == [2]
