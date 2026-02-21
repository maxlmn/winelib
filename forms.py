import streamlit as st
import time
from datetime import date
from shared import get_session, get_all_regions, get_region_name, TYPE_COLORS
from ui_utils import navigate_to
from shared import Producer, Wine, Bottle, TastingNote, Appellation, Varietal, Place, RestaurantVisit, Vineyard, Region
from constants import UI, BOTTLE_SIZES, CURRENCIES
from geo_utils import get_region_name


def _get_state(key, default=False):
    if key not in st.session_state: st.session_state[key] = default
    return st.session_state[key]

def _toggle_state(key):
    st.session_state[key] = not st.session_state[key]

def _render_wine_core_fields(session, defaults=None, include_producer=True, prefix="main", external_producer=None):
    # states arg is now ignored for toggling, as we use dropdowns.
    
    # 1. Producer
    sel_p = None
    new_prod_name = None
    new_prod_region = None
    
    # OUTPUT FLAGS
    is_new_p = False
    is_new_a = False
    is_new_v = False

    if include_producer:
        producers = session.query(Producer).order_by(Producer.name).all()
        p_names = [p.name for p in producers]
        
        # Logic to determine index
        p_idx = 0
        if defaults and defaults.get("producer") in p_names: 
            p_idx = p_names.index(defaults["producer"]) + 2 # +2 for Select + CreateNew
            
        p_options = [UI.SELECT.value, UI.CREATE_NEW.value] + sorted(p_names)
        sel_p_val = st.selectbox("Producer", p_options, index=p_idx, key=f"{prefix}_prod_sel")
        
        if sel_p_val == UI.CREATE_NEW:
            is_new_p = True
            sel_p = UI.CREATE_NEW
            c1, c2 = st.columns(2)
            new_prod_name = c1.text_input("New Producer Name", key=f"{prefix}_prod_new_name")
            
            all_regions = get_all_regions()
            reg_names = sorted([r.name for r in all_regions])
            new_prod_region = c2.selectbox("Producer Region", [UI.SELECT.value] + reg_names, key=f"{prefix}_prod_new_reg")
        else:
            sel_p = sel_p_val

    else:
        # Producer handled externally
        sel_p = external_producer or UI.EXTERNAL 


    c1, c2 = st.columns(2)
    # 2. Wine Details
    p_reg_name = ""
    if sel_p == UI.CREATE_NEW:
        p_reg_name = new_prod_region
    elif sel_p and sel_p not in [UI.SELECT, UI.EXTERNAL]:
        p_obj = session.query(Producer).filter_by(name=sel_p).first()
        if p_obj: p_reg_name = get_region_name(p_obj)
    
    cuv_val = defaults.get("cuvee", "") if defaults else ""
    new_wine_cuvee = c1.text_input("Cuvee/Name", value=cuv_val, key=f"{prefix}_cuvee")
    
    vin_val = defaults.get("vintage", "") if defaults else ""
    new_wine_vintage = c2.text_input("Vintage", value=vin_val, key=f"{prefix}_vintage")
    
    # Helper for Emojis
    def get_type_emoji(t):
        map = {
            "Red": "🔴", "White": "🟡", "Bubbles": "🍾", "Rose": "🌸", 
            "Sweet": "🍯", "Orange": "🟠", "Fortified": "🛡️"
        }
        return map.get(t, "🍷")

    sorted_types = sorted(TYPE_COLORS.keys())
    type_options = [f"{get_type_emoji(t)} {t}" for t in sorted_types]
    
    type_idx = 0
    if defaults and defaults.get("type") in sorted_types: 
        type_idx = sorted_types.index(defaults["type"])
        
    sel_type_str = c1.selectbox("Type", type_options, index=type_idx, key=f"{prefix}_type")
    new_wine_type = sel_type_str.split(" ", 1)[1] if " " in sel_type_str else sel_type_str
    
    # Disgorgement Date (Specific to Bubbles usually)
    new_wine_disgorge = ""
    if new_wine_type == "Bubbles":
         d_val = defaults.get("disgorgement_date") or "" if defaults else ""
         new_wine_disgorge = c2.text_input("Disgorgement Date", value=d_val, key=f"{prefix}_disgorge", help="For NV wines")
    
    all_regions = sorted(get_all_regions(), key=lambda r: r.name)
    
    # Defaults handling for region index
    reg_val = defaults.get("region") if defaults else None
    
    reg_opts = all_regions
    
    reg_idx = 0
    # 1. If we have a stored region name, try to find it
    if reg_val:
        for i, opt in enumerate(reg_opts):
            if opt.name == reg_val:
                reg_idx = i
                break
    # 2. Otherwise default to producer's region
    elif p_reg_name:
        for i, opt in enumerate(reg_opts):
            if opt.name == p_reg_name:
                reg_idx = i
                break

    def format_reg(opt):
        return opt.name if hasattr(opt, 'name') else str(opt)
        
    new_wine_region_val = c2.selectbox("Wine Region", reg_opts, index=reg_idx, key=f"{prefix}_region", format_func=format_reg)
    
    # 3. Appellation / Varietal / Vineyard
    c_av1, c_av2 = st.columns(2)
    
    # Appellation
    apps = session.query(Appellation).order_by(Appellation.name).all()
    a_names = [a.name for a in apps]
    a_options = [UI.SELECT.value, UI.CREATE_NEW.value] + a_names
    
    a_idx = 0
    if defaults and defaults.get("appellation") in a_names: 
        a_idx = a_names.index(defaults["appellation"]) + 2
    
    app_sel = c_av1.selectbox("Appellation", a_options, index=a_idx, key=f"{prefix}_app_sel")
    new_wine_app = None
    app_val = app_sel
    
    if app_sel == UI.CREATE_NEW:
        is_new_a = True
        new_wine_app = c_av1.text_input("New Appellation Name", key=f"{prefix}_app_new")
    
    # Check if we need to force rerun (if inside a form this won't help, but if outside it ensures update)
    # But wait, if inside form, st.rerun() works? No, callback doesn't run.
    # I must remove the form wrapper.
    pass # Placeholder comment
        
    # Varietal
    vars = session.query(Varietal).order_by(Varietal.name).all()
    v_names = [v.name for v in vars]
    v_options = [UI.SELECT.value, UI.CREATE_NEW.value] + v_names
    
    v_idx = 0
    if defaults and defaults.get("varietal") in v_names: 
        v_idx = v_names.index(defaults["varietal"]) + 2
        
    var_sel = c_av2.selectbox("Varietal", v_options, index=v_idx, key=f"{prefix}_var_sel")
    new_wine_var = None
    var_val = var_sel
    
    if var_sel == UI.CREATE_NEW:
        is_new_v = True
        new_wine_var = c_av2.text_input("New Varietal Name", key=f"{prefix}_var_new")

    # Vineyard
    # Resolve the intended region for vineyard filtering
    viny_region_obj = new_wine_region_val if isinstance(new_wine_region_val, Region) else None
    
    query = session.query(Vineyard)
    if viny_region_obj:
        query = query.filter(Vineyard.region_id == viny_region_obj.id)
    vinys = query.order_by(Vineyard.sub_region, Vineyard.village, Vineyard.name).all()
    
    def format_viny(v):
        parts = [p for p in [v.sub_region, v.village, v.name] if p and str(p).strip()]
        return " - ".join(parts) if parts else v.name

    viny_options = [UI.SELECT.value]
    viny_map = {} # Label -> ID
    for v in vinys:
        lbl = format_viny(v)
        viny_options.append(lbl)
        viny_map[lbl] = v.id

    v_idx = 0
    if defaults and defaults.get("vineyard"):
        # Find the label for the default vineyard name
        # We search by name here because defaults only has the name
        # but the selectbox will return the label which we map to ID.
        found = False
        for v in vinys:
            if v.name == defaults["vineyard"]:
                lbl = format_viny(v)
                if lbl in viny_options: 
                    v_idx = viny_options.index(lbl)
                    found = True
                    break
        if not found: v_idx = 0

    vineyard_lbl = st.selectbox("Vineyard (Optional)", viny_options, index=v_idx, key=f"{prefix}_vyd_sel")
    vineyard_id = viny_map.get(vineyard_lbl)
    
    new_wine_blend = st.text_input("Blend", value=defaults.get("blend", "") if defaults else "", key=f"{prefix}_blend")
    
    c_rp1, c_rp2 = st.columns(2)
    new_wine_rp_score = c_rp1.text_input("RP Score", value=str(defaults.get("rp_score", "")) if defaults else "", key=f"{prefix}_rps")
    new_wine_rp_url = c_rp2.text_input("RP URL", value=defaults.get("rp_url", "") if defaults else "", key=f"{prefix}_rpu")
    new_wine_rp_note = st.text_area("RP Note", value=defaults.get("rp_note", "") if defaults else "", key=f"{prefix}_rpn")
        
    c_dr1, c_dr2 = st.columns(2)
    new_wine_drink_start = c_dr1.number_input("Drink Window Start", value=defaults.get("drink_start", 0) if defaults else 0, key=f"{prefix}_ds")
    new_wine_drink_end = c_dr2.number_input("Drink Window End", value=defaults.get("drink_end", 0) if defaults else 0, key=f"{prefix}_de")
    
    return {
        "sel_p": sel_p,
        "new_prod_name": new_prod_name,
        "new_prod_region": new_prod_region,
        "cuvee": new_wine_cuvee,
        "vintage": new_wine_vintage,
        "disgorgement_date": new_wine_disgorge,
        "type": new_wine_type,
        "region_val": new_wine_region_val, # Region object or "Same as Producer"
        "appellation_val": app_val, # Selected value (name or "Create New")
        "new_app_name": new_wine_app,
        "varietal_val": var_val,
        "new_var_name": new_wine_var,
        "vineyard_id": vineyard_id,
        "blend": new_wine_blend,
        "rp_score": new_wine_rp_score,
        "rp_url": new_wine_rp_url,
        "rp_note": new_wine_rp_note,
        "drink_start": new_wine_drink_start,
        "drink_end": new_wine_drink_end,
        # Flags
        "new_p": is_new_p,
        "new_a": is_new_a,
        "new_v": is_new_v
    }

