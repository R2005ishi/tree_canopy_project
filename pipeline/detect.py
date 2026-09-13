"""DeepForest model loading and tree-crown inference."""

import streamlit as st
import pandas as pd

# Detection is always run at this low score threshold so that the full
# candidate set (including low-confidence boxes) is available in-memory.
# The UI's confidence slider then filters this dataframe live, without
# re-running the (expensive) model on every slider move.
_BASE_SCORE_THRESH = 0.05

PATCH_SIZE = 400
PATCH_OVERLAP = 0.05


@st.cache_resource(show_spinner="Loading DeepForest model (weecology/deepforest-tree)...")
def load_model():
    """Load the pretrained DeepForest tree-crown model. Cached across reruns."""
    from deepforest import main as df_main

    model = df_main.deepforest()
    model.load_model("weecology/deepforest-tree")
    model.config["score_thresh"] = _BASE_SCORE_THRESH
    return model


def run_detection(image_path: str) -> pd.DataFrame:
    """Run DeepForest's tiled prediction over the full image.

    Returns a dataframe with columns: xmin, ymin, xmax, ymax, score, label.
    Uses predict_tile (not predict_image) because input imagery is typically
    much larger than the model's native training patch size.
    """
    model = load_model()
    result = model.predict_tile(
        path=image_path,
        patch_size=PATCH_SIZE,
        patch_overlap=PATCH_OVERLAP,
    )

    if result is None or len(result) == 0:
        return pd.DataFrame(columns=["xmin", "ymin", "xmax", "ymax", "score", "label"])

    result = result.reset_index(drop=True)
    result["tree_id"] = result.index.astype(int)
    return result
