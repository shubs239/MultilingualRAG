"""
shorts_audio.py — Stage 2 of the YouTube Shorts pipeline
Reads production_sheet.json, generates audio per segment via ElevenLabs
(with Gemini TTS as fallback), then stitches full_audio.mp3 with pydub.
"""

import json
import os
import struct
import sys
import wave
from io import BytesIO

from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "cgSgspJ2msm6clMCkdW9")
API_KEY = os.getenv("API_KEY")

PRODUCTION_SHEET = "video/production_sheet.json"
AUDIO_DIR = "video/audio"


# ── ElevenLabs ────────────────────────────────────────────────────────────────

def generate_elevenlabs(seg: dict) -> bytes:
    from elevenlabs import ElevenLabs, VoiceSettings
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    el = seg["elevenlabs"]
    text = f"{el['emotion_tag']} {seg['spoken_text']}"
    audio_gen = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=el["stability"],
            similarity_boost=el["similarity_boost"],
            style=el["style"],
            use_speaker_boost=el["use_speaker_boost"],
        ),
    )
    # Generator → bytes
    chunks = []
    for chunk in audio_gen:
        if chunk:
            chunks.append(chunk)
    return b"".join(chunks)


# ── Gemini TTS fallback ───────────────────────────────────────────────────────

def generate_gemini_tts(seg: dict) -> bytes:
    from google import genai
    from google.genai import types

    if not API_KEY:
        raise EnvironmentError("API_KEY not set in .env")

    client = genai.Client(api_key=API_KEY)
    style_instruction = seg["gemini_tts"]["style_instruction"]
    text = f"{style_instruction} {seg['spoken_text']}"

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"
                    )
                )
            ),
        ),
    )

    # Extract audio bytes from the response
    audio_data = response.candidates[0].content.parts[0].inline_data.data
    # Gemini returns raw PCM; wrap in WAV container for pydub compatibility
    return _pcm_to_wav(audio_data)


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000, channels: int = 1, sampwidth: int = 2) -> bytes:
    """Wrap raw PCM bytes in a WAV header."""
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


# ── Helpers ───────────────────────────────────────────────────────────────────

def measure_duration(mp3_path: str) -> float:
    """Return duration in seconds using pydub."""
    from pydub import AudioSegment
    audio = AudioSegment.from_file(mp3_path)
    return len(audio) / 1000.0


def save_audio(audio_bytes: bytes, path: str, from_gemini: bool = False) -> None:
    """Save audio bytes. Gemini returns WAV; convert to MP3 via pydub."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if from_gemini:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(BytesIO(audio_bytes), format="wav")
        seg.export(path, format="mp3", bitrate="128k")
    else:
        with open(path, "wb") as f:
            f.write(audio_bytes)


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_audio(sheet_file: str = PRODUCTION_SHEET) -> None:
    print(f"Loading {sheet_file} …")
    with open(sheet_file, "r", encoding="utf-8") as f:
        sheet = json.load(f)

    os.makedirs(AUDIO_DIR, exist_ok=True)

    if "audio" not in sheet:
        sheet["audio"] = {"provider": None, "segment_files": {}}

    segments = sheet["segments"]
    segment_files = {}
    provider_used = None
    el_quota_exhausted = False

    for seg in segments:
        seg_id = seg["id"]
        out_path = f"{AUDIO_DIR}/segment-{seg_id}.mp3"
        print(f"\n  Segment {seg_id}: {seg['emotion']} — {seg['estimated_duration_sec']:.0f}s est.")

        audio_bytes = None
        provider = None

        # Try ElevenLabs unless quota is known exhausted
        if ELEVENLABS_API_KEY and not el_quota_exhausted:
            try:
                print(f"    → ElevenLabs (voice={ELEVENLABS_VOICE_ID}) …")
                audio_bytes = generate_elevenlabs(seg)
                provider = "elevenlabs"
            except Exception as e:
                err_str = str(e)
                print(f"    ElevenLabs error: {err_str}")
                if "quota" in err_str.lower() or "429" in err_str or "insufficient_quota" in err_str.lower():
                    print("    Quota exhausted — switching all remaining segments to Gemini TTS")
                    el_quota_exhausted = True
                # Fall through to Gemini TTS

        # Gemini TTS fallback
        if audio_bytes is None:
            try:
                print(f"    → Gemini TTS fallback …")
                audio_bytes = generate_gemini_tts(seg)
                provider = "gemini"
            except Exception as e:
                print(f"    Gemini TTS error: {e}")
                print(f"    Skipping segment {seg_id} — no audio generated")
                continue

        from_gemini = provider == "gemini"
        save_audio(audio_bytes, out_path, from_gemini=from_gemini)
        if provider_used is None:
            provider_used = provider

        actual_duration = measure_duration(out_path)
        print(f"    Saved → {out_path} ({actual_duration:.1f}s actual)")

        segment_files[str(seg_id)] = {
            "file": out_path,
            "actual_duration_sec": round(actual_duration, 2),
        }

    # Compute start/end times from actual durations
    cursor = 0.0
    for seg in segments:
        seg_id_str = str(seg["id"])
        if seg_id_str in segment_files:
            dur = segment_files[seg_id_str]["actual_duration_sec"]
            segment_files[seg_id_str]["start_sec"] = round(cursor, 2)
            segment_files[seg_id_str]["end_sec"] = round(cursor + dur, 2)
            cursor += dur

    # Stitch full audio
    full_audio_path = f"{AUDIO_DIR}/full_audio.mp3"
    stitch_audio(segment_files, full_audio_path)

    sheet["audio"] = {
        "provider": provider_used,
        "segment_files": segment_files,
        "full_audio": full_audio_path,
        "total_duration_sec": round(cursor, 2),
    }

    with open(sheet_file, "w", encoding="utf-8") as f:
        json.dump(sheet, f, ensure_ascii=False, indent=2)

    print(f"\n  Total audio duration : {cursor:.1f}s")
    print(f"  Full audio saved → {full_audio_path}")
    print(f"  Updated {sheet_file}")


def stitch_audio(segment_files: dict, output_path: str) -> None:
    from pydub import AudioSegment
    print(f"\n  Stitching {len(segment_files)} segments → {output_path} …")
    combined = AudioSegment.empty()
    for seg_id_str in sorted(segment_files.keys(), key=lambda x: int(x)):
        path = segment_files[seg_id_str]["file"]
        if os.path.exists(path):
            combined += AudioSegment.from_file(path, format="mp3")
        else:
            print(f"    Warning: {path} not found, skipping")
    combined.export(output_path, format="mp3", bitrate="128k")
    print(f"    Done ({len(combined)/1000:.1f}s total)")


if __name__ == "__main__":
    sheet_file = sys.argv[1] if len(sys.argv) > 1 else PRODUCTION_SHEET
    generate_audio(sheet_file)
