import streamlit as st
import pandas as pd
from shared import (
    Producer, Wine, Bottle, Place, TastingNote, 
    Appellation, RestaurantVisit, Vineyard, get_region_name,
    get_session
)
from ui_utils import navigate_to, display_region_line
from views.components import render_tasting_cards, render_cellar_cards
from geo_utils import (
    resolve_app_geometry, 
    resolve_vine_geometry,
    get_geometry_bounds,
    create_place_map,
    create_appellation_map,
    create_vineyard_map,
    create_wine_combined_map
)
from shapely.geometry import mapping as shape_mapping

def view_producer_detail(pid):
    #if st.button("Back"): navigate_to("Producers")
    session = get_session()
    p = session.get(Producer, pid)
    if p:           
        with st.container(border=True):
            m1,m2 = st.columns(2)
            with m1:
                st.title(p.name)
                r_name = get_region_name(p)
                loc_parts = [x for x in [r_name, p.subregion, p.village] if x and str(x).strip()]
                m1.caption(" > ".join(loc_parts))
                if p.winemaker: m1.write(f"**Winemaker:** {p.winemaker}")
                if p.owner: m1.write(f"**Owner:** {p.owner}")
                if p.lists:
                    l_str = str(p.lists).replace("[","").replace("]","").replace("'","").replace('"',"")
                    items = [x.strip() for x in l_str.split(',') if x.strip()]
                    if items:
                        st.caption("Lists")
                        with st.container(border=True):
                            for item in items:
                                st.write(item)
                
                if p.description:
                    st.caption("Description")
                    st.write(p.description)
                    
                if p.notes:
                    st.caption("Notes")
                    st.info(p.notes)

            with m2:
                # Stats
                n_bottles = 0
                active_bst = session.query(Bottle).join(Wine).filter(Wine.producer_id == pid, Bottle.qty > 0).all()
                if active_bst: n_bottles = sum(b.qty for b in active_bst)
                
                n_tastings = session.query(TastingNote).join(Bottle).join(Wine).filter(Wine.producer_id == pid).count()
                
                s1, s2 = st.columns(2)
                s1.metric("Bottles in Cellar", n_bottles)
                s2.metric("Wines Tasted", n_tastings)
                
                
                if p.website: st.markdown(f"**[Website]({p.website})**")
                if p.profile_url: st.markdown(f"**[Profile]({p.profile_url})**")
                
                if p.importers: st.write(f"**Importers:** {p.importers}")
                if st.button("Edit Producer"): navigate_to("Edit Producer", {"id": pid})
                
        
        display_region_line(get_region_name(p))
        
        # TABS
        tab_cellar, tab_history = st.tabs(["Cellar", "History"])
        
        with tab_cellar:
            active_bottles = session.query(Bottle).join(Wine).filter(Wine.producer_id == pid, Bottle.qty > 0).all()
            if active_bottles:
                # Prepare data for Cellar Cards
                data = []
                from shared import EXCHANGE_RATES
                
                def get_loc_group(loc):
                    if str(loc).startswith("H"): return "Home"
                    if str(loc).startswith("WB"): return "WineBanc"
                    return str(loc)
                    
                for b in active_bottles:
                    w = b.wine
                    price_sgd = (b.price or 0) * EXCHANGE_RATES.get(b.currency, 1.0)
                    data.append({
                        "Qty": b.qty,
                        "Color": w.type,
                        "Region": get_region_name(w),
                        "Domaine": w.producer.name,
                        "Cuvee": w.cuvee,
                        "Appellation": w.appellation.name if w.appellation else "",
                        "Vintage": w.vintage,
                        "wid": w.id,
                        "bid": b.id,
                        "Location": b.location,
                        "LocGroup": get_loc_group(b.location),
                        "Total(sgd)": b.qty * price_sgd
                    })
                
                inv_df = pd.DataFrame(data)
                render_cellar_cards(inv_df)
            else:
                st.info("No bottles from this producer currently in stock.")

        with tab_history:
            all_tastings = session.query(TastingNote).join(Bottle).join(Wine).filter(Wine.producer_id == pid).order_by(TastingNote.date.desc()).all()
            
            if all_tastings:
                # Group by Date + Place for Card Format
                grouped = {}
                for t in all_tastings:
                    d = t.date
                    pid_val = t.place.id if t.place else 0
                    key = (d, pid_val)
                    if key not in grouped:
                        grouped[key] = {
                            "type": "tasting_group",
                            "date": d,
                            "place_name": t.place.name if t.place else (t.location or "Unknown"),
                            "plid": pid_val if pid_val else None,
                            "wines": []
                        }
                    
                    w = t.bottle.wine
                    grouped[key]["wines"].append({
                        "Domaine": w.producer.name,
                        "Cuvee": w.cuvee,
                        "Appellation": w.appellation.name if w.appellation else "",
                        "Vintage": f"{w.vintage} - {w.disgorgement_date}" if (w.vintage == "NV" and w.disgorgement_date) else w.vintage,
                        "wid": w.id,
                        "tid": t.id,
                        "Notes": t.notes,
                        "Region": get_region_name(w),
                        "Color": w.type,
                        "City": t.place.city if t.place else "",
                        "Stars": t.place.michelin_stars if t.place else 0
                    })
                
                # Convert to list and sort
                events = list(grouped.values())
                events.sort(key=lambda x: x['date'], reverse=True)
                
                final_events = []
                for event in events:
                    # URL
                    if event.get('plid'):
                        event['url'] = f"/?page=Place+Detail&id={event['plid']}"
                        
                    # Meta
                    city = ""
                    stars = 0
                    if event["wines"]:
                        first = event["wines"][0]
                        city = first.get("City", "")
                        stars = first.get("Stars", 0) or 0
                    
                    meta_parts = []
                    if city: meta_parts.append(str(city))
                    if stars: meta_parts.append("⭐" * int(stars))
                    event['meta'] = " • ".join(meta_parts) if meta_parts else "&nbsp;"
                    
                    final_events.append(event)
                    
                render_tasting_cards(final_events)

            else:
                st.info("No personal tasting notes recorded for this producer yet.")
    
    session.close()

