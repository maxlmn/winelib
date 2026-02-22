import streamlit as st
import pandas as pd
from shared import get_session, get_region_name
from ui_utils import apply_colors, render_table, navigate_to
from sqlalchemy.orm import joinedload
from shared import Producer, Place, Region

def view_producers():
    st.markdown('# :material/domain: Producers', unsafe_allow_html=True)
    if st.button("Add New Producer"): navigate_to("Add Producer")
    session = get_session()
    prods = session.query(Producer)\
        .outerjoin(Producer.region_obj)\
        .order_by(Region.name, Producer.subregion, Producer.village, Producer.name)\
        .options(joinedload(Producer.region_obj))\
        .all()
    
    data = []
    for p in prods:
        r_name = get_region_name(p)
        data.append({
            "Name": p.name, 
            "Region": r_name, 
            "Subregion": p.subregion,
            "Village": p.village,
            "Winemaker": p.winemaker, 
            "Lists": p.lists,
            "Notes": p.notes,
            "id": p.id
        })
    df = pd.DataFrame(data)
    if "Lists" in df.columns:
        # Strip brackets AND quotes for clean display
        df["Lists"] = df["Lists"].str.strip("[]").str.replace("'", "").str.replace('"', "").str.strip()
    
    if not df.empty:
        # --- FILTERS ---
        f1, f2, f3, f4, f5, f6 = st.columns(6)
        sel_region = f1.multiselect("Region", sorted(df["Region"].dropna().unique().tolist()))
        sel_subregion = f2.multiselect("Subregion", sorted(df["Subregion"].dropna().unique().tolist()))
        sel_village = f3.multiselect("Village", sorted(df["Village"].dropna().unique().tolist()))
        sel_winemaker = f4.multiselect("Winemaker", sorted(df["Winemaker"].dropna().unique().tolist()))
        
        # Get unique individual lists for the dropdown
        list_options = []
        if "Lists" in df.columns:
            all_lists_str = df["Lists"].dropna().unique()
            split_lists = []
            for l_str in all_lists_str:
                # Content is already cleaned by strip/replace above
                split_lists.extend([item.strip() for item in str(l_str).split(",")])
            list_options = sorted(list(set(item for item in split_lists if item)))
            
        sel_lists = f5.multiselect("Lists", list_options)
        search_name = f6.text_input("Search Name")
        
        filtered_df = df.copy()
        if sel_region: filtered_df = filtered_df[filtered_df["Region"].isin(sel_region)]
        if sel_subregion: filtered_df = filtered_df[filtered_df["Subregion"].isin(sel_subregion)]
        if sel_village: filtered_df = filtered_df[filtered_df["Village"].isin(sel_village)]
        if sel_winemaker: filtered_df = filtered_df[filtered_df["Winemaker"].isin(sel_winemaker)]
        
        if sel_lists:
            # Robust check for list membership that handles special characters and leading/trailing spaces
            def has_selected_list(row_lists_str):
                if not row_lists_str or pd.isna(row_lists_str):
                    return False
                item_lists = [i.strip().strip("'\"") for i in str(row_lists_str).split(",")]
                return any(selected.strip().strip("'\"") in item_lists for selected in sel_lists)
            
            filtered_df = filtered_df[filtered_df["Lists"].apply(has_selected_list)]
            
        if search_name: filtered_df = filtered_df[filtered_df["Name"].str.contains(search_name, case=False, na=False)]
        
        if not filtered_df.empty:
            filtered_df['Name_Link'] = filtered_df.apply(lambda x: f"/?page=Producer+Detail&id={x['id']}&label={x['Name'].replace(' ', '+')}", axis=1)
            
            cols_to_show = ["Name_Link", "Region", "Subregion", "Village", "Winemaker", "Lists", "Notes"]
            styler = apply_colors(filtered_df[cols_to_show])
            
            render_table(
                styler, 
                config={"Name_Link": st.column_config.LinkColumn("Name", display_text=r"label=(.*?)(?:&|$)")}, 
                cols=cols_to_show
            )
        else:
            st.info("No producers match the selected filters.")
    session.close()



def view_places():
    st.markdown('# :material/restaurant: Places', unsafe_allow_html=True)
    if st.button("Add Restaurant Visit"): navigate_to("Add Restaurant Visit")
    session = get_session()
    # Eager load tastings and visits to calculate unique dates
    places = session.query(Place).options(joinedload(Place.tastings), joinedload(Place.visits)).order_by(Place.name).all()
    
    data = []
    for p in places:
        # Calculate unique dates visited
        tasting_dates = set(t.date for t in p.tastings if t.date)
        visit_dates = set(v.date for v in p.visits if v.date)
        all_dates = tasting_dates.union(visit_dates)
        
        data.append({
            "Name": p.name, 
            "City": p.city, 
            "Country": p.country, 
            "Type": p.type, 
            "Michelin Stars": p.michelin_stars if p.michelin_stars else 0,
            "Visits": len(all_dates),
            "Last Visit": max(all_dates) if all_dates else None,
            "id": p.id
        })
        
    df = pd.DataFrame(data)
    df = df.sort_values("Last Visit", ascending=False, na_position="last").reset_index(drop=True)
    session.close()

    if not df.empty:
        # --- FILTERS ---
        f1, f2, f3, f4, f5 = st.columns(5)
        sel_country = f1.multiselect("Country", sorted(df["Country"].dropna().unique().tolist()))
        sel_city = f2.multiselect("City", sorted(df["City"].dropna().unique().tolist()))
        sel_type = f3.multiselect("Type", sorted(df["Type"].dropna().unique().tolist()))
        sel_stars = f4.multiselect("Michelin Stars", sorted(df["Michelin Stars"].unique().tolist()))
        search_name = f5.text_input("Search Name")

        filtered_df = df.copy()
        if sel_country: filtered_df = filtered_df[filtered_df["Country"].isin(sel_country)]
        if sel_city: filtered_df = filtered_df[filtered_df["City"].isin(sel_city)]
        if sel_type: filtered_df = filtered_df[filtered_df["Type"].isin(sel_type)]
        if sel_stars: filtered_df = filtered_df[filtered_df["Michelin Stars"].isin(sel_stars)]
        if search_name: filtered_df = filtered_df[filtered_df["Name"].str.contains(search_name, case=False, na=False)]

        if not filtered_df.empty:
            filtered_df['Name_Link'] = filtered_df.apply(lambda x: f"/?page=Place+Detail&id={x['id']}&label={x['Name'].replace(' ', '+')}", axis=1)
            
            # Drop original Name before renaming link to avoid duplicate column names
            display_df = filtered_df.drop(columns=["Name"], errors="ignore").rename(columns={"Name_Link": "Name"})
            
            # Convert stars to emojis
            display_df["Michelin Stars"] = display_df["Michelin Stars"].apply(lambda x: "⭐" * int(x) if x > 0 else "")
            
            styler = apply_colors(display_df)
            
            render_table(
                styler,
                config={
                    "Name": st.column_config.LinkColumn("Name", display_text=r"label=(.*?)(?:&|$)"),
                    "Michelin Stars": st.column_config.TextColumn("Michelin Stars"),
                    "Visits": st.column_config.NumberColumn("Visits")
                },
                cols=["Name", "City", "Country", "Type", "Michelin Stars", "Visits", "Last Visit", "Notes"]
            )
        else:
            st.info("No places match the selected filters.")
    else:
        st.info("No places found.")