def _process_new_wine_form(session, data):
    pid = None
    # Producer
    # Check flag first, then value
    if data.get("new_p") or data.get("sel_p") == UI.CREATE_NEW:
        if not data.get("new_prod_name"): st.error("Producer Name Required"); st.stop()
        reg_obj = data["new_prod_region"] if isinstance(data.get("new_prod_region"), Region) else None
        prod = Producer(name=data["new_prod_name"], region_obj=reg_obj)
        session.add(prod); session.flush()
        pid = prod.id
    elif data.get("sel_p") and data["sel_p"] not in [UI.SELECT, UI.EXTERNAL]:
        # pid is the name if coming from _render_wine_core_fields? 
        # Actually sel_p is p_names result.
        existing_p = session.query(Producer).filter_by(name=data["sel_p"]).first()
        if existing_p: pid = existing_p.id
    
    # If producer logic is internal but no PID found
    if not pid and data.get("sel_p") != UI.EXTERNAL: st.error("Producer Required"); st.stop()
    
    aid = None
    sel_a = data.get("appellation_val")
    if data.get("new_a") or sel_a == UI.CREATE_NEW:
         if not data.get("new_app_name"): st.error("New Appellation Name Required"); st.stop()
         aname = data["new_app_name"]
         a = session.query(Appellation).filter_by(name=aname).first()
         if not a:
             # Logic to resolve region for the new Appellation
             w_region_val = data["region_val"]
             temp_reg_obj = w_region_val if isinstance(w_region_val, Region) else None

             # Re-fetch or merge to ensures it's in session
             if temp_reg_obj: temp_reg_obj = session.get(Region, temp_reg_obj.id)
             
             a = Appellation(name=aname, region_obj=temp_reg_obj)
             session.add(a); session.flush()
         aid = a.id
    elif sel_a and sel_a not in ["None", UI.SELECT]:
        a = session.query(Appellation).filter_by(name=sel_a).first()
        if a: aid = a.id
 
    vid = None
    sel_v = data.get("varietal_val")
    if data.get("new_v") or sel_v == UI.CREATE_NEW:
         if not data.get("new_var_name"): st.error("New Varietal Name Required"); st.stop()
         vname = data["new_var_name"]
         v = session.query(Varietal).filter_by(name=vname).first()
         if not v: v = Varietal(name=vname); session.add(v); session.flush()
         vid = v.id
    elif sel_v and sel_v not in ["None", UI.SELECT]:
         v = session.query(Varietal).filter_by(name=sel_v).first()
         if v: vid = v.id
            
    vineyard_id = data.get("vineyard_id")

    w_region_val = data["region_val"]
    reg_obj = session.get(Region, w_region_val.id) if isinstance(w_region_val, Region) else None

    nw = Wine(
        producer_id=pid, cuvee=data["cuvee"], vintage=data["vintage"], 
        type=data["type"], region_obj=reg_obj,
        appellation_id=aid, varietal_id=vid, vineyard_id=vineyard_id, 
        blend=data["blend"], rp_score=data["rp_score"], rp_note=data["rp_note"], 
        rp_url=data["rp_url"], drink_window_start=data["drink_start"], drink_window_end=data["drink_end"],
        disgorgement_date=data.get("disgorgement_date")
    )
    session.add(nw); session.flush()
    return nw.id

