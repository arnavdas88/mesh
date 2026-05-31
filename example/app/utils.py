def get_internal_data(data):
    internal_data = []
    for k, v in data.to_dict().items():
        if k.startswith("__") and k.endswith("__"):
            internal_data.append({
                "type": "",
                "tag": [k, "internal"],
                "data": v
            })
    return internal_data

def get_internal_data_type(key):
    if is_node_format(key):
        return "node"
    return "unknown"

def is_node_format(s: str) -> bool:
    # Ensure string is long enough to contain prefixes and suffixes
    if len(s) < 10:  
        return False
    return s.startswith("__node_") and s.endswith("__")