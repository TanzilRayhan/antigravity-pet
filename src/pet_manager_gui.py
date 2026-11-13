import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from config import PETS_DIR, load_config, save_config
from pet_loader import get_available_pets, PetDefinition, PetSpriteSheet
from downloader import PetCatalog

class PetManagerGUI:
    def __init__(self, on_pet_changed_callback=None):
        self.on_pet_changed_callback = on_pet_changed_callback
        self.cfg = load_config()
        self.catalog = PetCatalog(PETS_DIR)
        
        self.root = tk.Tk()
        self.root.title("Antigravity Pet Hub & Codex Gallery")
        self.root.geometry("820x560")
        self.root.minsize(750, 500)
        
        # Configure colors (Sleek dark theme matching Antigravity)
        self.bg_dark = "#0f172a"
        self.bg_card = "#1e293b"
        self.text_light = "#f8fafc"
        self.text_muted = "#94a3b8"
        self.accent_cyan = "#38bdf8"
        self.accent_hover = "#0284c7"
        
        self.root.configure(bg=self.bg_dark)

        # State
        self.installed_pets = []
        self.online_pets = []
        self.selected_pet = None
        self.preview_frames = []
        self.preview_idx = 0
        self.preview_timer = None

        self._build_ui()
        self.refresh_installed_pets()
        self.load_online_catalog()

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=self.bg_dark, pady=12, padx=16)
        header.pack(fill="x")
        
        title_label = tk.Label(
            header,
            text="✨ Antigravity Pet Hub",
            font=("Segoe UI", 16, "bold"),
            fg=self.accent_cyan,
            bg=self.bg_dark
        )
        title_label.pack(side="left")

        sub_label = tk.Label(
            header,
            text="Interactive Desktop Companion & Codex Pets Downloader",
            font=("Segoe UI", 10),
            fg=self.text_muted,
            bg=self.bg_dark
        )
        sub_label.pack(side="left", padx=12, pady=4)

        # Main notebook tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=8)

        # Style notebook
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=self.bg_dark, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.bg_card, foreground=self.text_light, padding=[16, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.accent_cyan)], foreground=[("selected", "#000000")])

        # Tab 1: Installed Pets & Settings
        self.tab_installed = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.tab_installed, text="  My Pets & Settings  ")
        self._build_installed_tab()

        # Tab 2: Online Codex Pets Gallery
        self.tab_gallery = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.tab_gallery, text="  Codex Pets Gallery (370+)  ")
        self._build_gallery_tab()

    def _build_installed_tab(self):
        container = tk.Frame(self.tab_installed, bg=self.bg_dark)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Left Column: Pets List
        left_col = tk.Frame(container, bg=self.bg_card, width=280)
        left_col.pack(side="left", fill="both", padx=(0, 10))

        lbl = tk.Label(left_col, text="Installed Pets", font=("Segoe UI", 11, "bold"), fg=self.text_light, bg=self.bg_card, pady=8)
        lbl.pack(fill="x")

        self.pets_listbox = tk.Listbox(
            left_col,
            bg="#0b1120",
            fg=self.text_light,
            selectbackground=self.accent_cyan,
            selectforeground="#000000",
            font=("Segoe UI", 10),
            borderwidth=0,
            highlightthickness=0
        )
        self.pets_listbox.pack(fill="both", expand=True, padx=8, pady=6)
        self.pets_listbox.bind("<<ListboxSelect>>", self._on_select_installed_pet)

        btn_activate = tk.Button(
            left_col,
            text="★ Set as Active Pet",
            bg=self.accent_cyan,
            fg="#000000",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
            command=self._apply_active_pet,
            pady=6
        )
        btn_activate.pack(fill="x", padx=8, pady=(4, 8))

        # Right Column: Live Preview & Settings
        right_col = tk.Frame(container, bg=self.bg_card)
        right_col.pack(side="right", fill="both", expand=True)

        # Preview Section
        prev_title = tk.Label(right_col, text="Live Animation Preview", font=("Segoe UI", 11, "bold"), fg=self.text_light, bg=self.bg_card, pady=6)
        prev_title.pack(fill="x")

        self.preview_canvas = tk.Canvas(right_col, width=160, height=170, bg="#0b1120", highlightthickness=1, highlightbackground="#334155")
        self.preview_canvas.pack(pady=6)

        self.pet_name_lbl = tk.Label(right_col, text="", font=("Segoe UI", 12, "bold"), fg=self.accent_cyan, bg=self.bg_card)
        self.pet_name_lbl.pack()

        self.pet_desc_lbl = tk.Label(right_col, text="", font=("Segoe UI", 9), fg=self.text_muted, bg=self.bg_card, wraplength=400)
        self.pet_desc_lbl.pack(pady=2)

        # Settings Divider
        sep = tk.Frame(right_col, height=1, bg="#334155")
        sep.pack(fill="x", padx=16, pady=10)

        # Settings Controls
        ctrls = tk.Frame(right_col, bg=self.bg_card, padx=16)
        ctrls.pack(fill="x")

        # Behavior Radio
        beh_frame = tk.Frame(ctrls, bg=self.bg_card)
        beh_frame.pack(fill="x", pady=4)
        tk.Label(beh_frame, text="Behavior Mode:", font=("Segoe UI", 9, "bold"), fg=self.text_light, bg=self.bg_card, width=14, anchor="w").pack(side="left")

        self.beh_var = tk.StringVar(value=self.cfg.get("behavior", "zero_g"))
        for val, txt in [("zero_g", "Zero-G Float"), ("roam", "Walk & Roam"), ("static", "Stay Put")]:
            rb = tk.Radiobutton(
                beh_frame, text=txt, variable=self.beh_var, value=val,
                fg=self.text_light, bg=self.bg_card, selectcolor=self.bg_dark,
                activebackground=self.bg_card, activeforeground=self.accent_cyan,
                command=self._on_behavior_change
            )
            rb.pack(side="left", padx=6)

        # Scale Slider
        scale_frame = tk.Frame(ctrls, bg=self.bg_card)
        scale_frame.pack(fill="x", pady=6)
        tk.Label(scale_frame, text="Scale / Size:", font=("Segoe UI", 9, "bold"), fg=self.text_light, bg=self.bg_card, width=14, anchor="w").pack(side="left")

        self.scale_slider = tk.Scale(
            scale_frame, from_=50, to=150, orient="horizontal",
            bg=self.bg_card, fg=self.text_light, troughcolor="#0b1120",
            highlightthickness=0, command=self._on_scale_change
        )
        self.scale_slider.set(int(self.cfg.get("scale", 0.75) * 100))
        self.scale_slider.pack(side="left", fill="x", expand=True, padx=6)

        # Checkboxes
        chk_frame = tk.Frame(ctrls, bg=self.bg_card)
        chk_frame.pack(fill="x", pady=4)

        self.sound_var = tk.BooleanVar(value=self.cfg.get("sound_enabled", True))
        chk_sound = tk.Checkbutton(
            chk_frame, text="Sound Effects", variable=self.sound_var,
            fg=self.text_light, bg=self.bg_card, selectcolor=self.bg_dark,
            activebackground=self.bg_card, activeforeground=self.accent_cyan,
            command=self._on_sound_toggle
        )
        chk_sound.pack(side="left", padx=6)

        self.speech_var = tk.BooleanVar(value=self.cfg.get("speech_enabled", True))
        chk_speech = tk.Checkbutton(
            chk_frame, text="Speech Bubbles", variable=self.speech_var,
            fg=self.text_light, bg=self.bg_card, selectcolor=self.bg_dark,
            activebackground=self.bg_card, activeforeground=self.accent_cyan,
            command=self._on_speech_toggle
        )
        chk_speech.pack(side="left", padx=16)

    def _build_gallery_tab(self):
        container = tk.Frame(self.tab_gallery, bg=self.bg_dark, padx=12, pady=10)
        container.pack(fill="both", expand=True)

        # Search Bar
        search_box = tk.Frame(container, bg=self.bg_card, pady=6, padx=8)
        search_box.pack(fill="x", pady=(0, 8))

        tk.Label(search_box, text="🔍 Search:", font=("Segoe UI", 10, "bold"), fg=self.text_light, bg=self.bg_card).pack(side="left", padx=4)
        
        self.search_entry = tk.Entry(search_box, font=("Segoe UI", 10), bg="#0b1120", fg=self.text_light, insertbackground=self.accent_cyan, borderwidth=0)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.search_entry.bind("<KeyRelease>", self._on_search_typed)

        btn_refresh = tk.Button(search_box, text="🔄 Refresh Catalog", bg="#334155", fg=self.text_light, relief="flat", command=self.load_online_catalog)
        btn_refresh.pack(side="right", padx=4)

        # Online List View
        cols = ("Name", "Category", "Author", "Status")
        self.gallery_tree = ttk.Treeview(container, columns=cols, show="headings", height=12)
        self.gallery_tree.heading("Name", text="Character Name")
        self.gallery_tree.heading("Category", text="Category")
        self.gallery_tree.heading("Author", text="Author")
        self.gallery_tree.heading("Status", text="Status")

        self.gallery_tree.column("Name", width=180)
        self.gallery_tree.column("Category", width=120)
        self.gallery_tree.column("Author", width=120)
        self.gallery_tree.column("Status", width=100)

        # Scrollbar
        scroll = ttk.Scrollbar(container, orient="vertical", command=self.gallery_tree.yview)
        self.gallery_tree.configure(yscrollcommand=scroll.set)
        self.gallery_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Bottom Download Action Bar
        act_bar = tk.Frame(self.tab_gallery, bg=self.bg_dark, pady=8, padx=12)
        act_bar.pack(fill="x")

        self.status_lbl = tk.Label(act_bar, text="Ready to download community pets from CodexPets / awesome-codex-pet.", font=("Segoe UI", 9), fg=self.text_muted, bg=self.bg_dark)
        self.status_lbl.pack(side="left")

        self.btn_download = tk.Button(
            act_bar,
            text="⬇ Download Selected Pet",
            bg=self.accent_cyan,
            fg="#000000",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
            command=self._download_selected_pet,
            padx=12,
            pady=4
        )
        self.btn_download.pack(side="right")

    def refresh_installed_pets(self):
        self.pets_listbox.delete(0, tk.END)
        self.installed_pets = get_available_pets(PETS_DIR)
        curr_slug = self.cfg.get("current_pet", "antigrav")
        
        select_idx = 0
        for idx, p in enumerate(self.installed_pets):
            display = p.display_name
            if p.slug == curr_slug:
                display += " (Active ★)"
                select_idx = idx
            self.pets_listbox.insert(tk.END, display)

        if self.installed_pets:
            self.pets_listbox.selection_set(select_idx)
            self._load_pet_preview(self.installed_pets[select_idx])

    def _on_select_installed_pet(self, event):
        sel = self.pets_listbox.curselection()
        if sel:
            idx = sel[0]
            if idx < len(self.installed_pets):
                self._load_pet_preview(self.installed_pets[idx])

    def _load_pet_preview(self, pet_def: PetDefinition):
        self.selected_pet = pet_def
        self.pet_name_lbl.config(text=pet_def.display_name)
        self.pet_desc_lbl.config(text=pet_def.description or "Codex compatible animated desktop companion.")

        try:
            sheet = PetSpriteSheet(pet_def, scale=0.7)
            # Load idle frames
            self.preview_frames = []
            frame_count = sheet.get_frame_count("idle")
            for i in range(frame_count):
                fr = sheet.get_frame("idle", i)
                self.preview_frames.append(ImageTk.PhotoImage(fr))
            self.preview_idx = 0
            self._animate_preview()
        except Exception as e:
            print(f"Error previewing pet: {e}")

    def _animate_preview(self):
        if not self.preview_frames:
            return
        img = self.preview_frames[self.preview_idx % len(self.preview_frames)]
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(80, 85, image=img)
        self.preview_idx += 1
        
        if self.preview_timer:
            self.root.after_cancel(self.preview_timer)
        self.preview_timer = self.root.after(160, self._animate_preview)

    def _apply_active_pet(self):
        if self.selected_pet:
            self.cfg["current_pet"] = self.selected_pet.slug
            save_config(self.cfg)
            self.refresh_installed_pets()
            if self.on_pet_changed_callback:
                self.on_pet_changed_callback(self.selected_pet.slug)
            messagebox.showinfo("Pet Activated", f"{self.selected_pet.display_name} is now your active Antigravity Pet!")

    def _on_behavior_change(self):
        val = self.beh_var.get()
        self.cfg["behavior"] = val
        save_config(self.cfg)

    def _on_scale_change(self, val):
        scale_val = float(val) / 100.0
        self.cfg["scale"] = scale_val
        save_config(self.cfg)

    def _on_sound_toggle(self):
        self.cfg["sound_enabled"] = self.sound_var.get()
        save_config(self.cfg)

    def _on_speech_toggle(self):
        self.cfg["speech_enabled"] = self.speech_var.get()
        save_config(self.cfg)

    def load_online_catalog(self):
        self.status_lbl.config(text="Fetching latest pets catalog...")
        def _fetch():
            data = self.catalog.fetch_catalog(force=True)
            self.root.after(0, lambda: self._populate_online_tree(data))
        t = threading.Thread(target=_fetch, daemon=True)
        t.start()

    def _populate_online_tree(self, data):
        self.online_pets = data
        for row in self.gallery_tree.get_children():
            self.gallery_tree.delete(row)

        installed_slugs = {p.slug for p in self.installed_pets}

        for p in data:
            name = p.get("name", "Unknown")
            cat = p.get("primary_category", "general")
            author = p.get("author", "community")
            slug = p.get("slug", "")
            status = "Installed ✓" if slug in installed_slugs else "Available"
            self.gallery_tree.insert("", tk.END, iid=slug, values=(name, cat, author, status))

        self.status_lbl.config(text=f"Loaded {len(data)} community pets. Select one and click Download!")

    def _on_search_typed(self, event):
        q = self.search_entry.get().strip().lower()
        for row in self.gallery_tree.get_children():
            self.gallery_tree.delete(row)

        installed_slugs = {p.slug for p in self.installed_pets}
        count = 0
        for p in self.online_pets:
            name = p.get("name", "").lower()
            slug = p.get("slug", "").lower()
            cat = p.get("primary_category", "").lower()
            author = p.get("author", "").lower()
            if not q or (q in name or q in slug or q in cat or q in author):
                disp_name = p.get("name", "Unknown")
                status = "Installed ✓" if slug in installed_slugs else "Available"
                self.gallery_tree.insert("", tk.END, iid=slug, values=(disp_name, p.get("primary_category", "general"), p.get("author", "community"), status))
                count += 1
        self.status_lbl.config(text=f"Found {count} pets matching '{q}'.")

    def _download_selected_pet(self):
        sel = self.gallery_tree.selection()
        if not sel:
            messagebox.showinfo("Select Pet", "Please select a pet from the list to download.")
            return

        slug = sel[0]
        self.status_lbl.config(text=f"Downloading {slug}... Please wait.")
        self.btn_download.config(state="disabled")

        def _on_complete(success, downloaded_slug, error):
            def _ui_update():
                self.btn_download.config(state="normal")
                if success:
                    self.status_lbl.config(text=f"Successfully downloaded {downloaded_slug}! ✓")
                    self.refresh_installed_pets()
                    # Update status in tree
                    if self.gallery_tree.exists(downloaded_slug):
                        vals = list(self.gallery_tree.item(downloaded_slug, "values"))
                        vals[3] = "Installed ✓"
                        self.gallery_tree.item(downloaded_slug, values=vals)
                    messagebox.showinfo("Download Complete", f"Pet '{downloaded_slug}' has been installed! You can now activate it.")
                else:
                    self.status_lbl.config(text=f"Failed to download: {error}")
                    messagebox.showerror("Download Error", f"Could not download {downloaded_slug}: {error}")
            self.root.after(0, _ui_update)

        self.catalog.download_pet(slug, callback=_on_complete)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = PetManagerGUI()
    app.run()
