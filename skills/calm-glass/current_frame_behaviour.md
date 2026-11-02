# Current frame behaviour

How the frame treats an image a raven reads, as measured; any frame update may change it.

- An image arrives untouched while it stays within both limits: at most 4,784 tiles of 28×28 px, and at most 2,576 px on the long side.
- Tiles are counted per side, rounded up: 2000×1848 makes 72 × 66 = 4,752 tiles and arrives untouched; 2000×1849 makes 72 × 67 = 4,824 and gets scaled down.
- The frame reads png, jpeg, gif and webp as they are.
- calm-glass counts an image's tokens as its tiles.
- These numbers live at the top of `calm_glass.py`: `tile_size`, `frame_tile_limit`, `frame_long_side_limit` and `frame_formats`.
