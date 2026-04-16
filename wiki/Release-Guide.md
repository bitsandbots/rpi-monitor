# Release Guide

RPiMonitor uses `release.sh` to manage versioning, packaging, and tagging. Run it from the repo root on your dev machine.

---

## Versioning

RPiMonitor follows [Semantic Versioning](https://semver.org/):

- **PATCH** (`2.0.x`) — bug fixes, docs, non-breaking internal changes
- **MINOR** (`2.x.0`) — new features, backward-compatible
- **MAJOR** (`x.0.0`) — breaking changes to API or config

The canonical version lives in `rpi_monitor.py`:

```python
VERSION = "2.0.0"
```

`release.sh` reads and writes this constant. `hub/rpi_monitor_hub.py` mirrors it.

---

## Creating a Release

### Dry run first

```bash
./release.sh 2.1.0 --dry-run
```

Shows exactly what would change — no files modified, no tags created.

### Cut the release

```bash
./release.sh 2.1.0
```

This will:
1. Validate the working tree is clean
2. Bump `VERSION = "2.1.0"` in `rpi_monitor.py` and `hub/rpi_monitor_hub.py`
3. Commit the bump: `chore: bump version to 2.1.0`
4. Create an annotated git tag: `v2.1.0`
5. Build `dist/rpi-monitor-2.1.0.tar.gz`
6. Generate `dist/rpi-monitor-2.1.0.sha256`

### Package current version (no bump)

```bash
./release.sh
```

Packages whatever `VERSION` is currently in `rpi_monitor.py` without bumping or tagging.

---

## Release Contents

The tarball includes:

```
rpi-monitor-2.1.0/
├── rpi_monitor.py
├── requirements.txt
├── templates/index.html
├── rpi-monitor.service
├── install.sh
├── .env.example
├── README.md
└── hub/
    ├── rpi_monitor_hub.py
    ├── requirements.txt
    ├── templates/hub.html
    ├── rpi-monitor-hub.service
    └── HUB_README.md
```

---

## Publishing the Release

After `release.sh` runs:

```bash
# Push the commit and tag
git push origin main && git push origin v2.1.0
```

Then on GitHub:
1. Go to **Releases → Draft a new release**
2. Select tag `v2.1.0`
3. Upload `dist/rpi-monitor-2.1.0.tar.gz`
4. Upload `dist/rpi-monitor-2.1.0.sha256`
5. Publish

---

## Install from a Release

On the target Pi:

```bash
curl -LO https://github.com/bitsandbots/rpi-monitor/releases/download/v2.1.0/rpi-monitor-2.1.0.tar.gz
sha256sum -c rpi-monitor-2.1.0.sha256
tar -xzf rpi-monitor-2.1.0.tar.gz
cd rpi-monitor-2.1.0 && sudo ./install.sh
```

---

## `dist/` is Gitignored

Built artifacts (`dist/`) are excluded from the repo by `.gitignore`. Only upload tarballs to GitHub Releases — never commit them.
