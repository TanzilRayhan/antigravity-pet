import os
import json
import math
from PIL import Image, ImageDraw, ImageFont, ImageChops

COLUMNS = 8
V1_ROWS = 9
V2_ROWS = 11
CELL_WIDTH = 192
CELL_HEIGHT = 208

STATE_MAP = {
    "idle": (0, 6, [280, 120, 120, 140, 140, 320]),
    "running-right": (1, 8, [120] * 8),
    "running-left": (2, 8, [120] * 8),
    "waving": (3, 4, [140, 140, 140, 280]),
    "jumping": (4, 5, [130, 130, 130, 130, 260]),
    "failed": (5, 8, [140] * 8),
    "waiting": (6, 6, [150] * 6),
    "running": (7, 6, [120] * 6),
    "review": (8, 6, [150] * 6),
}

class PetDefinition:
    def __init__(self, pet_dir):
        self.pet_dir = pet_dir
        self.slug = os.path.basename(pet_dir)
        self.manifest_path = os.path.join(pet_dir, "pet.json")
        self.spritesheet_path = None
        self.display_name = self.slug.capitalize()
        self.description = ""
        self.version = 1
        self._load_manifest()

    def _load_manifest(self):
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.display_name = data.get("displayName", self.display_name)
                    self.description = data.get("description", "")
                    self.version = data.get("spriteVersionNumber", 1)
                    rel_sheet = data.get("spritesheetPath", "spritesheet.webp")
                    self.spritesheet_path = os.path.join(self.pet_dir, rel_sheet)
            except Exception as e:
                print(f"Error parsing manifest for {self.slug}: {e}")

        # Fallback to search for image if not found
        if not self.spritesheet_path or not os.path.exists(self.spritesheet_path):
            for candidate in ["spritesheet.webp", "spritesheet.png", "sheet.png"]:
                cand_path = os.path.join(self.pet_dir, candidate)
                if os.path.exists(cand_path):
                    self.spritesheet_path = cand_path
                    break

    def is_valid(self):
        return self.spritesheet_path and os.path.exists(self.spritesheet_path)


class PetSpriteSheet:
    def __init__(self, pet_def: PetDefinition, scale: float = 0.75):
        self.pet_def = pet_def
        self.scale = max(0.3, min(2.5, scale))
        self.atlas = None
        self.cell_w = CELL_WIDTH
        self.cell_h = CELL_HEIGHT
        self.target_w = int(self.cell_w * self.scale)
        self.target_h = int(self.cell_h * self.scale)
        self.frames = {}       # state_name -> list of scaled PIL Images
        self.bgra_cache = {}    # state_name -> list of premultiplied BGRA bytes
        self.delays = {}        # state_name -> list of millisecond durations
        self._load_and_slice()

    def _load_and_slice(self):
        if not self.pet_def.is_valid():
            raise FileNotFoundError(f"Missing spritesheet for {self.pet_def.slug}")

        self.atlas = Image.open(self.pet_def.spritesheet_path).convert("RGBA")
        aw, ah = self.atlas.size
        self.cell_w = aw // COLUMNS
        # V1 is 9 rows (1872px high for 1536px width, ratio ~1.22)
        # V2 is 11 rows (2288px high for 1536px width, ratio ~1.49)
        if self.pet_def.version == 2 or ah >= 2100 or (ah / aw) > 1.35:
            rows = 11
        else:
            rows = 9
        self.cell_h = ah // rows

        self.target_w = int(self.cell_w * self.scale)
        self.target_h = int(self.cell_h * self.scale)

        # Slice each state
        for state_name, (row, default_count, default_delays) in STATE_MAP.items():
            if row >= rows:
                continue
            state_frames = []
            for col in range(COLUMNS):
                x0 = col * self.cell_w
                y0 = row * self.cell_h
                x1 = x0 + self.cell_w
                y1 = y0 + self.cell_h
                cell = self.atlas.crop((x0, y0, x1, y1))
                # Only include non-empty cells
                if cell.getbbox() is not None:
                    if self.scale == 1.0:
                        scaled = cell.copy()
                    else:
                        scaled = cell.resize((self.target_w, self.target_h), Image.Resampling.LANCZOS)
                    state_frames.append(scaled)
                else:
                    if len(state_frames) >= 1:
                        # Stop at first empty column
                        break

            if not state_frames:
                # If a row was completely empty, fallback to idle frame 0
                if "idle" in self.frames and self.frames["idle"]:
                    state_frames = [self.frames["idle"][0]]
                else:
                    empty = Image.new("RGBA", (self.target_w, self.target_h), (0, 0, 0, 0))
                    state_frames = [empty]

            self.frames[state_name] = state_frames

            # Calculate delays
            delays = []
            for i in range(len(state_frames)):
                if i < len(default_delays):
                    delays.append(default_delays[i])
                else:
                    delays.append(140)
            self.delays[state_name] = delays

    def get_frame(self, state: str, frame_idx: int) -> Image.Image:
        frames = self.frames.get(state) or self.frames.get("idle")
        if not frames:
            return Image.new("RGBA", (self.target_w, self.target_h), (0, 0, 0, 0))
        return frames[frame_idx % len(frames)]

    def get_delay(self, state: str, frame_idx: int) -> int:
        delays = self.delays.get(state) or [140]
        return delays[frame_idx % len(delays)]

    def get_frame_count(self, state: str) -> int:
        frames = self.frames.get(state) or self.frames.get("idle") or []
        return len(frames)


def get_available_pets(pets_dir: str):
    """Scan directory and return list of valid PetDefinition objects."""
    pets = []
    if not os.path.exists(pets_dir):
        return pets
    for entry in sorted(os.listdir(pets_dir)):
        p_path = os.path.join(pets_dir, entry)
        if os.path.isdir(p_path):
            p = PetDefinition(p_path)
            if p.is_valid():
                pets.append(p)
    return pets


def rgba_to_premultiplied_bgra(pil_img: Image.Image) -> bytes:
    """
    Ultra-fast PIL RGBA to premultiplied 32-bit BGRA bytes using Pillow C extension.
    Runs in ~1.5ms instead of ~25ms pure Python loops, completely avoiding CPU spikes.
    """
    r, g, b, a = pil_img.split()
    # ImageChops.multiply calculates (ch * a) // 255 in compiled C
    b_prem = ImageChops.multiply(b, a)
    g_prem = ImageChops.multiply(g, a)
    r_prem = ImageChops.multiply(r, a)
    bgra_img = Image.merge("RGBA", (b_prem, g_prem, r_prem, a))
    return bgra_img.tobytes()
