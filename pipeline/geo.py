"""Georeferencing helpers: GeoTIFF scale extraction, KML parsing, masking, area math.

All area math funnels through a projected (meters) CRS so that "m2" numbers
are true areas, not degree^2 or naive pixel counts. When the source image is
not georeferenced, callers fall back to a user-supplied meters/pixel scalar
and that fact is threaded back up to the UI so it can be labeled as such.
"""

import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from PIL import Image
from shapely.geometry import box as shapely_box, Polygon

KML_NAMESPACES = {"kml": "http://www.opengis.net/kml/2.2"}


class GeoTiffInfo:
    def __init__(self, is_geo, crs, transform, width, height,
                 pixel_size_x_m, pixel_size_y_m, note=""):
        self.is_geo = is_geo
        self.crs = crs
        self.transform = transform
        self.width = width
        self.height = height
        self.pixel_size_x_m = pixel_size_x_m
        self.pixel_size_y_m = pixel_size_y_m
        self.note = note


def read_geotiff_metadata(path: str) -> GeoTiffInfo:
    """Read CRS/transform from a GeoTIFF and derive true meters/pixel.

    If the CRS is geographic (degrees) or otherwise non-metric, meters/pixel
    is estimated by projecting a small patch around the image center into an
    appropriate UTM zone. Returns is_geo=False if the file has no CRS at all
    (e.g. a GeoTIFF exported without georeferencing).
    """
    import rasterio
    from pyproj import Transformer, CRS

    with rasterio.open(path) as src:
        crs = src.crs
        transform = src.transform
        width, height = src.width, src.height

        if crs is None:
            return GeoTiffInfo(False, None, transform, width, height, None, None,
                                note="File has no embedded CRS/transform.")

        native_px = abs(transform.a)
        native_py = abs(transform.e)

        if crs.is_projected and _linear_unit_is_metre(crs):
            return GeoTiffInfo(True, crs, transform, width, height, native_px, native_py)

        # Geographic (or non-metric projected) CRS: estimate meters/pixel by
        # projecting the two pixels adjacent to the image center into UTM.
        cx, cy = width / 2.0, height / 2.0
        x0, y0 = transform * (cx, cy)
        x1, y1 = transform * (cx + 1, cy)
        x2, y2 = transform * (cx, cy + 1)

        to_wgs84 = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
        lon0, lat0 = to_wgs84.transform(x0, y0)
        lon1, lat1 = to_wgs84.transform(x1, y1)
        lon2, lat2 = to_wgs84.transform(x2, y2)

        utm_crs = _estimate_utm_crs(lon0, lat0)
        to_utm = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
        ux0, uy0 = to_utm.transform(lon0, lat0)
        ux1, uy1 = to_utm.transform(lon1, lat1)
        ux2, uy2 = to_utm.transform(lon2, lat2)

        pixel_size_x_m = float(np.hypot(ux1 - ux0, uy1 - uy0))
        pixel_size_y_m = float(np.hypot(ux2 - ux0, uy2 - uy0))

        return GeoTiffInfo(
            True, crs, transform, width, height, pixel_size_x_m, pixel_size_y_m,
            note="CRS is not a metric projection; meters/pixel estimated via UTM reprojection at image center.",
        )


def _linear_unit_is_metre(crs) -> bool:
    try:
        axis = crs.axis_info[0]
        unit = (axis.unit_name or "").lower()
        return unit in ("metre", "meter", "m")
    except Exception:
        return True  # assume metric if we can't determine (common case)


def _estimate_utm_crs(lon: float, lat: float):
    from pyproj import CRS

    zone = int((lon + 180) / 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)


def parse_kml_polygon(path: str) -> Polygon:
    """Parse the first Polygon in a KML file into a shapely Polygon (lon/lat, EPSG:4326)."""
    tree = ET.parse(path)
    root = tree.getroot()

    coord_elem = root.find(".//kml:Polygon//kml:outerBoundaryIs//kml:coordinates", KML_NAMESPACES)
    if coord_elem is None:
        # Fall back to a namespace-agnostic search in case the file omits/varies the ns.
        for elem in root.iter():
            if elem.tag.endswith("coordinates"):
                coord_elem = elem
                break

    if coord_elem is None or not coord_elem.text:
        raise ValueError("No <Polygon><outerBoundaryIs><coordinates> found in KML file.")

    points = []
    for token in coord_elem.text.strip().split():
        parts = token.split(",")
        lon, lat = float(parts[0]), float(parts[1])
        points.append((lon, lat))

    if len(points) < 3:
        raise ValueError("KML polygon has fewer than 3 coordinates.")

    return Polygon(points)


