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
waiNSFWIllustrious_v150.safetensors
```

Defaults target portrait anime generation: `832x1216`, `28` steps, `CFG 5.0`.

## Install path used by this host

Download target on the Windows ComfyUI machine:

```text
C:\Chius\repo\github\ComfyUI\models\checkpoints\waiNSFWIllustrious_v150.safetensors
```

Source:

```text
https://huggingface.co/IbarakiDouji/WAI-NSFW-illustrious-SDXL/resolve/main/waiNSFWIllustrious_v150.safetensors
```

Size is about **6.9 GiB**.

## Verify inventory

```bash
curl -fsS http://10.0.0.180:8188/models/checkpoints
```

Expected to include `waiNSFWIllustrious_v150.safetensors`.

## Real generation through the gateway

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/v1/generations \
  -H 'content-type: application/json' \
  --data '{
    "profile_id": "wai-illustrious-t2i",
    "prompt": "masterpiece, best quality, 1girl, anime style, blue hair, rooftop, sunset",
    "negative_prompt": "worst quality, low quality, bad anatomy, bad hands, text, watermark",
    "width": 832,
    "height": 1216,
    "seed": 20260811,
    "steps": 20,
    "cfg": 5.0
  }'
```

Progress stream:

```bash
curl -N "http://127.0.0.1:8000/api/v1/jobs/$JOB_ID/events"
```

Cancel:

```bash
curl -fsS -X POST "http://127.0.0.1:8000/api/v1/jobs/$JOB_ID/cancel"
```

## Notes

- Anima remains the previously verified live path on this machine.
- WAI live verification depends on the checkpoint download completing and ComfyUI reloading model inventory.
- On an 8 GB laptop GPU, prefer moderate resolution/steps to reduce OOM risk.
