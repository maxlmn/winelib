import streamlit as st

# Import Shared & Utils
from ui_utils import navigate_to

# Import Modules
from forms import form_producer, form_wine, form_bottle, form_tasting, form_restaurant_visit, form_place
from views.cellar import view_cellar
from views.tasting_history import view_tasting_notes
from views.directory import view_producers, view_places
from views.details import view_producer_detail, view_wine_detail, view_bottle_detail, view_place_detail, view_appellation_detail, view_tasting_detail, view_vineyard_detail
from views.summary import view_summary
from views.map import view_map

# --- PAGE CONFIG ---
st.set_page_config(page_title="WineLib", layout="wide", page_icon="🍷")

# --- ROUTING & STATE ---
NAV_OPTIONS = ["Cellar", "Tasting Notes", "Summary", "Producers", "Places", "Map"]

# Initialize session state
if "page" not in st.session_state:
    st.session_state["page"] = "Cellar"

# Determine current view from URL or state
params = st.query_params.to_dict()
current_view = params.get("page", st.session_state["page"])

# Determine which sidebar option should be highlighted
sidebar_idx = None
if current_view in NAV_OPTIONS:
    sidebar_idx = NAV_OPTIONS.index(current_view)

# Sidebar navigation
st.sidebar.markdown('# :material/wine_bar: WineLib ', unsafe_allow_html=True)
selection = st.sidebar.radio("Navigation", NAV_OPTIONS, index=sidebar_idx)

# Handle sidebar interaction (Change of top-level page)
if selection is not None and selection != current_view:
    st.session_state["page"] = selection
    st.query_params.clear() 
    st.query_params["page"] = selection
    st.rerun()

st.sidebar.divider()
if st.sidebar.button("Clear Cache", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# Final current view for rendering
current_view = st.query_params.get("page", st.session_state["page"])

# --- MASTER ROUTING ---
if current_view == "Cellar":
    view_cellar()

elif current_view == "Tasting Notes":
    view_tasting_notes()

elif current_view == "Summary":
    view_summary()

elif current_view == "Producers":
    view_producers()

elif current_view == "Places":
    view_places()

elif current_view == "Map":
    view_map()

# Forms
elif current_view == "Add Producer":
    if st.button("Cancel"): navigate_to("Producers")
    form_producer()

elif current_view == "Add Wine":
    if st.button("Cancel"): navigate_to("Cellar")
    form_wine()

elif current_view == "Add Tasting":
    if st.button("Cancel"): navigate_to("Tasting Notes")
    form_tasting(wine_id=params.get("wine_id"), bottle_id=params.get("bottle_id"))

elif current_view == "Add Bottle":
    if st.button("Cancel"): navigate_to("Cellar")
    form_bottle()

elif current_view == "Add Restaurant Visit":
    if st.button("Cancel"): navigate_to("Places")
    form_restaurant_visit()

# Details
elif current_view == "Producer Detail":
    view_producer_detail(params.get("id"))

elif current_view == "Wine Detail":
    view_wine_detail(params.get("id"))

elif current_view == "Bottle Detail":
    view_bottle_detail(params.get("id"))

elif current_view == "Place Detail":
    view_place_detail(params.get("id"))

elif current_view == "Appellation Detail":
    view_appellation_detail(params.get("id"))

elif current_view == "Tasting Detail":
    view_tasting_detail(params.get("id"))

elif current_view == "Vineyard Detail":
    view_vineyard_detail(params.get("id"))

# Edits
elif current_view == "Edit Producer":
    if st.button("Back"): navigate_to("Producers")
    form_producer(params.get("id"))

elif current_view == "Edit Wine":
    if st.button("Back"): navigate_to("Cellar")
    form_wine(params.get("id"))

elif current_view == "Edit Bottle":
    if st.button("Back"): navigate_to("Cellar")
    form_bottle(params.get("id"))

elif current_view in ["Edit Tasting", "Edit_Tasting"]:
    if st.button("Back"): navigate_to("Tasting Notes")
    form_tasting(params.get("id"))

elif current_view == "Edit Place":
    if st.button("Cancel"): navigate_to("Place Detail", {"id": params.get("id")})
    form_place(params.get("id"))
