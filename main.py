import os
import re
import threading
import uuid
import winreg
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import customtkinter as ctk
import requests
from PIL import Image, UnidentifiedImageError

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class RSC(ctk.CTk):
    ICON_SIZE = (140, 140)
    REQUEST_TIMEOUT = 15
    IMAGE_TIMEOUT = 20
    THUMBNAIL_URL = "https://thumbnails.roblox.com/v1/places/gameicons"
    SEARCH_URL = "https://apis.roblox.com/search-api/omni-search"
    PLACE_UNIVERSE_URL = "https://apis.roblox.com/universes/v1/places/{place_id}/universe"
    GAME_DETAILS_URL = "https://games.roblox.com/v1/games"

    def __init__(self):
        super().__init__()
        self.title("RSC - Roblox Shortcut Creator")
        self.geometry("620x720")
        self.minsize(620, 600)
        self.protocol("WM_DELETE_WINDOW", self._close_application)

        self.ICONS_PATH = Path.home() / "RSC icons"
        self.ICONS_PATH.mkdir(parents=True, exist_ok=True)
        self.setup_paths()

        self.http = requests.Session()
        self.http.headers.update({"User-Agent": "RSC/1.0"})
        self.selected_game = None
        self.preview_image = None
        self.search_request_id = 0
        self.fonts = self._create_fonts()
        self._build_ui()

    @staticmethod
    def _create_fonts():
        return {
            "title": ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            "subtitle": ctk.CTkFont(family="Segoe UI", size=12),
            "section": ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            "body": ctk.CTkFont(family="Segoe UI", size=12),
            "game_title": ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            "button": ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        }

    def setup_paths(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            try:
                raw_path, _ = winreg.QueryValueEx(
                    key, "{758026A1-9253-400D-A76F-15E2157B228D}"
                )
            except FileNotFoundError:
                raw_path, _ = winreg.QueryValueEx(key, "Desktop")
        self.DESKTOP_PATH = Path(os.path.expandvars(raw_path)).expanduser()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="ew")

        ctk.CTkLabel(
            header_frame,
            text="Roblox Shortcut Creator",
            font=self.fonts["title"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame,
            text="Search for a game or paste a direct Roblox URL / Place ID",
            font=self.fonts["subtitle"],
            text_color="gray70",
        ).pack(anchor="w", pady=(2, 0))

        search_frame = ctk.CTkFrame(
            self,
            fg_color=("gray90", "gray17"),
            corner_radius=10,
        )
        search_frame.grid(row=1, column=0, padx=24, pady=8, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Enter Game Name, Roblox Link, or Place ID...",
            height=40,
            border_width=0,
            fg_color="transparent",
            font=self.fonts["body"],
        )
        self.search_entry.grid(row=0, column=0, padx=(12, 8), pady=6, sticky="ew")
        self.search_entry.bind("<Return>", lambda _event: self.search_game())

        self.search_button = ctk.CTkButton(
            search_frame,
            text="Search",
            width=100,
            height=34,
            corner_radius=8,
            font=self.fonts["button"],
            command=self.search_game,
        )
        self.search_button.grid(row=0, column=1, padx=(0, 6), pady=6)

        self.progress_bar = ctk.CTkProgressBar(self, height=3, corner_radius=0)
        self.progress_bar.grid(row=2, column=0, padx=24, pady=(0, 8), sticky="ew")
        self.progress_bar.set(0)

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=3, column=0, padx=24, pady=4, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)

        self.results_title = ctk.CTkLabel(
            content_frame,
            text="Search Results",
            font=self.fonts["section"],
        )
        self.results_title.grid(row=0, column=0, pady=(0, 4), sticky="w")

        self.results_frame = ctk.CTkScrollableFrame(
            content_frame,
            height=140,
            corner_radius=10,
            fg_color=("gray85", "gray14"),
        )
        self.results_frame.grid(row=1, column=0, pady=(0, 16), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self._show_results_placeholder("Matches will appear here after searching.")

        ctk.CTkLabel(
            content_frame,
            text="Selected Game Preview",
            font=self.fonts["section"],
        ).grid(row=2, column=0, pady=(0, 4), sticky="w")

        self.preview_card = ctk.CTkFrame(
            content_frame,
            corner_radius=12,
            fg_color=("gray85", "gray14"),
            border_width=1,
            border_color=("gray75", "gray25"),
        )
        self.preview_card.grid(row=3, column=0, sticky="ew")
        self.preview_card.grid_columnconfigure(1, weight=1)

        image_container = ctk.CTkFrame(
            self.preview_card,
            width=140,
            height=140,
            corner_radius=10,
            fg_color=("gray75", "gray20"),
        )
        image_container.grid(row=0, column=0, padx=16, pady=16)
        image_container.pack_propagate(False)

        self.thumbnail_label = ctk.CTkLabel(
            image_container,
            text="No Image",
            font=self.fonts["body"],
            text_color="gray50",
        )
        self.thumbnail_label.pack(expand=True, fill="both")

        details_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        details_frame.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="nsew")

        self.game_title_label = ctk.CTkLabel(
            details_frame,
            text="No game selected",
            font=self.fonts["game_title"],
            wraplength=260,
            justify="left",
            anchor="w",
        )
        self.game_title_label.pack(anchor="w", fill="x")

        self.game_id_label = ctk.CTkLabel(
            details_frame,
            text="",
            font=self.fonts["subtitle"],
            text_color="gray60",
            anchor="w",
        )
        self.game_id_label.pack(anchor="w", pady=(4, 0))

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=4, column=0, padx=24, pady=(12, 20), sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            bottom_frame,
            text="",
            font=self.fonts["subtitle"],
            text_color="gray70",
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.create_button = ctk.CTkButton(
            bottom_frame,
            text="Create Shortcut",
            height=40,
            width=160,
            corner_radius=8,
            font=self.fonts["button"],
            state="disabled",
            command=self.create_shortcut,
        )
        self.create_button.grid(row=0, column=1, sticky="e")

    @staticmethod
    def extract_place_id(value):
        value = value.strip()
        if value.isdigit():
            return value

        deep_link_match = re.search(r"placeid[=/](\d+)", value, re.IGNORECASE)
        if deep_link_match:
            return deep_link_match.group(1)

        parsed = urlparse(value)
        query_parameters = {
            key.casefold(): values for key, values in parse_qs(parsed.query).items()
        }
        query_id = query_parameters.get("placeid", [])
        if query_id and query_id[0].isdigit():
            return query_id[0]

        match = re.search(r"/(?:games|places)/(\d+)(?:/|$|[?#])", parsed.path, re.IGNORECASE)
        return match.group(1) if match else None

    def search_game(self):
        query = self.search_entry.get().strip()
        if not query:
            self._set_status("Please enter a game name or ID.", error=True)
            return

        request_id = self._new_search_request()
        place_id = self.extract_place_id(query)
        if place_id:
            self._start_game_lookup(place_id, request_id)
            return

        self.search_button.configure(state="disabled")
        self.progress_bar.start()
        self.results_title.configure(text="Search Results")
        self.game_title_label.configure(text="Searching games...")
        self.game_id_label.configure(text="")
        self._set_status("")
        threading.Thread(
            target=self._search_games,
            args=(query, request_id),
            daemon=True,
        ).start()

    def _new_search_request(self):
        self.search_request_id += 1
        self.selected_game = None
        self.create_button.configure(state="disabled")
        self._clear_results()
        return self.search_request_id

    def _search_games(self, query, request_id):
        try:
            payload = self._get_json(
                self.SEARCH_URL,
                params={
                    "searchQuery": query,
                    "sessionId": str(uuid.uuid4()),
                    "pageType": "all",
                },
            )
            games = self._extract_game_results(payload)
            self.after(0, self._show_search_results, games, request_id)
        except self._request_errors() as error:
            self.after(0, self._show_search_error, str(error), request_id)

    @staticmethod
    def _extract_game_results(payload):
        games = []
        seen_place_ids = set()
        for group in payload.get("searchResults", []):
            if group.get("contentGroupType") != "Game":
                continue
            for game in group.get("contents", []):
                place_id = game.get("rootPlaceId")
                name = game.get("name")
                if not place_id or not name or place_id in seen_place_ids:
                    continue
                seen_place_ids.add(place_id)
                games.append(
                    {
                        "place_id": str(place_id),
                        "name": str(name),
                        "creator": RSC._creator_name(game),
                    }
                )
        return games

    @staticmethod
    def _creator_name(game):
        creator = game.get("creator")
        if isinstance(creator, dict):
            return str(game.get("creatorName") or creator.get("name") or "Unknown")
        return str(game.get("creatorName") or creator or "Unknown")

    def _show_search_results(self, games, request_id):
        if not self._is_current_request(request_id):
            return

        self._stop_loading()
        self._clear_results()
        if not games:
            self._show_results_placeholder("No matching Roblox games found.")
            self.game_title_label.configure(text="No game selected")
            self._set_status("No results found.", error=True)
            return

        self.results_title.configure(text=f"Search Results ({len(games)})")
        for row, game in enumerate(games):
            self._add_result_button(row, game)
        self.game_title_label.configure(text="Select a game from above")
        self._set_status("")

    def _add_result_button(self, row, game):
        game_name = game["name"]
        creator_name = game["creator"]
        button_frame = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        button_frame.grid(row=row, column=0, padx=4, pady=2, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            button_frame,
            text=f"{game_name}\nby {creator_name}",
            anchor="w",
            height=42,
            corner_radius=6,
            fg_color=("gray80", "gray22"),
            hover_color=("gray75", "gray30"),
            text_color=("black", "white"),
            font=self.fonts["body"],
            command=lambda result=game: self.select_search_result(result),
        ).grid(row=0, column=0, sticky="ew")

    def select_search_result(self, game):
        request_id = self._new_search_request()
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, game["name"])
        self.results_title.configure(text="Search Results")
        self._start_game_lookup(game["place_id"], request_id)

    def _start_game_lookup(self, place_id, request_id):
        self.search_button.configure(state="disabled")
        self.progress_bar.start()
        self.game_title_label.configure(text="Loading details...")
        self.game_id_label.configure(text=f"Place ID: {place_id}")
        self._set_status("")
        threading.Thread(
            target=self._fetch_game,
            args=(place_id, request_id),
            daemon=True,
        ).start()

    def _fetch_game(self, place_id, request_id):
        try:
            universe_payload = self._get_json(
                self.PLACE_UNIVERSE_URL.format(place_id=place_id)
            )
            universe_id = universe_payload.get("universeId")
            if not universe_id:
                raise ValueError("Game experience not found.")

            game_payload = self._get_json(
                self.GAME_DETAILS_URL,
                params={"universeIds": universe_id},
            )
            games = game_payload.get("data", [])
            if not games:
                raise ValueError("Game details not found.")

            icon_payload = self._get_json(
                self.THUMBNAIL_URL,
                params={
                    "placeIds": place_id,
                    "size": "420x420",
                    "format": "Png",
                    "isCircular": "false",
                },
            )
            icon_data = icon_payload.get("data", [])
            image_url = icon_data[0].get("imageUrl") if icon_data else None
            if not image_url:
                raise ValueError("Game icon not available.")

            image = self._get_image(image_url)
            title = games[0].get("name") or f"Roblox Place {place_id}"
            self.after(0, self._show_game, place_id, title, image, image_url, request_id)
        except self._request_errors() as error:
            self.after(0, self._show_search_error, str(error), request_id)

    def _get_json(self, url, params=None):
        response = self.http.get(url, params=params, timeout=self.REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def _get_image(self, url):
        response = self.http.get(url, timeout=self.IMAGE_TIMEOUT)
        response.raise_for_status()
        with Image.open(BytesIO(response.content)) as image:
            return image.convert("RGBA")

    @staticmethod
    def _request_errors():
        return (
            requests.RequestException,
            UnidentifiedImageError,
            ValueError,
            KeyError,
            OSError,
            TypeError,
        )

    def _show_game(self, place_id, title, image, image_url, request_id):
        if not self._is_current_request(request_id):
            return

        self._stop_loading()
        preview = image.copy()
        preview.thumbnail(self.ICON_SIZE, Image.Resampling.LANCZOS)
        self.preview_image = ctk.CTkImage(
            light_image=preview,
            dark_image=preview,
            size=self.ICON_SIZE,
        )
        self.thumbnail_label.configure(image=self.preview_image, text="")
        self.game_title_label.configure(text=title)
        self.game_id_label.configure(text=f"Place ID: {place_id}")
        self.selected_game = {
            "place_id": place_id,
            "title": title,
            "image": image,
            "image_url": image_url,
        }
        self.create_button.configure(state="normal")
        self._set_status("Ready to create shortcut.")

    def _show_search_error(self, message, request_id):
        if not self._is_current_request(request_id):
            return

        self._stop_loading()
        self.game_title_label.configure(text="Error loading game")
        self.game_id_label.configure(text="")
        self._set_status(message or "An unexpected error occurred.", error=True)

    def _is_current_request(self, request_id):
        return request_id == self.search_request_id

    def _stop_loading(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.search_button.configure(state="normal")

    def _show_results_placeholder(self, text):
        self.results_placeholder = ctk.CTkLabel(
            self.results_frame,
            text=text,
            font=self.fonts["body"],
            text_color="gray60",
        )
        self.results_placeholder.grid(row=0, column=0, padx=12, pady=20)

    def _clear_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

    def create_shortcut(self):
        if not self.selected_game:
            return

        try:
            game = self.selected_game
            place_id = game["place_id"]
            title = game["title"]
            image = game["image"]
            self.ICONS_PATH.mkdir(parents=True, exist_ok=True)
            icon_path = self.ICONS_PATH / f"{place_id}.ico"
            image.save(
                icon_path,
                format="ICO",
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
            )

            self.DESKTOP_PATH.mkdir(parents=True, exist_ok=True)
            shortcut_path = self.DESKTOP_PATH / f"{self._safe_filename(title)}.url"
            shortcut_path.write_text(
                "[InternetShortcut]\r\n"
                f"URL=roblox://placeID={place_id}\r\n"
                f"IconFile={icon_path}\r\n"
                "IconIndex=0\r\n",
                encoding="utf-8",
            )
            self._set_status(f"Created: {shortcut_path.name}")
        except (OSError, ValueError) as error:
            self._set_status(f"Error: {error}", error=True)

    @staticmethod
    def _safe_filename(name):
        return re.sub(r"[<>:\"/\\|?*]", "_", name).strip(". ") or "Roblox Shortcut"

    def _set_status(self, text, error=False):
        text_color = "#ef5350" if error else "#66bb6a"
        self.status_label.configure(text=text, text_color=text_color)

    def _close_application(self):
        self.search_request_id += 1
        self.http.close()
        self.destroy()


if __name__ == "__main__":
    RSC().mainloop()