def form_producer(prod_id=None):
    st.markdown(f"### {'Edit' if prod_id else 'Add'} Producer")
    session = get_session()
    p = None
    if prod_id:
        p = session.get(Producer, prod_id)
        
    with st.form("producer_form"):
        name = st.text_input("Name", value=p.name if p else "")
        
        all_regions = sorted(get_all_regions(), key=lambda r: r.name)
        
        current_reg_name = get_region_name(p)
        reg_idx = 0
        if current_reg_name:
            for i, r in enumerate(all_regions):
                if r.name == current_reg_name:
                    reg_idx = i
                    break
        
        region_obj_sel = st.selectbox("Region", all_regions, index=reg_idx, format_func=lambda r: r.name)
        winemaker = st.text_input("Winemaker", value=p.winemaker if p else "")
        profile = st.text_input("Profile URL", value=p.profile_url if p else "")
        desc = st.text_area("Description", value=p.description if p else "")
        
        submitted = st.form_submit_button("Save Producer")
        if submitted:
            if not name: st.error("Name is required"); return
            reg_obj = session.get(Region, region_obj_sel.id) if region_obj_sel else None
            if p:
                p.name, p.region_obj = name, reg_obj
                p.winemaker, p.profile_url, p.description = winemaker, profile, desc
            else:
                session.add(Producer(name=name, region_obj=reg_obj, winemaker=winemaker, profile_url=profile, description=desc))
            session.commit()
            st.success("Producer saved!")
            time.sleep(0.5)
            navigate_to("Producers")
    session.close()

