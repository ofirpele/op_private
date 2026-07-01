"""Remove the background from an image (U^2-Net via rembg). Outputs a transparent PNG."""

import argparse
from pathlib import Path

from PIL import Image
from rembg import remove


def remove_background(src: Path, dst: Path, bgcolor=None) -> None:
    with Image.open(src) as img:
        result = remove(img.convert("RGBA"))

    if bgcolor is not None:
        background = Image.new("RGBA", result.size, tuple(bgcolor))
        background.paste(result, mask=result)
        result = background

    result.save(dst)
    print(f"Saved: {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove the background from an image.")
    parser.add_argument("input", type=Path, help="Path to the input image")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output path (default: <input>_nobg.png)",
    )
    parser.add_argument(
        "--bgcolor", type=int, nargs=4, metavar=("R", "G", "B", "A"),
        help="Fill the background with a solid RGBA color instead of transparency",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input file not found: {args.input}")

    dst = args.output or args.input.with_name(f"{args.input.stem}_nobg.png")
    remove_background(args.input, dst, args.bgcolor)


if __name__ == "__main__":
    main()
