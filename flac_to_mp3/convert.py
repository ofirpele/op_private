"""Convert FLAC files to 320kbps MP3. No ffmpeg required."""

import argparse
import sys
from pathlib import Path

import lameenc
import soundfile as sf


def convert_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)

    data, sample_rate = sf.read(str(src), dtype="int16", always_2d=True)
    num_channels = data.shape[1]

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(320)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(num_channels)
    encoder.set_quality(2)

    mp3_bytes = encoder.encode(data.tobytes())
    mp3_bytes += encoder.flush()

    dst.write_bytes(mp3_bytes)
    print(f"  {src} -> {dst}")


def convert(input_path: Path, output_dir: Path | None) -> None:
    if input_path.is_file():
        if input_path.suffix.lower() != ".flac":
            print(f"Error: {input_path} is not a FLAC file.", file=sys.stderr)
            sys.exit(1)
        dst_dir = output_dir or input_path.parent
        convert_file(input_path, dst_dir / input_path.with_suffix(".mp3").name)
    elif input_path.is_dir():
        flac_files = sorted(input_path.rglob("*.flac"))
        if not flac_files:
            print(f"No FLAC files found in {input_path}", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(flac_files)} FLAC file(s).")
        for src in flac_files:
            rel = src.relative_to(input_path)
            dst = ((output_dir / rel) if output_dir else src).with_suffix(".mp3")
            convert_file(src, dst)
    else:
        print(f"Error: {input_path} does not exist.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert FLAC files to 320kbps MP3.")
    parser.add_argument("input", type=Path, help="FLAC file or folder to convert")
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=None,
        help="Output directory (default: same as input)",
    )
    args = parser.parse_args()
    convert(args.input, args.output_dir)
    print("Done.")


if __name__ == "__main__":
    main()