def render_wine_content(session, wid):
    w = session.query(Wine).join(Producer).filter(Wine.id==wid).first()
    if w:
        m1,m2 = st.columns(2)
        with m1:
            st.title(f"{w.producer.name} {w.cuvee} {w.vintage}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Edit Wine", key=f"edit_w_{wid}"): navigate_to("Edit Wine", {"id": wid})
            with c2:
                if st.button("Go to Producer", key=f"go_p_{wid}"): navigate_to("Producer Detail", {"id": w.producer_id})
            st.write(f"**Region:** {get_region_name(w)}")
            st.write(f"**Type:** {w.type}")
            if w.type == "Bubbles" and w.disgorgement_date:
                st.write(f"**Disgorged:** {w.disgorgement_date}")
            if w.appellation:
                st.markdown(f"**Appellation:** [{w.appellation.name}](/?page=Appellation+Detail&id={w.appellation.id})")
            else:
                st.write(f"**Appellation:** N/A")
            
            if w.vineyard:
                v = w.vineyard
                parts = [p for p in [v.sub_region, v.village, v.name] if p and str(p).strip()]
                v_label = " - ".join(parts) if parts else v.name
                st.markdown(f"**Vineyard:** [{v_label}](/?page=Vineyard+Detail&id={v.id})")

            st.write(f"**Varietal:** {w.varietal.name if w.varietal else 'N/A'}")
            if w.blend: st.write(f"**Blend:** {w.blend}")
        with m2:
            # Map Rendering Logic
            from streamlit_folium import st_folium

            # Resolve geometries
            app_geo = None
            vine_geo = None
            
            if w.appellation:
                geom = resolve_app_geometry(w.appellation)
                if geom:
                    app_geo = shape_mapping(geom) if not isinstance(geom, dict) else geom

            if w.vineyard:
                geom = resolve_vine_geometry(vineyard=w.vineyard, region_name=get_region_name(w), 
                                            appellation_name=w.appellation.name if w.appellation else None)
                if geom:
                    vine_geo = shape_mapping(geom) if not isinstance(geom, dict) else geom
            
            # Create combined map
            m, label_str = create_wine_combined_map(w, app_geo, vine_geo)
            
            if m:
                if label_str:
                    st.caption(label_str)
                st_folium(m, height=400, width="100%", returned_objects=[])
            elif app_geo or vine_geo:
                st.error("Unified Map Error")



        
        display_region_line(get_region_name(w))

        if w.rp_score and w.rp_score != "-":
            m1,m2 = st.columns(2)
            with m1:
                st.write(f"**RP Score:** {w.rp_score}")
                if w.rp_url: st.link_button(f"View RP Page", w.rp_url)
            with m2:
                st.markdown("**RP Notes:**")
                st.write(w.rp_note if w.rp_note else "No critic notes available.")
        
        
        # Calculate all related IDs (same Producer, Cuvee, Appellation) to aggregate history/inventory
        all_ids_query = session.query(Wine.id).filter(
            Wine.producer_id == w.producer_id,
            Wine.cuvee == w.cuvee,
            Wine.appellation_id == w.appellation_id,
            Wine.varietal_id == w.varietal_id
        )
        all_ids = [r[0] for r in all_ids_query.all()]
        
        # Summary of Vintages
        # 1. In Cellar
        vintages_in_cellar = session.query(Wine.vintage, Wine.disgorgement_date).join(Bottle).filter(
            Wine.id.in_(all_ids),
            Bottle.qty > 0
        ).distinct().all()
        
        def format_v_list(v_rows):
            res = []
            for v, d in v_rows:
                if not v: continue
                if v == "NV" and d:
                    res.append(f"{v} - {d}")
                else:
                    res.append(v)
            return sorted(set(res), reverse=True)

        v_cellar = format_v_list(vintages_in_cellar)

        # 2. Drank (from Tasting Notes)
        vintages_drank = session.query(Wine.vintage, Wine.disgorgement_date).join(Bottle).join(TastingNote).filter(
            Wine.id.in_(all_ids)
        ).distinct().all()
        v_drank = format_v_list(vintages_drank)
        
        if v_cellar or v_drank:
            c1, c2 = st.columns(2)
            with c1:
                if v_cellar:
                    with st.container(border=True):
                        st.caption("Vintages in Cellar")
                        st.write(", ".join(v_cellar))
            with c2:
                if v_drank:
                    with st.container(border=True):
                        st.caption("Vintages Tasted")
                        st.write(", ".join(v_drank))
            #st.divider()

        
        # --- INVENTORY SECTION ---
        # TABS
        tab_cellar, tab_history, tab_cellar_all, tab_history_all = st.tabs(["Cellar", "History", "Cellar (All Vintages)", "History (All Vintages)"])
        
        # 1. CELLAR (Current Vintage)
        with tab_cellar:
            active_bottles = [b for b in w.inventory if b.qty > 0]
            if active_bottles:
                inv_data = []
                from shared import EXCHANGE_RATES
                
                def get_loc_group(loc):
                    if str(loc).startswith("H"): return "Home"
                    if str(loc).startswith("WB"): return "WineBanc"
                    return str(loc)
                
                for b in active_bottles:
                    price_sgd = (b.price or 0) * EXCHANGE_RATES.get(b.currency, 1.0)
                    inv_data.append({
                        "Qty": b.qty,
                        "Color": w.type,
                        "Region": get_region_name(w),
                        "Domaine": w.producer.name,
                        "Cuvee": w.cuvee,
                        "Appellation": w.appellation.name if w.appellation else "",
                        "Vintage": w.vintage,
                        "wid": w.id,
                        "bid": b.id,
                        "Location": b.location,
                        "LocGroup": get_loc_group(b.location),
                        "Total(sgd)": b.qty * price_sgd
                    })
                
                inv_df = pd.DataFrame(inv_data)
                render_cellar_cards(inv_df)
            else:
                st.info("No bottles of this vintage currently in stock.")

        # 2. HISTORY (Current Vintage)
        with tab_history:
            all_tastings = session.query(TastingNote).join(Bottle).filter(Bottle.wine_id == wid).order_by(TastingNote.date.desc()).all()
            
            if all_tastings:
                # Group by Date + Place
                grouped = {}
                for t in all_tastings:
                    d = t.date
                    pid_val = t.place.id if t.place else 0
                    key = (d, pid_val)
                    if key not in grouped:
                        grouped[key] = {
                            "type": "tasting_group",
                            "date": d,
                            "place_name": t.place.name if t.place else (t.location or "Unknown"),
                            "plid": pid_val if pid_val else None,
                            "wines": []
                        }
                    
                    grouped[key]["wines"].append({
                        "Domaine": w.producer.name,
                        "Cuvee": w.cuvee,
                        "Appellation": w.appellation.name if w.appellation else "",
                        "Vintage": f"{w.vintage} - {w.disgorgement_date}" if (w.vintage == "NV" and w.disgorgement_date) else w.vintage,
                        "wid": w.id,
                        "tid": t.id,
                        "Notes": t.notes,
                        "Region": get_region_name(w),
                        "Color": w.type,
                        "City": t.place.city if t.place else "",
                        "Stars": t.place.michelin_stars if t.place else 0
                    })
                
                events = list(grouped.values())
                events.sort(key=lambda x: x['date'], reverse=True)
                
                final_events = []
                for event in events:
                    # URL
                    if event.get('plid'):
                        event['url'] = f"/?page=Place+Detail&id={event['plid']}"
                        
                    # Meta
                    city = ""
                    stars = 0
                    if event["wines"]:
                        # All wines in this group share place info
                        first = event["wines"][0]
                        city = first.get("City", "")
                        stars = first.get("Stars", 0) or 0
                    
                    meta_parts = []
                    if city: meta_parts.append(str(city))
                    if stars: meta_parts.append("⭐" * int(stars))
                    event['meta'] = " • ".join(meta_parts) if meta_parts else "&nbsp;"
                    
                    final_events.append(event)
                    
                render_tasting_cards(final_events, key_suffix="history_curr")
            else:
                st.info("No personal tasting notes recorded for this vintage.")

        # 3. CELLAR (All Vintages)
        with tab_cellar_all:
            active_bottles_all = session.query(Bottle).filter(Bottle.wine_id.in_(all_ids), Bottle.qty > 0).all()
            if active_bottles_all:
                inv_data = []
                from shared import EXCHANGE_RATES
                
                def get_loc_group(loc):
                    if str(loc).startswith("H"): return "Home"
                    if str(loc).startswith("WB"): return "WineBanc"
                    return str(loc)
                
                for b in active_bottles_all:
                    w_sub = b.wine # Need to get the wine object for each bottle since IDs differ
                    price_sgd = (b.price or 0) * EXCHANGE_RATES.get(b.currency, 1.0)
                    inv_data.append({
                        "Qty": b.qty,
                        "Color": w_sub.type,
                        "Region": get_region_name(w_sub),
                        "Domaine": w_sub.producer.name,
                        "Cuvee": w_sub.cuvee,
                        "Appellation": w_sub.appellation.name if w_sub.appellation else "",
                        "Vintage": f"{w_sub.vintage} - {w_sub.disgorgement_date}" if (w_sub.vintage == "NV" and w_sub.disgorgement_date) else w_sub.vintage,
                        "wid": w_sub.id,
                        "bid": b.id,
                        "Location": b.location,
                        "LocGroup": get_loc_group(b.location),
                        "Total(sgd)": b.qty * price_sgd
                    })
                
                inv_df = pd.DataFrame(inv_data)
                render_cellar_cards(inv_df)
            else:
                st.info("No bottles of any vintage in stock.")

        # 4. HISTORY (All Vintages)
        with tab_history_all:
            all_tastings_all = session.query(TastingNote).join(Bottle).filter(Bottle.wine_id.in_(all_ids)).order_by(TastingNote.date.desc()).all()
            
            if all_tastings_all:
                # Group by Date + Place
                grouped = {}
                for t in all_tastings_all:
                    d = t.date
                    pid_val = t.place.id if t.place else 0
                    key = (d, pid_val)
                    if key not in grouped:
                        grouped[key] = {
                            "type": "tasting_group",
                            "date": d,
                            "place_name": t.place.name if t.place else (t.location or "Unknown"),
                            "plid": pid_val if pid_val else None,
                            "wines": []
                        }
                    
                    w_sub = t.bottle.wine
                    grouped[key]["wines"].append({
                        "Domaine": w_sub.producer.name,
                        "Cuvee": w_sub.cuvee,
                        "Appellation": w_sub.appellation.name if w_sub.appellation else "",
                        "Vintage": f"{w_sub.vintage} - {w_sub.disgorgement_date}" if (w_sub.vintage == "NV" and w_sub.disgorgement_date) else w_sub.vintage,
                        "wid": w_sub.id,
                        "tid": t.id,
                        "Notes": t.notes,
                        "Region": get_region_name(w_sub),
                        "Color": w_sub.type,
                        "City": t.place.city if t.place else "",
                        "Stars": t.place.michelin_stars if t.place else 0
                    })
                
                events = list(grouped.values())
                events.sort(key=lambda x: x['date'], reverse=True)
                
                final_events = []
                for event in events:
                    # URL
                    if event.get('plid'):
                        event['url'] = f"/?page=Place+Detail&id={event['plid']}"
                        
                    # Meta
                    city = ""
                    stars = 0
                    if event["wines"]:
                        first = event["wines"][0]
                        city = first.get("City", "")
                        stars = first.get("Stars", 0) or 0
                    
                    meta_parts = []
                    if city: meta_parts.append(str(city))
                    if stars: meta_parts.append("⭐" * int(stars))
                    event['meta'] = " • ".join(meta_parts) if meta_parts else "&nbsp;"
                    
                    final_events.append(event)
                    
                render_tasting_cards(final_events, key_suffix="history_all")
            else:
                st.info("No personal tasting notes recorded for any vintage.")

