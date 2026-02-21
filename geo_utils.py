import os
import sys
import streamlit as st
import geopandas as gpd
import json
import glob

# Ensure this directory is in sys.path for local imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import shared

from shared import get_region_name

# ISO to country name mapping (consistent across ETL and Streamlit)
ISO_MAP = shared.ISO_MAP

# Get default map tileset from shared config
AVAILABLE_TILESETS = getattr(shared, 'AVAILABLE_TILESETS', ['OpenStreetMap'])
if st.context.theme["type"] == "dark":
    AVAILABLE_TILESETS.append("CartoDB dark_matter")
if st.context.theme["type"] == "light":
    AVAILABLE_TILESETS.append("CartoDB positron")

def add_tile_layers(folium_map):
    """
    Add multiple tile layers to a folium map for user selection.
    Note: This should be called BEFORE adding LayerControl to the map.
    
    Args:
        folium_map: folium.Map object to add tile layers to
        
    Returns:
        The same folium.Map object with additional tile layers added
    """
    import folium
    
    # Add additional tile layers
    for tileset in AVAILABLE_TILESETS:
        folium.TileLayer(tileset, name=tileset, overlay=False, control=True).add_to(folium_map)
    
    # Add CSS to make layer control and attributions smaller
    from folium import Element
    css = """
    <style>
    .leaflet-control-layers {
        font-size: 11px !important;
    }
    .leaflet-control-layers-base label,
    .leaflet-control-layers-overlays label {
        font-size: 11px !important;
    }
    .leaflet-control-attribution {
        font-size: 10px !important;
    }
    </style>
    """
    folium_map.get_root().html.add_child(Element(css))
    folium.LayerControl(collapsed=False).add_to(folium_map)
    return folium_map

@st.cache_data
def get_inao_data():
    """Load French INAO parquet data."""
    path = os.path.join(CURRENT_DIR, "data", "geo", "france.parquet")
    if os.path.exists(path):
        try:
            gdf = gpd.read_parquet(path)
            if 'id_app' in gdf.columns:
               return gdf.set_index('id_app')['geometry'].to_dict()
        except: pass
    return {}

@st.cache_data
def get_country_pdo_data(country_iso):
    """Load country-specific PDO geometries from app_data/geo/{country}_pdo.parquet"""
    country_name = ISO_MAP.get(country_iso.upper(), country_iso.lower())
    path = os.path.join(CURRENT_DIR, "data", "geo", f"{country_name}_pdo.parquet")
    
    if os.path.exists(path):
        try:
            gdf = gpd.read_parquet(path)
            # Match on pdo_id (or osm_id if pdo_id is missing, depending on ETL version)
            if 'pdo_id' in gdf.columns:
                return gdf.set_index('pdo_id')['geometry'].to_dict()
            elif 'osm_id' in gdf.columns:
                return gdf.set_index('osm_id')['geometry'].to_dict()
        except: pass
    return {}

def get_vineyard_geo_paths(region, appellation_name=None):
    """
    Returns a list of potential parquet file paths for vineyard geometries
    based on the region and optionally the appellation.
    """
    base_path = os.path.join(CURRENT_DIR, "data", "geo", "vineyards")
    
    is_bourgogne = region and region.lower() in ["bourgogne", "burgundy"]
    is_premier_cru_app = appellation_name and "premier cru" in appellation_name.lower()
    
    paths = []
    
    # 1. Standard regional files
    if region:
        safe_name = region.lower().replace(" ", "_").replace("/", "_")
        path_pattern = os.path.join(base_path, f"{safe_name}_*.parquet")
        paths.extend(glob.glob(path_pattern))
    
    # 2. Burgundy Premier Crus
    # Include if explicitly requested OR broad load (appellation_name is None)
    if is_bourgogne:
        if is_premier_cru_app or appellation_name is None:
             inao_path = os.path.join(base_path, "vineyards_premier_crus_inao.parquet")
             if os.path.exists(inao_path):
                 paths.append(inao_path)

    return list(set(paths))

