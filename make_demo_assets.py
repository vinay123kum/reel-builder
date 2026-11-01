"""Create the fictional demo footage and logo. No real footage is needed to try the builder."""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).parent / "demo"
D.mkdir(exist_ok=True)
for name, a, b in [("a", "0xF2B5A0", "0x6B4EE6"), ("b", "0x13B5A6", "0xFFC12E"), ("c", "0xFF4F9A", "0x2B2F77")]:
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    f"gradients=s=1080x1920:r=30:d=6:c0={a}:c1={b}:speed=0.03", "-pix_fmt", "yuv420p",
                    str(D / f"clip_{name}.mp4")], check=True, capture_output=True)
im = Image.new("RGBA", (340, 340), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.ellipse((6, 6, 334, 334), fill=(255, 255, 255, 255))
f = ImageFont.truetype(str(Path(__file__).parent / "fonts/Poppins-Black.ttf"), 150)
d.text((170, 165), "MS", font=f, fill=(47, 75, 58, 255), anchor="mm")
im.save(D / "logo.png")
print("Demo assets in", D)
