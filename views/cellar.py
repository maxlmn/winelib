import re
import streamlit as st
import pandas as pd
import altair as alt
from shared import get_session, engine, EXCHANGE_RATES
from ui_utils import apply_colors, render_table, navigate_to, df_to_markdown
from shared import Bottle

SHELF_COLS = 8
SHELF_GROUPS = ["Home", "WineBanc", "Offsite"]
METRICS = {"Bottles": ("Bottles", ",.0f"), "Value (SGD)": ("Value", ",.0f")}


def _loc_sort_key(loc):
    # Natural sort so H2 < H10, then named bins (WBB, WBCC...) after numbered ones
    m = re.match(r"([A-Za-z]+?)(\d+)$", loc)
    return (m.group(1), 0, int(m.group(2)), "") if m else (loc[:2], 1, 0, loc)


def _shelf_group(loc):
    if loc.startswith("H"): return "Home"
    if loc.startswith("WB"): return "WineBanc"
    return "Offsite"


def _select_location(loc):
    # on_click callbacks run before the rerun, so they may write to the filter widgets' state
    current = st.session_state.get("cellar_sel_loc", [])
    st.session_state["cellar_sel_loc"] = [] if current == [loc] else [loc]
    st.session_state["cellar_sel_loc_group"] = []


def _shade(share):
    # Light rose -> deep wine; sqrt spreads out the many small bins
    lo, hi = (247, 232, 239), (122, 15, 58)
    t = share ** 0.5
    return "#%02x%02x%02x" % tuple(round(a + (b - a) * t) for a, b in zip(lo, hi))


def render_shelf_map(all_locations, data, selected_locs, metric):
    """One clickable tile per stocked location, grouped Home / WineBanc / Offsite. Every location is always
    drawn so the map stays physically stable; bins with nothing matching the current filters are greyed out."""
    agg = data.groupby("Location").agg(Bottles=("Qty", "sum"), Value=("TotalMarket(sgd)", "sum"))
    tiles = pd.DataFrame({"Location": sorted(all_locations, key=_loc_sort_key)})
    tiles = tiles.join(agg, on="Location").fillna({"Bottles": 0, "Value": 0})
    tiles["Group"] = tiles["Location"].map(_shelf_group)
    field, _ = METRICS[metric]
    # Shade within each group: Octavian alone would otherwise wash out every home shelf
    tiles["Peak"] = tiles.groupby("Group")[field].transform("max").replace(0, 1)

    css = []
    for _, t in tiles.iterrows():
        key = "shelf_" + re.sub(r"\W", "_", t["Location"])
        share = t[field] / t["Peak"]
        bg = _shade(share) if t["Bottles"] else "rgba(128,128,128,0.12)"
        fg = ("white" if share > 0.35 else "#3a0a1e") if t["Bottles"] else "inherit"
        ring = "0 0 0 3px #d4af37" if t["Location"] in selected_locs else "none"
        # !important: Streamlit's own hover/focus styles would otherwise repaint the tile after a click
        css.append(f".st-key-{key} button {{background:{bg} !important; color:{fg} !important; box-shadow:{ring} !important;"
                   f" border:1px solid rgba(128,128,128,0.25) !important; min-height:64px; width:100%;}}"
                   f".st-key-{key} button p {{color:{fg} !important;}}")
    st.markdown(f"<style>{''.join(css)}</style>", unsafe_allow_html=True)

    for group in SHELF_GROUPS:
        g = tiles[tiles["Group"] == group]
        if g.empty: continue
        st.markdown(f"**{group}** · {int(g['Bottles'].sum())} btl · ${g['Value'].sum():,.0f}")
        records = g.to_dict("records")
        for i in range(0, len(records), SHELF_COLS):
            cols = st.columns(SHELF_COLS)
            for col, t in zip(cols, records[i:i + SHELF_COLS]):
                stats = f"{int(t['Bottles'])} btl · ${t['Value'] / 1000:,.1f}k" if t["Bottles"] else "—"
                col.button(
                    f"**{t['Location']}**  \n{stats}",
                    key="shelf_" + re.sub(r"\W", "_", t["Location"]),
                    on_click=_select_location, args=(t["Location"],),
                    help=f"{t['Location']}: {int(t['Bottles'])} bottles · ${t['Value']:,.0f} SGD",
                    use_container_width=True,
                )


