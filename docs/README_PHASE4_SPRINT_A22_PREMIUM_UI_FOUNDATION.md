# Sprint A22 - Premium UI Foundation

Replaces the unstable stylesheet generator with a centralized theme system.

## Included
- Complete `stanky_market/ui/theme.py` rewrite
- Dune Gold theme
- Harkonnen Red theme
- Atreides Green theme
- Spice Purple theme
- Escaped QSS braces to prevent Python `NameError` stylesheet crashes
- Larger headers
- Theme-aware nav/button/table/tab/dialog styles
- Green/gray online/offline indicator styling

## Install
Copy the `stanky_market/ui/theme.py` file into your project, replacing the current file.

## Notes
This sprint stabilizes theming. Future sprints can now add theme-specific generated mascot/banner/nav art without breaking QSS parsing.
