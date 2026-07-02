"""Inpaint pixels of a given color using Stable Diffusion (Hugging Face Diffusers).

Unlike context-based inpainting (LaMa/OpenCV), Stable Diffusion *generates* new content
for the masked region from a text `--prompt`. Pixels within `--tolerance` of the target
color are masked (optionally grown to cover anti-aliased edges); SD then paints the mask.

To keep the rest of the image pixel-perfect, generation runs at a working resolution and
the SD output is composited back over the original *only* inside the mask.

First run downloads the SD inpainting checkpoint (several GB) from Hugging Face, cached
under ~/.cache/huggingface. On CPU, expect a few minutes per image.
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image

NAMED_COLORS = {
    "magenta": (255, 0, 255),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "red": (255, 0, 0),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}


def parse_color(value: str):
    if value.lower() in NAMED_COLORS:
        return NAMED_COLORS[value.lower()]
    parts = value.replace(" ", "").split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"Color must be a name {sorted(NAMED_COLORS)} or 'R,G,B', got: {value!r}"
        )
    return tuple(int(p) for p in parts)


def dilate(mask: np.ndarray, iterations: int) -> np.ndarray:
    """Binary dilation with a 3x3 cross, no SciPy dependency."""
    m = mask > 0
    for _ in range(iterations):
        out = m.copy()
        out[:-1, :] |= m[1:, :]
        out[1:, :] |= m[:-1, :]
        out[:, :-1] |= m[:, 1:]
        out[:, 1:] |= m[:, :-1]
        m = out
    return m


def working_size(w: int, h: int, target: int) -> tuple[int, int]:
    """Scale so the longest side is ~target, rounding each side to a multiple of 8."""
    scale = target / max(w, h)
    nw = max(8, round(w * scale / 8) * 8)
    nh = max(8, round(h * scale / 8) * 8)
    return nw, nh


def inpaint_color(src: Path, dst: Path, color, tolerance: int, grow: int,
                  prompt: str, negative: str, steps: int, guidance: float,
                  size: int, model: str, seed: int) -> None:
    from diffusers import StableDiffusionInpaintPipeline

    img = Image.open(src)
    alpha = img.getchannel("A") if img.mode == "RGBA" else None
    rgb = img.convert("RGB")
    W, H = rgb.size

    arr = np.asarray(rgb, dtype=np.int16)
    target = np.array(color, dtype=np.int16)
    mask = np.abs(arr - target).max(axis=2) <= tolerance
    if mask.sum() == 0:
        print(f"No pixels within tolerance {tolerance} of color {tuple(color)}; nothing to inpaint.")
        img.save(dst)
        print(f"Saved: {dst}")
        return
    if grow > 0:
        mask = dilate(mask, grow)
    print(f"Inpainting {int(mask.sum())} pixel(s) matching color {tuple(color)} "
          f"(tolerance {tolerance}, grow {grow}) with Stable Diffusion.")
    print(f"Model: {model} | prompt: {prompt!r} | steps: {steps} | guidance: {guidance}")

    mask_img = Image.fromarray((mask * 255).astype(np.uint8), mode="L")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"Device: {device} ({dtype}).")

    pipe = StableDiffusionInpaintPipeline.from_pretrained(model, torch_dtype=dtype)
    pipe = pipe.to(device)
    pipe.set_progress_bar_config(disable=False)

    ww, wh = working_size(W, H, size)
    small_rgb = rgb.resize((ww, wh), Image.LANCZOS)
    small_mask = mask_img.resize((ww, wh), Image.NEAREST)

    generator = torch.Generator(device=device).manual_seed(seed)
    out = pipe(
        prompt=prompt,
        negative_prompt=negative or None,
        image=small_rgb,
        mask_image=small_mask,
        num_inference_steps=steps,
        guidance_scale=guidance,
        height=wh,
        width=ww,
        generator=generator,
    ).images[0]

    generated = out.resize((W, H), Image.LANCZOS)

    # Composite: keep original everywhere except inside the mask.
    result = Image.composite(generated, rgb, mask_img)

    if alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha)

    result.save(dst)
    print(f"Saved: {dst}")


def main() -> None:
    p = argparse.ArgumentParser(description="Inpaint pixels of a given color with Stable Diffusion.")
    p.add_argument("input", type=Path, help="Path to the input image")
    p.add_argument("-o", "--output", type=Path, help="Output path (default: <input>_inpainted.png)")
    p.add_argument("-c", "--color", type=parse_color, default=(255, 0, 255),
                   help="Color to inpaint: a name or 'R,G,B' (default: magenta)")
    p.add_argument("-t", "--tolerance", type=int, default=30,
                   help="Max per-channel distance to match the color (default: 30)")
    p.add_argument("-g", "--grow", type=int, default=3,
                   help="Dilate the mask by N pixels to cover anti-aliased edges (default: 3)")
    p.add_argument("-p", "--prompt", default="",
                   help="Text prompt describing what to generate in the masked area")
    p.add_argument("-n", "--negative", default="",
                   help="Negative prompt")
    p.add_argument("--steps", type=int, default=25, help="Denoising steps (default: 25)")
    p.add_argument("--guidance", type=float, default=7.5, help="Guidance scale (default: 7.5)")
    p.add_argument("--size", type=int, default=512,
                   help="Working resolution for the longest side (default: 512)")
    p.add_argument("--model", default="stable-diffusion-v1-5/stable-diffusion-inpainting",
                   help="HF inpainting model id")
    p.add_argument("--seed", type=int, default=0, help="Random seed (default: 0)")
    args = p.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input file not found: {args.input}")

    dst = args.output or args.input.with_name(f"{args.input.stem}_inpainted.png")
    inpaint_color(args.input, dst, args.color, args.tolerance, args.grow,
                  args.prompt, args.negative, args.steps, args.guidance,
                  args.size, args.model, args.seed)


if __name__ == "__main__":
    main()