def render_vintage_heatmap(data, metric):
    h = data.assign(
        VintageBase=data["Vintage"].fillna("NV").astype(str).str.split(" - ").str[0],
        Region=data["Region"].fillna("Unknown"),
    )
    grid = h.groupby(["Region", "VintageBase"], as_index=False).agg(
        Bottles=("Qty", "sum"), Value=("TotalMarket(sgd)", "sum")
    )
    field, fmt = METRICS[metric]
    vintages = sorted(grid["VintageBase"].unique(), key=lambda v: (not v.isdigit(), int(v) if v.isdigit() else 0, v))
    regions = grid.groupby("Region")[field].sum().sort_values(ascending=False).index.tolist()
    grid["Share"] = grid[field] / (grid[field].max() or 1)
    grid["Label"] = grid.apply(lambda r: f"{int(r['Bottles'])}" if field == "Bottles" else f"{r['Value'] / 1000:,.0f}k", axis=1)

    base = alt.Chart(grid).encode(
        x=alt.X("VintageBase:O", sort=vintages, title="Vintage", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("Region:N", sort=regions, title=None),
    )
    rect = base.mark_rect(cornerRadius=3).encode(
        color=alt.Color(f"{field}:Q", scale=alt.Scale(scheme="purplered"), legend=alt.Legend(title=metric, format=fmt)),
        tooltip=[
            alt.Tooltip("Region:N"),
            alt.Tooltip("VintageBase:N", title="Vintage"),
            alt.Tooltip("Bottles:Q", format=",.0f"),
            alt.Tooltip("Value:Q", title="Value (SGD)", format=",.0f"),
        ],
    )
    text = base.mark_text(fontSize=10).encode(
        text="Label:N",
        color=alt.condition(alt.datum.Share > 0.55, alt.value("white"), alt.value("#3a0a1e")),
    )
    st.altair_chart(alt.layer(rect, text).properties(height=alt.Step(30)), use_container_width=True)


def view_cellar():
    st.markdown('# :material/warehouse: Cellar', unsafe_allow_html=True)
    
    session = get_session()
    
    # Stats
    bottles_in_stock = session.query(Bottle).filter(Bottle.qty > 0).all()
    total_qty = sum(b.qty for b in bottles_in_stock)
    total_cost = sum(b.qty * (b.price or 0) * EXCHANGE_RATES.get(b.currency, 1.0) for b in bottles_in_stock)
    total_market_val = sum(b.qty * (b.last_price if b.last_price else (b.price or 0)) * EXCHANGE_RATES.get(b.currency, 1.0) for b in bottles_in_stock)
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
            b.last_price as "MarketPrice",
            w.lwin as "LWIN",
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
        
        df['Price(sgd)'] = df.apply(lambda r: (r['raw_price'] or 0) * EXCHANGE_RATES.get(r['Currency'], 1.0), axis=1)
        
        def get_market_price_sgd(r):
            price = r['MarketPrice'] if pd.notnull(r['MarketPrice']) and r['MarketPrice'] > 0 else (r['raw_price'] or 0)
            return price * EXCHANGE_RATES.get(r['Currency'], 1.0)
            
        df['MarketPrice(sgd)'] = df.apply(get_market_price_sgd, axis=1)
        
        df['Vintage'] = df.apply(lambda x: f"{x['Vintage']} - {x['Disgorgement']}" if (x['Vintage'] == "NV" and pd.notnull(x['Disgorgement']) and x['Disgorgement']) else x['Vintage'], axis=1)
        df['LocGroup'] = df['Location'].apply(get_loc_group)
        df['TotalCost(sgd)'] = df['Qty'] * df['Price(sgd)']
        df['TotalMarket(sgd)'] = df['Qty'] * df['MarketPrice(sgd)']
        
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
        singapore_cost = singapore_df['TotalCost(sgd)'].sum()
        singapore_market = singapore_df['TotalMarket(sgd)'].sum()

        # --- Distribution by Location (Pie Charts) ---
        # Shared color scale so the same location has the same color in both donuts
        loc_domain = sorted(df['LocGroup'].unique().tolist())
        loc_scale = alt.Scale(domain=loc_domain, scheme='tableau10')

        def render_location_pie(data, value_col, title, value_format):
            grouped = data.groupby('LocGroup')[value_col].sum().reset_index()
            grouped = grouped[grouped[value_col] > 0].sort_values(value_col, ascending=False)
            total = grouped[value_col].sum()
            grouped['Pct'] = grouped[value_col] / total * 100 if total else 0
            st.caption(title)
            chart = alt.Chart(grouped).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(f'{value_col}:Q', stack=True),
                color=alt.Color('LocGroup:N', title='Location', scale=loc_scale),
                order=alt.Order(f'{value_col}:Q', sort='descending'),
                tooltip=[
                    alt.Tooltip('LocGroup:N', title='Location'),
                    alt.Tooltip(f'{value_col}:Q', title=title, format=value_format),
                    alt.Tooltip('Pct:Q', title='%', format='.1f'),
                ]
            )
            st.altair_chart(chart, use_container_width=True)

        with st.container(border=True):
            pc1, pc2 = st.columns(2)
            with pc1:
                render_location_pie(df, 'TotalMarket(sgd)', "Market Value by Location (SGD)", ",.0f")
            with pc2:
                render_location_pie(df, 'Qty', "Bottles by Location", ",.0f")

        with st.container(border=True):
            c1, c2, c3, c3b, c4, c5 = st.columns([0.7, 0.6, 0.9, 0.9, 1.1, 1.1])
            
            with c1:
                if st.button("Add Bottle", type="primary", use_container_width=True): navigate_to("Add Bottle")

            c2.caption("Total Bottles")
            c2.write(f"**{int(total_qty)}**")

            c3.caption("Cost (SGD)")
            c3.write(f"**${total_cost:,.0f}**")

            c3b.caption("SG Cost (SGD)")
            c3b.write(f"**${singapore_cost:,.0f}**")

            c4.caption("Market Value (SGD)")
            pct = ((total_market_val - total_cost) / total_cost * 100) if total_cost else 0
            color = "green" if pct >= 0 else "red"
            arrow = "▲" if pct >= 0 else "▼"
            c4.write(f"**${total_market_val:,.0f}** :{color}[{arrow} {abs(pct):.1f}%]")

            c5.caption("SG Market Value")
            sg_pct = ((singapore_market - singapore_cost) / singapore_cost * 100) if singapore_cost else 0
            sg_color = "green" if sg_pct >= 0 else "red"
            sg_arrow = "▲" if sg_pct >= 0 else "▼"
            c5.write(f"**${singapore_market:,.0f}** :{sg_color}[{sg_arrow} {abs(sg_pct):.1f}%]")

        # --- Detailed Inventory ---
        with st.container(border=True):
            search_query = st.text_input("Search", placeholder="Search by Producer, Cuvée, or Appellation...", label_visibility="collapsed")
            f1, f2, f3, f4, f5, f6 = st.columns(6)
            sel_color = f1.multiselect("Color", sorted(df["Color"].unique()))
            sel_region = f2.multiselect("Region", sorted(df["Region"].unique()))
            sel_prod = f3.multiselect("Producer", sorted(df["Domaine"].unique()))
            sel_vintage = f4.multiselect("Vintage", sorted([v for v in df["Vintage"].unique() if pd.notna(v)]))
            sel_loc_group = f5.multiselect("Location Group", sorted(df["LocGroup"].unique()), key="cellar_sel_loc_group")
            sel_loc = f6.multiselect("Location", sorted(df["Location"].unique()), key="cellar_sel_loc")

        # wine_df: every filter except location — the shelf map uses it so all bins stay on the map
        wine_df = df.copy()
        if search_query:
            q = search_query.lower()
            wine_df = wine_df[
                wine_df["Domaine"].str.lower().str.contains(q, na=False) |
                wine_df["Cuvee"].str.lower().str.contains(q, na=False) |
                wine_df["Appellation"].str.lower().str.contains(q, na=False)
            ]
        if sel_color: wine_df = wine_df[wine_df["Color"].isin(sel_color)]
        if sel_region: wine_df = wine_df[wine_df["Region"].isin(sel_region)]
        if sel_prod: wine_df = wine_df[wine_df["Domaine"].isin(sel_prod)]
        if sel_vintage: wine_df = wine_df[wine_df["Vintage"].isin(sel_vintage)]

        filtered_df = wine_df
        if sel_loc_group: filtered_df = filtered_df[filtered_df["LocGroup"].isin(sel_loc_group)]
        if sel_loc: filtered_df = filtered_df[filtered_df["Location"].isin(sel_loc)]
        
        if not filtered_df.empty:
            export_cols = ["Qty", "Format", "Color", "Region", "Domaine", "Cuvee", "Appellation", "Varietal", "Vintage", "Location", "Price(sgd)", "MarketPrice(sgd)", "RP"]
            export_md = (
                f"# Cellar export — {pd.Timestamp.now():%Y-%m-%d}\n\n"
                f"{int(filtered_df['Qty'].sum())} bottles · cost ${filtered_df['TotalCost(sgd)'].sum():,.0f} · "
                f"market ${filtered_df['TotalMarket(sgd)'].sum():,.0f} (SGD)\n\n"
                + df_to_markdown(filtered_df, export_cols) + "\n"
            )
            _, col_export = st.columns([0.8, 0.2])
            col_export.download_button(
                "Export to Markdown", export_md, file_name=f"cellar_{pd.Timestamp.now():%Y%m%d}.md",
                mime="text/markdown", icon=":material/download:", use_container_width=True
            )

            tab_cards, tab_list, tab_shelves, tab_vintages, tab_price = st.tabs(["Cards", "List", "Shelf Map", "Vintages", "Price Variations"])

            with tab_shelves:
                shelf_metric = st.radio("Shade by", list(METRICS), horizontal=True, key="cellar_shelf_metric")
                st.caption("Click a bin to filter the page to it, click it again to clear. "
                           "Darker = more, compared within each group · grey bins hold nothing matching the other filters.")
                render_shelf_map(df["Location"].unique(), wine_df, sel_loc, shelf_metric)

            with tab_vintages:
                heat_metric = st.radio("Shade by", list(METRICS), horizontal=True, key="cellar_heat_metric")
                render_vintage_heatmap(filtered_df, heat_metric)

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
            
            with tab_price:
                # Filter bottles that have both purchase price and market price
                price_df = filtered_df[
                    (filtered_df['raw_price'].notnull()) & (filtered_df['raw_price'] > 0) &
                    (filtered_df['MarketPrice'].notnull()) & (filtered_df['MarketPrice'] > 0)
                ].copy()
                
                if not price_df.empty:
                    price_df['PctChange'] = ((price_df['MarketPrice'] - price_df['raw_price']) / price_df['raw_price']) * 100
                    
                    def render_price_card(row):
                        pct = row['PctChange']
                        color = "green" if pct >= 0 else "red"
                        arrow = "▲" if pct >= 0 else "▼"
                        name = f"{row['Domaine']} - {row['Cuvee']}" if row['Cuvee'] else row['Domaine']
                        vintage = row['Vintage'] or ""
                        lwin_link = ""
                        if row.get('LWIN'):
                            lwin_link = f" [🔍](https://winelabs.ai/quote/{row['LWIN']})"
                        
                        st.markdown(
                            f"**[{name}](/?page=Bottle+Detail&id={row['bid']})** {vintage}  \n"
                            f"{row['raw_price']:.0f} {row['Currency']} → {row['MarketPrice']:.0f}  "
                            f":{color}[{arrow} {abs(pct):.0f}%]{lwin_link}"
                        )
                    
                    gains = price_df[price_df['PctChange'] >= 0].sort_values('PctChange', ascending=False).head(20)
                    losses = price_df[price_df['PctChange'] < 0].sort_values('PctChange', ascending=True).head(20)
                    
                    col_gain, col_loss = st.columns(2)
                    with col_gain:
                        st.subheader(":green[▲ Highest Gains]")
                        if not gains.empty:
                            for _, row in gains.iterrows():
                                with st.container(border=True):
                                    render_price_card(row)
                        else:
                            st.info("No gains found.")
                    
                    with col_loss:
                        st.subheader(":red[▼ Biggest Losses]")
                        if not losses.empty:
                            for _, row in losses.iterrows():
                                with st.container(border=True):
                                    render_price_card(row)
                        else:
                            st.info("No losses found.")
                else:
                    st.info("No bottles with both purchase price and market price available.")
        else:
            st.info("No wines match the selected filter.") 
    else:
        st.info("Cellar is empty.")
