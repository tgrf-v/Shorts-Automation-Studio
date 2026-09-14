import os
from typing import List
from app.models.caption import CaptionSegment


def format_ass_timestamp(seconds: float) -> str:
    """Formats seconds into ASS timestamp format: H:MM:SS.cc (centiseconds)"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


class SubtitleBurnInGenerator:
    """
    Generates Advanced SubStation Alpha (.ass) subtitle files tailored for
    vertical 9:16 (1080x1920) YouTube Shorts video composition with pixel-perfect
    positioning, outlines, and bold/highlight styling.
    """

    @classmethod
    def generate_ass(cls, segments: List[CaptionSegment], output_path: str) -> str:
        """
        Builds and writes a .ass subtitle file for burning in.
        Returns the absolute path to the generated file.
        """
        lines = [
            "[Script Info]",
            "Title: Shorts Automation Studio Subtitles",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            # Default style: White text, bold black outline, bottom aligned
            "Style: Default,Montserrat,64,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,260,1",
            # Bold style: Punchy heavy font
            "Style: Bold,Montserrat Black,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,2,60,60,260,1",
            # Highlight style: Vibrant gold/cyan primary color
            "Style: Highlight,Montserrat Black,76,&H0000E5FF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,260,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        for seg in segments:
            start_ts = format_ass_timestamp(seg.start_time)
            end_ts = format_ass_timestamp(seg.end_time)

            # Map style
            style_name = "Default"
            if seg.style == "bold":
                style_name = "Bold"
            elif seg.style == "highlight":
                style_name = "Highlight"

            # Position override tag: \an2 = bottom, \an5 = center, \an8 = top
            pos_tag = "\\an2"
            pos_val = seg.position.value if hasattr(seg.position, 'value') else str(seg.position)
            if pos_val == "top":
                pos_tag = "\\an8"
            elif pos_val == "center":
                pos_tag = "\\an5"

            clean_text = seg.text.replace("\n", " ").strip()
            # Escape curly braces for ASS
            clean_text = clean_text.replace("{", "(").replace("}", ")")

            event_line = f"Dialogue: 0,{start_ts},{end_ts},{style_name},,0,0,0,,{{{pos_tag}}}{clean_text}"
            lines.append(event_line)

        ass_content = "\n".join(lines) + "\n"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        return os.path.abspath(output_path)