@st.cache_data
def get_vineyard_data(region_name, appellation_name=None):
    """Loads all relevant vineyard geometries for a region."""
    if not region_name:
        return {}
        
    files = get_vineyard_geo_paths(region_name, appellation_name)
    if not files:
        return {}
    
    combined_geoms = {}
    for f in files:
        try:
            gdf = gpd.read_parquet(f)
            if 'id' in gdf.columns:
                combined_geoms.update(gdf.set_index('id')['geometry'].to_dict())
            elif 'vineyard_id' in gdf.columns:
                combined_geoms.update(gdf.set_index('vineyard_id')['geometry'].to_dict())
        except: pass
            
    return combined_geoms

@st.cache_data
def get_ava_data():
    """Load US AVA parquet data."""
    # Robust path construction
    path = os.path.join(CURRENT_DIR, "data", "geo", "us_avas_combined.parquet")
    if os.path.exists(path):
        try:
            gdf = gpd.read_parquet(path)
            # Create a lookup map. 
            # We need to map our constructed pdo_id back to geometry.
            # Our pdo_id format is "US-AVA-{ava_id}"
            
            lookup = {}
            for _, row in gdf.iterrows():
                try:
                    aid = row.get('ava_id')
                    if aid:
                         pid = f"US-AVA-{str(aid)}"
                         lookup[pid] = row['geometry']
                except: pass
            return lookup
        except Exception as e:
            print(f"Error loading AVA data: {e}")
            pass
    return {}

def resolve_app_geometry(app, inao_lookup=None, pdo_lookups=None, ava_lookup=None):
    """Resolves appellation geometry from various sources (INAO, PDO, AVA, DB)."""
    
    pdo_id = getattr(app, 'pdo_id', '') or ''
    
    # 0. US AVAs
    # Simplified logic: If country is US and we have a PDO ID, look it up.
    if app.pdo_id and app.region_obj and app.region_obj.country in ["United States", "USA"]:
        if ava_lookup is None:
            ava_lookup = get_ava_data()
        
        # The pdo_id stored in DB is like "US-AVA-temecula_valley"
        # The ava_lookup keys are also "US-AVA-temecula_valley"
        if app.pdo_id in ava_lookup:
            return ava_lookup[app.pdo_id]


    # 1. France INAO
    # Only load IF region is in France or it has an inao_id / FR pdo_id
    if app.inao_id:
        region = get_region_name(app)
        
        # Robust France check: DB country field is "France", or name is "France", or pdo_id contains -FR-
        is_france = (app.region_obj and app.region_obj.country == "France") or \
                    (region and region.lower() == "france") or \
                    (pdo_id and '-FR-' in pdo_id.upper())
        
        if is_france:
            if inao_lookup is None:
                inao_lookup = get_inao_data()
            
            # Type safety: inao_id might be int in DB but str in parquet index
            val = inao_lookup.get(app.inao_id)
            if val is None:
                val = inao_lookup.get(str(app.inao_id))
            
            if val is not None:
                return val
    
    # 2. Non-France PDO
    if app.pdo_id:
        try:
            parts = app.pdo_id.split('-')
            if len(parts) >= 2:
                iso = parts[1]
                if iso != "FR" and iso != "AVA": # Skip FR and our custom AVA
                    if pdo_lookups is not None:
                        if iso not in pdo_lookups:
                            pdo_lookups[iso] = get_country_pdo_data(iso)
                        lookup = pdo_lookups[iso]
                    else:
                        lookup = get_country_pdo_data(iso)
                    
                    if app.pdo_id in lookup:
                        return lookup[app.pdo_id]
        except: pass
        
    # 3. Fallback to GeoJSON in DB
    if app.geojson:
        try:
            return json.loads(app.geojson)
        except: pass
    return None

