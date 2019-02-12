import json

def date_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, 'email'):
        return obj.email()

    return obj


def data2json(data):
    return json.dumps(
        data,
        default=date_handler,
        indent=2,
        separators=(',', ': '),
        sort_keys=True,
        ensure_ascii=False)