def boxes_to_projected_geodataframe(df: pd.DataFrame, geo_info: GeoTiffInfo):
    """Convert pixel bounding boxes to real-world polygons and reproject to a UTM (meters) CRS.

    Returns (gdf_native_crs, gdf_utm_crs). Both are geopandas GeoDataFrames indexed
    like `df`, carrying all of df's columns plus `geometry`.
    """
    import geopandas as gpd

    geoms = []
    for _, row in df.iterrows():
        x0, y0 = geo_info.transform * (row["xmin"], row["ymin"])
        x1, y1 = geo_info.transform * (row["xmax"], row["ymax"])
        geoms.append(shapely_box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    gdf = gpd.GeoDataFrame(df.reset_index(drop=True).copy(), geometry=geoms, crs=geo_info.crs)

    utm_crs = gdf.estimate_utm_crs() if len(gdf) else _default_utm_from_bounds(geo_info)
    gdf_utm = gdf.to_crs(utm_crs)
    return gdf, gdf_utm


def _default_utm_from_bounds(geo_info: GeoTiffInfo):
    from pyproj import Transformer

    cx, cy = geo_info.width / 2.0, geo_info.height / 2.0
    x, y = geo_info.transform * (cx, cy)
    to_wgs84 = Transformer.from_crs(geo_info.crs, "EPSG:4326", always_xy=True)
    lon, lat = to_wgs84.transform(x, y)
    return _estimate_utm_crs(lon, lat)


def kml_polygon_to_image_crs(polygon_wgs84: Polygon, image_crs):
    import geopandas as gpd

    gdf = gpd.GeoDataFrame({"geometry": [polygon_wgs84]}, crs="EPSG:4326")
    return gdf.to_crs(image_crs).geometry.iloc[0]


def rasterize_boundary_mask(polygon_image_crs, transform, out_shape):
    """Rasterize a polygon (in the raster's own CRS) into a boolean pixel mask."""
    from rasterio.features import rasterize

    mask = rasterize(
        [(polygon_image_crs, 1)],
        out_shape=out_shape,
        transform=transform,
        fill=0,
        dtype="uint8",
    )
    return mask.astype(bool)


def filter_detections_by_mask(df: pd.DataFrame, mask: np.ndarray) -> pd.DataFrame:
    """Keep only detections whose box centroid falls inside the given pixel mask."""
    if len(df) == 0:
        return df

    cx = ((df["xmin"] + df["xmax"]) / 2.0).round().astype(int)
    cy = ((df["ymin"] + df["ymax"]) / 2.0).round().astype(int)

    h, w = mask.shape
    in_bounds = (cx >= 0) & (cx < w) & (cy >= 0) & (cy < h)

    keep = np.zeros(len(df), dtype=bool)
    idx_in = np.where(in_bounds.values)[0]
    keep[idx_in] = mask[cy.values[idx_in], cx.values[idx_in]]

    return df[keep].reset_index(drop=True)


def polygon_area_m2(polygon_wgs84: Polygon) -> float:
    """True area (m2) of a WGS84 lon/lat polygon, via UTM reprojection."""
    import geopandas as gpd

    lon, lat = polygon_wgs84.centroid.x, polygon_wgs84.centroid.y
    utm_crs = _estimate_utm_crs(lon, lat)
    gdf = gpd.GeoDataFrame({"geometry": [polygon_wgs84]}, crs="EPSG:4326").to_crs(utm_crs)
    return float(gdf.geometry.iloc[0].area)


def simple_box_areas_m2(df: pd.DataFrame, meters_per_pixel: float) -> pd.Series:
    """Area of each box (m2) using a flat scalar meters/pixel (non-georeferenced path)."""
    width_px = (df["xmax"] - df["xmin"]).abs()
    height_px = (df["ymax"] - df["ymin"]).abs()
    return width_px * height_px * (meters_per_pixel ** 2)


def read_raster_as_rgb_pil(path: str, is_geotiff: bool) -> Image.Image:
    """Load an image (GeoTIFF or ordinary PNG/JPG) as a displayable RGB PIL image."""
    if not is_geotiff:
        return Image.open(path).convert("RGB")

    import rasterio

    with rasterio.open(path) as src:
        band_count = min(src.count, 3)
        arr = src.read(list(range(1, band_count + 1)))

    arr = np.moveaxis(arr, 0, -1)
    if arr.shape[-1] == 1:
        arr = np.repeat(arr, 3, axis=-1)
    elif arr.shape[-1] == 2:
        arr = np.dstack([arr, arr[..., :1]])

    if arr.dtype != np.uint8:
        arr = _stretch_to_uint8(arr)

    return Image.fromarray(arr, mode="RGB")


def _stretch_to_uint8(arr: np.ndarray) -> np.ndarray:
    """Percentile-stretch each band to 0-255 for display (detection uses the raw file, not this)."""
    arr = arr.astype(np.float32)
    out = np.zeros(arr.shape, dtype=np.uint8)
    for b in range(arr.shape[-1]):
        band = arr[..., b]
        lo, hi = np.percentile(band, [1, 99])
        if hi <= lo:
            hi = lo + 1.0
        band = np.clip((band - lo) / (hi - lo), 0, 1) * 255
        out[..., b] = band.astype(np.uint8)
    return out


def polygon_to_pixel_coords(polygon_image_crs, transform):
    """Convert a polygon in the raster's CRS to a list of (x, y) pixel coordinates."""
    inv = ~transform
    return [inv * (x, y) for x, y in polygon_image_crs.exterior.coords]