def resolve_vine_geometry(vineyard, region_name=None, appellation_name=None, field_lookup=None):
    """Resolves vineyard geometry from various sources (Parquet, DB)."""
    # 1. Parquet
    if vineyard.vineyard_id:
        if not region_name:
            region_name = get_region_name(vineyard)
            
        if field_lookup is None and region_name:
            field_lookup = get_vineyard_data(region_name, appellation_name)
        
        if field_lookup and vineyard.vineyard_id in field_lookup:
            return field_lookup[vineyard.vineyard_id]
    
    # 2. DB Fallback
    if vineyard.geojson:
        try:
            return json.loads(vineyard.geojson)
        except: pass
    return None


from shapely.geometry import shape

def get_geometry_bounds(geo):
    """
    Returns bounds [[min_lat, min_lng], [max_lat, max_lng]] for a geometry.
    Compatible with folium.fit_bounds().
    Returns None if geometry is invalid or empty.
    """
    if not geo:
        return None
        
    try:
        # Convert to Shapely Geometry
        geom = None
        if isinstance(geo, dict):
            type_ = geo.get('type')
            if type_ == 'FeatureCollection':
                from shapely.ops import unary_union
                geoms = []
                for f in geo.get('features', []):
                    g = f.get('geometry')
                    if g:
                        geoms.append(shape(g))
                if geoms:
                    geom = unary_union(geoms)
            elif type_ == 'Feature':
                 g = geo.get('geometry')
                 if g:
                     geom = shape(g)
            else:
                geom = shape(geo)
        elif hasattr(geo, 'geom_type'):
            geom = geo
            
        if geom and not geom.is_empty:
             minx, miny, maxx, maxy = geom.bounds
             return [[miny, minx], [maxy, maxx]]  # [[min_lat, min_lng], [max_lat, max_lng]]
             
    except Exception:
        pass
    
    return None


def create_place_map(place):
    """
    Create a folium map for a place (restaurant/location).
    
    Args:
        place: Place object with lat, lng, name, and michelin_stars attributes
        
    Returns:
        folium.Map object or None if coordinates are missing
    """
    if not place.lat or not place.lng:
        return None
        
    import folium
    
    try:
        # Center map on place
        m = folium.Map(location=[place.lat, place.lng], zoom_start=15)
        
        # Add marker
        tooltip = f"{place.name} ({place.michelin_stars}*)" if place.michelin_stars else place.name
        folium.Marker(
            [place.lat, place.lng], 
            tooltip=tooltip,
            icon=folium.Icon(color="red", icon="cutlery", prefix='fa')
        ).add_to(m)
        
        # Add additional tile layers for selection
        add_tile_layers(m)
        
        return m
    except Exception:
        return None


def create_appellation_map(appellation, geo_data, color="#c27ba0"):
    """
    Create a folium map for an appellation.
    
    Args:
        appellation: Appellation object with name attribute
        geo_data: GeoJSON geometry data (dict or Shapely geometry)
        color: Hex color for the polygon/marker (default: purple)
        
    Returns:
        folium.Map object or None if geometry is invalid
    """
    if not geo_data:
        return None
        
    import folium
    
    try:
        bounds = get_geometry_bounds(geo_data)
        
        if bounds:      
            min_lat, min_lng = bounds[0]
            max_lat, max_lng = bounds[1]
            center = [(min_lat + max_lat) / 2, (min_lng + max_lng) / 2]
        else:
            center = [47.0, 4.0]

        m = folium.Map(location=center, zoom_start=10)

        if geo_data['type'] == 'Point':
            coords = geo_data['coordinates']
            lat, lon = coords[1], coords[0]
            folium.CircleMarker(
                location=[lat, lon],
                radius=6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                tooltip=appellation.name
            ).add_to(m)
        else:
            folium.GeoJson(
                geo_data,
                style_function=lambda x: {
                    'fillColor': color,
                    'color': color,
                    'weight': 1,
                    'fillOpacity': 0.4
                },
                tooltip=appellation.name
            ).add_to(m)
        
        if bounds:
            m.fit_bounds(bounds)

        # Add additional tile layers for selection
        add_tile_layers(m)

        return m
    except Exception:
        return None