def form_wine(wine_id=None):
    st.markdown(f"### {'Edit' if wine_id else 'Add'} Wine")
    session = get_session()
    w = None
    if wine_id:
        w = session.get(Wine, wine_id)
    
    # Defaults dictionary for editing
    defaults = None
    if w:
        defaults = {
            "producer": w.producer.name if w.producer else None,
            "cuvee": w.cuvee,
            "vintage": w.vintage,
            "type": w.type,
            "region": get_region_name(w),
            "appellation": w.appellation.name if w.appellation else None,
            "varietal": w.varietal.name if w.varietal else None,
            "vineyard": w.vineyard.name if w.vineyard else None,
            "blend": w.blend,
            "rp_score": w.rp_score,
            "rp_note": w.rp_note,
            "rp_url": w.rp_url,
            "drink_start": w.drink_window_start,
            "rp_url": w.rp_url,
            "drink_start": w.drink_window_start,
            "drink_end": w.drink_window_end,
            "disgorgement_date": w.disgorgement_date
        }

    # Render Toggles (Outside Form)
    # states = _manage_wine_creation_state("main_wine") # REMOVED: Deprecated

    # Form - Removed st.form for real-time reactivity (Region -> Vineyard filtering)
    # with st.form("wine_form"):
    data = _render_wine_core_fields(session, defaults=defaults)
    
    submitted = st.button("Save Wine")
    if submitted:
        # Re-use the processing logic from _process_new_wine_form? 
        # Ideally yes, but that creates a NEW wine. Here we might be UPDATING.
        # Let's adapt the logic here.
        
        # 1. Producer
        pid = None
        # Check data for flags instead of states
        if data["new_p"]:
             if not data["new_prod_name"]: st.error("New producer name required"); return
             reg_obj = data["new_prod_region"] if isinstance(data.get("new_prod_region"), Region) else None
             if reg_obj: reg_obj = session.get(Region, reg_obj.id)
             new_p = Producer(name=data["new_prod_name"], region_obj=reg_obj)
             session.add(new_p); session.flush(); pid = new_p.id
        elif data["sel_p"] != "Select...":
             pid = session.query(Producer.id).filter_by(name=data["sel_p"]).scalar()
        else:
             st.error("Producer required"); return
        
        # 2. Appellation
        aid = None
        # Check data for flags
        if data["new_a"]:
            if not data["new_app_name"]: st.error("New appellation name required"); return
            new_a = Appellation(name=data["new_app_name"]); session.add(new_a); session.flush(); aid = new_a.id
        elif data["appellation_val"] and data["appellation_val"] != "Select...":
            aid = session.query(Appellation.id).filter_by(name=data["appellation_val"]).scalar()
        
        # 3. Varietal
        vid = None
        # Check data for flags
        if data["new_v"]:
            if not data["new_var_name"]: st.error("New varietal name required"); return
            new_v = Varietal(name=data["new_var_name"]); session.add(new_v); session.flush(); vid = new_v.id
        elif data["varietal_val"] and data["varietal_val"] != "Select...":
            vid = session.query(Varietal.id).filter_by(name=data["varietal_val"]).scalar()

        # 4. Vineyard
        viny_id = data.get("vineyard_id")

        # 5. Region Logic
        w_region_val = data["region_val"]
        reg_obj = session.get(Region, w_region_val.id) if isinstance(w_region_val, Region) else None

        # 6. Save or Update
        if w:
            w.producer_id, w.cuvee, w.vintage, w.type = pid, data["cuvee"], data["vintage"], data["type"]
            w.region_obj = reg_obj
            w.appellation_id, w.varietal_id, w.vineyard_id, w.blend, w.rp_score, w.rp_note, w.rp_url = aid, vid, viny_id, data["blend"], data["rp_score"], data["rp_note"], data["rp_url"]
            w.drink_window_start, w.drink_window_end = data["drink_start"], data["drink_end"]
            w.disgorgement_date = data.get("disgorgement_date", "")
            session.commit(); st.success("Wine Updated")
        else:
            nw = Wine(
                producer_id=pid, cuvee=data["cuvee"], vintage=data["vintage"], 
                type=data["type"], region_obj=reg_obj,
                appellation_id=aid, varietal_id=vid, vineyard_id=viny_id, 
                blend=data["blend"], rp_score=data["rp_score"], rp_note=data["rp_note"], 
                rp_url=data["rp_url"], drink_window_start=data["drink_start"], 
                drink_window_end=data["drink_end"],
                disgorgement_date=data.get("disgorgement_date", "")
            )
            session.add(nw); session.commit(); st.success("Wine Created")
        
        time.sleep(0.5)
        navigate_to("Wines")
    session.close()

