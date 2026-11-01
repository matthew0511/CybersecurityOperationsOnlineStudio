"""Bound raw ASGI input before JSON, multipart or database processing."""
import json
import math
import hmac
from urllib.parse import parse_qsl

MAX_BODY = 7 * 1024 * 1024
SECURITY_HEADERS = {
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
    'Strict-Transport-Security': 'max-age=31536000',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
}


def safe_compare(left, right):
    """Malformed token types and Unicode fail closed without compare_digest errors."""
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    try:
        return hmac.compare_digest(left.encode('utf-8'), right.encode('utf-8'))
    except UnicodeError:
        return False


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON member')
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError('Non-finite JSON number')


def validate_json(raw):
    value = json.loads(raw, object_pairs_hook=_object, parse_constant=_nonfinite)
    if not isinstance(value, dict):
        raise ValueError('JSON object required')
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > 10000 or depth > 24:
            raise ValueError('JSON structure limit')
        if isinstance(item, dict):
            pending.extend((key, depth + 1) for key in item)
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            if len(item) > 16000 or any(ord(ch) == 0 or 0xD800 <= ord(ch) <= 0xDFFF for ch in item):
                raise ValueError('Invalid or oversized JSON text')
        elif isinstance(item, float):
            if not math.isfinite(item) or abs(item) > 1e15:
                raise ValueError('JSON number out of range')
        elif isinstance(item, int) and not isinstance(item, bool) and not -(2**63) <= item < 2**63:
            raise ValueError('JSON integer out of range')
    return value


class RequestBoundary:
    """Buffer no more than the advertised cap, including unknown-length bodies."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = scope.get('headers', [])
        try:
            target = scope.get('path', '')
            query = scope.get('query_string', b'')
            if len(query) > 16384:
                return await self.reject(send, 414, 'Request target is too long')
            values = [target] + [part for pair in parse_qsl(query.decode('ascii'), errors='strict', max_num_fields=100) for part in pair]
            if any(any(ord(ch) == 0 or 0xD800 <= ord(ch) <= 0xDFFF for ch in value) for value in values):
                return await self.reject(send, 422, 'Invalid request target encoding')
        except (ValueError, UnicodeError):
            return await self.reject(send, 422, 'Invalid request target encoding')
        lengths = [v for k, v in headers if k.lower() == b'content-length']
        declared = None
        if lengths:
            if len(lengths) != 1 or not lengths[0] or not lengths[0].isdigit():
                return await self.reject(send, 400, 'Invalid Content-Length')
            if len(lengths[0]) > 10:
                return await self.reject(send, 413, 'Request exceeds 7 MiB')
            declared = int(lengths[0])
            if declared > MAX_BODY:
                return await self.reject(send, 413, 'Request exceeds 7 MiB')
        chunks = []
        total = 0
        consumed = scope['method'] in {'POST', 'PUT', 'PATCH', 'DELETE'} or bool(declared)
        if consumed:
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b'')
                total += len(chunk)
                if total > MAX_BODY:
                    return await self.reject(send, 413, 'Request exceeds 7 MiB')
                chunks.append(chunk)
                if not message.get('more_body', False):
                    break
            if declared is not None and declared != total:
                return await self.reject(send, 400, 'Request length did not match Content-Length')
        raw = b''.join(chunks)
        content_type = next((v.decode('latin-1').split(';', 1)[0].strip().lower() for k, v in headers if k.lower() == b'content-type'), '')
        if raw and (not content_type or content_type == 'application/json' or content_type.endswith('+json')):
            try:
                validate_json(raw)
            except (ValueError, UnicodeError, RecursionError):
                return await self.reject(send, 422, 'Invalid JSON type, encoding, number or structure')
        if not consumed:
            return await self.app(scope, receive, send)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': raw, 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)

    @staticmethod
    async def reject(send, status, message):
        body = json.dumps({'detail': message}).encode()
        headers = [(k.lower().encode(), v.encode()) for k, v in SECURITY_HEADERS.items()]
        headers += [(b'content-type', b'application/json'), (b'content-length', str(len(body)).encode())]
        await send({'type': 'http.response.start', 'status': status, 'headers': headers})
        await send({'type': 'http.response.body', 'body': body})
