
import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import mapping as shape_mapping
from sqlalchemy import or_

from shared import get_session, get_all_regions, get_region_name
from shared import Appellation, Vineyard
from geo_utils import (
    resolve_app_geometry, 
    resolve_vine_geometry,
    get_geometry_bounds,
    add_tile_layers
)

# Redundant cached functions removed (moved to geo_utils.py)

def view_map():
    st.markdown("# :material/map: Appellations Map", unsafe_allow_html=True)
    
    session = get_session()
    try:
        # --- 1. Fetch available data ---
        # Get all regions from DB (cached)
        all_regions = get_all_regions()
        region_map = {r.name: r for r in all_regions}
        
        # Filter regions that actually have geodata (optional but good for UX)
        # For now, let's just use all regions that are referenced in active data
        active_app_region_ids = session.query(Appellation.region_id).filter(
            or_(Appellation.geojson.isnot(None), Appellation.inao_id.isnot(None), Appellation.pdo_id.isnot(None))
        ).distinct().all()
        active_vine_region_ids = session.query(Vineyard.region_id).filter(
            or_(Vineyard.geojson.isnot(None), Vineyard.vineyard_id.isnot(None))
        ).distinct().all()
        
        active_ids = set([r[0] for r in active_app_region_ids if r[0]])
        active_ids.update([r[0] for r in active_vine_region_ids if r[0]])
        
        display_regions = [r for r in all_regions if r.id in active_ids]
        sorted_region_names = sorted([r.name for r in display_regions])
        
        if not sorted_region_names:
            st.info("No mapped data found.")
            return

        # --- 3. UI Filters ---
        
        # Filter 1: Region (Selectbox)
        default_idx = 0
        if "Loire" in sorted_region_names:
            default_idx = sorted_region_names.index("Loire")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_region_name = st.selectbox("Region", sorted_region_names, index=default_idx)
            selected_region = region_map[selected_region_name]

        # Filter content based on Region Object
        region_apps = session.query(Appellation).filter(
            Appellation.region_id == selected_region.id,
            or_(Appellation.geojson.isnot(None), Appellation.inao_id.isnot(None), Appellation.pdo_id.isnot(None))
        ).all()
        
        region_vineyards = session.query(Vineyard).filter(
            Vineyard.region_id == selected_region.id,
            or_(Vineyard.geojson.isnot(None), Vineyard.vineyard_id.isnot(None))
        ).all()
        
        # Filter 2: Appellations (Multiselect)
        # Options: Name -> ID map to handle duplicate names if any (though unlikely within region)
        app_options = sorted(list(set([a.name for a in region_apps])))
        with col2:
            selected_app_names = st.multiselect("Appellations", app_options)
            
        # Filter 3: Vineyards (Multiselect)
        def format_v(v):
            parts = [x for x in [v.sub_region, v.village, v.name] if x]
            return " - ".join(parts)
            
        v_map = {format_v(v): v for v in region_vineyards}
        vineyard_options = sorted(list(v_map.keys()))
        
        with col3:
            selected_vineyard_labels = st.multiselect("Vineyards", vineyard_options)
            
        # --- 4. Prepare Map Data ---
        
        # Logic: Show SELECTED items.
        
        map_features = []
        
        # Appellations to Render
        apps_to_render = []
        if selected_app_names:
            apps_to_render = [a for a in region_apps if a.name in selected_app_names]
        
        # Vineyards to Render
        vines_to_render = []
        if selected_vineyard_labels:
            vines_to_render = [v_map[label] for label in selected_vineyard_labels]
            
        # Local get_app_geometry removed (using resolve_app_geometry from geo_utils)

        # Helper to add feature
        def add_feature(geo, name, fid, ftype):
            try:
                 if geo['type'] == 'Point':
                    coords = geo['coordinates'] # [lon, lat]
                    lat, lon = coords[1], coords[0]
                    map_features.append({
                        "type": "marker",
                        "location": [lat, lon],
                        "name": name,
                        "id": fid,
                        "ftype": ftype
                    })
                 elif geo['type'] in ['Polygon', 'MultiPolygon']:
                     # Wrap geometry in a Feature to support properties
                     feature = {
                         "type": "Feature",
                         "geometry": geo,
                         "properties": {
                             "name": name,
                             "id": fid,
                             "ftype": ftype
                         }
                     }
                     map_features.append({
                         "type": "geojson",
                         "geo": feature,
                         "name": name,
                         "id": fid,
                         "ftype": ftype
                     })
                 elif geo['type'] == 'FeatureCollection':
                     map_features.append({
                         "type": "geojson",
                         "geo": geo,
                         "name": name,
                         "id": fid,
                         "ftype": ftype
                     })
            except Exception as e:
                pass

        # A. Process Appellations
        for app in apps_to_render:
            geom = resolve_app_geometry(app)
            if geom:
                geo = shape_mapping(geom) if not isinstance(geom, dict) else geom
                add_feature(geo, app.name, app.id, "Appellation")

        # B. Process Vineyards
        for v in vines_to_render:
            geom = resolve_vine_geometry(v)
            if geom:
                geo = shape_mapping(geom) if not isinstance(geom, dict) else geom
                add_feature(geo, v.name, v.id, "Vineyard")

        # --- 5. Render Map ---
        
        # Determine Center
        start_loc = [46.0, 4.0] # France Default
        start_zoom = 6
        
        # If we have selection, center on the first item
        if map_features:
            first = map_features[0]
            # geo_utils.get_geometry_bounds returns bounds for fit_bounds
            geo = first.get('geo') or {"type": "Point", "coordinates": [first['location'][1], first['location'][0]]}
            bounds = get_geometry_bounds(geo)
            if bounds:
                # Calculate center from bounds
                min_lat, min_lng = bounds[0]
                max_lat, max_lng = bounds[1]
                start_loc = [(min_lat + max_lat) / 2, (min_lng + max_lng) / 2]
        
        m = folium.Map(location=start_loc, zoom_start=start_zoom)
        
        # Apply fit_bounds if we have a selection
        if map_features and bounds:
            m.fit_bounds(bounds)
        
        # Draw Features
        
        # Assign Colors (Dynamic from Region or Fixed Fallback)
        for f in map_features:
            region_color = selected_region.color if selected_region.color else "#c27ba0"
            color = region_color if f['ftype'] == "Appellation" else "#228b22"
            f['color'] = color
            
            if f['type'] == 'geojson':
                g = f['geo']
                if g.get('type') == 'Feature':
                    if 'properties' not in g: g['properties'] = {}
                    g['properties']['color'] = color
                    g['properties']['ftype'] = f['ftype']

        def style_function(feature):
            props = feature.get('properties', {})
            ftype = props.get('ftype', 'Unknown')
            default_color = '#c27ba0' if ftype == 'Appellation' else '#228b22'
            color = props.get('color', default_color)
            
            return {
                'fillColor': color,
                'color': color,
                'weight': 1 if ftype == 'Appellation' else 2,
                'fillOpacity': 0.4 if ftype == 'Appellation' else 0.6
            }

        # Markers
        for f in [x for x in map_features if x['type'] == 'marker']:
            color = f['color']
            popup_html = f"<b>{f['ftype']}:</b> {f['name']}<br><a href='/?page={f['ftype']}+Detail&id={f['id']}' target='_top'>Open Details</a>"
            folium.CircleMarker(
                location=f['location'],
                radius=6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                tooltip=f"{f['ftype']}: {f['name']}",
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(m)
            
        # GeoJSONs
        for f in [x for x in map_features if x['type'] == 'geojson']:
            popup_html = f"<b>{f['ftype']}:</b> {f['name']}<br><a href='/?page={f['ftype']}+Detail&id={f['id']}' target='_top'>Open Details</a>"
            folium.GeoJson(
                f['geo'],
                name=f['name'],
                style_function=style_function,
                tooltip=f"{f['ftype']}: {f['name']}",
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(m)

        # Add multiple tile layers for selection
        add_tile_layers(m)

        if not map_features:
            st.info("Select Appellations or Vineyards to view them on the map.")

        st_folium(m, width="100%", height=1000, returned_objects=[])

        # --- 6. Detailed Information ---
        if apps_to_render or vines_to_render:
            st.divider()
            st.subheader("Selected Details")
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown("### :material/label: Appellations")
                if not apps_to_render:
                    st.info("No appellations selected.")
                for a in apps_to_render:
                    with st.container(border=True):
                        st.markdown(f"#### {a.name}")

                        r_name = get_region_name(a) or 'Unknown'
                        st.write(f"**Region:** {r_name}")
                        if a.subregion:
                            st.write(f"**Sub-region:** {a.subregion}")
                        st.write(f"**Type:** {a.type}")
                        
                        if hasattr(a, 'category') and a.category:
                            st.write(f"**Category:** {a.category}")
                        
                        if hasattr(a, 'pdo_id') and a.pdo_id:
                            reg_text = f" (Reg: {a.registration_date})" if getattr(a, 'registration_date', None) else ""
                            st.write(f"**PDO ID:** {a.pdo_id}{reg_text}")

                        yields = []
                        if getattr(a, 'max_yield_hl', None): yields.append(f"{a.max_yield_hl} hl/ha")
                        if getattr(a, 'max_yield_kg', None): yields.append(f"{a.max_yield_kg} kg/ha")
                        if yields:
                            st.write(f"**Max Yield:** {', '.join(yields)}")

                        if getattr(a, 'varieties_text', None):
                            with st.expander("Authorized Varieties"):
                                st.write(a.varieties_text)

                        if a.details:
                            with st.expander("Notes"):
                                st.write(a.details)
                        
                        st.markdown(f"[:material/open_in_new: Open Details](/?page=Appellation+Detail&id={a.id})")

            with col_right:
                st.markdown("### :material/location_on: Vineyards")
                if not vines_to_render:
                    st.info("No vineyards selected.")
                for v in vines_to_render:
                    with st.container(border=True):
                        st.markdown(f"#### {v.name}")
                        r_name = get_region_name(v) or 'Unknown'
                        st.write(f"**Region:** {r_name}")
                        if v.sub_region:
                            st.write(f"**Sub-region:** {v.sub_region}")
                        if v.village:
                            st.write(f"**Village:** {v.village}")
                        
                        st.markdown(f"[:material/open_in_new: Open Details](/?page=Vineyard+Detail&id={v.id})")
    finally:
        session.close()
