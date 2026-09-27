너의 임무는 Ornith 1.5 9B / 1Cat-vLLM WBS5 frozen candidate set의 **로컬 실행 가능성만 검증**하는 것이다.

중요: 이번 작업에서는 GPU measured inference가 금지되어 있다.

절대로 다음을 실행하지 마라:
- vLLM API server 실제 model startup
- model weight load를 유발하는 명령
- warmup inference
- completion/chat request
- benchmark workload
- CUDA Graph 실제 model capture
- 128K request
- 성능 측정
- GPU를 사용하는 model forward

가능한 작업은 다음으로 제한한다:
- 파일/JSON/config/source inspection
- installed package/version/hash 확인
- CLI `--help` 또는 parser/source 수준 option 존재 확인
- Python package source inspection
- model metadata/config 파일 inspection
- 명령 문자열 생성 및 diff 검증
- extension symbol/API 존재 여부를 model load 없이 안전하게 검사할 수 있는 경우의 static check
- repository state 확인
- 향후 실행용 preflight checklist 작성

## Frozen candidate set

새 candidate를 추가하지 마라.

### R0
ID:
`ORN15-9B-1CAT-WBS5-R0-BASELINE`

Core settings:
- model `/srv/models/ornith-1.5-9b-nvfp4`
- served model `Ornith-1.5-9B`
- NVFP4
- TP2
- KV `float16`
- max model len `131072`
- max num seqs `2`
- max num batched tokens `4096`
- gpu memory utilization `0.90`
- target attention `FLASH_ATTN_V100`
- target `--enforce-eager`
- speculative method `mtp`
- num speculative tokens `1`
- drafter attention `TRITON_ATTN`
- `CUDA_VISIBLE_DEVICES=0,1`

### R1
ID:
`ORN15-9B-1CAT-WBS5-R1-MBT8192`

Only permitted change from R0:
`max_num_batched_tokens 4096 -> 8192`

### R2
ID:
`ORN15-9B-1CAT-WBS5-R2-TARGET-GRAPH`

Only permitted change from R0:
remove target `--enforce-eager`

Do not change the MTP speculative configuration.

### R3
ID:
`ORN15-9B-1CAT-WBS5-R3-MTP2`

Only permitted change from R0:
`num_speculative_tokens 1 -> 2`

Target must return to R0 eager mode.
MBT must return to 4096.

## Exact identities that must be checked

Model repository:
`ornith-ai/Ornith-1.5-9B-NVFP4`

Expected revision:
`155f200d85ad58464571c77d5e1122ea5d419d7b`

Expected path:
`/srv/models/ornith-1.5-9b-nvfp4`

Runtime:
`1Cat-vLLM 1.5.0`

Expected wheel:
`1cat_vllm-1.5.0-cp312-cp312-linux_x86_64.whl`

Expected wheel SHA256:
`2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b`

Expected environment from previous evidence:
- Python 3.12.x
- torch `2.10.0+cu128`
- CUDA userspace 12.8
- 2 × Tesla V100-SXM2-16GB
- compute capability 7.0
- flash_attn_v100 1.2.0

Do not silently accept a different version.

## Required static verification

### 1. Runtime identity
Verify:
- installed 1Cat package version
- installed wheel/package hash if recoverable
- Python version
- torch version
- flash_attn_v100 version
- CUDA-visible GPU inventory without running model inference

Report PASS/FAIL/UNKNOWN separately.

### 2. Model identity
Inspect the local model directory without loading the model.

Confirm:
- config files exist
- pinned repository/revision metadata if locally recorded
- quantization metadata says NVFP4
- selected metadata hashes match repository evidence where available
- `mtp_num_hidden_layers`
- model architecture name
- `layer_types`
- presence of linear-attention/GDN hybrid structure
- MTP-related metadata/weight filenames or tensor-index references that can be established without loading tensors

Do not invent a whole-directory SHA256 if one has never been defined.

### 3. NVFP4 SM70 path
Using installed 1Cat source/binary inspection only, establish whether this pinned build contains:
- exact-SM70 ModelOpt NVFP4 support
- `VLLM_SM70_NVFP4_TURBOMIND`
- SM70 TurboMind NVFP4 preparation/apply path
- required extension/API symbols if safely inspectable without model startup

Determine whether the future R0 launch is expected to resolve to the SM70 TurboMind NVFP4 W4A16 path.

