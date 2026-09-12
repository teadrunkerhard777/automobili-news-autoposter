from collectors.normalizer import normalize_item


def collect_static(source):
    """Collect local example items without any network dependency."""

    return [
        normalize_item(item, source["name"])
        for item in source.get("items", [])
    ]

