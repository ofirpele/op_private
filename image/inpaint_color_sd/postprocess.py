"""Refine the shirt-filled result (self-contained -- needs only the shirt PNG):
  * sharpen the soft SD-generated (right) shirt so it matches the crisp left shirt,
  * feather the alpha along the right silhouette edge for a soft, anti-aliased cutout.

The "right shirt" region is found geometrically: opaque, bottom-right, not skin.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from shirt_fill import dilate, erode, close


def main() -> None:
    p = argparse.ArgumentParser(description="Sharpen + feather the right shirt region.")
    p.add_argument("input", type=Path, help="Shirt-filled RGBA image to refine")
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument("--detail-thr", type=float, default=4.5,
                   help="Sharpen pixels whose local detail is below this (soft = SD-generated)")
    p.add_argument("--sharpen", type=float, default=180.0, help="UnsharpMask percent")
    p.add_argument("--sharpen-radius", type=float, default=2.0)
    p.add_argument("--feather", type=float, default=1.6, help="Alpha feather blur radius (px)")
    p.add_argument("--debug-mask", type=Path)
    args = p.parse_args()

    cur = Image.open(args.input).convert("RGBA")
    W, H = cur.size
    arr = np.asarray(cur)
    rgb = arr[:, :, :3].astype(np.int16)
    alpha = arr[:, :, 3]
    R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]

    opaque = alpha >= 128
    trans = ~opaque
    yy, xx = np.mgrid[0:H, 0:W]

    # Local-detail map: FIND_EDGES then blur = how much fine texture is around each pixel.
    # The crisp real shirt reads high (~8); the soft SD fill reads low (~2).
    edges = cur.convert("L").filter(ImageFilter.FIND_EDGES)
    detail = np.asarray(edges.filter(ImageFilter.GaussianBlur(8))).astype(float)

    # Right shirt to sharpen: soft (low detail), neutral-colored (white/gray shirt, not warm
    # skin/scalp where R >> B), below the face, on the right side.
    neutral = np.abs(R - B) < 22
    region = opaque & neutral & (detail < args.detail_thr) & (xx > 0.5 * W) & (yy > 0.52 * H)
    region = dilate(erode(region, 1), 1)   # open: drop isolated speckle
    region = region & opaque

    # --- Sharpen the region (fade the mask so there is no seam at its border) -----------
    rgb_img = cur.convert("RGB")
    sharp = rgb_img.filter(ImageFilter.UnsharpMask(radius=args.sharpen_radius,
                                                   percent=int(args.sharpen), threshold=1))
    mask = Image.fromarray((region * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(4))
    result_rgb = Image.composite(sharp, rgb_img, mask)

    # --- Feather the alpha on the RIGHT shirt silhouette edge ---------------------------
    edge = dilate(trans, 2) & dilate(opaque, 2)          # opaque/transparent boundary
    right_edge = edge & (xx > 0.5 * W) & (yy > 0.5 * H)  # right side, shirt (not head)
    band = dilate(right_edge, 3)
    alpha_blur = np.asarray(cur.getchannel("A").filter(ImageFilter.GaussianBlur(args.feather)))
    out_alpha = np.where(band, alpha_blur, alpha).astype(np.uint8)

    print(f"sharpened region {int(region.sum())} px | feathered edge band {int(band.sum())} px")

    if args.debug_mask:
        dbg = np.asarray(rgb_img).copy()
        dbg[region] = (0.5 * dbg[region] + [0, 100, 0]).astype(np.uint8)
        dbg[band] = [255, 0, 0]
        Image.fromarray(dbg).save(args.debug_mask)
        print(f"Saved debug mask: {args.debug_mask}")

    result = result_rgb.convert("RGBA")
    result.putalpha(Image.fromarray(out_alpha, "L"))
    result.save(args.output)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