def _component_wine_selector(session, prefix="main", default_wine_id=None):
    # Returns selector_state dict
    
    # 1. Producer
    producers = session.query(Producer).order_by(Producer.name).all()
    p_names = [p.name for p in producers]
    
    def_p_idx = 0
    w_def = None
    if default_wine_id:
        w_def = session.get(Wine, default_wine_id)
        if w_def and w_def.producer.name in p_names:
            def_p_idx = p_names.index(w_def.producer.name) + 2

    sel_p_str = st.selectbox("Producer", ["Select...", "➕ Create New..."] + p_names, index=def_p_idx, key=f"{prefix}_sel_p")
    
    selected_pid = None
    is_new_producer = (sel_p_str == "➕ Create New...")
    
    if not is_new_producer and sel_p_str != "Select...":
        p_map = {p.name: p.id for p in producers}
        selected_pid = p_map.get(sel_p_str)

    # 2. Wine (If Producer Selected)
    selected_wid = None
    is_new_wine = False
    defaults = None
    
    if is_new_producer:
        is_new_wine = True # Must create new wine for new producer
        
    elif selected_pid:
        wines = session.query(Wine).filter_by(producer_id=selected_pid).order_by(Wine.cuvee, Wine.vintage).all()
        
        # Build Options
        # Build Options
        options = [UI.SELECT.value, UI.CREATE_NEW_WINE.value]
        
        # Helper for Emojis
        def get_type_emoji(t):
            map = {
                "Red": "🔴", "White": "🟡", "Bubbles": "🍾", "Rose": "🌸", 
                "Sweet": "🍯", "Orange": "🟠", "Fortified": "🛡️"
            }
            return map.get(t, "🍷")

        
        # Helper: Create consistent label
        def make_label(type, cuvee, app="", var="", vintage=None, disgorge=None):
            emoji = get_type_emoji(type)
            parts = [f"{emoji} {cuvee}"]
            if vintage:
                v_str = f"({vintage})"
                if vintage == "NV" and disgorge:
                    v_str = f"({vintage} - {disgorge})"
                parts.append(v_str)
            
            details = [x for x in [app, var] if x]
            if details: parts.append("- " + ", ".join(details))
            return " ".join(parts)

        # Group wines for "New Vintage" functionality
        # Key: (Type, Cuvee, Appellation, Varietal)
        # Value: List of wines
        groups = {}
        for w in wines:
            key = (w.type, w.cuvee, 
                   w.appellation.name if w.appellation else "",
                   w.varietal.name if w.varietal else "")
            groups.setdefault(key, []).append(w)

        group_map = {} # New Vintage Label -> List of wines defaults
        w_map = {} # Label -> ID

        # Build options list
        sorted_keys = sorted(groups.keys(), key=lambda k: k) # Simple tuple sort works
        
        for k in sorted_keys:
            w_type, w_cuvee, w_app, w_var = k
            g_wines = groups[k]
             
            # 1. Existing Wines
            for w in g_wines:
                lbl = make_label(w.type, w.cuvee, w_app, w_var, w.vintage, w.disgorgement_date)
                options.append(lbl)
                w_map[lbl] = w.id
            
            # 2. "New Vintage" Option for this group
            group_lbl = make_label(w_type, w_cuvee, w_app, w_var)
            nv_lbl = f"{group_lbl}{UI.NEW_VINTAGE_SUFFIX.value}"
            options.append(nv_lbl)
            group_map[nv_lbl] = g_wines
            
        # Determine Default Index
        def_w_idx = 0
        if w_def and w_def.producer_id == selected_pid:
             lbl = make_label(
                 w_def.type, w_def.cuvee, 
                 w_def.appellation.name if w_def.appellation else "",
                 w_def.varietal.name if w_def.varietal else "",
                 w_def.vintage,
                 w_def.disgorgement_date
             )
             if lbl in options: def_w_idx = options.index(lbl)
        
        sel_w_str = st.selectbox("Wine", options, index=def_w_idx, key=f"{prefix}_sel_w")
        
        if sel_w_str == UI.CREATE_NEW_WINE:
            is_new_wine = True
        elif sel_w_str in group_map:
            is_new_wine = True
            # Pre-fill defaults from existing wine of this group (use most recent added)
            template_w = group_map[sel_w_str][-1]
            defaults = {
                "cuvee": template_w.cuvee,
                "vintage": "", 
                "type": template_w.type,
                "region": get_region_name(template_w),
                "appellation": template_w.appellation.name if template_w.appellation else None,
                "varietal": template_w.varietal.name if template_w.varietal else None,
                "vineyard": template_w.vineyard.name if template_w.vineyard else None,
                "blend": template_w.blend,
                "rp_score": "", "rp_note": "", "rp_url": "",
                "drink_start": template_w.drink_window_start,
                "drink_end": template_w.drink_window_end,
                "disgorgement_date": ""
            }
        elif sel_w_str != UI.SELECT:
             selected_wid = w_map.get(sel_w_str)

        if is_new_wine:
             pass # Logic handled in form render
              
    return {
        "is_new_producer": is_new_producer,
        "is_new_wine": is_new_wine,
        "selected_pid": selected_pid,
        "selected_wid": selected_wid,
        "sel_p_str": sel_p_str,
        "defaults": defaults
    }

def _component_creation_inputs(session, selector_state, prefix="main"):
    # Renders inputs inside form
    form_data = {}
    
    if selector_state["is_new_producer"]:
        c1, c2 = st.columns(2)
        form_data["new_prod_name"] = c1.text_input("New Producer Name", key=f"{prefix}_npn")
        
        all_regions = sorted(get_all_regions(), key=lambda r: r.name)
        reg_opts = [UI.SELECT.value] + all_regions
        form_data["new_prod_region"] = c2.selectbox("Region", reg_opts, key=f"{prefix}_npr", format_func=lambda x: x.name if hasattr(x, 'name') else x)
        form_data["sel_p"] = UI.CREATE_NEW
    else:
        form_data["sel_p"] = selector_state["sel_p_str"]
        
    if selector_state["is_new_wine"]:
        st.caption("New Wine Details")
        # Use defaults from selector_state (for New Vintage)
        core_data = _render_wine_core_fields(session, defaults=selector_state["defaults"], include_producer=False, prefix=prefix, external_producer=selector_state["sel_p_str"])
        # Update, but preserve producer-related fields which were set above
        for k, v in core_data.items():
             if k not in ["sel_p", "new_p", "new_prod_name", "new_prod_region"]:
                 form_data[k] = v
        # Explicitly set the new_p flag based on selector state
        form_data["new_p"] = selector_state["is_new_producer"]
        
    return form_data

