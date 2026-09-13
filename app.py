"""Tree Crown Detection & Canopy Area Tool

Upload a forest image (GeoTIFF/PNG/JPG), optionally a KML boundary, detect
individual tree crowns with DeepForest, and see canopy area / cover estimates
with every number traceable to how it was computed.
"""

import hashlib
import os
import tempfile

import pandas as pd
import streamlit as st

from pipeline import detect, geo, visualize
from ui import hero, theme

st.set_page_config(
    page_title="Tree Crown & Canopy Area Tool",
    page_icon="🌲",
    layout="wide",
)

theme.inject()
theme.page_heading("Tree Crown Detection & Canopy Area Tool")
hero.render()

# ---------------------------------------------------------------------------
# Permanent, non-collapsible limitations panel (requirement #10)
# ---------------------------------------------------------------------------
with st.container(key="limitations"):
    st.markdown("##### ⚠️ Limitations — read before trusting these numbers")
    st.markdown(
        "- The detection model was **pretrained on NEON forest data** (largely North American "
        "temperate/mixed forest). Its accuracy on other biomes, canopy types, or imagery sources "
        "(different sensors, resolutions, sun angles) is **unverified in this tool**.\n"
        "- **Dense or overlapping crowns are likely undercounted** — the model detects individual "
        "objects and struggles to separate touching canopies.\n"
        "- Crown area is computed from **bounding boxes**, which **overestimate** true crown area "
        "since real crowns are roughly elliptical, not rectangular.\n"
        "- If meters/pixel was **user-supplied** (plain PNG/JPG) rather than read from a GeoTIFF's "
        "CRS, **every area number on this page inherits that uncertainty** — garbage scale in, "
        "garbage area out.\n"
        "- **No ground-truth validation has been performed** on this image unless you run the "
        "spot-check below."
    )

st.write("")

# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------
theme.eyebrow("1 · Input")

with st.container(key="upload_panel"):
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        image_file = st.file_uploader(
            "Upload forest image", type=["tif", "tiff", "png", "jpg", "jpeg"]
        )
    with col_up2:
        kml_file = st.file_uploader("Optional: KML boundary", type=["kml"])


def _save_temp(uploaded_file) -> str:
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name


if image_file is None:
    st.info("Upload a GeoTIFF, PNG, or JPG of a forest area to get started.")
    st.stop()

image_bytes = image_file.getvalue()
image_hash = hashlib.md5(image_bytes).hexdigest()

if st.session_state.get("image_hash") != image_hash:
    st.session_state.image_hash = image_hash
    st.session_state.image_path = _save_temp(image_file)
    st.session_state.detections = None  # force re-detection on new image

image_path = st.session_state.image_path
is_geotiff = os.path.splitext(image_file.name)[1].lower() in (".tif", ".tiff")

# ---------------------------------------------------------------------------
# Scale: confirmed (GeoTIFF) vs user-supplied (plain image) — requirement #3
# ---------------------------------------------------------------------------
geo_info = None
scale_source = None
meters_per_pixel = None

if is_geotiff:
    try:
        geo_info = geo.read_geotiff_metadata(image_path)
    except Exception as e:
        st.warning(f"Could not read GeoTIFF metadata ({e}). Treating as a plain image.")
        geo_info = None
        is_geotiff = False

st.write("")
theme.eyebrow("2 · Scale")

with st.container(key="scale_panel"):
    if geo_info is not None and geo_info.is_geo:
        scale_source = "confirmed"
        theme.trust_chip(
            True,
            "Confirmed from GeoTIFF CRS",
            f"{geo_info.crs} · {geo_info.pixel_size_x_m:.4f} m/pixel (x) × "
            f"{geo_info.pixel_size_y_m:.4f} m/pixel (y)"
            + (f"<br>{geo_info.note}" if geo_info.note else ""),
        )
    else:
        if is_geotiff:
            st.warning("GeoTIFF has no embedded CRS — falling back to manual scale entry.")
        scale_source = "user-supplied"
        theme.trust_chip(
            False,
            "User-supplied · unverified",
            "This image has no georeferencing, so the scale below cannot be checked against "
            "anything. Every area and cover figure on this page inherits its uncertainty.",
        )
        meters_per_pixel = st.number_input(
            "Meters per pixel",
            min_value=0.0001, max_value=100.0, value=0.10, step=0.01, format="%.4f",
            help="This image has no georeferencing, so this value cannot be checked against "
                 "anything. Every area/cover number below is only as accurate as this input.",
        )

# ---------------------------------------------------------------------------
# KML boundary
# ---------------------------------------------------------------------------
polygon_wgs84 = None
polygon_image_crs = None
kml_path = None

