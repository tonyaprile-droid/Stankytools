# Sprint A5 - Cache Manager + Automatic Cleanup

Adds AppData-only cleanup helpers for:

- old update ZIPs
- old Deep Desert map captures
- temporary download files
- empty cache folders
- guild-specific cached logo/banner folders

Suggested startup hook:

```python
from stanky_market.sync.cache_tasks import run_startup_cache_cleanup
run_startup_cache_cleanup()
```

This sprint does not delete anything from the installed app folder.