def create_vineyard_map(vineyard, geo_data):
    """
    Create a folium map for a vineyard.
    
    Args:
        vineyard: Vineyard object with name attribute
        geo_data: GeoJSON geometry data (dict or Shapely geometry)
        
    Returns:
        folium.Map object or None if geometry is invalid
    """
    if not geo_data:
        return None
        
    import folium
    
    try:
        bounds = get_geometry_bounds(geo_data)
        
        if bounds:
            min_lat, min_lng = bounds[0]
            max_lat, max_lng = bounds[1]
            center = [(min_lat + max_lat) / 2, (min_lng + max_lng) / 2]
        else:
            center = [47.0, 4.0]
        
        m = folium.Map(location=center, zoom_start=14)
        folium.GeoJson(geo_data, name=vineyard.name, style_function=lambda x: {
            'fillColor': '#228b22', 'color': '#228b22', 'fillOpacity': 0.4, 'weight': 2
        }).add_to(m)
        
        if bounds:
            m.fit_bounds(bounds)
        
        # Add additional tile layers for selection
        add_tile_layers(m)
        
        return m
    except Exception:
        return None


def create_wine_combined_map(wine, appellation_geo=None, vineyard_geo=None):
    """
    Create a combined folium map showing both appellation and vineyard for a wine.
    
    Args:
        wine: Wine object with appellation and vineyard attributes
        appellation_geo: Optional pre-resolved appellation geometry (dict or Shapely geometry)
        vineyard_geo: Optional pre-resolved vineyard geometry (dict or Shapely geometry)
        
    Returns:
        tuple: (folium.Map object or None, label string describing what's shown)
    """
    import folium
    
    targets = []
    
    # Add appellation if available
    if appellation_geo:
        targets.append({
            "geo": appellation_geo,
            "name": wine.appellation.name if wine.appellation else "Appellation",
            "type": "Appellation",
            "color": "#c27ba0"
        })
    
    # Add vineyard if available
    if vineyard_geo:
        targets.append({
            "geo": vineyard_geo,
            "name": wine.vineyard.name if wine.vineyard else "Vineyard",
            "type": "Vineyard",
            "color": "#228b22"
        })
    
    if not targets:
        return None, ""
    
    try:
        # Use first geometry for initial center
        primary = targets[0]
        bounds = get_geometry_bounds(primary['geo'])
        
        if bounds:
            min_lat, min_lng = bounds[0]
            max_lat, max_lng = bounds[1]
            center = [(min_lat + max_lat) / 2, (min_lng + max_lng) / 2]
        else:
            center = [47.0, 4.0]

        m = folium.Map(location=center, zoom_start=10)
        
        # Add all features to the same map
        for t in targets:
            geo = t['geo']
            if geo['type'] == 'Point':
                folium.CircleMarker(
                    location=[geo['coordinates'][1], geo['coordinates'][0]], 
                    radius=6, color=t['color'],
                    fill=True, fill_color=t['color'], fill_opacity=0.7,
                    tooltip=f"{t['type']}: {t['name']}"
                ).add_to(m)
            else:
                style_function = lambda x, c=t['color']: {
                    'fillColor': c, 'color': c, 'fillOpacity': 0.4, 'weight': 1
                }
                folium.GeoJson(geo, name=t['name'], style_function=style_function, 
                             tooltip=f"{t['type']}: {t['name']}").add_to(m)
        
        # Fit bounds to show all features
        if bounds:
            m.fit_bounds(bounds)
        
        add_tile_layers(m)
        
        # Create label string
        label_str = " + ".join([f"{t['type']}: {t['name']}" for t in targets])
        
        return m, label_str
    except Exception as e:
        import traceback
        print(f"Error in create_wine_combined_map: {e}")
        traceback.print_exc()
        return None, ""
