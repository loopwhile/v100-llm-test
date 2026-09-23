# WBS 1.3 — LiteLLM Gateway Verification

## Verdict

PASS

## Scope

LiteLLM is required only for the Ornith 1.5 9B `1GPU×2-independent` topology.

It is not part of shared TP2 serving for Qwen3.8, Ornith 35B, Gemma4, or Ornith 9B TP2.

## Runtime identity

- LiteLLM: `1.101.0`
- OCI revision: `18243cd7af4c3325165ba68b21379e2719e051c7`
- Image digest: `sha256:d295634e09c648dcdb72c4cc2dd226f5fb87823a73e88cbbed6f205e4deb044b`

## Gateway configuration

Verified configuration:

- one logical model group: `Ornith-1.5-9B`
- backend A: `127.0.0.1:18080`
- backend B: `127.0.0.1:18081`
- routing strategy: `least-busy`
- backend `max_parallel_requests=1`
- router `num_retries=0`
- backend `max_retries=0`

## Liveness

`GET /health/liveliness` returned HTTP 200 and `"I'm alive!"`.

The generic `/health` endpoint was intentionally not used for gateway preflight because it can trigger backend health activity.

The test container was removed after verification and port 18079 returned to free state.

## Evidence

- `preflight.txt`
- `litellm-config.yaml`
- `gateway.log`
