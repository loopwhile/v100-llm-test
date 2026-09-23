# WBS 1.3 — 1Cat-vLLM STOCK Verification

## Verdict

PASS

## Runtime identity

- 1Cat-vLLM: `1.5.0`
- Wheel: `1cat_vllm-1.5.0-cp312-cp312-linux_x86_64.whl`
- Wheel SHA256: `2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b`
- Python: `3.12.14`
- Torch: `2.10.0+cu128`
- Torch CUDA: `12.8`
- `flash_attn_v100`: `1.2.0`

## Qwen3.8-27B STOCK artifact

- Path: `/srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4`
- Quantization: NVFP4 compressed-tensors
- TP topology: TP2
- Speculative decoding: none / target-only

## TP2 128K startup

PASS with:

- `tensor_parallel_size=2`
- `max_model_len=131072`
- `max_num_seqs=1`
- `kv_cache_dtype=fp8_e5m2`
- `attention_backend=FLASH_ATTN_V100`
- `gpu_memory_utilization=0.965`
- `speculative_config=None`

Runtime evidence:

- TP0 and TP1 both used `FLASH_ATTN_V100`
- available KV cache: `2.22 GiB`
- GPU KV cache capacity: `133,984 tokens`
- `/health`: HTTP 200
- `/v1/models`: reports `max_model_len=131072`
- GPU0/GPU1 each held one TP worker
- server shut down cleanly and port 18080 returned to free state

## GPU memory utilization observations

- `0.90`: insufficient KV capacity for 131072 tokens
- `0.98`: requested reservation exceeded free startup memory
- `0.965`: verified working startup value

`0.965` is a verified working value, not claimed to be the minimum viable value.

## Tokenizer / template / tool profile

- tokenizer class: `Qwen2Tokenizer`
- tokenizer `model_max_length`: `262144`
- `chat_template.jinja`: present
- tokenizer-config chat template: present
- `enable_thinking` is supported by the template
- thinking is enabled when `enable_thinking` is omitted or true
- `enable_thinking=false` is explicitly supported by the template
- tool calls use an XML-style `<tool_call><function=...>` representation

1Cat-vLLM exposes:

- `--enable-auto-tool-choice`
- `--tool-call-parser`
- `--reasoning-parser`
- `--default-chat-template-kwargs`

The artifact itself does not pin a specific tool-call parser or reasoning parser name. No parser identity is invented or inferred here.

## Ornith 1.5 9B STOCK

GPU0/GPU1 TP1 startup is not executed in WBS 1.3 because the exact STOCK 1Cat artifact repository/revision/path is not yet pinned.

This remains pending artifact resolution in WBS 1.5.

## Evidence

- `discovery.txt`
- `runtime-identity.txt`
- `backend-model-check.txt`
- `tp2-startup-status.txt`
- `tp2-runtime-check.txt`
- `tp2-server.log`
- `tp2-startup-0965.txt`
- `tp2-shutdown-check.txt`
- `tp2-server-0965.log`
- `profile-check.txt`
- `profile-requirements.txt`
