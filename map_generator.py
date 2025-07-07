# map_generator.py

import os
import shutil
import zipfile
from datetime import datetime, timedelta
import eumdac
import json
from shapely.geometry import shape, Point

import numpy as np
import pandas as pd
import xarray as xr

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from matplotlib.colors import LogNorm

CLIENT_ID = os.getenv('EUMDAC_CLIENT_ID')
CLIENT_SECRET = os.getenv('EUMDAC_CLIENT_SECRET')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp_extract")
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUT_DIR = os.path.join(STATIC_DIR, "generated_maps")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

_eumdac_datastore = None
_countries_data = None
_country_shapes_cache = {}

def get_datastore():
    """initializes and returns a singleton EUMDAC DataStore instance"""
    global _eumdac_datastore
    if _eumdac_datastore is None:
        if not CLIENT_ID or not CLIENT_SECRET:
            raise ValueError("EUMDAC API credentials not found in .env file")
        credentials = (CLIENT_ID, CLIENT_SECRET)
        _eumdac_datastore = eumdac.DataStore(eumdac.AccessToken(credentials))
    return _eumdac_datastore

def get_country_data(country_code):
    """loads and caches a country's shape and bounding box from the geojson file"""
    global _countries_data, _country_shapes_cache
    if country_code in _country_shapes_cache:
        return _country_shapes_cache[country_code]

    if _countries_data is None:
        geojson_path = os.path.join(BASE_DIR, "static", "data", "countries.geojson")
        with open(geojson_path, encoding='utf-8') as f:
            _countries_data = json.load(f)

    for feature in _countries_data['features']:
        props = feature['properties']
        if props.get('ISO3166-1-Alpha-2') == country_code:
            geom = shape(feature['geometry'])
            result = {"shape": geom, "bounds": geom.bounds}
            _country_shapes_cache[country_code] = result
            return result
    
    raise ValueError(f"country with ISO code '{country_code}' not found.")

def process_single_flash_product(product):
    """downloads, extracts, and processes a single satellite data product"""
    product_name = str(product)
    downloaded_filename = os.path.join(TEMP_DIR, f"{product_name}.zip")
    body_chunk_path = None
    try:
        with product.open() as fsrc, open(downloaded_filename, mode='wb') as fdst:
            shutil.copyfileobj(fsrc, fdst)
        
        with zipfile.ZipFile(downloaded_filename, 'r') as zf:
            nc_files = [f for f in zf.namelist() if f.endswith('.nc')]
            if not nc_files: return None
            
            body_nc_file = max(nc_files, key=lambda f: zf.getinfo(f).file_size)
            zf.extract(body_nc_file, TEMP_DIR)
            body_chunk_path = os.path.join(TEMP_DIR, body_nc_file)

        with xr.open_dataset(body_chunk_path, engine='netcdf4') as ds:
            if 'flashes' not in ds.sizes or ds.sizes['flashes'] == 0:
                return None
            return pd.DataFrame({
                'lat': ds['latitude'].values,
                'lon': ds['longitude'].values
            })
    except Exception as e:
        print(f"error processing product {product_name}: {e}")
        return None
    finally:
        if body_chunk_path and os.path.exists(body_chunk_path):
            os.remove(body_chunk_path)
        if os.path.exists(downloaded_filename):
            os.remove(downloaded_filename)

def get_flashes_for_period(start_dt, end_dt):
    """generator that fetches and processes lightning data for a given time period"""
    yield {"status": "Connecting to EUMETSAT...", "progress": 2}
    datastore = get_datastore()
    collection = datastore.get_collection('EO:EUM:DAT:0691')
    
    yield {"status": "Searching for products...", "progress": 5}
    products = list(collection.search(dtstart=start_dt, dtend=end_dt))
    
    if not products:
        yield {"status": "no satellite products found for this period.", "progress": 100, "done": True, "error": True}
        return
        
    yield {"status": f"found {len(products)} products. processing...", "progress": 15}
    
    all_flashes_dfs = []
    for i, product in enumerate(products):
        progress = 15 + int((i + 1) / len(products) * 70)
        yield {"status": f"processing product {i + 1}/{len(products)}...", "progress": progress}
        flash_df = process_single_flash_product(product)
        if flash_df is not None:
            all_flashes_dfs.append(flash_df)
            
    yield {"status": "Consolidating data...", "progress": 90}
    
    if not all_flashes_dfs:
        yield {"status": "no valid lightning data could be extracted.", "progress": 100, "done": True, "error": True}
        return
        
    combined_df = pd.concat(all_flashes_dfs, ignore_index=True)
    yield {"status": f"Finished. Found {len(combined_df):,} flashes.", "progress": 95, "data": combined_df, "done": True}