def form_bottle(bottle_id=None):
    st.markdown(f"### {'Edit' if bottle_id else 'Add'} Bottle")
    session = get_session()
    b = None
    if bottle_id:
        b = session.get(Bottle, bottle_id)
        
    # Wine Selection (Outside Form for Interactivity)
    # This replaces the huge list loading and the toggle logic
    wine_id = b.wine_id if b else None
    
    # 1. Selector Component
    selector_state = _component_wine_selector(session, prefix="bottle", default_wine_id=wine_id)
    
    # 2. Form (Inputs and Save) - Removed st.form wrapper for interactivity
    # Render creation inputs (New Producer / New Wine fields)
    wine_form_data = _component_creation_inputs(session, selector_state, prefix="bottle")
    st.divider()

    col1, col2 = st.columns(2)
    qty = col1.number_input("Quantity", min_value=0, value=b.qty if b else 1)
    b_sizes = [x.value for x in BOTTLE_SIZES]
    size = col2.selectbox("Size", b_sizes, index=b_sizes.index(b.bottle_size) if b and b.bottle_size in b_sizes else 0)
    location = col1.text_input("Location", value=b.location if b else "")
    price = col2.number_input("Price", value=float(b.price) if b else 0.0)
    
    c_curr_idx = 0
    currs = [x.value for x in CURRENCIES]
    if b and b.currency in currs: c_curr_idx = currs.index(b.currency)
    currency = col1.selectbox("Currency", currs, index=c_curr_idx)
    
    vendor = col2.text_input("Vendor", value=b.vendor if b else "")
    prov = col1.text_input("Provenance", value=b.provenance if b else "")
    p_date = col2.date_input("Purchase Date", value=b.purchase_date if b else date.today())
    
    submitted = st.button("Save Bottle")
    if submitted:
        final_wid = None
        if selector_state["is_new_wine"]:
                # Create New Wine
                final_wid = _process_new_wine_form(session, wine_form_data)
        else:
                # Existing Wine
                final_wid = selector_state["selected_wid"]
        
        if not final_wid: st.error("Wine is required"); st.stop()
        
        if b:
            b.wine_id, b.qty, b.bottle_size, b.location, b.price, b.currency, b.vendor, b.provenance, b.purchase_date = final_wid, qty, size, location, price, currency, vendor, prov, p_date
        else:
            session.add(Bottle(wine_id=final_wid, qty=qty, bottle_size=size, location=location, price=price, currency=currency, vendor=vendor, provenance=prov, purchase_date=p_date))
        session.commit()
        st.success("Bottle saved!")
        time.sleep(0.5)
        navigate_to("Cellar")
    session.close()

