STANKYTOOLS PLACEABLES IMPORT

This package adds 42 placeable items and their images to the existing StankyTools database.

Run from the StankyTools repository root:

    py path\to\StankyTools-Placeables-Import\import_placeables.py

For example, if you extract this folder into the repository root:

    py StankyTools-Placeables-Import\import_placeables.py

The script:
- preserves all existing catalog data
- inserts or updates the 42 listed items
- copies images to the StankyTools AppData item_images folder
- uses Utility as the main catalog category
- preserves Fabricators, Refineries, Storage, and Utilities as subcategories
- marks every entry as item type Placeable
