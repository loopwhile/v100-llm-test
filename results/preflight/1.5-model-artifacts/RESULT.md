# WBS 1.5 — model artifact resolution

## Verdict

`DONE`

Artifact identity and runtime compatibility are recorded separately. An exact artifact does not imply that the current V100 runtime has been proven compatible.

## Qwen3.8-27B

### llama.cpp

- repository: `unsloth/Qwen3.8-27B-GGUF`
- revision: `4ca720788d1e01f1bff70c033e0d0028fd02e502`
- path: `/srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf`
- SHA256: `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`
- quant: `UD-Q4_K_M`
- benchmark lanes: `TARGET`, `NGRAM`

Qwen3.8-27B does not use the MTP/MTP_NGRAM llama.cpp benchmark lanes.

### STOCK 1Cat

- repository: `QUASAR-QAT/Qwen3.8-27B-QUASAR-NVFP4`
- revision: `15d2e47bffe5d8ad23928879f8f7d2f74909e259`
- path: `/srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4`
- quant: NVFP4
- runtime preflight: PASS

### v100-skinny

- repository: `RadixArk/Qwen3.8-27B-NVFP4`
- revision: `554ebba9b5f1b79dc11246341960360e6ef05ef4`
- artifact identity: verified
- current 2×V100-16GB verdict: `FAIL_OOM_MODEL_LOAD`
- boot gate: `NOT_REACHED`
- local RadixArk checkpoint removed after preflight

## Ornith 1.5 9B

### llama.cpp

- path: `/srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf`
- revision recovered from local provenance: `5957ee5dcb88e9a9f4cd9a23c649320d20a574cd`
- SHA256: `79a9925bb7771dea3530d57b185e97b9713a73a7c06bdb9804f7d019aa42f480`
- source repository identity: `UNRESOLVED`

No repository name is inferred.

### STOCK 1Cat

- repository: `ornith-ai/Ornith-1.5-9B-NVFP4`
- revision: `155f200d85ad58464571c77d5e1122ea5d419d7b`
- path: `/srv/models/ornith-1.5-9b-nvfp4`
- artifact identity: verified
- V100 runtime compatibility: `PENDING`

## Ornith 1.5 35B-A3B

### llama.cpp

Base:

- repository: `ornith-ai/Ornith-1.5-35B-A3B-GGUF`
- revision: `12393612fd4f730ff5aadc23e9b8f9648aa49ceb`
- path: `/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf`
- SHA256: `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`

MTP companion:

- revision: `04eb5f9915607c840716ae817717431f0ba6df07`
- path: `/srv/models/ornith-1.5-35b-a3b-gguf/mtp-Ornith-1.5-35B-A3B-Abliterated-MTPv2-Q8_0.gguf`
- SHA256: `7d58b16ecab1a30884f76f1372680405a52a30547d94fb6b61cef802a7311ab6`
- source repository identity: `UNRESOLVED`

### STOCK 1Cat

- repository: `ornith-ai/Ornith-1.5-35B-A3B-NVFP4`
- revision: `94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa`
- path: `/srv/models/ornith-1.5-35b-a3b-nvfp4`
- artifact identity: verified
- V100 runtime compatibility: `PENDING`

## Gemma4 26B-A4B

### llama.cpp

Base:

- repository: `unsloth/gemma-4-26B-A4B-it-qat-GGUF`
- revision: `7b92b5b28818151e8669af2e45e88d6086f490dd`
- path: `/srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf`
- SHA256: `a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891`

MTP companion:

- same repository/revision
- path: `/srv/models/gemma-4-26b-a4b-it-qat-gguf/mtp-gemma-4-26B-A4B-it.gguf`
- SHA256: `7272d97595f0d4c74bd7b623492b7dbdaafd8b7c72f329a8270ba4eca68f768a`

### STOCK 1Cat

`PENDING`

No exact local NVFP4 artifact is currently pinned.

## non-Qwen v100-skinny

`UNSUPPORTED`

The pinned v100-skinny v1.1 contract is Qwen3.8-specific. No exact standalone v1.1 contract is pinned for Ornith or Gemma.
