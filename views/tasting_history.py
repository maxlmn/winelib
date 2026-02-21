import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func
from shared import get_session, engine
from ui_utils import apply_colors, render_table, navigate_to
from shared import (
    TastingNote, Place, RestaurantVisit
)

def view_tasting_notes():
    st.markdown('# :material/wine_bar: Tastings', unsafe_allow_html=True)
    
    session = get_session()
    total_notes = session.query(TastingNote).count()
    avg_score = session.query(func.avg(TastingNote.rating)).scalar() or 0
    m1, m2 = st.columns(2)
    
    with st.container(border=True):
        c1, c2 = st.columns([1, 1])
        
        with c1:
            if st.button("Add Tasting", type="primary"): navigate_to("Add Tasting")

        c2.caption("Total Notes")
        c2.write(f"**{int(total_notes)}**")

    # Custom CSS handled by shared component


    # Handle filtering by Wine ID

    wid = st.query_params.get("wid")
    
    query = """
        SELECT 
            w.type as "Color",
            r.name as "Region",
            p.name as "Domaine",
            w.cuvee as "Cuvee",
            a.name as "Appellation",
            v.name as "Varietal",
            w.blend as "Blend",
            w.vintage as "Vintage",
            w.disgorgement_date as "Disgorgement",
            t.date as "Date",
            t.sequence as "Seq",
            b.provenance as "Provenance",
            b.bottle_size as "Format",
            b.price as "Price",
            t.glasses as "Glasses",
            pl.name as "Location",
            t.location as "loc_raw",
            t.notes as "Notes",
            w.rp_score as "RP",
            pl.city as "City", pl.michelin_stars as "Stars", pl.lat as "Lat", pl.lng as "Lng",
            p.id as "pid", w.id as "wid", t.id as "tid", pl.id as "plid", a.id as "aid"
        FROM tasting_notes t
        JOIN cellar b ON t.bottle_id = b.id
        JOIN wines w ON b.wine_id = w.id
        JOIN producers p ON w.producer_id = p.id
        LEFT JOIN regions r ON w.region_id = r.id
        LEFT JOIN appellations a ON w.appellation_id = a.id
        LEFT JOIN varietals v ON w.varietal_id = v.id
        LEFT JOIN places pl ON t.place_id = pl.id
    """
    
    if wid:
        query += f" WHERE w.id = {wid}"
        
    query += " ORDER BY t.date DESC"
    
    df = pd.read_sql(query, engine)
    session.close()
    
    if not df.empty:
        df['Location'] = df['Location'].fillna(df['loc_raw'])
        df['Vintage'] = df.apply(lambda x: f"{x['Vintage']} - {x['Disgorgement']}" if (x['Vintage'] == "NV" and pd.notnull(x['Disgorgement']) and x['Disgorgement']) else x['Vintage'], axis=1)
        
        # --- FILTERS ---
        with st.container(border=True):
            f1, f2, f3, f4, f5 = st.columns(5)
            
            sel_color = f1.multiselect("Color", sorted(df["Color"].unique()))
            sel_region = f2.multiselect("Region", sorted(df["Region"].unique().tolist()))
            sel_prod = f3.multiselect("Producer", sorted(df["Domaine"].unique().tolist()))
            sel_loc = f4.multiselect("Location", sorted(df["Location"].unique().tolist()))
        
            # Date range filter
            min_date = pd.to_datetime(df["Date"]).min().date()
            data_max_date = pd.to_datetime(df["Date"]).max().date()
            today = datetime.now().date()
            picker_max_date = max(data_max_date, today)
            ytd_start = datetime(today.year, 1, 1).date()
            
            # Explicitly set end_date to today for relative periods to avoid T-1 issues
            end_date = picker_max_date 

            period_options = ["Year to Date", "All", "Last 30 Days", "Custom"]
            selected_period = f5.selectbox("Period", period_options, index=0)
        
            # Determine start/end dates
            if selected_period == "Year to Date":
                start_date = max(min_date, ytd_start)
                end_date = picker_max_date
            elif selected_period == "Last 30 Days":
                start_date = max(min_date, today - timedelta(days=30))
                end_date = picker_max_date
            elif selected_period == "All":
                start_date = min_date
                end_date = picker_max_date
            elif selected_period == "Custom":
                # Ensure initial value is valid
                init_start = max(min_date, ytd_start)
                if init_start > picker_max_date: init_start = picker_max_date
                
                d_range = f5.date_input("Range", value=(init_start, picker_max_date), min_value=min_date, max_value=picker_max_date, label_visibility="collapsed")
                if isinstance(d_range, tuple) and len(d_range) == 2:
                    start_date, end_date = d_range
                else:
                    start_date = init_start
                    end_date = picker_max_date
        
        # Apply filtering
        filtered_df = df.copy()
        if sel_color: filtered_df = filtered_df[filtered_df["Color"].isin(sel_color)]
        if sel_region: filtered_df = filtered_df[filtered_df["Region"].isin(sel_region)]
        if sel_prod: filtered_df = filtered_df[filtered_df["Domaine"].isin(sel_prod)]
        if sel_loc: filtered_df = filtered_df[filtered_df["Location"].isin(sel_loc)]
        
        # Apply Date Filter
        if selected_period != "All":
             filtered_df = filtered_df[
                (pd.to_datetime(filtered_df["Date"]).dt.date >= start_date) & 
                (pd.to_datetime(filtered_df["Date"]).dt.date <= end_date)
            ]

        if filtered_df.empty:
            st.info("No notes match the selected filters.")
            return


        # Tabs
        # Tabs
        tab_cards, tab_list, tab_map = st.tabs(["Cards", "List", "Map"])
        
        with tab_list:
            if filtered_df.empty:
                 st.info("No notes match the selected filters.")
            else:
                filtered_df['Domaine_Link'] = filtered_df.apply(lambda x: f"/?page=Producer+Detail&id={x['pid']}&label={x['Domaine'].replace(' ', '+')}", axis=1)
                filtered_df['Cuvee_Link'] = filtered_df.apply(lambda x: f"/?page=Wine+Detail&id={x['wid']}&label={x['Cuvee'].replace(' ', '+') if pd.notnull(x['Cuvee']) and x['Cuvee'].strip() else '-'}", axis=1)
                filtered_df['Seq_Link'] = filtered_df.apply(lambda x: f"/?page=Edit_Tasting&id={x['tid']}&label={int(x['Seq']) if pd.notnull(x['Seq']) else 0}", axis=1)
                filtered_df['Location_Link'] = filtered_df.apply(lambda x: f"/?page=Place+Detail&id={x['plid']}&label={str(x['Location']).replace(' ', '+')}" if pd.notnull(x['plid']) else None, axis=1)
                filtered_df['Appellation_Link'] = filtered_df.apply(lambda x: f"/?page=Appellation+Detail&id={int(x['aid'])}&label={x['Appellation'].replace(' ', '+')}" if pd.notnull(x['aid']) else x['Appellation'], axis=1)
                
                # Prepare columns and renames
                display_df = filtered_df.drop(columns=["Seq", "Location", "Appellation"], errors="ignore")
                rename_map = {"Seq_Link": "Seq", "Location_Link": "Location", "Appellation_Link": "Appellation"}
                
                # Moved "Date" to first position as per request
                cols_to_show = ["Date", "Seq", "Color", "Region", "Domaine_Link", "Cuvee_Link", "Appellation", "Varietal", "Vintage", "Format", "Glasses", "Location", "RP"]
                
                # Calculate which columns actually exist (or will exist after rename)
                current_cols = display_df.rename(columns=rename_map).columns.tolist()
                final_cols = [c for c in cols_to_show if c in current_cols]

                # Create styler with renamed columns
                styler = apply_colors(display_df.rename(columns=rename_map))

                render_table(
                    styler,
                    config={
                        "Seq": st.column_config.LinkColumn("Seq", display_text=r"label=(.*?)(?:&|$)"),
                        "Domaine_Link": st.column_config.LinkColumn("Domaine", display_text=r"label=(.*?)(?:&|$)"),
                        "Cuvee_Link": st.column_config.LinkColumn("Cuvee", display_text=r"label=(.*?)(?:&|$)"),
                        "Appellation": st.column_config.LinkColumn("Appellation", display_text=r"label=(.*?)(?:&|$)"),
                        "Location": st.column_config.LinkColumn("Location", display_text=r"label=(.*?)(?:&|$)"),
                        "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                        "Glasses": st.column_config.NumberColumn("Glasses", format="%.1f")
                    },
                    cols=final_cols
                )

        with tab_cards:

            
                # 1. Fetch Restaurant Visits (if not filtered out by wine attributes)
                visits_data = []
                
                # If any wine-specific filter is active, we skip visits as they don't have these attributes
                wine_filters_active = any([sel_color, sel_region, sel_prod])
                
                if not wine_filters_active:
                    session = get_session()
                    from sqlalchemy.orm import joinedload
                    v_query = session.query(RestaurantVisit).options(joinedload(RestaurantVisit.place))
                    
                    # Apply Date Filter
                    if selected_period != "All":
                        v_query = v_query.filter(RestaurantVisit.date >= start_date, RestaurantVisit.date <= end_date)
                        
                    # Apply Location Filter (if active)
                    if sel_loc:
                        v_query = v_query.filter(Place.name.in_(sel_loc))
                        
                    visits = v_query.all()
                    
                    for v in visits:
                        visits_data.append({
                            "type": "visit",
                            "date": v.date,
                            "place_name": v.place.name,
                            "city": v.place.city,
                            "stars": v.place.michelin_stars,
                            "notes": v.notes,
                            "id": v.id,
                            "obj": v
                        })
                    # session.close() # Keep open until end of function

                # 2. Process Tasting Notes (filtered_df)
                if not filtered_df.empty:
                    # Group by (Date, Place)
                    # We need to ensure date is date object
                    filtered_df["DateObj"] = pd.to_datetime(filtered_df["Date"]).dt.date
                    
                    grouped_tastings = filtered_df.groupby(["DateObj", "Location"])
                    
                    tastings_data = []
                    for (d, loc), group in grouped_tastings:
                        # Meta info from first row if available
                        first = group.iloc[0]
                        
                        tastings_data.append({
                            "type": "tasting_group",
                            "date": d,
                            "place_name": loc,
                            # Sort by Seq (ensure numeric)
                            "wines": group.sort_values("Seq").to_dict("records"),
                            "plid": first["plid"] if pd.notnull(first["plid"]) else None
                        })
                else:
                    tastings_data = []

                # 3. Merge and Sort
                all_events = visits_data + tastings_data
                all_events.sort(key=lambda x: x["date"], reverse=True)
                
                if not all_events:
                     st.info("No stats available.")
                
                # 4. Prepare for Shared Component
                final_events = []
                for event in all_events:
                    # Header URL
                    place_url = "#"
                    if event.get("id") and event["type"] == "visit":
                        pid = event["obj"].place.id
                        place_url = f"/?page=Place+Detail&id={pid}"
                    elif event.get("plid"):
                        place_url = f"/?page=Place+Detail&id={event['plid']}"
                    
                    # Metadata HTML Construction
                    city = ""
                    stars = 0
                    if event["type"] == "visit":
                        city = event.get("city")
                        stars = event.get("stars") or 0
                    elif event["type"] == "tasting_group":
                        if event["wines"]:
                            first_row = event["wines"][0] 
                            city = first_row.get("City")
                            stars = first_row.get("Stars")
                            if pd.isna(stars): stars = 0
                            else: stars = int(stars)
                            if pd.isna(city): city = ""

                    meta_parts = []
                    if city: meta_parts.append(city)
                    if stars: meta_parts.append("⭐" * stars)
                    meta_html = " • ".join(meta_parts) if meta_parts else "&nbsp;"
                    
                    # Add computed fields
                    event['url'] = place_url
                    event['meta'] = meta_html
                    
                    final_events.append(event)

                from views.components import render_tasting_cards
                render_tasting_cards(final_events)
                
                # Close the session if it was opened
                if not wine_filters_active:
                    session.close()

        with tab_map:
            # Aggregate unique places with coordinates
            unique_places = {}

            # 1. From Visits
            if wine_filters_active == False:
                 # visits are already fetched
                 if 'visits' in locals():
                     for v in visits:
                         if v.place and v.place.lat and v.place.lng:
                             unique_places[v.place.id] = {
                                 "name": v.place.name,
                                 "lat": v.place.lat,
                                 "lng": v.place.lng,
                                 "count": 1, 
                                 "type": "Visit"
                             }
            
            # 2. From filtered_df
            if not filtered_df.empty:
                # Iterate rows to find places
                # ensure we have Lat/Lng columns
                if "Lat" in filtered_df.columns and "Lng" in filtered_df.columns:
                     for _, row in filtered_df.iterrows():
                         if pd.notnull(row["Lat"]) and pd.notnull(row["Lng"]):
                             pid = int(row["plid"])
                             if pid not in unique_places:
                                 unique_places[pid] = {
                                     "name": row["Location"],
                                     "lat": row["Lat"],
                                     "lng": row["Lng"],
                                     "count": 0,
                                     "type": "Tasting"
                                 }
                             unique_places[pid]["count"] += 1

            if unique_places:
                import folium
                from streamlit_folium import st_folium

                # Determine center
                lats = [d['lat'] for d in unique_places.values()]
                lngs = [d['lng'] for d in unique_places.values()]
                
                if lats and lngs:
                    # Calculate bounds
                    min_lat, max_lat = min(lats), max(lats)
                    min_lng, max_lng = min(lngs), max(lngs)
                    
                    # Center for initialization
                    center_lat = (min_lat + max_lat) / 2
                    center_lng = (min_lng + max_lng) / 2
                    
                    # Create map and let folium handle zoom via fit_bounds
                    m = folium.Map(location=[center_lat, center_lng], zoom_start=5)
                    m.fit_bounds([[min_lat, min_lng], [max_lat, max_lng]])
                else:
                    m = folium.Map(location=[47.0, 4.0], zoom_start=4)

                for pid, data in unique_places.items():
                    tooltip = f"{data['name']} ({data['count']} events)"
                    
                    # Create popup link
                    # values matching app.py routing
                    popup_html = f"<b>{data['name']}</b><br><a href='/?page=Place+Detail&id={pid}' target='_top'>Open Details</a>"
                    
                    folium.Marker(
                        [data['lat'], data['lng']],
                        tooltip=tooltip,
                        popup=folium.Popup(popup_html, max_width=300),
                        icon=folium.Icon(color="red", icon="cutlery", prefix='fa')
                    ).add_to(m)
                
                st_folium(m, height=500, width="100%", returned_objects=[])
                
            else:
                st.info("No geocoded places data available for current selection.")

    else:
        st.info("No notes found.")
