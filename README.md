# 🎮 Roblox Shortcut Creator (RSC)

Create desktop shortcuts for your favorite Roblox games — in just one click.

---

### ⬇️ Download
👉 **[Download the latest RSC.exe](../../raw/master/dist/RSC.exe)**

> ⚠️ **Windows SmartScreen Notice** > Windows may display a *"Windows protected your PC"* warning when running the `.exe`.
> This happens because the application is not signed with an expensive code-signing certificate.
>
> **How to run it:**
> 1. Click **"More info"** on the popup.
> 2. Click **"Run anyway"**.
> 
**This project is 100% open source.** You can review all the code in `main.py` or compile it yourself from source.

---

## ❓ What is this?

To create a shortcut for a specific Roblox game manually, you have to go through **18 tedious steps**:

<details>
<summary><b>👀 Click to see the painful manual way (18 steps)</b></summary>

1. Open Roblox in your browser.
2. Search for the game you want and open its page.
3. Copy its `Place ID` from the browser URL.
4. Go to your desktop
5. Right-click → **New** → **Shortcut**.
7. Enter the deep link: `roblox://placeID=YOUR_ID`.
8. Name the shortcut and save it.
9. Search Google for the game's official icon image.
10. Download the image.
11. Open an online converter to turn the image into an `.ico` file.
12. Download and save the `.ico` file to a folder you won't delete.
13. Right-click your new desktop shortcut → **Properties**.
14. Click **Change Icon...** → **Browse...**
15. Find and select the downloaded `.ico` file.
16. Click **OK** → **Apply**.
17. Repeat this for every single game...

</details>

### 🚀 The RSC Way:
1. Open **RSC**.
2. Search for the game (or paste a link / Place ID).
3. Click **Create Shortcut**.

That's it! RSC handles the API lookup, downloads the high-res icon, creates the `.ico` file, and sets up your desktop shortcut automatically.

---

## 📸 How It Works

```text
        ┌──────────────────┐
        │  Search Game /   │
        │ Paste Link / ID  │
        └────────┬─────────┘
                 ▼
       ┌───────────────────┐
       │ Roblox Public API │
       └─────────┬─────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌──────────────┐   ┌───────────────┐
│ Game Details │   │ High-Res Icon │
└──────┬───────┘   └───────┬───────┘
       │                   │
       └─────────┬─────────┘
                 ▼
    ┌──────────────────────────┐
    │ Generate `.ico` & `.url` │
    │    on your Desktop!      │
    └──────────────────────────┘