def _run_data_pipeline(start_dt, end_dt, country_code):
    """full pipeline: fetches data, then filters it for a specific country"""
    flash_data_generator = get_flashes_for_period(start_dt, end_dt)
    all_flashes = pd.DataFrame()
    for update in flash_data_generator:
        if update.get("done"):
            if update.get("error"):
                yield update
                return
            all_flashes = update.get("data", pd.DataFrame())
            break
        else:
            yield update
            
    try:
        country_data = get_country_data(country_code)
        country_shape = country_data["shape"]
        min_lon, min_lat, max_lon, max_lat = country_data["bounds"]
    except ValueError as e:
        yield {"status": str(e), "progress": 100, "done": True, "error": True}
        return

    yield {"status": f"filtering data for {country_code}...", "progress": 96}
    
    df_in_box = all_flashes[
        (all_flashes['lon'] >= min_lon) & (all_flashes['lon'] <= max_lon) &
        (all_flashes['lat'] >= min_lat) & (all_flashes['lat'] <= max_lat)
    ].copy()
    
    if df_in_box.empty:
        yield {"status": f"no flashes within the bounding box of {country_code}.", "progress": 100, "done": True, "error": True}
        return
        
    points = [Point(xy) for xy in zip(df_in_box['lon'], df_in_box['lat'])]
    is_within = [point.within(country_shape) for point in points]
    df_filtered = df_in_box[is_within]

    if df_filtered.empty:
        yield {"status": f"no lightning strikes found directly over {country_code}.", "progress": 100, "done": True, "error": True}
        return
        
    yield {"status": "data filtered.", "progress": 97, "data": df_filtered, "bounds": country_data["bounds"], "done": True}

def generate_density_map(year, month, day, grid_res_km, filename_key, country_code):
    """a single, unified function to generate all daily density maps"""
    filename = f"overlay_{filename_key}_{country_code}_{year}-{month:02d}-{day:02d}.png"
    relative_url_path = os.path.join("generated_maps", filename).replace("\\", "/")
    full_save_path = os.path.join(STATIC_DIR, relative_url_path)

    if os.path.exists(full_save_path):
        yield {"status": "found cached map.", "progress": 100, "done": True, "result": relative_url_path}
        return

    df_filtered = pd.DataFrame()
    country_bounds = None
    pipeline = _run_data_pipeline(
        datetime(year, month, day),
        datetime(year, month, day) + timedelta(days=1),
        country_code
    )
    for update in pipeline:
        if update.get("done"):
            if update.get("error"):
                yield update
                return
            df_filtered = update["data"]
            country_bounds = update["bounds"]
            break
        else:
            yield update

    yield {"status": "generating map overlay...", "progress": 98}
    
    extent = [country_bounds[0], country_bounds[2], country_bounds[1], country_bounds[3]]

    aspect_ratio = (extent[1] - extent[0]) / (extent[3] - extent[2])
    fig = plt.figure(figsize=(10, 10 / aspect_ratio))
    ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.PlateCarree())
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    if not df_filtered.empty:
        lat_span_km = (extent[3] - extent[2]) * 111
        lon_span_km = (extent[1] - extent[0]) * 111 * np.cos(np.radians(np.mean(extent[2:])))
        bins = [int(lon_span_km / grid_res_km), int(lat_span_km / grid_res_km)]
        
        density, xedges, yedges = np.histogram2d(
            df_filtered['lon'], df_filtered['lat'], bins=bins, 
            range=[[extent[0], extent[1]], [extent[2], extent[3]]]
        )
        density_masked = np.ma.masked_where(density == 0, density)
        
        ax.pcolormesh(
            xedges, yedges, density_masked.T, 
            transform=ccrs.PlateCarree(), cmap='turbo', norm=LogNorm(), alpha=0.75
        )
    
    plt.savefig(full_save_path, dpi=200, bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig)
    
    yield {"status": "map generated!", "progress": 100, "done": True, "result": relative_url_path}

def generate_daily_lowres_density(year, month, day, country_code):
    yield from generate_density_map(year, month, day, 5.0, "lowres", country_code)

def generate_daily_hires_density(year, month, day, country_code):
    yield from generate_density_map(year, month, day, 1.0, "hires", country_code)