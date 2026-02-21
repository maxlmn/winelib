import streamlit as st
import pandas as pd
from shared import get_session, engine, EXCHANGE_RATES
from ui_utils import apply_colors, render_table, navigate_to
from shared import Bottle

def view_cellar():
    st.markdown('# :material/warehouse: Cellar', unsafe_allow_html=True)
    
    session = get_session()
    
    # Stats
    bottles_in_stock = session.query(Bottle).filter(Bottle.qty > 0).all()
    total_qty = sum(b.qty for b in bottles_in_stock)
    total_val = sum(b.qty * b.price * EXCHANGE_RATES.get(b.currency, 1.0) for b in bottles_in_stock)
    unique_lines = len(bottles_in_stock)
    
    # Custom CSS handled by shared component
        
    query = """
        SELECT 
            b.location as "Location",
            b.qty as "Qty",
            w.type as "Color",
            r.name as "Region",
            p.name as "Domaine",
            w.cuvee as "Cuvee",
            a.name as "Appellation",
            v.name as "Varietal",
            w.vintage as "Vintage",
            w.disgorgement_date as "Disgorgement",
            b.bottle_size as "Format",
            b.price as "raw_price",
            b.currency as "Currency",
            w.rp_score as "RP",
            b.purchase_date as "DatePurchased",
            p.id as "pid", w.id as "wid", b.id as "bid", a.id as "aid"
        FROM cellar b
        JOIN wines w ON b.wine_id = w.id
        JOIN producers p ON w.producer_id = p.id
        LEFT JOIN regions r ON w.region_id = r.id
        LEFT JOIN appellations a ON w.appellation_id = a.id
        LEFT JOIN varietals v ON w.varietal_id = v.id
        WHERE b.qty > 0
        ORDER BY r.name, p.name, w.vintage DESC
    """
    df = pd.read_sql(query, engine)
    session.close()
    
    if not df.empty:
        # --- Aggregation / Summary Table ---
        def get_loc_group(loc):
            if str(loc).startswith("H"): return "Home"
            if str(loc).startswith("WB"): return "WineBanc"
            return str(loc)
        
        df['Price(sgd)'] = df.apply(lambda r: r['raw_price'] * EXCHANGE_RATES.get(r['Currency'], 1.0), axis=1)
        df['Vintage'] = df.apply(lambda x: f"{x['Vintage']} - {x['Disgorgement']}" if (x['Vintage'] == "NV" and pd.notnull(x['Disgorgement']) and x['Disgorgement']) else x['Vintage'], axis=1)
        df['LocGroup'] = df['Location'].apply(get_loc_group)
        df['Total(sgd)'] = df['Qty'] * df['Price(sgd)']
        
        # Singapore Value Calculation (Excl. Paris, Octavian, Chemaze, Beaune)
        # Normalize check to simple substring or exact match? User said "Paris, Octavian, Chemaze, Beaune"
        # We will assume case-insensitive substring match for safety? Or exact? 
        # Existing code uses startswith. Let's use flexible string check.
        excluded_keywords = ["Paris", "Chemaze", "Beaune", "Octavian"]
        
        def is_singapore(loc):
            loc_s = str(loc)
            for k in excluded_keywords:
                if k in loc_s: return False
            return True
            
        singapore_df = df[df['Location'].apply(is_singapore)]
        singapore_val = singapore_df['Total(sgd)'].sum()

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            
            with c1:
                if st.button("Add Bottle", type="primary", use_container_width=True): navigate_to("Add Bottle")

            c2.caption("Total Bottles")
            c2.write(f"**{int(total_qty)}**")

            c3.caption("Est. Value (SGD)")
            c3.write(f"**${total_val:,.0f}**")

            c4.caption("Est. SG Value (SGD)")
            c4.write(f"**${singapore_val:,.0f}**")

        # --- Detailed Inventory ---
        with st.container(border=True):
            f1, f2, f3, f4, f5 = st.columns(5)
            sel_color = f1.multiselect("Color", sorted(df["Color"].unique()))
            sel_region = f2.multiselect("Region", sorted(df["Region"].unique()))
            sel_prod = f3.multiselect("Producer", sorted(df["Domaine"].unique()))
            sel_loc_group = f4.multiselect("Location Group", sorted(df["LocGroup"].unique()))
            sel_loc = f5.multiselect("Location", sorted(df["Location"].unique()))
        
        filtered_df = df.copy()
        if sel_color: filtered_df = filtered_df[filtered_df["Color"].isin(sel_color)]
        if sel_region: filtered_df = filtered_df[filtered_df["Region"].isin(sel_region)]
        if sel_prod: filtered_df = filtered_df[filtered_df["Domaine"].isin(sel_prod)]
        if sel_loc_group: filtered_df = filtered_df[filtered_df["LocGroup"].isin(sel_loc_group)]
        if sel_loc: filtered_df = filtered_df[filtered_df["Location"].isin(sel_loc)]
        
        if not filtered_df.empty:
            tab_cards, tab_list = st.tabs(["Cards", "List"])
            
            with tab_list:
                filtered_df = filtered_df.copy() # Avoid SettingWithCopy
                filtered_df['Domaine_Link'] = filtered_df.apply(lambda x: f"/?page=Producer+Detail&id={x['pid']}&label={x['Domaine'].replace(' ', '+')}", axis=1)
                filtered_df['Cuvee_Link'] = filtered_df.apply(lambda x: f"/?page=Wine+Detail&id={x['wid']}&label={x['Cuvee'].replace(' ', '+') if pd.notnull(x['Cuvee']) and x['Cuvee'].strip() else '-'}", axis=1)
                filtered_df['Qty_Link'] = filtered_df.apply(lambda x: f"/?page=Bottle+Detail&id={x['bid']}&label={str(x['Qty'])}", axis=1)
                filtered_df['Appellation_Link'] = filtered_df.apply(lambda x: f"/?page=Appellation+Detail&id={int(x['aid'])}&label={x['Appellation'].replace(' ', '+')}" if pd.notnull(x['aid']) else x['Appellation'], axis=1)
                
                # Drop original columns being replaced by links
                display_df = filtered_df.drop(columns=["Qty", "Appellation"], errors="ignore")
                # Rename Link columns for display
                display_df = display_df.rename(columns={"Qty_Link": "Qty", "Appellation_Link": "Appellation"})
                
                cols = ["Qty", "Format", "Color", "Region", "Domaine_Link", "Cuvee_Link", "Appellation", "Varietal", "Vintage", "Location", "Price(sgd)", "RP", "DatePurchased"]
                
                styler = apply_colors(display_df[cols + ["Domaine"]])
                
                render_table(
                    styler,
                    config={
                        "Qty": st.column_config.LinkColumn("Qty", display_text=r"label=(.*?)(?:&|$)"),
                        "Domaine_Link": st.column_config.LinkColumn("Domaine", display_text=r"label=(.*?)(?:&|$)"),
                        "Cuvee_Link": st.column_config.LinkColumn("Cuvee", display_text=r"label=(.*?)(?:&|$)"),
                        "Appellation": st.column_config.LinkColumn("Appellation", display_text=r"label=(.*?)(?:&|$)"),
                        "DatePurchased": st.column_config.DateColumn("DatePurchased", format="YYYY-MM-DD"),
                        "Price(sgd)": st.column_config.NumberColumn("Price(sgd)", format="%.1f")
                    },
                    cols=cols
                )

            with tab_cards:
                from views.components import render_cellar_cards
                render_cellar_cards(filtered_df)
        else:
            st.info("No wines match the selected filter.") 
    else:
        st.info("Cellar is empty.")
