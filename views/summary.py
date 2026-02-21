import streamlit as st
import pandas as pd
import altair as alt
from shared import get_session, engine, TYPE_COLORS, get_region_colors_map
from sqlalchemy import func
from shared import TastingNote, Bottle, Wine, Place, RestaurantVisit

def render_colored_bar(label, value, total, color, suffix=""):
    percent = (value / total) * 100 if total > 0 else 0
    st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 0.9rem;">
                <span style="font-weight: 500;">{label}</span>
                <span style="color: var(--text-muted);">{value}{suffix} ({percent:.1f}%)</span>
            </div>
            <div style="background-color: var(--background-bar); border-radius: 6px; height: 10px; width: 100%;">
                <div style="background-color: {color}; height: 100%; width: {percent}%; border-radius: 6px; box-shadow: 0 0 8px {color}44;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

def sort_vintage(v):
    if not v or v == "NV": return 9999
    try: return int(v)
    except: return 0

def view_summary():
    st.markdown('# :material/pie_chart: Intelligence Dashboard', unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["Tasting History", "Cellar Inventory"])
    with t1:
        render_tasting_summary()
        
    with t2:
        render_cellar_summary()

def render_tasting_summary():
    session = get_session()
    total_notes = session.query(TastingNote).count()
    unique_wines = session.query(func.count(func.distinct(Wine.id))).join(Bottle).join(TastingNote).scalar()
    #avg_rating = session.query(func.avg(TastingNote.rating)).scalar() or 0
    
    # Calculate Michelin Stats
    # 1. Unique Places Visited (Tastings or Visits) that have stars
    star_places = session.query(Place).filter(Place.michelin_stars > 0).all()
    
    # Places from Tasting Notes
    tasting_place_ids = {r[0] for r in session.query(TastingNote.place_id).distinct()}
    # Places from Visits
    visit_place_ids = {r[0] for r in session.query(RestaurantVisit.place_id).distinct()}
    
    all_visited_ids = tasting_place_ids.union(visit_place_ids)
    
    # Sum stars for unique visited places
    unique_michelin_stars = 0
    for p in star_places:
        if p.id in all_visited_ids:
            unique_michelin_stars += p.michelin_stars
            
    # 2. Total Cumulative Stars (Sum of stars for every visit day)
    # Get distinct (date, place_id) from tastings
    tasting_visits = session.query(TastingNote.date, TastingNote.place_id).distinct().all()
    # Get distinct (date, place_id) from visits
    manual_visits = session.query(RestaurantVisit.date, RestaurantVisit.place_id).distinct().all()
    
    # Combine into a set of (date, place_id) to deduplicate same-day overlapping
    all_visits_set = set(tasting_visits).union(set(manual_visits))
    
    total_cumulative_stars = 0
    # Create map for fast lookup
    place_stars_map = {p.id: p.michelin_stars for p in star_places}
    
    for date, place_id in all_visits_set:
        stars = place_stars_map.get(place_id, 0)
        total_cumulative_stars += stars

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Tasting Notes", total_notes)
    m2.metric("Unique Wines", unique_wines)
    m3.metric("Unique Michelin Stars", unique_michelin_stars, help="Sum of stars of unique restaurants visited")
    m4.metric("Total Stars Experience", total_cumulative_stars, help="Sum of stars accumulated over all visits")
    session.close()
    st.divider()

    query = """
        SELECT w.type as "Color", r.name as "Region", p.name as "Producer", p.id as "pid",
               a.name as "Appellation", a.id as "aid", w.vintage as "Vintage", t.rating as "Rating"
        FROM tasting_notes t
        JOIN cellar b ON t.bottle_id = b.id
        JOIN wines w ON b.wine_id = w.id
        JOIN producers p ON w.producer_id = p.id
        LEFT JOIN regions r ON w.region_id = r.id
        LEFT JOIN appellations a ON w.appellation_id = a.id
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        st.info("No tasting notes found.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Distribution by Color")
        counts = df["Color"].value_counts().reset_index()
        counts.columns = ["Color", "Count"] # Explicitly rename
        
        # Prepare color scale
        domain = [k for k in TYPE_COLORS.keys()]
        range_ = [TYPE_COLORS[k][0] for k in TYPE_COLORS.keys()]
        
        chart = alt.Chart(counts).mark_bar().encode(
            x=alt.X('Color', sort='-y'),
            y='Count',
            color=alt.Color('Color', scale=alt.Scale(domain=domain, range=range_), legend=None),
            tooltip=['Color', 'Count']
        )
        st.altair_chart(chart, use_container_width=True)
        
        region_colors = get_region_colors_map()
        
        st.write("")
        st.subheader("Top 10 Domaines")
        # Color by Region. Group by Producer + Region
        top_prods = df.groupby(["Producer", "pid", "Region"]).size().reset_index(name="Count").sort_values("Count", ascending=False).head(10)
        
        for _, row in top_prods.iterrows():
            color = region_colors.get(row["Region"], "#7b68ee")
            label = row["Producer"]
            pid_int = int(row["pid"]) if pd.notnull(row["pid"]) else 0
            if pid_int:
                 label = f'<a href="/?page=Producer+Detail&id={pid_int}" target="_self" style="text-decoration:none; color:inherit;">{row["Producer"]}</a>'
            
            render_colored_bar(label, row["Count"], df.shape[0], color)
        
        st.write("")
        st.subheader("Top 10 Appellations")
        # st.dataframe(df["Appellation"].value_counts().head(10).reset_index(name="Notes"), hide_index=True, width="stretch")
        top_apps = df.groupby(["Appellation", "aid", "Region"]).size().reset_index(name="Count").sort_values("Count", ascending=False).head(10)
        
        for _, row in top_apps.iterrows():
            color = region_colors.get(row["Region"], "#7b68ee")
            label = row["Appellation"]
            # Add Link
            aid_int = int(row["aid"]) if pd.notnull(row["aid"]) else 0
            if aid_int:
                 # Use HTML a tag for render_colored_bar compatibility
                 label = f'<a href="/?page=Appellation+Detail&id={aid_int}" target="_self" style="text-decoration:none; color:inherit;">{row["Appellation"]}</a>'
            
            render_colored_bar(label, row["Count"], df.shape[0], color)

    with c2:
        st.subheader("Distribution by Region")
        counts = df["Region"].value_counts().reset_index()
        counts.columns = ["Region", "count"]
        total = counts["count"].sum()
        for _, row in counts.iterrows():
            render_colored_bar(row["Region"], row["count"], total, region_colors.get(row["Region"], "#7b68ee"))

    st.write("")
    st.subheader("Vintage Distribution")
    vintages = sorted(df["Vintage"].unique().tolist(), key=sort_vintage)
    v_counts = df["Vintage"].value_counts().reindex(vintages).reset_index(name="Count")
    st.bar_chart(v_counts.set_index("Vintage"))

def render_cellar_summary():
    session = get_session()
    total_bottles = session.query(func.sum(Bottle.qty)).filter(Bottle.qty > 0).scalar() or 0
    total_value = session.query(func.sum(Bottle.qty * Bottle.price)).filter(Bottle.qty > 0).scalar() or 0
    unique_wines = session.query(func.count(func.distinct(Wine.id))).join(Bottle).filter(Bottle.qty > 0).scalar() or 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Bottles", total_bottles)
    m2.metric("Unique Wines", unique_wines)
    m3.metric("Estimated Value", f"${total_value:,.0f}")
    session.close()
    st.divider()

    query = """
        SELECT w.type as "Color", r.name as "Region", p.name as "Producer", p.id as "pid",
               a.name as "Appellation", a.id as "aid", w.vintage as "Vintage", b.qty as "Qty", b.price as "Price"
        FROM cellar b
        JOIN wines w ON b.wine_id = w.id
        JOIN producers p ON w.producer_id = p.id
        LEFT JOIN regions r ON w.region_id = r.id
        LEFT JOIN appellations a ON w.appellation_id = a.id
        WHERE b.qty > 0
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        st.info("No bottles found in cellar.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Quantity by Color")
        counts = df.groupby("Color")["Qty"].sum().reset_index()
        
        # Prepare color scale
        domain = [k for k in TYPE_COLORS.keys()]
        range_ = [TYPE_COLORS[k][0] for k in TYPE_COLORS.keys()]
        
        chart = alt.Chart(counts).mark_bar().encode(
            x=alt.X('Color', sort='-y'),
            y='Qty',
            color=alt.Color('Color', scale=alt.Scale(domain=domain, range=range_), legend=None),
            tooltip=['Color', 'Qty']
        )
        st.altair_chart(chart, use_container_width=True)
        
        region_colors = get_region_colors_map()
        
        st.write("")
        st.subheader("Top 10 Domaines (Inventory)")
        # st.dataframe(df.groupby("Producer")["Qty"].sum().sort_values(ascending=False).head(10).reset_index(name="Bottles"), hide_index=True, width="stretch")
        top_prods = df.groupby(["Producer", "pid", "Region"])["Qty"].sum().reset_index(name="Qty").sort_values("Qty", ascending=False).head(10)
        total_btls = df["Qty"].sum()
        
        for _, row in top_prods.iterrows():
            color = region_colors.get(row["Region"], "#7b68ee")
            label = row["Producer"]
            pid_int = int(row["pid"]) if pd.notnull(row["pid"]) else 0
            if pid_int:
                 label = f'<a href="/?page=Producer+Detail&id={pid_int}" target="_self" style="text-decoration:none; color:inherit;">{row["Producer"]}</a>'
            
            render_colored_bar(label, int(row["Qty"]), total_btls, color, suffix=" btls")


    with c2:
        st.subheader("Quantity by Region")
        counts = df.groupby("Region")["Qty"].sum().sort_values(ascending=False).reset_index()
        total = counts["Qty"].sum()
        for _, row in counts.iterrows():
            render_colored_bar(row["Region"], int(row["Qty"]), total, region_colors.get(row["Region"], "#7b68ee"), suffix=" btls")

    st.write("")
    st.subheader("Vintage Distribution (Inventory)")
    vintages = sorted(df["Vintage"].unique().tolist(), key=sort_vintage)
    v_counts = df.groupby("Vintage")["Qty"].sum().reindex(vintages).reset_index(name="Bottles")
    st.bar_chart(v_counts.set_index("Vintage"))