def view_wine_detail(wid):
    #if st.button("Back"): navigate_to("Wines")
    session = get_session()
    render_wine_content(session, wid)
    session.close()

def view_bottle_detail(bid):
    #if st.button("Back"): navigate_to("Cellar")
    session = get_session()
    b = session.query(Bottle).join(Wine).join(Producer).filter(Bottle.id==bid).first()
    if b:
        with st.container(border=True):
            m1, m2 = st.columns(2)
            with m1:
                st.subheader(f"{b.qty}x{b.bottle_size} @ {b.location}")
                c1, c2 = st.columns(2)
                if c1.button("Edit Bottle"): navigate_to("Edit Bottle", {"id": bid})
                if c2.button("Drink"): navigate_to("Add Tasting", {"bottle_id": bid})
            with m2:
                st.write(f"**Price:** {b.price} {b.currency}" if b.price else "**Price:** N/A")
                st.write(f"**Vendor:** {b.vendor}")
                st.write(f"**Provenance:** {b.provenance}")
                st.write(f"**Purchase Date:** {b.purchase_date}")
        render_wine_content(session, b.wine_id)
    session.close()

def view_place_detail(plid):
    # if st.button("Back"): navigate_to("Places")
    session = get_session()
    p = session.get(Place, plid)
    p = session.get(Place, plid)
    if p:
        c1, c2 = st.columns([3, 1])
        with c1: st.title(p.name)
        with c2: 
            if st.button("Edit Place"): navigate_to("Edit Place", {"id": plid})
        
        # Calculate Stats
        notes = session.query(TastingNote).filter_by(place_id=plid).all()
        visits = session.query(RestaurantVisit).filter_by(place_id=plid).all()
        
        nb_tastings = len(notes)
        
        # Unique dates logic
        tasting_dates = set([n.date for n in notes if n.date])
        visit_dates = set([v.date for v in visits if v.date])
        all_dates = tasting_dates.union(visit_dates)
        nb_visits = len(all_dates)

        with st.container(border=True):
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.caption("Total Visits")
            mc1.write(f"**{nb_visits}**")
            
            mc2.caption("Wines Tasted")
            mc2.write(f"**{nb_tastings}**")
            
            mc3.caption("Michelin Stars")
            mc3.write(f"**{p.michelin_stars if p.michelin_stars else 0}**")

        # Calculate Total Cost
        from shared import EXCHANGE_RATES
        total_cost_sgd = 0.0
        for n in notes:
            if n.bottle and n.bottle.price:
                rate = EXCHANGE_RATES.get(n.bottle.currency, 1.0)
                total_cost_sgd += (n.bottle.price * rate)
        
        mc4.caption("Total Wine Value (SGD)")
        mc4.write(f"**${total_cost_sgd:,.2f}**")

        with st.container(border=True):
            mc1, mc2, mc3 = st.columns(3)
            mc1.caption("City")
            mc1.write(f"**{p.city}**")
            mc2.caption("Country")
            mc2.write(f"**{p.country}**")
            mc3.caption("Type")
            mc3.write(f"**{p.type}**")
        
        if p.notes:
            with st.container(border=True):
                st.caption("Notes")
                st.write(p.notes)
        
        # MAP DISPLAY
        if p.lat and p.lng:
            from streamlit_folium import st_folium
            from geo_utils import create_place_map
            
            m = create_place_map(p)
            if m:
                st_folium(m, height=300, width="100%", returned_objects=[])
            else:
                st.error("Error loading map")
        
        
        st.divider()
        st.subheader("History")
        
        # We already fetched notes and visits earlier for stats, but let's assume we need to process them for display
        # notes = session.query(TastingNote).filter_by(place_id=plid).order_by(TastingNote.date.desc()).all()
        # visits = session.query(RestaurantVisit).filter_by(place_id=plid).order_by(RestaurantVisit.date.desc()).all()
        
        events = []
        
        # 1. Visits
        for v in visits:
            events.append({
                "type": "visit",
                "date": v.date,
                "place_name": p.name, # Current place
                "city": p.city,
                "stars": p.michelin_stars,
                "notes": v.notes,
                "id": v.id
            })
            
        # 2. Tastings (grouped by date)
        grouped_tastings = {}
        for n in notes:
            d = n.date
            if d not in grouped_tastings:
                grouped_tastings[d] = {
                    "type": "tasting_group",
                    "date": d,
                    "place_name": p.name,
                    "plid": plid,
                    "wines": []
                }
            
            w = n.bottle.wine
            grouped_tastings[d]["wines"].append({
                "Domaine": w.producer.name,
                "Cuvee": w.cuvee,
                "Appellation": w.appellation.name if w.appellation else "",
                "Vintage": w.vintage,
                "wid": w.id,
                "tid": n.id,
                "Notes": n.notes,
                "Region": get_region_name(w),
                "Color": w.type,
                "City": p.city,
                "Stars": p.michelin_stars
            })
            
        events.extend(list(grouped_tastings.values()))
        events.sort(key=lambda x: x['date'], reverse=True)
        
        if events:
            # Prep for render
            final_events = []
            for event in events:
                # Meta
                city = event.get('city') or (event['wines'][0].get('City') if event.get('wines') else "")
                stars = event.get('stars') or (event['wines'][0].get('Stars') if event.get('wines') else 0)
                
                meta_parts = []
                if city: meta_parts.append(str(city))
                if stars: meta_parts.append("⭐" * int(stars))
                event['meta'] = " • ".join(meta_parts) if meta_parts else "&nbsp;"
                
                # No need for URL since we are ON the place detail page? 
                # Or render it anyway for consistency? Code below links to '#' or current page.
                event['url'] = "#"
                event['place_name'] = p.name  # Override just in case
                
                final_events.append(event)
                
            render_tasting_cards(final_events)
        else:
            st.info("No history recorded.")
    session.close()

