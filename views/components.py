import streamlit as st
import glob
import os
import base64
from shared import get_region_colors_map, TYPE_COLORS

CURRENT_DIR = os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def render_tasting_cards(events, key_suffix=""):
    """
    Renders a grid of tasting cards (Visits or Tasting Groups).
    
    Args:
        events (list): List of event dictionaries.
        key_suffix (str): Optional suffix to ensure unique keys for interactive elements.
    """
    if not events:
        st.info("No notes found.")
        return

    # Check for Show Notes Inline preference
    show_inline = st.checkbox("Show Notes Inline", value=False, key=f"inline_notes_{len(events)}_{key_suffix}")

    # Inject CSS once
    st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] > div.wine-card {
        background-color: transparent;
    }
    .wine-card {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        overflow: hidden; 
        background-color: var(--background-color);
        color: var(--text-color);
    }
    
    .wine-card-header {
        background-color: rgba(128, 128, 128, 0.1);
        padding: 10px 15px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .wine-card-header a {
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .wine-card-body {
        padding: 15px;
    }
    
    .wine-card-meta {
        font-size: 0.9rem;
        color: gray;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    region_colors = get_region_colors_map()
    for event in events:
        # Prepare Data for Rendering
        place_url = event.get('url', '#')
        place_name = event.get('place_name', 'Unknown Place')
        date_str = event['date'].strftime('%Y-%m-%d')
        
        # Meta HTML
        meta_html = event.get('meta', '&nbsp;')
        
        # Body Content
        body_content = ""
        
        if event['type'] == 'visit':
            notes = event.get('notes')
            if notes:
                body_content += f"<div style='font-style: italic; color: #555;'>{notes}</div>"
            else:
                body_content += "<span style='color: #888; font-size: 0.9em;'>No notes.</span>"
        
        elif event['type'] == 'tasting_group':
            body_content += "<ul style='padding-left: 20px; margin-top: 5px;'>"
            for w in event['wines']:
                # Expecting dictionary w/ keys: Domaine, Cuvee, Appellation, Vintage, wid, Notes, Region, Color
                prod = w.get('Domaine', '')
                cuvee = w.get('Cuvee', '')
                app = w.get('Appellation', '')
                year = w.get('Vintage', '')
                wid = w.get('wid', 0)
                tid = w.get('tid')
                wine_url = f"/?page=Wine+Detail&id={wid}"
                tasting_url = f"/?page=Tasting+Detail&id={tid}" if tid else "#"
                
                # Note Logic
                note_text = w.get('Notes', '')
                safe_note = str(note_text).replace('"', '&quot;').replace("'", "&apos;") if note_text else ""
                
                note_html = ""
                if show_inline and note_text:
                     note_html = f"<br><a href='{tasting_url}' target='_self' style='color: #666; font-size: 0.9em; font-style: italic; text-decoration: none; margin-left: 20px; display: block;'>&gt; {w['Notes']}</a>"
                
                # Tooltip on wine link
                note_attr = f" title=\"{safe_note}\"" if safe_note and not show_inline else ""

                # Colors
                region = w.get('Region', 'Other')
                r_color = region_colors.get(region, "#ccc")
                w_type = w.get('Color', 'Other')
                type_cols = TYPE_COLORS.get(w_type, ["#ccc", "#000"])
                w_color = type_cols[0]

                # Visuals
                region_bar = f"<span style='display: inline-block; width: 4px; height: 12px; background-color: {r_color}; margin-right: 6px; border-radius: 2px; vertical-align: middle;'></span>"
                color_circle = f"<span style='display: inline-block; width: 10px; height: 10px; background-color: {w_color}; border-radius: 50%; margin-right: 6px; vertical-align: middle;'></span>"
                
                # Label
                label_html = f"{region_bar}<b>{prod}</b>"
                if cuvee: label_html += f" - {cuvee}"
                if app: label_html += f" ({app})"
                label_html += f" {color_circle}<span style='color: #666;'>[{year}]</span>"
                
                action_link=""
                # Action Link (Icon)
                if not note_text:
                    icon = "➕"
                    action_link = f"&nbsp;<a href='{tasting_url}' target='_self' style='text-decoration: none; font-size: 0.8em; opacity: 0.7;'>{icon}</a>"
                
                body_content += f"<li style='margin-bottom: 8px; list-style: none; margin-left: -20px;'><a href='{wine_url}' target='_self' style='text-decoration: none; color: inherit; hover: {{text-decoration: underline;}}'{note_attr}>{label_html}</a>{action_link}{note_html}</li>"
            body_content += "</ul>"

        # Render Card
        # Check for image
        img_html = ""
        try:
            # Pattern: place.lower()_YYYY-MM-DD.*
            # Example: data/images/the french laundry_2023-10-27.jpg
            search_pattern = os.path.join(CURRENT_DIR, "data", "images", f"{place_name.lower()}_{date_str}.*")
            matches = glob.glob(search_pattern)
            if matches:
                # Use the first match
                file_path = matches[0]
                with open(file_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                    ext = os.path.splitext(file_path)[1].lower().replace('.', '')
                    # Simple mime mapping
                    mime = 'jpeg' if ext in ['jpg', 'jpeg'] else ext
                    if ext == 'svg': mime = 'svg+xml'
                    
                    img_src = f"data:image/{mime};base64,{encoded}"
                    img_html = f"""
<div style="margin-left: 15px; flex-shrink: 0;">
    <img src="{img_src}" style="max-width: 500px; max-height: 500px; border-radius: 4px; object-fit: cover;">
</div>
"""
        except Exception:
            pass

        # Render Card
        card_html = f"""
<div class="wine-card">
<div class="wine-card-header">
<a href="{place_url}" target="_self" style="text-decoration: none; color: var(--primary-color);">{place_name}</a>
<span style="color: #666; font-size: 0.9rem;">{date_str}</span>
</div>
<div class="wine-card-body" style="display: flex; align-items: flex-start;">
<div style="flex: 1;">
<div class="wine-card-meta">{meta_html}</div>
{body_content}
</div>
{img_html}
</div>
</div>
"""
        st.markdown(card_html, unsafe_allow_html=True)


def render_cellar_cards(bottles_df):
    """
    Renders the collapsible cellar cards grouped by Location Group.
    
    Args:
        bottles_df (pd.DataFrame): DataFrame containing bottle columns:
            - Qty, Region, Color, Domaine, Cuvee, Appellation, Vintage, wid
            - LocGroup (for grouping)
            - Total(sgd)
    """
    if bottles_df.empty:
        st.info("Cellar is empty or no matches.")
        return

    region_colors = get_region_colors_map()

    # Helper for inner wine list
    def get_wine_list_html(wines_df):
        if wines_df.empty: return ""
        html_c = "<ul style='padding-left: 0px; margin-top: 5px; list-style: none;'>"
        # Sort by Region > Producer > Cuvee > Vintage
        wines_df = wines_df.sort_values(by=['Region', 'Domaine', 'Cuvee', 'Vintage'], ascending=[True, True, True, False])
        
        for _, row in wines_df.iterrows():
            qty = int(row['Qty'])
            region = row['Region']
            r_color = region_colors.get(region, "#ccc")
            
            w_type = row.get('Color', 'Other')
            type_cols = TYPE_COLORS.get(w_type, ["#ccc", "#000"])
            w_color = type_cols[0]
            
            prod = row['Domaine']
            cuvee = row['Cuvee']
            app = row['Appellation']
            year = row['Vintage']
            wid = row['wid']
            bid = row['bid']
            wine_url = f"/?page=Bottle+Detail&id={bid}"
            
            # Region Bars (one per bottle)
            region_bars = ""
            for _ in range(qty):
                region_bars += f"<span style='display: inline-block; width: 4px; height: 12px; background-color: {r_color}; margin-right: 2px; border-radius: 2px; vertical-align: middle;'></span>"
            
            # Type Dot
            type_dot = f"<span style='display: inline-block; width: 8px; height: 8px; background-color: {w_color}; border-radius: 50%; margin-left: 6px; margin-right: 4px; vertical-align: middle;'></span>"
            
            # Text
            text_label = f"<b>{prod}</b>"
            if cuvee and str(cuvee).strip(): text_label += f" - {cuvee}"
            if app and str(app).strip(): text_label += f" ({app})"
            
            line_html = f"""
<li style='margin-bottom: 6px; display: flex; align-items: center;'>
<div style='margin-right: 8px; white-space: nowrap;'>{region_bars}</div>
<div>
<a href="{wine_url}" target="_self" style="text-decoration: none; color: inherit; margin-right: 0px;">{text_label}</a>
{type_dot}
<span style='color: #666; font-size: 0.9em;'>[{year}]</span>
</div>
</li>
"""
            html_c += line_html
        html_c += "</ul>"
        return html_c

    # Group by LocGroup
    if 'LocGroup' not in bottles_df.columns:
        # Fallback if LocGroup missing, just group all under 'Inventory'
        bottles_df['LocGroup'] = 'Inventory'

    groups = bottles_df.groupby("LocGroup")
    
    for loc_group, group_df in groups:
        # Stats
        total_bottles = group_df['Qty'].sum()
        total_val = group_df['Total(sgd)'].sum() if 'Total(sgd)' in group_df.columns else 0
        
        reds_df = group_df[group_df['Color'] == 'Red']
        reds_count = reds_df['Qty'].sum()
        
        whites_df = group_df[group_df['Color'] != 'Red']
        whites_count = whites_df['Qty'].sum()
        
        # Colors
        red_hex = TYPE_COLORS.get('Red', ['#b11226'])[0]
        white_hex = TYPE_COLORS.get('White', ['#f1c232'])[0]
        
        red_dot = f"<span style='display: inline-block; width: 10px; height: 10px; background-color: {red_hex}; border-radius: 50%; margin-right: 4px;'></span>"
        white_dot = f"<span style='display: inline-block; width: 10px; height: 10px; background-color: {white_hex}; border-radius: 50%; margin-right: 4px;'></span>"
        
        # Bars
        bars_html = "<div style='display: flex; gap: 2px; flex-wrap: wrap;'>"
        sorted_group = group_df.sort_values(by=['Region'])
        for _, row in sorted_group.iterrows():
            qty = int(row['Qty'])
            r_color = region_colors.get(row['Region'], "#ccc")
            for _ in range(qty):
                bars_html += f"<span style='width: 4px; height: 16px; background-color: {r_color}; border-radius: 2px;'></span>"
        bars_html += "</div>"
        
        # Summary HTML - DEDENTED STRICTLY
        summary_html = f"""
<summary style='cursor: pointer; padding: 10px; background-color: rgba(128,128,128,0.1); border-radius: 5px; list-style: none; display: flex; flex-direction: column; color: var(--text-color);'>
<div style='display: flex; align-items: center; width: 100%; margin-bottom: 8px;'>
<span style='margin-right: 15px; font-weight: 600;'>{loc_group} | {total_bottles} Bottles (${total_val:,.0f})</span>
<span style='margin-left: auto; display: flex; align-items: center;'>
{red_dot} <span style='margin-right: 12px;'>{reds_count}</span>
{white_dot} <span>{whites_count}</span>
</span>
</div>
<div style='width: 100%;'>
{bars_html}
</div>
</summary>
"""
        
        reds_html = get_wine_list_html(reds_df)
        whites_html = get_wine_list_html(whites_df)
        
        columns_html = f"""
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
<div>{reds_html}</div>
<div>{whites_html}</div>
</div>
"""
        
        details_open = " open" if loc_group == "Home" else ""
        full_html = f"""
<details{details_open} style="margin-bottom: 10px; border: 1px solid rgba(128,128,128,0.2); border-radius: 5px; padding: 5px;">
{summary_html}
<div style="padding: 10px;">
{columns_html}
</div>
</details>
"""
        st.markdown(full_html, unsafe_allow_html=True)