def form_tasting(note_id=None, wine_id=None, bottle_id=None):
    st.markdown(f"### {'Edit' if note_id else 'Add'} Tasting Note")
    session = get_session()
    
    tn = None
    if note_id:
        tn = session.get(TastingNote, note_id)
        
    bottles = session.query(Bottle).join(Wine).join(Producer).order_by(Producer.name).all()
    
    # 1. Determine Mode (Cellar vs Other)
    # Default is "Other Wine" for generic "Add Tasting"
    default_mode_idx = 1 
    
    # Smart Defaulting based on args
    preselect_bottle_id = None
    preselect_wine_id = None
    if bottle_id:
        # "Drink" from Cellar Bottle view
        b_target = session.get(Bottle, bottle_id)
        if b_target: 
            preselect_bottle_id = b_target.id
            default_mode_idx = 0 # Cellar Bottle
    elif wine_id:
        try:
             preselect_wine_id = int(wine_id)
             # Check if we have bottles of this wine
             if any(b.wine_id == preselect_wine_id and b.qty > 0 for b in bottles):
                 default_mode_idx = 0 # Cellar Bottle
        except: pass

    # Persist "Other Wine" if "New Wine" creation is active
    nw_key = "tasting_create_new_wine"
    _get_state(nw_key, False)
    if st.session_state[nw_key]: default_mode_idx = 1
    
    # Render Mode Radio (Outside Form, triggers rerun)
    if note_id:
        # Editing: Lock Mode based on bottle type
        b = session.get(Bottle, tn.bottle_id)
        if b.provenance == "Ad-Hoc":
             mode = "Other Wine"
        else:
             mode = "Cellar Bottle"
        # Optional: Show badge? st.caption(f"Source: {mode}")
    else:
        mode = st.radio("Source", ["Cellar Bottle", "Other Wine"], index=default_mode_idx)
    
    # 3. Preparation of Lists & States (Outside Form)
    b_map = {}
    selector_state = None
    
    if mode == "Cellar Bottle":
        available_bottles = [b for b in bottles if b.qty > 0]
        if preselect_bottle_id:
             pb = session.get(Bottle, preselect_bottle_id)
             if pb and pb not in available_bottles: available_bottles.append(pb)
        b_map = {f"{b.wine.producer.name} - {b.wine.cuvee} ({b.wine.vintage}) - {b.bottle_size} @ {b.location}": b.id for b in available_bottles}
    
    elif mode == "Other Wine":
        selector_state = _component_wine_selector(session, prefix="tasting_other", default_wine_id=preselect_wine_id)

    places = session.query(Place).order_by(Place.name).all()
    place_map = {p.name: p.id for p in places}
    
    # 4. Global Form - Removed st.form for interactivity
    # with st.form("tasting_form"):
    if True: # Using if True to minimize indentation changes if desired, but better to dedent.
        selected_bid = None
        selected_wid = None
        wine_form_data = {}
        
        # --- SECTION A: WINE / BOTTLE SELECTION ---
        if note_id:
             # Editing: Lock Wine/Bottle Selection
             b = session.get(Bottle, tn.bottle_id)
             st.info(f"🍷 {b.wine.producer.name} - {b.wine.cuvee} ({b.wine.vintage})")
             selected_bid = tn.bottle_id
             selected_wid = b.wine_id
             
             # Allow editing bottle details for ALL modes (Cellar or Other)
             st.markdown("#### Bottle Details")

             c_b1, c_b2, c_b3 = st.columns(3)
             b_sizes = [x.value for x in BOTTLE_SIZES]
             currs = [x.value for x in CURRENCIES]
             new_bot_size = c_b1.selectbox("Bottle Size", b_sizes, index=b_sizes.index(b.bottle_size) if b.bottle_size in b_sizes else 0)
             new_bot_price = c_b2.number_input("Purchase Price", value=float(b.price) if b.price else 0.0)
             new_bot_curr = c_b3.selectbox("Currency", currs, index=currs.index(b.currency) if b.currency in currs else 0)
             new_bot_vendor = c_b1.text_input("Vendor", value=b.vendor if b.vendor else "")
             new_bot_prov = c_b2.text_input("Provenance", value=b.provenance if b.provenance else "") # Default empty for generic
             new_bot_date = c_b3.date_input("Purchase Date", value=b.purchase_date if b.purchase_date else date.today())
             
        elif mode == "Cellar Bottle":
             # Selectbox INSIDE form -> No Reloads!
             def_b_idx = 0
             if preselect_bottle_id and preselect_bottle_id in b_map.values():
                 vals = list(b_map.values())
                 def_b_idx = vals.index(preselect_bottle_id) + 1
             
             sel_b = st.selectbox("Select Bottle", [UI.SELECT.value] + list(b_map.keys()), index=def_b_idx)
             if sel_b != UI.SELECT: selected_bid = b_map[sel_b]
             
        elif mode == "Other Wine":
            wine_form_data = _component_creation_inputs(session, selector_state, prefix="tasting_other")
            if not selector_state["is_new_wine"]:
                selected_wid = selector_state["selected_wid"]

            # Ad-Hoc Bottle Details (Always needed for Other Wine)
            st.markdown("#### Bottle Details")
            c_b1, c_b2, c_b3 = st.columns(3)
            b_sizes = [x.value for x in BOTTLE_SIZES]
            currs = [x.value for x in CURRENCIES]
            new_bot_size = c_b1.selectbox("Bottle Size", b_sizes)
            new_bot_price = c_b2.number_input("Purchase Price", value=0.0)
            new_bot_curr = c_b3.selectbox("Currency", currs)
            new_bot_vendor = c_b1.text_input("Vendor")
            new_bot_prov = c_b2.text_input("Provenance", value="Ad-Hoc")
            new_bot_date = c_b3.date_input("Purchase Date", value=date.today())

        st.divider()
        
        # --- SECTION B: TASTING DETAILS ---
        c1, c2 = st.columns(2)
        d_drank = c1.date_input("Date Drank", value=tn.date if tn else date.today())
        
        p_idx = 0
        if tn and tn.place_id:
             p_obj = session.get(Place, tn.place_id)
             if p_obj and p_obj.name in place_map: p_idx = list(place_map.keys()).index(p_obj.name) + 2 # +2 for Select... and Create New...
        
        sel_place = st.selectbox("Place", [UI.SELECT.value, UI.CREATE_NEW_PLACE.value] + list(place_map.keys()), index=p_idx)
        
        new_place_data = {}
        if sel_place == UI.CREATE_NEW_PLACE:
             st.caption("New Place Details")
             new_place_data["name"] = st.text_input("New Place Name")
             cp1, cp2 = st.columns(2)
             new_place_data["city"] = cp1.text_input("City")
             new_place_data["country"] = cp2.text_input("Country")
             new_place_data["type"] = st.selectbox("Type", ["Restaurant", "Winery", "Home", "Bar", "Friend's Place", "Other"])

        with c2:
             rating = st.number_input("Score", min_value=50, max_value=100, value=tn.rating if tn else 90)
             glasses = st.number_input("Glasses", value=tn.glasses if tn else 1.0, step=0.5)
        
        tags = st.text_input("Tags", value=tn.tags if tn else "")
        sequence = st.number_input("Sequence", value=tn.sequence if tn else 1)
        notes = st.text_area("Notes", value=tn.notes if tn else "")
        
        consume = False
        if not note_id and mode == "Cellar Bottle":
             consume = st.checkbox("Consume Bottle (Reduce Qty)", value=True)

        submitted = st.button("Save Note")
        if submitted:
            try:
                # 1. Resolve Place
                pid = None
                ploc = "Unknown"
                if sel_place == UI.CREATE_NEW_PLACE:
                    if not new_place_data["name"]: st.error("Place Name Required"); st.stop()
                    p = Place(name=new_place_data["name"], city=new_place_data["city"], country=new_place_data["country"], type=new_place_data["type"])
                    session.add(p); session.flush(); pid = p.id; ploc = p.name
                elif sel_place != UI.SELECT:
                    pid = place_map[sel_place]; ploc = sel_place
                
                # 2. Resolve Bottle
                final_bid = selected_bid
                
                if mode == "Cellar Bottle":
                    if not final_bid: st.error("Bottle selection required"); st.stop()
                    if consume:
                        b_obj = session.get(Bottle, final_bid)
                        if b_obj.qty > 0: b_obj.qty -= 1
                elif not final_bid:
                    # Other Wine - Create New Bottle since we don't have one (not editing)
                    wid = selected_wid
                    if selector_state and selector_state["is_new_wine"]:
                         wid = _process_new_wine_form(session, wine_form_data)
                    
                    if not wid: st.error("Wine selection required"); st.stop()
                    
                    # Create Ad-Hoc Bottle
                    nb = Bottle(wine_id=wid, qty=0, location="Consumed", provenance=new_bot_prov, bottle_size=new_bot_size, price=new_bot_price, currency=new_bot_curr, vendor=new_bot_vendor, purchase_date=new_bot_date)
                    session.add(nb); session.flush(); final_bid = nb.id

                if not final_bid: st.error("Bottle required"); st.stop()

                # Update Bottle Details (Ad-Hoc or Edit Mode)
                if final_bid and (mode == "Other Wine" or note_id):
                     # Ensure variables are captured (they are in scope if mode matches)
                     b_upd = session.get(Bottle, final_bid)
                     if b_upd:
                         b_upd.bottle_size = new_bot_size
                         b_upd.price = new_bot_price
                         b_upd.currency = new_bot_curr
                         b_upd.vendor = new_bot_vendor
                         b_upd.provenance = new_bot_prov
                         b_upd.purchase_date = new_bot_date

                # 3. Save Note
                if note_id and tn:
                    tn.date, tn.place_id, tn.location, tn.tags, tn.rating, tn.glasses, tn.sequence, tn.notes = d_drank, pid, ploc, tags, rating, glasses, sequence, notes
                    session.commit(); st.success("Note Updated")
                else:
                    tn = TastingNote(bottle_id=final_bid, date=d_drank, rating=rating, notes=notes, tags=tags, location=ploc, place_id=pid, glasses=glasses, sequence=sequence)
                    session.add(tn); session.commit(); st.success("Note Saved")
                
                time.sleep(0.5)
                navigate_to("Tasting Notes")
            except Exception as e: st.error(f"Error: {str(e)}")
    session.close()

