# WAI profile status

## Intent

`wai-illustrious-t2i` is a gateway workflow profile for WAI Illustrious-family SDXL checkpoints. It uses a standard ComfyUI API graph:

- `CheckpointLoaderSimple`
- positive/negative `CLIPTextEncode`
- `EmptyLatentImage`
- `KSampler` (`euler_ancestral`, `normal`)
- `VAEDecode`
- `SaveImage`

Default checkpoint name:

```text
waiNSFWIllustrious_v140.safetensors
```

Defaults target portrait anime generation: `832x1216`, `28` steps, `CFG 5.0`.

## Current host blockage (inspected 2026-08-11)

On the Windows ComfyUI checkout at `C:\Chius\repo\github\ComfyUI`:

- workflows present: only `Anima_Turbo_T2I.json` / `Anima_Turbo_T2I_api.json`
- `models/diffusion_models`: `anima-turbo-v1.0.safetensors`
- `models/checkpoints`: empty (placeholder only)
- no WAI / Illustrious checkpoint or workflow file found

Therefore `wai-illustrious-t2i` is registered and renderable by the gateway, but a live generation against this host will fail until a matching checkpoint is installed.

## Minimal unblock path

1. Install a WAI Illustrious SDXL checkpoint into:

```text
C:\Chius\repo\github\ComfyUI\models\checkpoints\
```

2. If the filename differs from `waiNSFWIllustrious_v140.safetensors`, either rename it to match or update the profile template `ckpt_name`.

3. Confirm ComfyUI inventory:

```bash
curl -fsS http://10.0.0.180:8188/models/checkpoints
```

4. Submit through the gateway:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/v1/generations \
  -H 'content-type: application/json' \
  --data '{
    "profile_id": "wai-illustrious-t2i",
    "prompt": "masterpiece, best quality, 1girl, anime style",
    "width": 832,
    "height": 1216,
    "seed": 42,
    "steps": 28,
    "cfg": 5.0
  }'
```

## Why this is not fake-runnable

The project rule is gateway-first and environment-honest: profiles may be registered ahead of model install, but docs must not claim a live path that the host cannot execute. Anima remains the verified runnable family on this machine.
