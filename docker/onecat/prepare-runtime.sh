#!/usr/bin/env bash
# Run on P520. Snapshot the working installation without changing it.
set -euo pipefail
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runtime_venv=${ONECAT_SOURCE_VENV:-/home/loopwhile/qwen3.8-bench-runtime/venv}
runtime_python=/home/loopwhile/.local/share/uv/python/cpython-3.12.14-linux-x86_64-gnu
runtime_wheel=/home/loopwhile/1cat-vllm-wheel/1cat_vllm-1.5.0-cp312-cp312-linux_x86_64.whl
hook_source=${ONECAT_RUNTIME_HOOKS:-"$task_dir/../../scripts/runtime_hooks"}
if [ -f "$task_dir/runtime_hooks/sitecustomize.py" ]; then
    hook_source="$task_dir/runtime_hooks"
fi
context_dir="$task_dir/build-context"
test ! -e "$context_dir" || { echo "Build context already exists: $context_dir" >&2; exit 1; }
printf '%s  %s\n' 2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b "$runtime_wheel" | sha256sum --check
"$runtime_venv/bin/python" -c 'import importlib.metadata as m; assert m.version("1cat-vllm") == "1.5.0"'
mkdir -p "$context_dir/runtime_hooks"
cp "$task_dir/Dockerfile" "$context_dir/Dockerfile"
cp "$hook_source/sitecustomize.py" "$context_dir/runtime_hooks/"
cp -a --reflink=auto "$runtime_python" "$context_dir/python"
cp -a --reflink=auto "$runtime_venv" "$context_dir/venv"
"$runtime_venv/bin/python" - "$context_dir" "$runtime_wheel" <<'PY'
import datetime, hashlib, importlib.metadata as metadata, json, pathlib, sys
context, wheel = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
packages = sorted(
    ({"name": d.metadata["Name"], "version": d.version} for d in metadata.distributions()),
    key=lambda d: d["name"].lower(),
)
# Hash the actual snapshot, including custom/local package changes.
digest = hashlib.sha256()
count = 0
for root in (context / "python", context / "venv", context / "runtime_hooks"):
    for p in sorted(root.rglob("*")):
        if not (p.is_file() or p.is_symlink()):
            continue
        digest.update(str(p.relative_to(context)).encode() + b"\0")
        if p.is_symlink():
            digest.update(b"link\0" + str(p.readlink()).encode())
        else:
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    digest.update(chunk)
        digest.update(b"\0")
        count += 1
receipt = {
    "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "method": "embedded installed-runtime snapshot; no runtime bind mounts",
    "python": sys.version,
    "source_venv": sys.prefix,
    "wheel": wheel.name,
    "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    "snapshot_sha256": digest.hexdigest(),
    "snapshot_files": count,
    "packages": packages,
    "note": "Wheel provenance and installed snapshot identity are recorded separately.",
}
(context / "runtime-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({k: v for k, v in receipt.items() if k != "packages"}, indent=2))
PY
docker build -t onecat-vllm:1.5.0-p520-r1 "$context_dir"
docker image inspect onecat-vllm:1.5.0-p520-r1 --format '{{.Id}}' > "$task_dir/image-id.txt"
cp "$context_dir/runtime-receipt.json" "$task_dir/runtime-receipt.json"