def form_restaurant_visit(visit_id=None):
    st.markdown(f"### {'Edit' if visit_id else 'Add'} Restaurant Visit")
    session = get_session()
    
    rv = None
    if visit_id:
        rv = session.get(RestaurantVisit, visit_id)
        
    places = session.query(Place).order_by(Place.name).all()
    place_map = {p.name: p.id for p in places}
    
    current_place_idx = 0
    if rv and rv.place_id:
        p_obj = session.get(Place, rv.place_id)
        if p_obj and p_obj.name in place_map:
            current_place_idx = list(place_map.keys()).index(p_obj.name) + 1
    
    sel_place = st.selectbox("Place", [UI.SELECT.value, UI.CREATE_NEW_PLACE.value] + list(place_map.keys()), index=current_place_idx + 1 if current_place_idx > 0 else 0)
    
    with st.form("visit_form"):
        date_visit = st.date_input("Date", value=rv.date if rv else date.today())
        
        new_place_name = None
        new_place_city = None
        new_place_country = None
        new_place_type = None
        
        if sel_place == UI.CREATE_NEW_PLACE:
            new_place_name = st.text_input("New Place Name")
            c_p1, c_p2 = st.columns(2)
            new_place_city = c_p1.text_input("City")
            new_place_country = c_p2.text_input("Country")
            new_place_type = st.selectbox("Type", ["Restaurant", "Winery", "Home", "Bar", "Friend's Place", "Other"])

        notes = st.text_area("Notes", value=rv.notes if rv else "")
        
        submitted = st.form_submit_button("Save Visit")
        if submitted:
            try:
                # 1. Handle Place
                final_place_id = None
                
                if sel_place == "➕ Create New Place...":
                    if not new_place_name: st.error("Place Name Required"); st.stop()
                    p = Place(name=new_place_name, city=new_place_city, country=new_place_country, type=new_place_type)
                    session.add(p); session.flush()
                    final_place_id = p.id
                elif sel_place != "Select...":
                    final_place_id = place_map[sel_place]
                else:
                    st.error("Place selection required"); st.stop()

                # 2. Create/Update Visit
                if visit_id and rv:
                    rv.date, rv.place_id, rv.notes = date_visit, final_place_id, notes
                    session.commit(); st.success("Visit Updated"); time.sleep(0.5); navigate_to("Places")
                else:
                    nv = RestaurantVisit(date=date_visit, place_id=final_place_id, notes=notes)
                    session.add(nv)
                    session.commit(); st.success("Visit Saved"); time.sleep(0.5); navigate_to("Places")
            except Exception as e: st.error(str(e))
    session.close()

def form_place(place_id=None):
    st.markdown(f"### {'Edit' if place_id else 'Add'} Place")
    session = get_session()
    
    p = None
    if place_id:
        p = session.get(Place, place_id)
    
    # If adding (though currently only edit is linked), defaults apply
    # but the form is designed mostly for editing an existing place.
    
    with st.form("place_form"):
        name = st.text_input("Name", value=p.name if p else "")
        c1, c2 = st.columns(2)
        city = c1.text_input("City", value=p.city if p else "")
        country = c2.text_input("Country", value=p.country if p else "")
        
        c3, c4 = st.columns(2)
        p_type = c3.selectbox("Type", ["Restaurant", "Winery", "Home", "Bar", "Friend's Place", "Other"], index=["Restaurant", "Winery", "Home", "Bar", "Friend's Place", "Other"].index(p.type) if p and p.type in ["Restaurant", "Winery", "Home", "Bar", "Friend's Place", "Other"] else 0)
        stars = c4.number_input("Michelin Stars", min_value=0, max_value=3, value=p.michelin_stars if p and p.michelin_stars else 0)
        
        notes = st.text_area("Notes", value=p.notes if p else "")
        
        submitted = st.form_submit_button("Save Place")
        if submitted:
            if not name: st.error("Name is required"); st.stop()
            
            if p:
                p.name, p.city, p.country, p.type, p.michelin_stars, p.notes = name, city, country, p_type, stars, notes
                session.commit(); st.success("Place Updated"); time.sleep(0.5); navigate_to("Place Detail", {"id": place_id})
            else:
                # Should not really be reached via "Add" button yet, but for completeness
                new_p = Place(name=name, city=city, country=country, type=p_type, michelin_stars=stars, notes=notes)
                session.add(new_p)
                session.commit(); st.success("Place Created"); time.sleep(0.5); navigate_to("Places")
    session.close()