if kml_file is not None:
    kml_path = _save_temp(kml_file)
    try:
        polygon_wgs84 = geo.parse_kml_polygon(kml_path)
        st.success("KML boundary parsed.")
        if is_geotiff and geo_info is not None and geo_info.is_geo:
            polygon_image_crs = geo.kml_polygon_to_image_crs(polygon_wgs84, geo_info.crs)
        else:
            st.warning(
                "This image is not georeferenced, so the KML boundary cannot be aligned to its "
                "pixels. The boundary will be **ignored** for clipping/area calculations — "
                "only a GeoTIFF supports KML clipping."
            )
    except Exception as e:
        st.error(f"Could not parse KML file: {e}")

# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
st.write("")
theme.eyebrow("3 · Detection")

run_clicked = st.button("Run tree crown detection", type="primary", key="run_detection")

if run_clicked:
    with st.spinner("Running DeepForest detection (predict_tile over the full image)..."):
        st.session_state.detections = detect.run_detection(image_path)

if st.session_state.get("detections") is None:
    st.info("Click **Run tree crown detection** to analyze this image.")
    st.stop()

full_df = st.session_state.detections

if len(full_df) == 0:
    st.warning("No trees detected in this image at all (even at very low confidence).")
    st.stop()

# ---------------------------------------------------------------------------
# Confidence threshold — live recompute (requirement #6)
# ---------------------------------------------------------------------------
with st.container(key="threshold_panel"):
    st.markdown("##### Confidence threshold")
    st.caption(
        "Lowering this includes more (but less certain) detections. Watch how much the tree "
        "count and canopy area swing as you move it — that swing **is** the model's uncertainty."
    )
    threshold = st.slider(
        "Minimum detection confidence to count as a tree",
        min_value=0.05, max_value=0.99, value=0.30, step=0.01,
        label_visibility="collapsed",
    )

df = full_df[full_df["score"] >= threshold].reset_index(drop=True)

# ---------------------------------------------------------------------------
# Clip to KML boundary (requirement #5)
# ---------------------------------------------------------------------------
mask = None
if polygon_image_crs is not None and geo_info is not None and geo_info.is_geo:
    mask = geo.rasterize_boundary_mask(
        polygon_image_crs, geo_info.transform, (geo_info.height, geo_info.width)
    )
    before = len(df)
    df = geo.filter_detections_by_mask(df, mask)
    st.caption(f"Clipped to KML boundary: {before} → {len(df)} detections kept (centroid inside polygon).")

# ---------------------------------------------------------------------------
# Areas
# ---------------------------------------------------------------------------
if geo_info is not None and geo_info.is_geo and len(df) > 0:
    gdf_native, gdf_utm = geo.boxes_to_projected_geodataframe(df, geo_info)
    areas_m2 = gdf_utm.geometry.area.reset_index(drop=True)
elif len(df) > 0:
    areas_m2 = geo.simple_box_areas_m2(df, meters_per_pixel).reset_index(drop=True)
    gdf_native, gdf_utm = None, None
else:
    areas_m2 = pd.Series([], dtype=float)
    gdf_native, gdf_utm = None, None

df = df.copy()
df["area_m2"] = areas_m2.values if len(areas_m2) == len(df) else 0.0

total_canopy_m2 = float(df["area_m2"].sum())
total_canopy_ha = total_canopy_m2 / 10_000.0

# Area of interest: smaller of KML polygon vs full image extent (requirement #7)
if geo_info is not None and geo_info.is_geo:
    full_extent_m2 = geo_info.width * geo_info.height * geo_info.pixel_size_x_m * geo_info.pixel_size_y_m
elif meters_per_pixel is not None:
    from PIL import Image as _PILImage
    with _PILImage.open(image_path) as _im:
        _w, _h = _im.size
    full_extent_m2 = _w * _h * (meters_per_pixel ** 2)
else:
    full_extent_m2 = None

aoi_m2 = full_extent_m2
aoi_label = "full image extent"
if polygon_wgs84 is not None and geo_info is not None and geo_info.is_geo:
    kml_area_m2 = geo.polygon_area_m2(polygon_wgs84)
    if full_extent_m2 is None or kml_area_m2 < full_extent_m2:
        aoi_m2 = kml_area_m2
        aoi_label = "KML boundary"

canopy_cover_pct = (total_canopy_m2 / aoi_m2 * 100.0) if aoi_m2 else None

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
st.write("")
theme.eyebrow("4 · Results")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Tree count", f"{len(df):,}")
m2.metric("Total canopy area", f"{total_canopy_m2:,.1f} m²", f"{total_canopy_ha:,.3f} ha")
m3.metric(
    "Canopy cover",
    f"{canopy_cover_pct:.1f}%" if canopy_cover_pct is not None else "n/a",
    help=f"Canopy area ÷ area of interest ({aoi_label}).",
)
m4.metric(
    "Scale used",
    f"{geo_info.pixel_size_x_m:.3f} m/px" if (geo_info and geo_info.is_geo) else f"{meters_per_pixel:.3f} m/px",
    "confirmed" if scale_source == "confirmed" else "⚠ user-supplied",
    delta_color="normal" if scale_source == "confirmed" else "off",
)
st.caption(
    "Canopy area is the sum of **bounding-box** areas (an overestimate of true crown area — "
    "see limitations above). Cover % is measured against the " + aoi_label + "."
)

# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------
st.write("")
theme.eyebrow("5 · Visualization")

base_image = geo.read_raster_as_rgb_pil(image_path, is_geotiff and geo_info is not None and geo_info.is_geo)
annotated = visualize.draw_boxes(base_image, df)

if polygon_image_crs is not None and geo_info is not None and geo_info.is_geo:
    pixel_coords = geo.polygon_to_pixel_coords(polygon_image_crs, geo_info.transform)
    annotated = visualize.draw_polygon_outline(annotated, pixel_coords)

viz_col, hist_col = st.columns([2, 1])
with viz_col:
    with st.container(key="viz_panel"):
        st.image(
            annotated,
            caption=f"{len(df)} trees detected (threshold ≥ {threshold:.2f})",
            width="stretch",
        )
with hist_col:
    with st.container(key="hist_panel"):
        fig = visualize.crown_size_histogram(df["area_m2"].values)
        st.pyplot(fig, width="stretch")

# ---------------------------------------------------------------------------
# Export (requirement #9)
# ---------------------------------------------------------------------------
st.write("")
theme.eyebrow("6 · Export")

export_df = df[["tree_id", "xmin", "ymin", "xmax", "ymax", "area_m2", "score"]].rename(
    columns={"tree_id": "id", "score": "confidence"}
)
csv_bytes = export_df.to_csv(index=False).encode("utf-8")

with st.container(key="export_panel"):
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.download_button(
            "⬇  Download CSV",
            data=csv_bytes,
            file_name="tree_detections.csv",
            mime="text/csv",
            width="stretch",
        )
    with exp_col2:
        if gdf_native is not None and len(gdf_native) > 0:
            geojson_str = gdf_native.to_crs("EPSG:4326")[["tree_id", "area_m2", "score", "geometry"]].to_json()
            st.download_button(
                "⬇  Download GeoJSON",
                data=geojson_str,
                file_name="tree_detections.geojson",
                mime="application/geo+json",
                width="stretch",
            )
        else:
            st.caption("GeoJSON export requires a georeferenced (GeoTIFF) input.")

# ---------------------------------------------------------------------------
# Optional spot-check validation (requirement #11)
# ---------------------------------------------------------------------------
st.write("")
theme.eyebrow("7 · Spot-check validation (optional)")

with st.container(key="spotcheck_panel"):
    st.caption(
        "Manually count the trees in a small crop, enter that number, and see how the model's "
        "detections in that same crop compare. This is a **count-based approximation**, not a "
        "location-matched precision/recall — it can tell you if the model found roughly the right "
        "*number* of trees in that area, not whether it found the *right* trees."
    )

    img_w, img_h = base_image.size
    with st.form("spot_check_form"):
        c1, c2, c3, c4 = st.columns(4)
        cx0 = c1.number_input("Crop xmin", 0, img_w, 0)
        cy0 = c2.number_input("Crop ymin", 0, img_h, 0)
        cx1 = c3.number_input("Crop xmax", 0, img_w, min(400, img_w))
        cy1 = c4.number_input("Crop ymax", 0, img_h, min(400, img_h))
        manual_count = st.number_input("Trees you counted by eye in this crop", min_value=0, value=0, step=1)
        submitted = st.form_submit_button("Compare")

    if submitted:
        if cx1 <= cx0 or cy1 <= cy0:
            st.error("Crop max must be greater than crop min.")
        else:
            crop_img = annotated.crop((cx0, cy0, cx1, cy1))
            centroid_x = (df["xmin"] + df["xmax"]) / 2.0
            centroid_y = (df["ymin"] + df["ymax"]) / 2.0
            in_crop = (
                (centroid_x >= cx0) & (centroid_x <= cx1) & (centroid_y >= cy0) & (centroid_y <= cy1)
            )
            predicted_count = int(in_crop.sum())

            st.image(crop_img, caption=f"Crop: model detected {predicted_count} trees here")

            if manual_count == 0 and predicted_count == 0:
                st.info("Both counts are zero — nothing to compare.")
            else:
                precision_est = min(predicted_count, manual_count) / predicted_count if predicted_count else 0.0
                recall_est = min(predicted_count, manual_count) / manual_count if manual_count else 0.0
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Model count (crop)", predicted_count)
                sc2.metric("Your manual count", int(manual_count))
                sc3.metric("Count agreement", f"{min(predicted_count, manual_count)}/{max(predicted_count, manual_count)}")
                st.markdown(
                    f"- **Precision estimate:** {precision_est:.0%} (rough — count-based, not IoU-matched)\n"
                    f"- **Recall estimate:** {recall_est:.0%} (rough — count-based, not IoU-matched)"
                )
                st.session_state["spot_check_done"] = True

    if st.session_state.get("spot_check_done"):
        st.caption("✅ A spot-check has been run this session for this image (see above).")
