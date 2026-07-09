# Shared utility functions

def generate_unique_id() -> str:
    import uuid
    return str(uuid.uuid4())


def validate_bbox(bbox: list) -> bool:
    """Validate a bounding box in the format [min_lon, min_lat, max_lon, max_lat]"""
    if len(bbox) != 4:
        return False
    min_lon, min_lat, max_lon, max_lat = bbox
    return (-180 <= min_lon <= 180 and
            -90 <= min_lat <= 90 and
            -180 <= max_lon <= 180 and
            -90 <= max_lat <= 90 and
            min_lon < max_lon and
            min_lat < max_lat)