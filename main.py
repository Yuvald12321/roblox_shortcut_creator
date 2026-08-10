import os
import re
import threading
import winreg
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import customtkinter as ctk
import requests
from PIL import Image


class RSC(ctk.CTk):
    ICON_SIZE = (160, 160)
    THUMBNAIL_URL = "https://thumbnails.roblox.com/v1/places/gameicons"
    PLACE_UNIVERSE_URL = "https://apis.roblox.com/universes/v1/places/{place_id}/universe"
    GAME_DETAILS_URL = "https://games.roblox.com/v1/games"

    def __init__(self):
        super().__init__()
        self.title("RSC - Roblox Shortcut Creator")
        self.geometry("600x460")

        self.ICONS_PATH = Path.home() / "RSC icons"
        self.ICONS_PATH.mkdir(parents=True, exist_ok=True)
        self.setup_paths()

        self.selected_game = None
        self.preview_image = None
        self._build_ui()

    def setup_paths(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            try:
                raw_path, _ = winreg.QueryValueEx(key, "{758026A1-9253-400D-A76F-15E2157B228D}")
            except FileNotFoundError:
                raw_path, _ = winreg.QueryValueEx(key, "Desktop")
        self.DESKTOP_PATH = Path(os.path.expandvars(raw_path)).expanduser()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        heading = ctk.CTkLabel(self, text="Roblox Shortcut Creator", font=ctk.CTkFont(size=24, weight="bold"))
        heading.grid(row=0, column=0, padx=24, pady=(24, 12), sticky="w")

        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=1, column=0, padx=24, pady=8, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Paste a Roblox game URL or Place ID")
        self.search_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.search_entry.bind("<Return>", lambda _event: self.search_game())
        self.search_button = ctk.CTkButton(search_frame, text="Search", width=100, command=self.search_game)
        self.search_button.grid(row=0, column=1)

        self.preview_card = ctk.CTkFrame(self)
        self.preview_card.grid(row=2, column=0, padx=24, pady=16, sticky="ew")
        self.preview_card.grid_columnconfigure(1, weight=1)

        self.thumbnail_label = ctk.CTkLabel(self.preview_card, text="No preview", width=160, height=160)
        self.thumbnail_label.grid(row=0, column=0, padx=18, pady=18)
        self.game_title_label = ctk.CTkLabel(
            self.preview_card, text="Search for a Roblox experience to preview it.",
            font=ctk.CTkFont(size=17, weight="bold"), wraplength=330, justify="left"
        )
        self.game_title_label.grid(row=0, column=1, padx=(0, 18), pady=18, sticky="w")

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray70")
        self.status_label.grid(row=3, column=0, padx=24, pady=(0, 8), sticky="w")
        self.create_button = ctk.CTkButton(
            self, text="Create Shortcut", state="disabled", command=self.create_shortcut
        )
        self.create_button.grid(row=4, column=0, padx=24, pady=(4, 24), sticky="e")

    @staticmethod
    def extract_place_id(value):
        value = value.strip()
        if value.isdigit():
            return value

        parsed = urlparse(value)
        query_id = parse_qs(parsed.query).get("placeId", [])
        if query_id and query_id[0].isdigit():
            return query_id[0]

        match = re.search(r"/(?:games|places)/(\d+)(?:/|$|[?#])", parsed.path, re.IGNORECASE)
        return match.group(1) if match else None

    def search_game(self):
        place_id = self.extract_place_id(self.search_entry.get())
        self.selected_game = None
        self.create_button.configure(state="disabled")

        if not place_id:
            self._set_status("Enter a valid Roblox game URL or Place ID.", error=True)
            return

        self.search_button.configure(state="disabled")
        self.game_title_label.configure(text="Looking up game…")
        self._set_status("")
        self.game_title_label.configure(text="Looking up game...")
        threading.Thread(target=self._fetch_game, args=(place_id,), daemon=True).start()

    def _fetch_game(self, place_id):
        try:
            universe_response = requests.get(
                self.PLACE_UNIVERSE_URL.format(place_id=place_id), timeout=15
            )
            universe_response.raise_for_status()
            universe_id = universe_response.json().get("universeId")
            if not universe_id:
                raise ValueError("No Roblox experience was found for that Place ID.")

            game_response = requests.get(
                self.GAME_DETAILS_URL, params={"universeIds": universe_id}, timeout=15
            )
            game_response.raise_for_status()
            games = game_response.json().get("data", [])
            if not games:
                raise ValueError("No Roblox experience was found for that Place ID.")

            icon_response = requests.get(
                self.THUMBNAIL_URL,
                params={"placeIds": place_id, "size": "420x420", "format": "Png", "isCircular": "false"},
                timeout=15,
            )
            icon_response.raise_for_status()
            icon_data = icon_response.json().get("data", [])
            image_url = icon_data[0].get("imageUrl") if icon_data else None
            if not image_url:
                raise ValueError("Roblox did not provide an icon for this game.")

            image_response = requests.get(image_url, timeout=20)
            image_response.raise_for_status()
            image = Image.open(BytesIO(image_response.content)).convert("RGBA")
            title = games[0].get("name") or f"Roblox Place {place_id}"
            self.after(0, self._show_game, place_id, title, image, image_url)
        except (requests.RequestException, ValueError, OSError, IndexError, KeyError) as error:
            self.after(0, self._show_search_error, str(error))

    def _show_game(self, place_id, title, image, image_url):
        preview = image.copy()
        preview.thumbnail(self.ICON_SIZE, Image.Resampling.LANCZOS)
        self.preview_image = ctk.CTkImage(light_image=preview, dark_image=preview, size=self.ICON_SIZE)
        self.thumbnail_label.configure(image=self.preview_image, text="")
        self.game_title_label.configure(text=title)
        self.selected_game = {"place_id": place_id, "title": title, "image": image, "image_url": image_url}
        self.create_button.configure(state="normal")
        self.search_button.configure(state="normal")
        self._set_status("Game found.")

    def _show_search_error(self, message):
        self.search_button.configure(state="normal")
        self.game_title_label.configure(text="Unable to load game preview.")
        self._set_status(message, error=True)

    def create_shortcut(self):
        if not self.selected_game:
            return

        try:
            game = self.selected_game
            icon_path = self.ICONS_PATH / f"{game['place_id']}.ico"
            game["image"].save(icon_path, format="ICO",
                               sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

            self.DESKTOP_PATH.mkdir(parents=True, exist_ok=True)
            shortcut_path = self.DESKTOP_PATH / f"{self._safe_filename(game['title'])}.url"
            shortcut_path.write_text(
                "[InternetShortcut]\n"
                f"URL=roblox://placeID={game['place_id']}\n"
                f"IconFile={icon_path}\n"
                "IconIndex=0\n",
                encoding="utf-8",
            )
            self._set_status(f"Shortcut created: {shortcut_path.name}")
        except OSError as error:
            self._set_status(f"Could not create shortcut: {error}", error=True)

    @staticmethod
    def _safe_filename(name):
        return re.sub(r'[<>:"/\\|?*]', "_", name).strip(". ") or "Roblox Shortcut"

    def _set_status(self, text, error=False):
        self.status_label.configure(text=text, text_color="#e57373" if error else "gray70")


if __name__ == "__main__":
    RSC().mainloop()
