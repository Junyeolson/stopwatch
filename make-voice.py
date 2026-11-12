"""Generate natural Korean narration with edge-tts (Microsoft neural voices)
and embed it into shorts.html (built from template.html).

Usage:  python make-voice.py [--voice ko-KR-SunHiNeural] [--rate +25%]
Voices: ko-KR-SunHiNeural (F), ko-KR-InJoonNeural (M), ko-KR-HyunsuMultilingualNeural (M)
"""
import argparse, asyncio, base64, json, os, sys

import edge_tts
from mutagen.mp3 import MP3

DIR = os.path.dirname(os.path.abspath(__file__))
MAX_SPEECH = 28.5  # seconds; timeline is 30s total


async def synth(text, voice, rate, path):
    """Save MP3 and return when speech actually ends (seconds), ignoring trailing silence."""
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:  # older edge-tts without the boundary option
        comm = edge_tts.Communicate(text, voice, rate=rate)
    end = 0.0
    with open(path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif "Boundary" in chunk["type"]:
                end = max(end, (chunk["offset"] + chunk["duration"]) / 1e7)
    return end


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="ko-KR-SunHiNeural")
    ap.add_argument("--rate", default="+25%")
    a = ap.parse_args()

    with open(os.path.join(DIR, "script.json"), encoding="utf-8") as f:
        script = json.load(f)
    tmp = os.path.join(DIR, "voice")
    os.makedirs(tmp, exist_ok=True)

    out, total = [], 0.0
    for seg in script:
        path = os.path.join(tmp, seg["id"] + ".mp3")
        spoken = await synth(seg.get("tts", seg["say"]), a.voice, a.rate, path)
        length = MP3(path).info.length
        # timeline slot = real speech end + small tail (fallback: full file length)
        dur = min(length, spoken + 0.25) if spoken > 0 else length
        total += dur
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        out.append({"id": seg["id"], "dur": round(dur, 3), "b64": b64})
        print(f"{seg['id']:<6} {dur:5.2f}s  {seg['say']}")
    print(f"speech total: {total:.2f}s  (voice={a.voice}, rate={a.rate})")
    if total > MAX_SPEECH:
        print(f"WARNING: speech exceeds {MAX_SPEECH}s - use a faster --rate", file=sys.stderr)

    with open(os.path.join(DIR, "template.html"), encoding="utf-8") as f:
        tpl = f.read()
    html = tpl.replace("/*VOICE_DATA*/[]", json.dumps(out, separators=(",", ":")))
    with open(os.path.join(DIR, "shorts.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("wrote shorts.html")


asyncio.run(main())
