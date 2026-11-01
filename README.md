# reel-builder

Short-form video as code. Describe the shots in JSON and get a finished vertical Reel with every cut on the beat.

![Frames from the demo reel](docs/contact_sheet.png)

*Frames from the demo reel*

## Why it exists

Announcement Reels follow the same pattern each time. Once the format is defined, new versions shouldn't need a timeline editor.

## How it works

- Times every shot in beats, so cuts land on the music
- Renders sticker titles with a pop-in animation
- Covers each cut with a torn-paper wipe
- Synthesises an original backing track, so there's no music licensing to clear
- Adds your logo and exports H.264 at 1080x1920

## Run it

```bash
pip install -r requirements.txt
# ffmpeg must be on PATH
python make_demo_assets.py
python reel.py reel.example.json   # writes out/reel.mp4
```

## Notes

The demo uses generated gradients and a fictional brand. Sample output: [docs/demo.mp4](docs/demo.mp4). Fonts are Poppins, under the SIL Open Font License.

## Stack

Python, ffmpeg, Pillow, NumPy

Built by [Vinay Kumar](https://vinaykumar.work) with Claude Code. I set the design and rules and reviewed the output.
