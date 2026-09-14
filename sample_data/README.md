# Sample data

## `OSBS_029.tif` — try the tool with this

A 40 m × 40 m aerial RGB tile from NEON's Ordway-Swisher Biological Station,
Florida — the kind of imagery DeepForest was trained on, so it's a fair first test.

| | |
|---|---|
| Format | GeoTIFF, 3-band RGB, 400 × 400 px |
| CRS | EPSG:32617 (WGS 84 / UTM zone 17N) |
| Resolution | 0.1 m/pixel, read from the file — the app shows it as **confirmed** |
| Ground truth | 61 trees, hand-annotated by the DeepForest authors |

**Source:** shipped as example data in [DeepForest](https://github.com/weecology/DeepForest)
(MIT License, © Weecology). The imagery originates from the
[NEON Airborne Observation Platform](https://data.neonscience.org/data-products/DP3.30010.001);
cite NEON per its data usage and citation policy if you publish results from it.

### What to expect

Verified with DeepForest 2.1.0 — other versions may differ slightly:

- **55 trees detected** at the default 0.30 threshold, against 61 annotated.
- Every detection scores between 0.30 and 0.80, so dragging the slider *below*
  0.30 changes nothing on this tile. Drag it up to 0.50 to see the count drop to 35.
- About **689 m² of canopy**, **43% cover** of the tile at the default threshold.
- Because it's georeferenced, the GeoJSON export is enabled.

### Spot-check against the ground truth

In the spot-check form, set the crop to `0, 0 → 400, 400` (the whole tile) and
enter **61** as your manual count.

## More imagery

Use your own drone or aerial orthomosaic (GeoTIFF preferred, PNG/JPG work with a
manually entered scale), or download more NEON RGB tiles from the
[NEON Data Portal](https://data.neonscience.org/data-products/DP3.30010.001).
