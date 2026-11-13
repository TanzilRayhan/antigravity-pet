import os
import urllib.request
import json
import threading

CATALOG_URL = "https://raw.githubusercontent.com/legeling/awesome-codex-pet/main/pets.json"
RAW_BASE_URL = "https://raw.githubusercontent.com/legeling/awesome-codex-pet/main/pets"

class PetCatalog:
    def __init__(self, pets_dir):
        self.pets_dir = pets_dir
        self.cached_catalog = []
        self._cache_file = os.path.join(self.pets_dir, ".catalog_cache.json")
        self._load_local_cache()

    def _load_local_cache(self):
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    self.cached_catalog = json.load(f)
            except Exception:
                pass

    def fetch_catalog(self, force=False):
        """Fetch remote catalog list asynchronously or synchronously."""
        if self.cached_catalog and not force:
            return self.cached_catalog

        try:
            req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self.cached_catalog = data
                try:
                    with open(self._cache_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False)
                except Exception:
                    pass
                return data
        except Exception as e:
            print(f"Error fetching catalog: {e}")
            return self.cached_catalog or []

    def search(self, query: str):
        """Search pets by name, category, or description."""
        pets = self.fetch_catalog()
        q = query.strip().lower()
        if not q:
            return pets[:30]
        results = []
        for p in pets:
            name = p.get("name", "").lower()
            slug = p.get("slug", "").lower()
            desc = p.get("description", "").lower()
            cat = p.get("primary_category", "").lower()
            if q in name or q in slug or q in desc or q in cat:
                results.append(p)
        return results

    def download_pet(self, slug: str, callback=None):
        """Download a pet by slug into pets_dir/slug with path sanitization."""
        import re
        clean_slug = re.sub(r'[^a-zA-Z0-9_\-]', '', str(slug))
        clean_slug = os.path.basename(clean_slug)

        def _invoke_cb(success, err=None):
            if not callback:
                return
            try:
                callback(success, clean_slug, err)
            except TypeError:
                try:
                    callback(success, err)
                except Exception as ex:
                    print(f"Callback error: {ex}")
            except Exception as ex:
                print(f"Callback error: {ex}")

        def _task():
            dest_dir = os.path.abspath(os.path.join(self.pets_dir, clean_slug))
            if not dest_dir.startswith(os.path.abspath(self.pets_dir)):
                _invoke_cb(False, "Access denied")
                return

            os.makedirs(dest_dir, exist_ok=True)
            
            manifest_url = f"{RAW_BASE_URL}/{clean_slug}/pet.json"
            sheet_url = f"{RAW_BASE_URL}/{clean_slug}/spritesheet.webp"
            
            try:
                # 1. Download manifest
                req = urllib.request.Request(manifest_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    manifest_data = resp.read()
                with open(os.path.join(dest_dir, "pet.json"), "wb") as f:
                    f.write(manifest_data)
                
                # 2. Download spritesheet
                req = urllib.request.Request(sheet_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    sheet_data = resp.read()
                with open(os.path.join(dest_dir, "spritesheet.webp"), "wb") as f:
                    f.write(sheet_data)

                _invoke_cb(True, None)
            except Exception as e:
                print(f"Failed to download {clean_slug}: {e}")
                _invoke_cb(False, str(e))

        t = threading.Thread(target=_task, daemon=True)
        t.start()
