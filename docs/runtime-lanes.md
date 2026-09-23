# Runtime Lanes

Turn 4 exposes mandatory serving lanes. A launch plan is not a capacity PASS.

## llama.cpp

Every llama.cpp candidate has four explicit rows:

| Lane | Configuration | Required |
| --- | --- | --- |
| TARGET | \`--spec-type none\` | yes |
| NGRAM | \`--spec-type ngram-simple\` | yes |
| MTP | \`--spec-type draft-mtp --spec-draft-n-max 3\` | explicit result row |
| MTP_NGRAM | \`--spec-type draft-mtp,ngram-simple --spec-draft-n-max 3\` | explicit result row |

TARGET↔NGRAM is mandatory even when MTP is not usable. Unsupported MTP/composite support is recorded as \`UNSUPPORTED\`, not deleted.

### 128K topology

Shared TP2 C1 uses \`--ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072\`.

Shared TP2 C2 uses \`--ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072\`. The launcher also enables the slots endpoint so C2 residency/processing can be sampled during the run.

The C2 value intentionally asks for two independent 128K logical contexts. If it does not fit, preserve the OOM/capacity result.

\`1gpu-x2-independent\` starts two separate C1/128K servers, one on each GPU. It is only available to models that declare that topology.

## 1Cat-vLLM stock

Stock retains the imported 1Cat-vLLM 1.5.0 wheel identity, FLASH_ATTN_V100, TP2, 128K per sequence, and \`max_num_seqs=1|2\`. Ornith 1.5 9B additionally has a first-class 1GPU×2 STOCK topology once its exact NVFP4 artifact and exact MTP speculative launch configuration are resolved: two TP1 processes, one pinned to each V100, each with \`max_model_len=131072\` and \`max_num_seqs=1\`. A non-target speculative candidate without a pinned launch configuration fails closed as \`UNSUPPORTED\`.

## v100-skinny

v100-skinny is mandatory but is a separate runtime identity, not a switch on stock 1Cat 1.5.0. Its pinned v1.1 contract remains the experimental shared TP2 lane; it is not silently reused for the independent TP1×2 topology.

Pinned upstream v1.1 contract:

- skinny commit: \`5b589c0dc81223e0ba65bcb3e755874723f8b515\`
- base 1Cat-vLLM: 1.2.2
- base wheel SHA256: \`8a628983ad9d675559910372643220c418b307ddc7fd52ac65a7f5fbcb104bc6\`
- published checkpoint: \`RadixArk/Qwen3.8-27B-NVFP4@554ebba9b5f1b79dc11246341960360e6ef05ef4\`
- FP16 KV
- QPN2/QPN8
- MTP

The upstream v1.1 serving script hard-codes TP4. This repository therefore treats TP2 as an **experimental mandatory compatibility lane** and builds a direct TP2 command from the pinned v1.1 environment. No TP4 result is inherited as a 2×16GB PASS.

For 128K live context the project uses MTP k=3 and decode partition 1024. The upstream README recommends shallower k=3 for long live context; our result still requires fresh measurement.

The standalone v1.1 contract is Qwen3.8-specific. Other models keep a mandatory skinny row but may resolve to \`UNSUPPORTED\`.

## Skinny TP2 boot gate

After the compatibility warm request, run:

```bash
python3 scripts/skinny_gate.py --log <server.log> --tp 2 --depth 3
```

The TP2 census expectation is **256** protected FP8 module instances (128 per rank × 2 ranks), not the upstream TP4 script's hard-coded 512. The gate also requires the requested MTP depth, lm_head QPN route, no repack fallback, declined checkpoint FP8-KV directive, zero scalar-paged calls, XQA, QPN2 and QPN8 dispatch.
