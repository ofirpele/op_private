"""Download YouTube audio as 320kbps MP3. No system ffmpeg needed (uses PyAV)."""

import argparse
import tempfile
from pathlib import Path

import av
import yt_dlp


def transcode_to_mp3(src: Path, dst: Path) -> None:
    with av.open(str(src)) as inp:
        in_stream = inp.streams.audio[0]
        sample_rate = in_stream.sample_rate or 44100

        with av.open(str(dst), "w") as out:
            out_stream = out.add_stream("libmp3lame", rate=sample_rate)
            out_stream.bit_rate = 320_000

            for packet in inp.demux(in_stream):
                for frame in packet.decode():
                    frame.pts = None
                    for pkt in out_stream.encode(frame):
                        out.mux(pkt)

            for pkt in out_stream.encode(None):
                out.mux(pkt)


def download(url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(Path(tmpdir) / "%(title)s.%(ext)s"),
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        src_files = [f for f in Path(tmpdir).iterdir() if f.suffix != ".part"]
        if not src_files:
            raise RuntimeError("No file was downloaded")

        src = src_files[0]
        dst = output_dir / src.with_suffix(".mp3").name
        print(f"Converting to MP3: {dst.name}")
        transcode_to_mp3(src, dst)
        print(f"Saved: {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download YouTube audio as 320kbps MP3.")
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=Path("."),
        help="Output directory (default: current directory)",
    )
    args = parser.parse_args()
    download(args.url, args.output_dir)


if __name__ == "__main__":
    main()
