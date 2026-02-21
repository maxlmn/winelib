import streamlit as st
import pandas as pd
import numpy as np
from shared import get_region_colors_map, TYPE_COLORS

COLOR_PRODUCER = "#d9ead3"
COLOR_SEC = "#ead1dc"
COLOR_VINTAGE = "#d9d2e9"
COLOR_APPELATION = "#ead1dc"

def render_table(styler, config, cols):
    # Ensure specific columns expand to fill space if using container width
    new_config = config.copy() if config else {}
    greedy_cols = ["Producer", "Domaine", "Domaine_Link", "Cuvee", "Cuvee_Link", "Link"]
    for c in cols:
        if c in greedy_cols and c not in new_config:
            # We use "large" to suggest these should take more space
            new_config[c] = st.column_config.Column(width="large")
            
    n_rows = len(styler.data)
    height = min((n_rows + 1) * 35 + 3, 2000)
    if height < 150: height = 150
    st.dataframe(styler, column_config=new_config, hide_index=True, width="stretch", column_order=cols, height=height)


def navigate_to(page_name, params=None):
    st.session_state["page"] = page_name
    st.query_params["page"] = page_name
    if params:
        for k, v in params.items():
            st.query_params[k] = v
    else:
        st.query_params.clear()
        st.query_params["page"] = page_name
    st.rerun()

def display_region_line(region):
    region_colors = get_region_colors_map()
    color = region_colors.get(region, "#7b68ee")
    st.markdown(f'<hr style="border: none; border-top: 3px solid {color}; margin: 5px 0 15px 0; opacity: 0.8;">', unsafe_allow_html=True)

opacity = "80"
color_dark = "#808080"
def apply_colors(df):
    region_colors = get_region_colors_map()
    
    def color_region(val):
        color = region_colors.get(val)
        if color: return f'font-weight: bold; color: {color};'
        return ''
        
    def color_type(val):
        cols = TYPE_COLORS.get(val)
        if cols: return f'font-weight: bold; color: {cols[0]}; font-size: 1.2em; text-align: center;'
        return ''
    
    def color_producer(val):
        col = COLOR_PRODUCER
        return f'font-weight: bold;' 
    
    def color_appellation(val):
        col = COLOR_APPELATION
        return f'font-weight: bold;' 
    styler = df.style
    
    if "Region" in df.columns:
        styler = styler.map(color_region, subset=["Region"])
    if "Color" in df.columns: 
        styler = styler.map(color_type, subset=["Color"])
        styler = styler.format({"Color": lambda x: "●"})
    if "Type" in df.columns and not "City" in df.columns:
        styler = styler.map(color_type, subset=["Type"])
        styler = styler.format({"Type": lambda x: "●"})
        
    prod_cols = [c for c in df.columns if c in ["Producer", "Domaine", "Producer_Link", "Domaine_Link", "Name_Link"]]
    if prod_cols:
        styler = styler.map(color_producer, subset=prod_cols)
        
    app_var_cols = [c for c in df.columns if c in ["Appellation", "Varietal"]]
    if app_var_cols:
        styler = styler.map(color_appellation, subset=app_var_cols)

    if "Vintage" in df.columns:
        try:
            vintages = pd.to_numeric(df["Vintage"], errors='coerce')
            min_v = vintages.min()
            max_v = vintages.max()
            
            def get_vintage_color(v):
                try:
                    year = float(v)
                    if np.isnan(year): return ''
                    if min_v == max_v:
                        return 'font-weight: bold; background-color: #d9ead3; color: black'
                    
                    norm = (year - min_v) / (max_v - min_v)
                    # Custom interpolation from purple-ish to green-is
                    s_rgb = [209, 196, 233] # Start
                    e_rgb = [217, 234, 211] # End
                    curr_rgb = [int(s + (e - s) * norm) for s, e in zip(s_rgb, e_rgb)]
                    hex_color = '#{:02x}{:02x}{:02x}'.format(*curr_rgb)
                    return f'font-weight: bold; color: black; background-color: {hex_color};'
                except:
                    return f'font-weight: bold; color: black; background-color: {COLOR_VINTAGE};'
                 
            #styler = styler.map(get_vintage_color, subset=["Vintage"])
            styler = styler.map(lambda x: f'font-weight: bold;', subset=["Vintage"])
        except Exception:
            pass

    return styler
