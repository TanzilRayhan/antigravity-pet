import time
from PIL import Image, ImageDraw, ImageFont

class SpeechManager:
    def __init__(self):
        self.current_text = ""
        self.expire_time = 0.0
        self.font = None
        self._load_font()

    def _load_font(self):
        try:
            # Try Windows system font (Segoe UI, Arial, Tahoma)
            for f_name in ["segoeui.ttf", "arial.ttf", "tahoma.ttf"]:
                f_path = f"C:\\Windows\\Fonts\\{f_name}"
                try:
                    self.font = ImageFont.truetype(f_path, 13)
                    break
                except Exception:
                    continue
        except Exception:
            pass
        if not self.font:
            self.font = ImageFont.load_default()

    def say(self, text: str, duration: float = 2.8):
        self.current_text = text
        self.expire_time = time.time() + duration

    def is_active(self) -> bool:
        return time.time() < self.expire_time and bool(self.current_text)

    def get_text(self) -> str:
        if self.is_active():
            return self.current_text
        return ""

    def render_bubble(self, max_width: int = 180) -> Image.Image:
        """Render a speech bubble as an RGBA image."""
        if not self.is_active():
            return None

        text = self.current_text
        # Measure text using getbbox
        try:
            bbox = self.font.getbbox(text)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except Exception:
            tw, th = len(text) * 7, 14

        pad_x = 12
        pad_y = 6
        bubble_w = max(70, min(max_width, tw + pad_x * 2))
        bubble_h = th + pad_y * 2
        tail_h = 7
        total_h = bubble_h + tail_h + 4

        img = Image.new("RGBA", (bubble_w + 8, total_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        # Bubble rect
        x0, y0 = 4, 2
        x1, y1 = x0 + bubble_w, y0 + bubble_h

        # Shadow
        d.rounded_rectangle([x0 + 1, y0 + 1, x1 + 1, y1 + 1], radius=8, fill=(0, 0, 0, 40))

        # Main white bubble
        d.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=(255, 255, 255, 245), outline=(30, 41, 59, 220), width=2)

        # Speech tail pointing down-center
        cx = (x0 + x1) // 2
        tail_pts = [(cx - 5, y1 - 1), (cx + 5, y1 - 1), (cx, y1 + tail_h)]
        d.polygon(tail_pts, fill=(255, 255, 255, 245), outline=(30, 41, 59, 220))
        # Clear seam
        d.line([(cx - 4, y1 - 1), (cx + 4, y1 - 1)], fill=(255, 255, 255, 255), width=2)

        # Draw text centered
        tx = x0 + (bubble_w - tw) // 2
        ty = y0 + (bubble_h - th) // 2 - 1
        d.text((tx, ty), text, font=self.font, fill=(15, 23, 42, 255))

        return img
