from comfy_helper.workflows.profile import (
    ParameterBinding,
    WorkflowDefaults,
    WorkflowProfile,
)

ANIMA_TURBO_TEMPLATE = {
    "1": {
        "class_type": "UNETLoader",
        "inputs": {
            "unet_name": "anima-turbo-v1.0.safetensors",
            "weight_dtype": "default",
        },
    },
    "2": {
        "class_type": "CLIPLoader",
        "inputs": {"clip_name": "qwen_3_06b_base.safetensors", "type": "qwen_image"},
    },
    "3": {
        "class_type": "VAELoader",
        "inputs": {"vae_name": "qwen_image_vae.safetensors"},
    },
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
    "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
    "6": {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
    },
    "7": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 0,
            "steps": 10,
            "cfg": 1.0,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1.0,
            "model": ["1", 0],
            "positive": ["4", 0],
            "negative": ["5", 0],
            "latent_image": ["6", 0],
        },
    },
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
    "9": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "comfy-helper/anima-turbo", "images": ["8", 0]},
    },
}


class WorkflowRegistry:
    def __init__(self, profiles: list[WorkflowProfile]) -> None:
        self._profiles = {profile.id: profile for profile in profiles}

    def list(self) -> list[WorkflowProfile]:
        return list(self._profiles.values())

    def get(self, profile_id: str) -> WorkflowProfile:
        try:
            return self._profiles[profile_id]
        except KeyError as exc:
            raise KeyError(f"unknown workflow profile: {profile_id}") from exc


def get_default_registry() -> WorkflowRegistry:
    return WorkflowRegistry(
        [
            WorkflowProfile(
                id="anima-turbo-t2i",
                name="Anima Turbo text-to-image",
                description="Fast square anime illustration profile for the installed Anima Turbo model.",
                model_family="anima",
                model_dependencies=[
                    "anima-turbo-v1.0.safetensors",
                    "qwen_3_06b_base.safetensors",
                    "qwen_image_vae.safetensors",
                ],
                defaults=WorkflowDefaults(
                    negative_prompt="worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, extra fingers, bad hands, text, watermark",
                    width=1024,
                    height=1024,
                    steps=10,
                    cfg=1.0,
                ),
                template=ANIMA_TURBO_TEMPLATE,
                bindings={
                    "prompt": ParameterBinding(node_id="4", input_name="text"),
                    "negative_prompt": ParameterBinding(node_id="5", input_name="text"),
                    "width": ParameterBinding(node_id="6", input_name="width"),
                    "height": ParameterBinding(node_id="6", input_name="height"),
                    "seed": ParameterBinding(node_id="7", input_name="seed"),
                    "steps": ParameterBinding(node_id="7", input_name="steps"),
                    "cfg": ParameterBinding(node_id="7", input_name="cfg"),
                },
            )
        ]
    )
