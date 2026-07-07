from __future__ import annotations

import sys
from pathlib import Path


def fmt(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/StankyTools")
    if not root.exists():
        print(f"Not found: {root}")
        return 1
    files = [p for p in root.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    print(f"Total: {fmt(total)}  Files: {len(files)}  Root: {root}")
    print("\nLargest files:")
    for p in sorted(files, key=lambda x: x.stat().st_size, reverse=True)[:35]:
        print(f"{fmt(p.stat().st_size):>10}  {p.relative_to(root)}")
    print("\nLargest top-level folders:")
    folder_sizes: dict[str, int] = {}
    for p in files:
        rel = p.relative_to(root)
        top = rel.parts[0] if len(rel.parts) else p.name
        folder_sizes[top] = folder_sizes.get(top, 0) + p.stat().st_size
    for name, size in sorted(folder_sizes.items(), key=lambda kv: kv[1], reverse=True)[:25]:
        print(f"{fmt(size):>10}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