Clearly distinguish:
- source/binary capability exists
- actual future model run route is not yet measured

### 4. SM70/Qwen3.5 runtime defaults
Confirm pinned build contains the logic for:
- `enable_prefix_caching=True` for server + linear attention
- `mamba_cache_mode=align`
- MTP greedy draft selection
- `use_local_argmax_reduction=True`
- drafter CUDA Graph enabled by default when speculative `enforce_eager` is absent
- target `FLASH_ATTN_V100`
- GDN FlashQLA decode route
- current SM70 MTP CUDA Graph capture-size logic

Report default values and the source locations that produce them.

### 5. R1 feasibility
Without running inference:
- confirm `--max-num-batched-tokens 8192` is syntactically accepted by the pinned CLI/config
- verify R1 differs from R0 by exactly one effective setting
- verify changing MBT does not itself alter `num_speculative_tokens`, TP, max_num_seqs, KV dtype, attention backends or target eager/graph selection
- inspect whether the MTP verifier graph-shape calculation depends on MBT; report exact finding

### 6. R2 feasibility
Without capturing graphs or loading the model:
- confirm removing `--enforce-eager` permits target CUDA Graph in the pinned config
- determine expected `decode_query_len` for MTP1
- determine expected verifier capture shapes for C2
- confirm those shapes are inserted into the pinned capture-size logic
- list every automatic compilation/graph setting expected to change merely because target eager is removed
- distinguish configured graph eligibility from future actual graph replay/hit evidence

### 7. R3 feasibility
Inspect exact local Ornith metadata and pinned 1Cat source.

Confirm:
- exact `mtp_num_hidden_layers`
- effective/native `n_predict` derivation
- whether `num_speculative_tokens=2` satisfies pinned validation rules
- whether this means reuse of the same MTP layer
- expected decode query length
- expected C2 verifier graph shapes
- any explicit source warning for depth >1
- no hidden change to target eager, MBT, TP, KV or attention backend

Do not claim MTP2 is performant or correct. Only determine whether the pinned runtime/config permits it.

### 8. Prefix-cache confound check
Do not run inference.

Inspect the WBS5 workload-generation path and determine how Project A/B prompts are constructed.

If the final generated tokenized prompts cannot be known without server/model tokenizer execution, mark the exact common-prefix token length as `NEEDS FUTURE RUNTIME CHECK`.

Do not disable prefix caching. It is part of the frozen runtime behavior.

### 9. Metric-definition check
Inspect the repository benchmark harness and document the exact formulas for:
- per-request TTFT
- per-request decode TPS
- mean request decode TPS
- aggregate decode TPS
- end-to-end output TPS
- batch wall time

Explicitly confirm whether:
`mean_request_decode_tps * concurrency`
is or is not expected to equal `aggregate_decode_tps`.

### 10. Frozen command diff validation
Produce the exact future launch command for R0, R1, R2 and R3, but DO NOT execute them.

Perform a normalized diff:
- R1 vs R0 must contain only MBT 4096→8192
- R2 vs R0 must contain only removal of `--enforce-eager`
- R3 vs R0 must contain only MTP token depth 1→2

If any hidden generated config causes another effective runtime variable to change, report it explicitly.

## Admission gate note

WBS3 contains a semantic discrepancy on Project B.

Before any WBS5 measured candidate is eventually executed, a separate G0 semantic requalification must be performed using the pre-registered WBS3 concurrency semantic oracle.

Do NOT perform G0 now because it requires inference.

Only verify that:
- the required workload/oracle files exist
- their hashes/paths can be frozen
- the expected Project B seeded defect is still the `JobQueue.pop` check → await → heappop race

## Required output

Return:

1. Overall result:
   - `READY_FOR_FUTURE_G0`
   - `BLOCKED`
   - or `READY_WITH_STATIC_UNKNOWNS`

2. A verification table with:
   - check
   - expected
   - observed
   - PASS/FAIL/UNKNOWN
   - evidence path/source

3. R0/R1/R2/R3 exact command table.

4. Normalized command/config diff proving one-variable-at-a-time compliance.

5. Items that cannot be proven without future model startup/inference.

6. Any blocker that must be fixed before G0.

Do not modify benchmark results.
Do not create fake PASS evidence.
Do not run GPU inference.
Do not add candidates.
Do not recommend new optimization knobs.