def view_appellation_detail(aid):
    #if st.button("Back"): navigate_to("Map")
    
    session = get_session()
    # Handle potentially malformed IDs (e.g. "1284.0")
    try:
        aid = int(float(aid))
    except (ValueError, TypeError):
        aid = 0

    a = session.get(Appellation, aid)
    
    if a:
        st.title(a.name)
        m1, m2 = st.columns([1, 1])
        with m1:
            st.write(f"**Region:** {get_region_name(a) if get_region_name(a) else 'Unknown'}")
            if a.subregion:
                st.write(f"**Sub-region:** {a.subregion}")
            st.write(f"**Type:** {a.type}")
            
            # PDO Metadata
            if hasattr(a, 'category') and a.category:
                st.write(f"**Category:** {a.category}")
            
            if hasattr(a, 'pdo_id') and a.pdo_id:
                reg_text = f" (Reg: {a.registration_date})" if getattr(a, 'registration_date', None) else ""
                st.write(f"**PDO ID:** {a.pdo_id}{reg_text}")

            if hasattr(a, 'max_yield_hl') and (a.max_yield_hl or a.max_yield_kg):
                 yields = []
                 if a.max_yield_hl: yields.append(f"{a.max_yield_hl} hl/ha")
                 if a.max_yield_kg: yields.append(f"{a.max_yield_kg} kg/ha")
                 st.write(f"**Max Yield:** {', '.join(yields)}")

            if a.location_link:
                st.markdown(f"[View Official Info]({a.location_link})")
            
            if hasattr(a, 'varieties_text') and a.varieties_text:
                 # Count items roughly
                 count = len(a.varieties_text.split(','))
                 with st.expander(f"Authorized Varieties ({count})", expanded=True):
                     st.write(a.varieties_text)

            if a.details:
                with st.expander("Details"):
                    st.write(a.details)
            
        with m2:
            # Small map if geojson exists or INAO data
            
            # Resolve Geometry
            geom = resolve_app_geometry(a)
            geo_data = shape_mapping(geom) if geom and not isinstance(geom, dict) else geom

            if geo_data:
                from streamlit_folium import st_folium
                from geo_utils import create_appellation_map
                
                color = a.region_obj.color if a.region_obj and a.region_obj.color else "#c27ba0"
                m = create_appellation_map(a, geo_data, color)
                
                if m:
                    st_folium(m, height=250, width="100%", returned_objects=[])
                else:
                    st.error("Map Error")


            if hasattr(a, 'municipalities') and a.municipalities:
                with st.expander("Municipalities", expanded=True):
                    st.write(a.municipalities)


        #st.divider()

        display_region_line(get_region_name(a))
        
        # TABS
        tab1, tab2 = st.tabs(["History", "Cellar"])

        
        with tab1:
            # Tastings for wines from this appellation
            tastings = session.query(TastingNote)\
                .join(Bottle)\
                .join(Wine)\
                .filter(Wine.appellation_id == aid)\
                .order_by(TastingNote.date.desc())\
                .all()
                
            if tastings:
                # Group
                grouped = {}
                for t in tastings:
                    d = t.date
                    pid = t.place.id if t.place else 0
                    key = (d, pid)
                    if key not in grouped:
                        place_name = t.place.name if t.place else (t.location or "Unknown")
                        grouped[key] = {
                            "type": "tasting_group",
                            "date": d,
                            "place_name": place_name,
                            "plid": pid if pid else None,
                            "wines": []
                        }
                    
                    w = t.bottle.wine
                    grouped[key]["wines"].append({
                        "Domaine": w.producer.name,
                        "Cuvee": w.cuvee,
                        "Appellation": w.appellation.name if w.appellation else "",
                        "Vintage": w.vintage,
                        "wid": w.id,
                        "Notes": t.notes,
                        "Region": get_region_name(w),
                        "Color": w.type,
                        "City": t.place.city if t.place else "",
                        "Stars": t.place.michelin_stars if t.place else 0
                    })
                
                events = list(grouped.values())
                events.sort(key=lambda x: x['date'], reverse=True)
                
                # Prep
                final_events = []
                for event in events:
                    if event.get('plid'):
                        event['url'] = f"/?page=Place+Detail&id={event['plid']}"
                    
                    city = ""
                    stars = 0
                    if event["wines"]:
                        first = event["wines"][0]
                        city = first.get("City", "")
                        stars = first.get("Stars", 0) or 0
                    
                    meta_parts = []
                    if city: meta_parts.append(str(city))
                    if stars: meta_parts.append("⭐" * int(stars))
                    event['meta'] = " • ".join(meta_parts) if meta_parts else "&nbsp;"
                    
                    final_events.append(event)
                    
                render_tasting_cards(final_events)
            else:
                st.info("No tastings for this appellation.")

        with tab2:
            # Inventory for this appellation
            bottles = session.query(Bottle)\
                .join(Wine)\
                .filter(Wine.appellation_id == aid, Bottle.qty > 0)\
                .all()
                
            if bottles:
                data = []
                from shared import EXCHANGE_RATES
                def get_loc_group(loc):
                    if str(loc).startswith("H"): return "Home"
                    if str(loc).startswith("WB"): return "WineBanc"
                    return str(loc)

                for b in bottles:
                    w = b.wine
                    price_sgd = (b.price or 0) * EXCHANGE_RATES.get(b.currency, 1.0)
                    data.append({
                        "Qty": b.qty,
                        "Color": w.type,
                        "Region": get_region_name(w),
                        "Domaine": w.producer.name,
                        "Cuvee": w.cuvee,
                        "Appellation": w.appellation.name if w.appellation else "",
                        "Vintage": w.vintage,
                        "wid": w.id,
                        "bid": b.id,
                        "Location": b.location,
                        "LocGroup": get_loc_group(b.location),
                        "Total(sgd)": b.qty * price_sgd
                    })
                
                inv_df = pd.DataFrame(data)
                render_cellar_cards(inv_df)
            else:
                st.info("No bottles in cellar from this appellation.")
    
    session.close()

