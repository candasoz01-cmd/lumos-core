# Ring Playground: live read-only verification

This feature branch includes the existing Amazon hackathon simulators and the
credentialed Ring adapter. It does not change the deployed Lumos application.
The Alexa+ web simulation remains a separate demonstration.

## Recorded evidence

On 2026-09-19, the existing integration registry called the official remote
`https://api.amazonvision.com` API using a temporary Ring Developer Playground
token. The recording used a local operator verification view, not customer UI.

| UTC | Request | Result | Observed duration |
| --- | --- | --- | --- |
| 11:32:17 | `GET /v1/devices` | HTTP 200, one test device | 1085 ms |
| 11:32:27 | `GET /v1/devices/{id}/status` | HTTP 200, `online=true` | 1370 ms |

These are real remote requests for an official Playground simulated test device.
They are not physical Ring hardware evidence or a performance benchmark.
No video stream, recording access, device control or Ring-driven task flow is
implemented by this read-only path.

Recorded adapter SHA-256:
`2a7805a4373e6534826acd5def095359efbf3f3917686f3a1b22140cd3bf55ae`.

## Reproduce

Use the project's Python environment and development dependencies. The tests
use injected transport responses and do not contact Ring:

```sh
PYTHONPATH=src:packages/kando_runtime/src:packages/kando_bridge/src KANDO_MOCK=1 python -m pytest -q tests/test_ring_live_adapter.py tests/test_amazon_hackathon_simulators.py tests/test_global_integration_catalog.py
```

For a live run, create a test device and a fresh token in the official Ring
Developer Playground. Its UI states a 30-minute token lifetime. Run the following
from the repository root in a local terminal. The token is entered without echo,
kept in process memory and removed from the process environment after the calls.
Only response status and device count are printed. Do not record token entry.

```sh
PYTHONPATH=src python - <<'PY'
import getpass
import os
from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations

registry = register_default_integrations()
os.environ['RING_API_TOKEN'] = getpass.getpass('Temporary Ring token: ')
try:
    result = registry.run(IntegrationRequest('amazon_hackathon', 'ring_live_list_devices', {}))
    devices = result.data.get('document', {}).get('data', [])
    print({'action': 'list', 'ok': result.ok, 'http_status': result.data.get('http_status'), 'count': len(devices)})
    if not result.ok:
        raise SystemExit(1)
    for device in devices:
        result = registry.run(IntegrationRequest('amazon_hackathon', 'ring_live_status', {'device_id': device['id']}))
        data = result.data.get('document', {}).get('data', {})
        online = data.get('attributes', {}).get('online')
        print({'action': 'status', 'ok': result.ok, 'http_status': result.data.get('http_status'), 'online': online})
        if not result.ok:
            raise SystemExit(1)
finally:
    os.environ.pop('RING_API_TOKEN', None)
PY
```

The registry actions are `ring_live_list_devices` and `ring_live_status` under
provider `amazon_hackathon`. The similarly named `ring_list_devices` and
`ring_status` actions are offline simulator actions. Missing tokens fail closed;
401/403 responses report `token_expired_or_invalid`. Repeat runs require a fresh
token and may produce different device counts or status values.

## Video and validation

The 55.694-second English demo has synthetic narration and burned-in captions.
It shows the actual recorded list/status requests, with narration pauses.
The video file SHA-256 is
`161fac43ec59444a9e8f86e8ba09e91b9a8bceefbbdd2b543395d6c56a005e08`.

At publication preparation, all 26 focused tests above and Ruff checks passed.
This evidence does not establish production authorization readiness, physical
device behavior, or automatic actions. Apache-2.0 repository licensing applies.
