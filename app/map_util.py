from ipyleaflet import GeoJSON, LayerGroup, WidgetControl
from ipywidgets import Text, HTML
import json 

class MapLayer:
    label: str 
    filename: str 
    name_field: str 
    style: dict 


def get_map_layer(filename, style_overrides:dict = {}):
    style = {
            "opacity": 1,  
            "dashArray": "9",  
            "fillOpacity": 0.1,  
            "weight": 1,
    }
    style.update(style_overrides)
    with open(f"data/{filename}", "r") as f:
        boundaries = json.load(f)
    
    geo_json = GeoJSON(  
        data=boundaries,  
        style=style,
        hover_style={"color": "white", "dashArray": "0", "fillOpacity": 0.5},  
    )  

    return geo_json


map_layers = [
    MapLayer(
        label = "Industrial corridors",
        filename = "Boundaries - Industrial Corridors (current).geojson",
        name_field = 'name',
        style =  {
                    "color": "red", 
                    "fillOpacity": 0.25
                }
    )
]