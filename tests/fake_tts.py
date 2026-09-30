"""Local media-pipeline test double; never used by GitHub Actions publishing."""

import math
import struct
import sys
import wave

args = sys.argv[1:]
output = args[args.index("-w") + 1]
speech = " ".join(arg for arg in args if not arg.startswith("-") and arg != output and not arg.startswith("en-"))
duration = max(0.4, len(speech.split()) * 0.37)
rate = 22050
with wave.open(output, "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(rate)
    frames = bytearray()
    for n in range(int(rate * duration)):
        sample = int(1000 * math.sin(2 * math.pi * 440 * n / rate))
        frames.extend(struct.pack("<h", sample))
    wav.writeframes(frames)
