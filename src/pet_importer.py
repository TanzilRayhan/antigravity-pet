import os
import io
import json
import time
import zipfile
import math
from PIL import Image, ImageSequence, ImageOps

COLUMNS = 8
V1_ROWS = 9
CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_W = COLUMNS * CELL_WIDTH  # 1536
ATLAS_H = V1_ROWS * CELL_HEIGHT # 1872

def sanitize_slug(name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or f"pet-{int(time.time())}"

def fit_and_center_cell(src_img: Image.Image, cell_w=CELL_WIDTH, cell_h=CELL_HEIGHT, pad=12) -> Image.Image:
    """Resize image to fit cleanly within cell bounds while preserving aspect ratio, centered."""
    src = src_img.convert("RGBA")
    max_w = cell_w - (pad * 2)
    max_h = cell_h - (pad * 2)
    
    sw, sh = src.size
    if sw <= 0 or sh <= 0:
        return Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))

    ratio = min(max_w / sw, max_h / sh)
    nw = max(1, int(sw * ratio))
    nh = max(1, int(sh * ratio))
    
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    cell = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))
    
    # Place bottom-aligned or centered
    ox = (cell_w - nw) // 2
    oy = (cell_h - nh) // 2
    cell.paste(resized, (ox, oy), resized)
    return cell