def view_tasting_detail(tid):
    session = get_session()
    n = session.get(TastingNote, tid)
    if n:
        # TASTING DETAILS
        with st.container(border=True):
            st.subheader("Tasting Note")
            m1, m2 = st.columns([3, 1])
            with m1:
                st.write(f"**Date:** {n.date}")
                if n.place:
                    st.write(f"**Place:** {n.place.name}")
                    if n.place.city: st.caption(f"{n.place.city}, {n.place.country}")
                elif n.location:
                    st.write(f"**Location:** {n.location}")
                
                if n.notes:
                    st.write(f"**Notes:** {n.notes}")
                else:
                    st.caption("No notes")
            with m2:
                if n.rating: st.metric("Rating", n.rating)
                if n.glasses: st.metric("Glasses", n.glasses)
                
                if st.button("Edit Tasting", key=f"edit_tn_{tid}"): 
                    navigate_to("Edit Tasting", {"id": tid})

        # BOTTLE DETAILS
        b = n.bottle
        if b:
            st.markdown("---")
            st.subheader("Bottle Details")
            with st.container(border=True):
                m1, m2 = st.columns(2)
                with m1:
                    st.write(f"**Size:** {b.bottle_size}")
                    st.write(f"**Location:** {b.location}")
                    st.write(f"**Vendor:** {b.vendor}")
                    st.write(f"**Provenance:** {b.provenance}")
                with m2:
                    st.write(f"**Price:** {b.price} {b.currency}")
                    st.write(f"**Purchase Date:** {b.purchase_date}")
                    if st.button("Edit Bottle", key=f"edit_b_{b.id}"): 
                         navigate_to("Edit Bottle", {"id": b.id})

            # WINE DETAILS
            st.markdown("---")
            st.subheader("Wine Details")
            render_wine_content(session, b.wine_id)

    else:
        st.error("Tasting Note not found.")
    session.close()

