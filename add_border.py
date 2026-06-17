import argparse

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description="Add a black border around an image.")
    parser.add_argument("input", help="Path to the input image")
    parser.add_argument("border-size", type=int, default=70, help="Border size in pixels")
    parser.add_argument("color", default="black", help="color")
    args = parser.parse_args()

    img = Image.open(args.input)

    border_size = args.border_size
    bordered_img = Image.new("RGB", (img.width + 2*border_size, img.height + 2*border_size), color=args.color)
    bordered_img.paste(img, (border_size, border_size))

    bordered_img.save("b_" + args.input)
    
if __name__ == "__main__":
    main()
