from ipyleaflet import GeoJSON, LayerGroup, WidgetControl
from ipywidgets import Text, HTML
import json 
import geopandas as gpd 
import pandas as pd 

class MapLayer:
    label: str
    layer_type: str # "points" | "bounds"
    point_label: str 
    filename: str  
    style: dict 
    gdf: gpd.GeoDataFrame
    def __init__(self, label, layer_type, point_label, filename, style) -> None:
        self.label = label
        self.layer_type = layer_type
        self.point_label = point_label
        self.filename = filename
        self.style = style 
        self.gdf = gpd.read_file(f'data/{self.filename}').set_geometry('geometry')
    
    def __repr__(self):
        return self.label
        



map_layer_config = {
    "corridors": MapLayer(
        label = "Industrial corridors",
        layer_type = "bounds",
        point_label = "Industrial corridor",
        filename = "Boundaries - Industrial Corridors (current).geojson",
        style =  {
                    "color": "grey", 
                    "weight":.75,
                    "fillOpacity": 0.5
                }
    ), 
    "communities": MapLayer(
        label = "Community areas", 
        layer_type = "bounds",
        point_label = "Community area",
        filename = "Boundaries - Community Areas (current).geojson",
        style =  {
            "color": "grey", 
            "fillOpacity": 0,
            "weight": 0.6
        }
    ),
    "tracts": MapLayer(
        label = "Census tracts", 
        layer_type = "bounds",
        point_label = "Census tract",
        filename = "ej_index.geojson",
        style =  {}
    )
}




map_layer_config_chinese = {
    "corridors": MapLayer(
        label = "工业区域",
        layer_type = "bounds",
        point_label = "工业区域",
        filename = "Boundaries - Industrial Corridors (current).geojson",
        style =  {
                    "color": "grey", 
                    "weight":.75,
                    "fillOpacity": 0.5
                }
    ), 
    "communities": MapLayer(
        label = " 邻里界线", 
        layer_type = "bounds",
        point_label = " 邻里界线",
        filename = "Boundaries - Community Areas (current).geojson",
        style =  {
            "color": "grey", 
            "fillOpacity": 0,
            "weight": 0.6
        }
    ),
    "tracts": MapLayer(
        label = "人口普查调查区", 
        layer_type = "bounds",
        point_label = "人口普查调查区",
        filename = "ej_index.geojson",
        style =  {}
    )
}




map_layer_config_spanish = {
    "corridors": MapLayer(
        label = "corredor industrial",
        layer_type = "bounds",
        point_label = "corredor industrial",
        filename = "Boundaries - Industrial Corridors (current).geojson",
        style =  {
                    "color": "grey", 
                    "weight":.75,
                    "fillOpacity": 0.5
                }
    ), 
    "communities": MapLayer(
        label = "zona comunidad", 
        layer_type = "bounds",
        point_label = "zona comunidad",
        filename = "Boundaries - Community Areas (current).geojson",
        style =  {
            "color": "grey", 
            "fillOpacity": 0,
            "weight": 0.6
        }
    ),
    "tracts": MapLayer(
        label = "distrito censal", 
        layer_type = "bounds",
        point_label = "distrito censal",
        filename = "ej_index.geojson",
        style =  {}
    )
}

def locate_point(lat, long, bounds):
    marker = gpd.points_from_xy(x=long, y=lat, crs="EPSG:4326")
    mf = gpd.GeoDataFrame(marker).set_geometry(0).rename_geometry('geometry')
    result = gpd.sjoin(bounds, mf)
    if len(result) > 0:
        return result.head(1)['name'].squeeze()
    else:
        return None 

