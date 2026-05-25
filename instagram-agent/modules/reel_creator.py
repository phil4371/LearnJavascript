import subprocess
import tempfile
import shutil
from pathlib import Path


class ReelCreator:
    """Erstellt ein 9:16 Reel aus 4 Bildern via FFmpeg (Ken-Burns + Crossfade + Musik)."""

    FRAME_DURATION = 5      # Sekunden pro Bild
    TRANSITION_DURATION = 1  # Sekunden Crossfade
    OUTPUT_W = 1080
    OUTPUT_H = 1920

    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir
        self.music_dir = assets_dir / "music"
        self.font_dir = assets_dir / "fonts"
        self._check_ffmpeg()

    def create(
        self,
        image_paths: list[Path],
        output_path: Path,
        title: str = "",
        cta: str = "",
        music_file: Path = None,
    ) -> Path:
        if len(image_paths) < 2:
            raise ValueError("Mindestens 2 Bilder benötigt")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            scaled = self._scale_images(image_paths, tmp)
            raw_video = tmp / "raw.mp4"
            self._ken_burns_concat(scaled, raw_video, title, cta)
            if music_file and music_file.exists():
                self._add_music(raw_video, music_file, output_path)
            else:
                shutil.copy(raw_video, output_path)
        return output_path

    def _scale_images(self, image_paths: list[Path], tmp: Path) -> list[Path]:
        scaled = []
        for i, src in enumerate(image_paths):
            dst = tmp / f"img_{i:02d}.jpg"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(src),
                    "-vf", f"scale={self.OUTPUT_W}:{self.OUTPUT_H}:force_original_aspect_ratio=increase,"
                           f"crop={self.OUTPUT_W}:{self.OUTPUT_H}",
                    str(dst),
                ],
                check=True, capture_output=True,
            )
            scaled.append(dst)
        return scaled

    def _ken_burns_concat(self, images: list[Path], output: Path, title: str, cta: str):
        n = len(images)
        total = n * self.FRAME_DURATION

        # Input-Argumente
        inputs = []
        for img in images:
            inputs += ["-loop", "1", "-t", str(self.FRAME_DURATION + self.TRANSITION_DURATION), "-i", str(img)]

        # Filterchain: zoompan pro Bild + xfade-Kette
        filter_parts = []
        for i in range(n):
            # Leichter Ken-Burns Zoom (1.0 → 1.05)
            zoom = f"[{i}:v]zoompan=z='min(zoom+0.001,1.05)':d={self.FRAME_DURATION * 25}:"
            zoom += f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            zoom += f"s={self.OUTPUT_W}x{self.OUTPUT_H},setpts=PTS-STARTPTS,fps=25[v{i}]"
            filter_parts.append(zoom)

        # Xfade-Kette
        prev = "v0"
        offset = self.FRAME_DURATION - self.TRANSITION_DURATION
        for i in range(1, n):
            out = f"xf{i}" if i < n - 1 else "vout_notxt"
            xf = f"[{prev}][v{i}]xfade=transition=fade:duration={self.TRANSITION_DURATION}:offset={offset}[{out}]"
            filter_parts.append(xf)
            prev = out
            offset += self.FRAME_DURATION

        # Textüberlagerung
        txt_filter = "[vout_notxt]"
        if title:
            safe_title = title.replace("'", "\\'").replace(":", "\\:")[:60]
            font_path = self._find_font()
            txt_filter += (
                f"drawtext=text='{safe_title}':fontfile={font_path}:"
                f"fontsize=52:fontcolor=white:borderw=3:bordercolor=black:"
                f"x=(w-text_w)/2:y=h*0.08,"
            )
        if cta:
            safe_cta = cta.replace("'", "\\'").replace(":", "\\:")[:80]
            font_path = self._find_font()
            txt_filter += (
                f"drawtext=text='{safe_cta}':fontfile={font_path}:"
                f"fontsize=38:fontcolor=white:borderw=2:bordercolor=black:"
                f"x=(w-text_w)/2:y=h*0.88"
            )
        txt_filter = txt_filter.rstrip(",") + "[vfinal]"
        filter_parts.append(txt_filter)

        filter_complex = ";".join(filter_parts)

        cmd = (
            inputs
            + ["-filter_complex", filter_complex, "-map", "[vfinal]",
               "-t", str(total), "-c:v", "libx264", "-preset", "fast",
               "-crf", "23", "-pix_fmt", "yuv420p", "-y", str(output)]
        )
        subprocess.run(["ffmpeg"] + cmd, check=True, capture_output=True)

    def _add_music(self, video: Path, music: Path, output: Path):
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(video),
                "-i", str(music),
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-af", "afade=t=out:st=" + str(self.FRAME_DURATION * 4 - 2) + ":d=2",
                "-shortest",
                str(output),
            ],
            check=True, capture_output=True,
        )

    def _find_font(self) -> str:
        candidates = list(self.font_dir.glob("*.ttf")) if self.font_dir.exists() else []
        if candidates:
            return str(candidates[0])
        # System-Fallback
        for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                     "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]:
            if Path(path).exists():
                return path
        return "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

    def _check_ffmpeg(self):
        if not shutil.which("ffmpeg"):
            raise EnvironmentError("ffmpeg nicht gefunden — bitte installieren: sudo apt install ffmpeg")
