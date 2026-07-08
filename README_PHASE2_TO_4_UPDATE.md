# StankyTools Phase 2-4 Update

Implemented in this build:

- Deep Desert map marker selection now syncs with the Placed Intel list.
  - Clicking a POI/base marker highlights the matching row.
  - The list automatically scrolls the selected row into view.
  - The marker keeps the stronger selected map highlight.
- Existing list-to-map behavior remains intact.
  - Clicking a row still centers/highlights the map marker.
- ROLE and CODE badge assets were recreated so the words are part of the icon itself.
- StatusPill icon rendering now supports wider word-badge icons without crushing them.

Notes:
- This phase focuses on safe UX/polish changes that do not change database schemas.
- Continue testing with two app windows open for realtime guild/POI data behavior.