def convert_image_or_gif_to_spritesheet(file_bytes: bytes, ext: str, target_dir: str, name: str, desc: str) -> dict:
    """
    Takes raw file bytes (GIF, PNG, WEBP, JPG) and synthesizes a 100% compliant
    8x9 Codex spritesheet with pet.json metadata.
    """
    os.makedirs(target_dir, exist_ok=True)
    slug = os.path.basename(target_dir)

    # Open image
    img_stream = io.BytesIO(file_bytes)
    im = Image.open(img_stream)

    # Check if already a full spritesheet (e.g. 1536x1872 or 8x9 ratio)
    aw, ah = im.size
    is_already_sheet = (aw >= 600 and ah >= 700 and (aw % 8 == 0) and (ah / aw > 1.0 and ah / aw < 1.6))
    
    if is_already_sheet and not getattr(im, "is_animated", False):
        sheet_path = os.path.join(target_dir, "spritesheet.webp")
        im.convert("RGBA").save(sheet_path, "WEBP", quality=100, method=6)
        
        ver = 2 if (ah / aw) > 1.35 else 1
        meta = {
            "id": slug,
            "displayName": name,
            "description": desc,
            "spriteVersionNumber": ver,
            "spritesheetPath": "spritesheet.webp"
        }
        with open(os.path.join(target_dir, "pet.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return {"success": True, "slug": slug, "name": name}

    # Extract frames if animated GIF / WEBP
    frames = []
    try:
        for frame in ImageSequence.Iterator(im):
            frames.append(frame.copy().convert("RGBA"))
    except Exception:
        frames = [im.convert("RGBA")]

    if not frames:
        frames = [im.convert("RGBA")]

    # Create empty 8x9 atlas
    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))

    # Pre-process cell frames
    cell_frames = [fit_and_center_cell(f) for f in frames]
    num_frames = len(cell_frames)

    # Generate animations per row
    def get_frame(seq, idx):
        return seq[idx % len(seq)]

    # Row 0: Idle (6 frames)
    for c in range(6):
        if num_frames > 1:
            frame = get_frame(cell_frames, c)
        else:
            # Procedural gentle breathing bounce
            dy = int(math.sin(c * (math.pi / 3)) * 3)
            base = cell_frames[0]
            frame = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
            frame.paste(base, (0, dy), base)
        atlas.paste(frame, (c * CELL_WIDTH, 0 * CELL_HEIGHT), frame)

    # Row 1: Running Right (8 frames)
    for c in range(8):
        f = get_frame(cell_frames, c)
        # Add slight walk bob
        dy = -2 if c % 2 == 1 else 0
        tmp = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
        tmp.paste(f, (0, dy), f)
        atlas.paste(tmp, (c * CELL_WIDTH, 1 * CELL_HEIGHT), tmp)

    # Row 2: Running Left (8 frames - horizontally flipped)
    for c in range(8):
        f = get_frame(cell_frames, c)
        flipped = ImageOps.mirror(f)
        dy = -2 if c % 2 == 1 else 0
        tmp = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
        tmp.paste(flipped, (0, dy), flipped)
        atlas.paste(tmp, (c * CELL_WIDTH, 2 * CELL_HEIGHT), tmp)

    # Row 3: Waving (4 frames)
    for c in range(4):
        f = get_frame(cell_frames, c)
        atlas.paste(f, (c * CELL_WIDTH, 3 * CELL_HEIGHT), f)

    # Row 4: Jumping (5 frames)
    for c in range(5):
        f = get_frame(cell_frames, c)
        jump_y = -int(math.sin(c * (math.pi / 4)) * 14)
        tmp = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
        tmp.paste(f, (0, jump_y), f)
        atlas.paste(tmp, (c * CELL_WIDTH, 4 * CELL_HEIGHT), tmp)

    # Row 5: Failed / Sleeping (8 frames)
    for c in range(8):
        f = get_frame(cell_frames, c)
        atlas.paste(f, (c * CELL_WIDTH, 5 * CELL_HEIGHT), f)

    # Row 6: Waiting (6 frames)
    for c in range(6):
        f = get_frame(cell_frames, c)
        atlas.paste(f, (c * CELL_WIDTH, 6 * CELL_HEIGHT), f)

    # Row 7: Running (6 frames)
    for c in range(6):
        f = get_frame(cell_frames, c)
        atlas.paste(f, (c * CELL_WIDTH, 7 * CELL_HEIGHT), f)

    # Row 8: Review / Thinking (6 frames)
    for c in range(6):
        f = get_frame(cell_frames, c)
        atlas.paste(f, (c * CELL_WIDTH, 8 * CELL_HEIGHT), f)

    sheet_path = os.path.join(target_dir, "spritesheet.webp")
    atlas.save(sheet_path, "WEBP", quality=100, method=6)

    meta = {
        "id": slug,
        "displayName": name,
        "description": desc,
        "spriteVersionNumber": 1,
        "spritesheetPath": "spritesheet.webp"
    }
    with open(os.path.join(target_dir, "pet.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return {"success": True, "slug": slug, "name": name}

def import_zip_bytes(zip_bytes: bytes, target_root_dir: str, fallback_name: str = None) -> dict:
    """
    Extracts a pet zip archive (such as from codexpets.net or GitHub)
    into target_root_dir/<slug> and validates it.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as e:
        return {"success": False, "error": f"Invalid zip archive: {e}"}

    members = zf.namelist()
    if not members:
        return {"success": False, "error": "Zip file is empty"}

    # Find pet.json if present
    manifest_info = None
    sheet_info = None
    manifest_data = {}

    for name in members:
        base = os.path.basename(name).lower()
        if base == "pet.json":
            manifest_info = name
            try:
                manifest_data = json.loads(zf.read(name).decode("utf-8"))
            except Exception:
                pass
        elif "spritesheet" in base or base.endswith((".webp", ".png", ".gif")):
            if not sheet_info:
                sheet_info = name

    # Determine slug & name
    slug = manifest_data.get("id")
    if not slug:
        if fallback_name:
            slug = sanitize_slug(fallback_name)
        else:
            # Check top level folder in zip
            parts = [m for m in members if "/" in m]
            if parts:
                top_folder = parts[0].split("/")[0]
                slug = sanitize_slug(top_folder)
            else:
                slug = f"imported-pet-{int(time.time())}"

    display_name = manifest_data.get("displayName") or (fallback_name or slug.replace("-", " ").capitalize())
    desc = manifest_data.get("description", "Imported Codex Pet companion")
    ver = manifest_data.get("spriteVersionNumber", 1)

    target_dir = os.path.join(target_root_dir, slug)
    os.makedirs(target_dir, exist_ok=True)

    extracted_sheet = None
    for item in zf.infolist():
        if item.is_dir():
            continue
        base = os.path.basename(item.filename)
        if not base or base.startswith("."):
            continue

        out_path = os.path.join(target_dir, base)
        with open(out_path, "wb") as f:
            f.write(zf.read(item.filename))

        if "spritesheet" in base.lower() or base.endswith((".webp", ".png")):
            if not extracted_sheet or "spritesheet" in base.lower():
                extracted_sheet = base

    # Ensure pet.json exists
    manifest_path = os.path.join(target_dir, "pet.json")
    if not os.path.exists(manifest_path):
        meta = {
            "id": slug,
            "displayName": display_name,
            "description": desc,
            "spriteVersionNumber": ver,
            "spritesheetPath": extracted_sheet or "spritesheet.webp"
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    return {"success": True, "slug": slug, "name": display_name}