def view_vineyard_detail(vid):
    session = get_session()
    # Handle potentially malformed IDs
    try:
        vid = int(float(vid))
    except (ValueError, TypeError):
        vid = 0

    v = session.get(Vineyard, vid)
    
    if v:
        st.title(v.name)
        m1, m2 = st.columns([1, 1])
        with m1:
            r_name = get_region_name(v)
            loc_parts = [x for x in [r_name, v.sub_region, v.village] if x and str(x).strip()]
            st.write(f"**Location:** {' > '.join(loc_parts)}")
            if v.vineyard_id:
                st.write(f"**External ID:** {v.vineyard_id}")
            
        with m2:
            # Map Rendering
            from streamlit_folium import st_folium
            import json

            geo_data = None
            if v.vineyard_id:
                sample_wine = session.query(Wine).filter(Wine.vineyard_id == vid).first()
                app_name = sample_wine.appellation.name if sample_wine and sample_wine.appellation else None
                geom = resolve_vine_geometry(v, get_region_name(v), app_name)
                geo_data = shape_mapping(geom) if geom and not isinstance(geom, dict) else geom
            
            if not geo_data and v.geojson:
                try: geo_data = json.loads(v.geojson)
                except: pass

            if geo_data:
                m = create_vineyard_map(v, geo_data)
                if m:
                    st_folium(m, height=300, width="100%", key=f"v_map_{vid}", returned_objects=[])
                else:
                    st.error("Map Error")
            else:
                st.info("No geographical data available for this vineyard.")
        
        display_region_line(get_region_name(v))

        # Tabs for Cellar and History
        tab_cellar, tab_history = st.tabs(["Cellar", "History"])
        
        with tab_cellar:
            active_bottles = session.query(Bottle).join(Wine).filter(Wine.vineyard_id == vid, Bottle.qty > 0).all()
            if active_bottles:
                inv_data = []
                from shared import EXCHANGE_RATES
                for b in active_bottles:
                    w = b.wine
                    price_sgd = (b.price or 0) * EXCHANGE_RATES.get(b.currency, 1.0)
                    inv_data.append({
                        "Qty": b.qty,
                        "Color": w.type,
                        "Region": get_region_name(w),
                        "Domaine": w.producer.name,
                        "Cuvee": w.cuvee,
                        "Appellation": w.appellation.name if w.appellation else "",
                        "Vintage": w.vintage,
                        "wid": w.id,
                        "bid": b.id,
                        "Location": b.location,
                        "Total(sgd)": b.qty * price_sgd
                    })
                render_cellar_cards(pd.DataFrame(inv_data))
            else:
                st.info("No bottles from this vineyard currently in cellar.")

        with tab_history:
            all_tastings = session.query(TastingNote).join(Bottle).join(Wine).filter(Wine.vineyard_id == vid).order_by(TastingNote.date.desc()).all()
            if all_tastings:
                grouped = {}
                for t in all_tastings:
                    d = t.date
                    key = (d, t.place_id if t.place else 0)
                    if key not in grouped:
                        grouped[key] = {
                            "type": "tasting_group",
                            "date": d,
                            "place_name": t.place.name if t.place else (t.location or "Unknown"),
                            "plid": t.place_id,
                            "wines": []
                        }
                    w = t.bottle.wine
                    grouped[key]["wines"].append({
                        "Domaine": w.producer.name,
                        "Cuvee": w.cuvee,
                        "Appellation": w.appellation.name if w.appellation else "",
                        "Vintage": w.vintage,
                        "wid": w.id,
                        "tid": t.id,
                        "Notes": t.notes,
                        "Region": get_region_name(w),
                        "Color": w.type,
                        "City": t.place.city if t.place else "",
                        "Stars": t.place.michelin_stars if t.place else 0
                    })
                events = list(grouped.values())
                events.sort(key=lambda x: x['date'], reverse=True)
                
                final_events = []
                for e in events:
                    if e.get('plid'):
                        e['url'] = f"/?page=Place+Detail&id={e['plid']}"
                    
                    # Meta
                    city = ""
                    stars = 0
                    if e["wines"]:
                        first = e["wines"][0]
                        city = first.get("City", "")
                        stars = first.get("Stars", 0) or 0
                    
                    meta_parts = []
                    if city: meta_parts.append(str(city))
                    if stars: meta_parts.append("⭐" * int(stars))
                    e['meta'] = " • ".join(meta_parts) if meta_parts else "&nbsp;"
                    
                    final_events.append(e)

                render_tasting_cards(final_events, key_suffix=f"v_hist_{vid}")
            else:
                st.info("No tasting history for this vineyard.")
    else:
        st.error("Vineyard not found.")
    session.close()
