# Installation guide

## Requirements
- **Metroid Prime Trilogy**, European PAL release (game ID **R3MP01**). Other releases do **not** work.
- **Dolphin**, or a **Wii** with **USB Loader GX**.
- A **Classic Controller** (or Classic Controller Pro) plugged into Wii Remote 1.

## Files
| File | Use |
|---|---|
| `codes/R3MP01.ini` | The code, already enabled, for Dolphin |
| `codes/R3MP01.gct` | The code, for the Wii |
| `codes/R3MP01.txt` | The code as text for USB Loader GX's cheat manager |
| `codes/classic_controller.txt` | The code on its own, to paste by hand |

There is a single code for the whole Trilogy: the Trilogy menu, Prime 1, Prime 2 and Prime 3.

## Dolphin
1. **Enable cheats:** *Config → General → Enable Cheats*.
2. **Copy the code:** put `R3MP01.ini` in `Documents/Dolphin Emulator/GameSettings/`. Back up any existing `R3MP01.ini` first, as it will be overwritten.
   - Alternative: right-click the game → *Properties → Gecko Codes → Add*, and paste `classic_controller.txt`.
3. **Set up the controller:** *Controllers → Wii Remote 1: Emulated Wii Remote → Configure*, set **Extension** to **Classic Controller** and map its buttons to your pad.
4. In *Properties → Gecko Codes*, tick **only** "Classic Controller pre1.0". Don't enable older versions or other controller codes at the same time: they all change the controls.

## Wii (USB Loader GX)
1. Copy `R3MP01.gct` to `SD:/codes/R3MP01.gct` (create the `codes` folder at the root of the SD card if needed, and remove any other `R3MP01.gct`).
2. In USB Loader GX, open the game's settings:
   - **Ocarina: On.**
   - **Hook Type: VBI** (the default). If the controls do nothing, try AXNextFrame.
   - **Debugger: Off.** With the Gecko debugger on, the loader leaves only 1864 bytes for codes and the mod (2984 bytes) won't load.
   - **Alternate DOL: Off.** Boot Trilogy normally and choose the game from its menu. The loader hooks the code again every time the Trilogy menu starts one of the games.
3. Plug the Classic Controller into the Wii Remote and start the game. **Don't touch the sticks while it loads:** the Wii takes that position as the centre.

**If the loader says it can't find the cheat file:** copy `R3MP01.txt` to `SD:/txtcodes/R3MP01.txt`, open the game's cheat manager in USB Loader GX, tick "Classic Controller pre1.0" and choose *Create GCT* (it creates the same file as `R3MP01.gct`).

## Controls
See the tables in the [README](../README.md#controls).

## Known issues
- **The hand in Prime 3 bounces slightly** when pushed all the way to the side of a console.
- **The in-game icons still show Wii Remote and Nunchuk buttons.**
- **Stick "stuck" after boot:** let go of the sticks and reconnect the controller.
- **Not enough room for other codes:** the mod uses 2984 of the 3272 bytes Dolphin allows, so other large codes won't fit alongside it.

## Reporting a problem
Say which game (Prime 1, 2 or 3), what you were doing, and whether it was on Dolphin or a Wii (and which Hook Type you used).
