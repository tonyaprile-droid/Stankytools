StankyTools Catalog Import v1.3

This update changes stanky_market/catalog_importer.py so the app imports only the requested Dune Gaming Tools pages:

- /items/augment -> Augmentations
- /items/garment?tier=6 -> Garments
- /items/utility -> Utility
- /items/vehicles -> Vehicles
- /items/weapons?tier=6 -> Weapons
- /items/misc/components -> Components
- /items/misc/fuel -> Fuel
- /items/misc/rawresources -> Raw Resources
- /items/misc/refinedresources -> Refined Resources

The importer:
- downloads item images into data/catalog_images/
- skips items already in your local catalog
- uses a 1.75 second delay between requests
- does not crawl construction/customization/generic misc categories

Run it in the app with Catalog -> Import Dune Item Database.
