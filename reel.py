"""Build a beat-locked 1080x1920 Reel from a JSON spec.

    python make_demo_assets.py      # creates fictional footage + logo in demo/
    python reel.py reel.example.json

Each shot is timed in beats, so every cut lands on the music. Stickers pop in with a small
wobble, a torn-paper wipe covers each cut, and an original backing track is synthesised.
"""
import json, math, random, shutil, subprocess, sys, wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).parent
W, H, FPS = 1080, 1920, 30
FONTS = ROOT / "fonts"
WORK = ROOT / "work"


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit("ffmpeg failed:\n" + r.stderr[-1500:])


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)


def rgb(h, a=255):
    h = h.lstrip("#")
    return int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16), a


def sticker(lines, angle=-4, plate="#FFFFFF", pad=(46, 26)):
    """lines = [[text, weight, size, color]]. Rounded plate with a soft shadow, rotated."""
    fl = [(t, font(wt, sz), c) for t, wt, sz, c in lines]
    ws = [f.getlength(t) for t, f, _ in fl]
    hs = [f.getbbox(t)[3] - f.getbbox("H")[1] for t, f, _ in fl]
    gap, m = 6, 60
    w = int(max(ws) + 2 * pad[0]); h = int(sum(hs) + gap * (len(hs) - 1) + 2 * pad[1])
    img = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((m, m + 10, m + w, m + h + 10), 34, fill=110)
    img.paste((30, 10, 60, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((m, m, m + w, m + h), 34, fill=rgb(plate))
    y = m + pad[1]
    for (t, f, c), tw, th in zip(fl, ws, hs):
        d.text((m + (w - tw) / 2, y - f.getbbox("H")[1]), t, font=f, fill=rgb(c))
        y += th + gap
    return img.rotate(angle, resample=Image.BICUBIC, expand=True)


def pop_in(name, img, cx, cy, frames=10):
    """0 -> 118% -> 100% with a slight wobble, as full-frame RGBA PNGs."""
    out = WORK / "seq" / name
    out.mkdir(parents=True, exist_ok=True)
    for i in range(frames):
        p = (i + 1) / frames
        s = (1 - (1 - p) ** 3) * (1 + .18 * math.sin(p * math.pi))
        rot = 6 * (1 - p) * math.cos(p * 6)
        im = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC).rotate(rot, Image.BICUBIC, expand=True)
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fr.alpha_composite(im, (max(0, int(cx - im.width / 2)), max(0, int(cy - im.height / 2))))
        fr.save(out / f"{i:03d}.png")
    return out


def torn_edge(seed, amp=22):
    rnd, pts, x = random.Random(seed), [], 0.0
    for y in range(0, H + 24, 24):
        x = max(-amp, min(amp, x + rnd.uniform(-amp, amp) * .6))
        pts.append((x + rnd.uniform(-6, 6), y))
    return pts


def torn_wipe(n=14):
    """A paper sheet slides right to left and fully covers the frame at the midpoint."""
    out = WORK / "seq" / "torn"
    out.mkdir(parents=True, exist_ok=True)
    sw, le, ri = 1500, torn_edge(1), torn_edge(2)
    for i in range(n):
        t = i / (n - 1); p = t * t * (3 - 2 * t)
        x0 = W + 60 - p * (W + sw + 120)
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        poly = [(x0 + dx, y) for dx, y in le] + [(x0 + sw + dx, y) for dx, y in reversed(ri)]
        ImageDraw.Draw(im).polygon(poly, fill=(250, 247, 240, 255))
        im.save(out / f"{i:03d}.png")
    return out, n


def music(total, beat, path):
    """Original four-chord backing: kick, clap, bass and pluck."""
    sr = 48000; N = int((total + 1) * sr); mix = np.zeros(N)
    notes = {"C": 261.63, "D": 293.66, "E": 329.63, "F": 349.23, "G": 392.0, "A": 440.0, "B": 493.88}
    prog = [("C", "CEG"), ("G", "GBD"), ("A", "ACE"), ("F", "FAC")]
    rng = np.random.default_rng(3)

    def add(sig, start):
        i = int(start * sr); e = min(N, i + len(sig))
        if i < N:
            mix[i:e] += sig[:e - i]

    for k in range(int((total + 1) / beat) + 1):
        bt = k * beat; bar, b = divmod(k, 4); root, chord = prog[bar % 4]
        x = np.arange(int(.18 * sr)) / sr
        add(.55 * np.sin(2 * np.pi * (50 + 70 * np.exp(-x * 30)) * x) * np.exp(-x * 18), bt)
        if b in (1, 3):
            nz = np.diff(rng.standard_normal(int(.12 * sr)), prepend=0)
            add(.18 * nz * np.exp(-np.arange(len(nz)) / sr * 28), bt)
        if b in (0, 2):
            f = notes[root] / 4; x = np.arange(int(.42 * sr)) / sr
            add(.3 * (np.sin(2 * np.pi * f * x) + .3 * np.sin(4 * np.pi * f * x)) * np.exp(-x * 5), bt)
        for h, nn in enumerate((chord[(b * 2) % 3], chord[(b * 2 + 1) % 3])):
            f = notes[nn] * 2; x = np.arange(int(.35 * sr)) / sr
            add(.07 * (np.sin(2 * np.pi * f * x) + .4 * np.sin(4 * np.pi * f * x)) * np.exp(-x * 9), bt + h * beat / 2)
    mix = (np.tanh(mix * 1.2) * .6)[:int(total * sr)]
    st = np.stack([mix, np.roll(mix, int(.012 * sr))], 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype("<i2").tobytes())


def render_shot(i, s, dur, base):
    out = WORK / f"shot_{i:02d}.mp4"
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p"
    cmd = ["ffmpeg", "-y", "-ss", s.get("ss", 0), "-t", dur, "-i", base / s["src"]]
    if s.get("sticker"):
        st = s["sticker"]
        seq = pop_in(f"sticker_{i}", sticker(st["lines"], st.get("angle", -4)), st.get("x", W / 2), st.get("y", H / 2))
        cmd += ["-framerate", FPS, "-i", seq / "%03d.png", "-filter_complex",
                f"[0:v]{vf}[b];[b][1:v]overlay=eof_action=repeat:format=auto[v]", "-map", "[v]"]
    else:
        cmd += ["-vf", vf]
    run(cmd + ["-t", dur, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-an", out])
    return out


def build(spec_path):
    spec_path = Path(spec_path).resolve()
    spec, base = json.loads(spec_path.read_text(encoding="utf-8")), spec_path.parent
    beat = 60 / spec.get("bpm", 120)
    shutil.rmtree(WORK, ignore_errors=True); WORK.mkdir()
    durs = [s["beats"] * beat for s in spec["shots"]]
    clips = [render_shot(i, s, d, base) for i, (s, d) in enumerate(zip(spec["shots"], durs))]
    (WORK / "concat.txt").write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", WORK / "concat.txt", "-c", "copy", WORK / "body.mp4"])

    total = sum(durs)
    music(total, beat, WORK / "music.wav")
    seq, n = torn_wipe()
    cuts = [sum(durs[:i]) for i in range(1, len(durs))]
    cmd = ["ffmpeg", "-y", "-i", WORK / "body.mp4"]
    for c in cuts:
        cmd += ["-framerate", FPS, "-itsoffset", round(c - n / FPS / 2, 3), "-i", seq / "%03d.png"]
    idx, graph, last = len(cuts) + 1, [], "0:v"
    for i in range(len(cuts)):
        graph.append(f"[{last}][{i + 1}:v]overlay=eof_action=pass:format=auto[t{i}]"); last = f"t{i}"
    if spec.get("logo"):
        cmd += ["-i", base / spec["logo"]]
        graph.append(f"[{idx}:v]scale=170:-1[lg];[{last}][lg]overlay=W-w-50:60[vf]"); last = "vf"; idx += 1
    cmd += ["-i", WORK / "music.wav", "-filter_complex", ";".join(graph), "-map", f"[{last}]", "-map", f"{idx}:a",
            "-t", round(total, 3), "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart"]
    out = base / spec.get("output", "out/reel.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    run(cmd + [out])
    print(f"Wrote {out} ({total:.1f}s, {len(clips)} shots)")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "reel.example.json")
