"""Repaint the blue arm + hand in the bottom-left into shirt, completing Ofir's shirt.

The region to repaint is found by flooding from the left image edge through all opaque,
non-white-shirt (or skin) pixels: Ofir's thick white collar is a barrier, so the flood
grabs the arm + shadow + hand but never leaks into his shirt. That region is neutralized
to off-white and regenerated as shirt by Stable Diffusion; its alpha is made solid (finger
gaps closed) so it reads as a shoulder in a shirt rather than a hand.
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from shirt_fill import dilate, erode, close


def working_size(w: int, h: int, target: int):
    scale = target / max(w, h)
    return max(8, round(w * scale / 8) * 8), max(8, round(h * scale / 8) * 8)


def main() -> None:
    p = argparse.ArgumentParser(description="Repaint bottom-left arm/hand into shirt.")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument("--prompt", default="plain white cotton collared button-up shirt fabric, "
                   "small dark diamond print, natural daylight photo, sharp focus")
    p.add_argument("--negative", default="blue, denim, jeans, skin, hand, fingers, arm, "
                   "colorful, blurry, text, watermark")
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--guidance", type=float, default=7.5)
    p.add_argument("--size", type=int, default=512)
    p.add_argument("--model", default="stable-diffusion-v1-5/stable-diffusion-inpainting")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--debug-mask", type=Path)
    args = p.parse_args()

    img = Image.open(args.input).convert("RGBA")
    W, H = img.size
    arr = np.asarray(img)
    rgb = arr[:, :, :3].astype(np.int16)
    alpha = arr[:, :, 3]
    R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    opaque = alpha >= 128
    yy, xx = np.mgrid[0:H, 0:W]

    # --- Find the arm+hand region -----------------------------------------------------
    zone = (xx < 0.30 * W) & (yy > 0.48 * H)
    mn, ptp = rgb.min(2), rgb.max(2) - rgb.min(2)
    white_shirt = opaque & (mn > 110) & (ptp < 60)          # Ofir's shirt = flood barrier
    skin = (R > G + 8) & (G > B + 3) & (R > 100)
    candidate = opaque & zone & (~white_shirt | skin)
    seed = candidate & ((xx < 3) | (skin & zone))            # left edge + the hand
    region = seed.copy()
    prev = -1
    while int(region.sum()) != prev:
        prev = int(region.sum())
        region = (region | dilate(region, 4)) & candidate    # step<barrier width -> no leak
    region |= opaque & (xx < 0.14 * W) & (yy > 0.80 * H)     # guarantee the hand corner
    region = close(region, 10) & opaque

    # Solid alpha: fill finger-gap notches so the silhouette is a smooth shoulder.
    solid = close(region | (opaque & zone), 14)
    filled_gaps = solid & ~opaque                            # transparent notches to become shirt
    paint = region | filled_gaps                             # pixels whose colour SD must make

    print(f"region {int(region.sum())} px | filled gaps {int(filled_gaps.sum())} px")

    if args.debug_mask:
        alf = alpha[:, :, None] / 255.0
        vis = (rgb * alf + 255 * (1 - alf)).astype(np.uint8)
        vis[region] = [255, 0, 0]
        vis[filled_gaps] = [0, 0, 255]
        Image.fromarray(vis).save(args.debug_mask)
        print(f"Saved debug mask: {args.debug_mask}")

    # --- Neutralize + SD inpaint ------------------------------------------------------
    clean = arr[:, :, :3].copy()
    clean[paint] = [235, 233, 230]
    rgb_img = Image.fromarray(clean, "RGB")
    sd_mask = dilate(paint, 3)
    sd_mask_img = Image.fromarray((sd_mask * 255).astype(np.uint8), "L")

    from diffusers import StableDiffusionInpaintPipeline
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"Device: {device}. Loading {args.model} ...")
    pipe = StableDiffusionInpaintPipeline.from_pretrained(args.model, torch_dtype=dtype).to(device)
    pipe.set_progress_bar_config(disable=False)

    ww, wh = working_size(W, H, args.size)
    out = pipe(
        prompt=args.prompt, negative_prompt=args.negative,
        image=rgb_img.resize((ww, wh), Image.LANCZOS),
        mask_image=sd_mask_img.resize((ww, wh), Image.NEAREST),
        num_inference_steps=args.steps, guidance_scale=args.guidance,
        height=wh, width=ww,
        generator=torch.Generator(device=device).manual_seed(args.seed),
    ).images[0].resize((W, H), Image.LANCZOS)

    result_rgb = Image.composite(out, rgb_img, Image.fromarray((sd_mask * 255).astype(np.uint8), "L"))

    # Alpha: everything we painted becomes opaque shirt.
    out_alpha = alpha.copy()
    out_alpha[paint] = 255

    result = result_rgb.convert("RGBA")
    result.putalpha(Image.fromarray(out_alpha, "L"))
    result.save(args.output)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
