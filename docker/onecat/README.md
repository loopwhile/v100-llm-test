# P520 1Cat-vLLM Docker runtime

Ornith-1.5-35B-A3B-NVFP4를 1Cat-vLLM 1.5.0 / R1 설정으로 실행한다.
OpenCode용 자동 도구 선택, `qwen3_xml` tool call parser, `qwen3` reasoning parser를 적용한다.

## P520에서 사용

현재 상태(2026-10-03): 사용자 요청으로 서버를 중지했다(`exited`, exit code 0).
컨테이너·이미지·캐시·모델과 tool parser 설정은 보존되어 있으며, 아래 `start`로 다시 실행한다.

배포 경로는 `/home/loopwhile/onecat-docker`다. SSH 접속 후 실행한다.

```bash
cd /home/loopwhile/onecat-docker
./onecat.sh start
./onecat.sh status
./onecat.sh health
./onecat.sh logs
./onecat.sh stop
```

`start`는 기존 컨테이너가 있으면 다시 시작한다. `restart`도 제공한다.
Docker Compose는 필요 없다. `unless-stopped` 정책으로 재부팅 후 자동 시작하며,
명시적으로 `stop`한 컨테이너는 사용자가 다시 `start`할 때까지 중지 상태를 유지한다.
모델 로딩과 R1 컴파일 때문에 준비까지 수분이 걸릴 수 있다. `status`에서
`healthy`를 확인한 뒤 API를 사용한다.

API: `http://127.0.0.1:18080/v1` (P520 기준).
Model ID: `Ornith-1.5-35B-A3B`.
기존 SSH 포트 포워딩을 그대로 사용할 수 있다. 새 터널이 필요하면 노트북에서:

```bash
ssh -N -L 18080:127.0.0.1:18080 p520
```

일반 채팅 요청 확인:

```bash
curl --fail http://127.0.0.1:18080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Ornith-1.5-35B-A3B","messages":[{"role":"user","content":"안녕"}],"max_tokens":64,"chat_template_kwargs":{"enable_thinking":false}}'
```

## 격리 구성

- Python 3.12.14와 기존 venv 전체를 이미지에 포함한다. 실행 중 호스트 venv를 마운트하거나 사용하지 않는다.
- CUDA 12.8.1 Ubuntu 24.04 기반 이미지 digest를 고정한다. NVIDIA 드라이버는 Docker GPU runtime이 제공한다.
- 모델 `/srv/models/ornith-1.5-35b-a3b-nvfp4`는 읽기 전용 bind mount다.
- `cache/`만 쓰기 가능한 영속 bind mount다. 컨테이너 `/tmp`와 8 GiB `/dev/shm`은 독립적이다.
- FlashInfer의 별도 캐시 규칙은 `FLASHINFER_WORKSPACE_BASE=/cache`로 지정한다.
- TileLang은 `TILELANG_CACHE_DIR=/cache/tilelang`, 임시 파일은 `/tmp/tilelang`을 사용한다.
- XDG 설정, CUDA JIT와 Torch extension 캐시도 `/cache`로 지정하며 vLLM usage stats는 비활성화한다.
- 컨테이너는 UID/GID 1000의 일반 사용자로 실행하며 루트 파일시스템은 읽기 전용이다.
- 호스트의 네트워크/PID/IPC namespace나 Docker socket은 공유하지 않는다.
- 컨테이너 내부 `0.0.0.0:8080`을 P520 `127.0.0.1:18080`에만 publish한다.
- R1: TP2, max length 131072, max sequences 2, MBT 4096, GPU memory utilization 0.90,
  `FLASH_ATTN_V100`, KV `fp8_e5m2`, target-only, graph auto (`--enforce-eager` 없음).
- 운영 명령에 `--enable-auto-tool-choice --tool-call-parser qwen3_xml --reasoning-parser qwen3`를 추가한다.
- 저장소의 `scripts/runtime_hooks/sitecustomize.py` 호환성 hook도 이미지에 포함한다.

모델의 기존 chat template을 사용한다. 노트북 OpenCode의 `onecat` 및 `onecat-a`
provider는 기존 endpoint와 model ID로 연결할 수 있다. 서버 기동 후 검증하려면:

```bash
python3 verify-tools.py --output tool-api-receipt.json
```

이 검증은 실제 작은 inference 요청을 보내며 `auto` 일반/스트리밍, `required`,
지정 도구 호출과 도구 결과 후속 응답을 확인한다. 반환된 도구를 실행하지는 않는다.
노트북 OpenCode에서는 별도 임시 폴더에서 `read`, `write` 후 `read`까지 검증했고,
JSX의 줄바꿈·따옴표·XML 문자가 포함된 파일 내용이 byte-exact로 보존됐다.
검증에 사용한 임시 permission 설정은 노트북의 실제 OpenCode 설정을 수정하지 않는다.

## 이미지 빌드 및 재현 범위

저장소 checkout을 P520에서 사용할 경우:

```bash
cd docker/onecat
./prepare-runtime.sh
```

빌드 스크립트는 P520의 기존 설치 환경을 새 `build-context/`에 복사하고
`onecat-vllm:1.5.0-p520-r1` 이미지를 빌드한다. 이미 존재하는 build context를
덮어쓰지 않는다. 원본 wheel SHA256을 검사하고 실제 복사한 Python·venv·hook
파일들의 SHA256 및 설치 패키지 버전을 `runtime-receipt.json`에 기록한다.
원본 venv와 uv Python은 변경하지 않는다. 런처는 `image-id.txt`의 이미지 ID로
실행하므로 동일 이름의 이미지 tag가 바뀌어도 기존 실행 이미지가 자동 교체되지 않는다.

이 방식은 검증된 설치본의 스냅샷이다. wheel만으로 새로 설치하는 빌드나
전체 의존성 wheelhouse는 아니다. Python 경로와 venv symlink를 보존하기 위해
이미지 안에서도 원래 절대 경로를 사용한다. 호스트 캐시나 사용자 인증 파일은 복사하지 않는다.
기반 이미지 digest와 설치 Python 패키지는 고정되지만 apt 시스템 패키지는
빌드 시 Ubuntu 저장소에서 설치하므로 전체 이미지가 bit-for-bit 재현되는 빌드는 아니다.

현재 Docker 운영 검증은 시작·health·짧은 채팅 및 도구 호출/OpenCode 연동 확인이다. 기존 R1의 128K/C2
벤치마크 결과는 호스트 프로세스의 측정이며 Docker에서 새로 재측정한 수치로 간주하지 않는다.
배포 이미지 ID, 실제 환경·mount·명령·검증 응답은
[배포 검증 기록](../../state/onecat-docker-deployment.json)에 보존했다.
도구 호출 및 OpenCode 검증은 [tool call 검증 기록](../../state/onecat-toolcall-validation.json)을 참조한다.

참고: [1Cat-vLLM upstream](https://github.com/1CatAI/1Cat-vLLM),
[Docker GPU 지원](https://docs.docker.com/engine/containers/resource_constraints/#gpu),
[Ornith 권장 parser 설정](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-NVFP4#serving-ornith-15-35b-a3b).
