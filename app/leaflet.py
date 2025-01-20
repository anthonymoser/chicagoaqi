from ipyleaflet import GeoJSON, Map, Marker, SearchControl, LayersControl, LayerGroup, WidgetControl
from ipywidgets import Text, HTML
from urllib.parse import urlparse
from shiny import App, ui, render, reactive 
from shiny.types import ImgData
from shinywidgets import output_widget, render_widget  
import json
from uuid import uuid4 
import pandas as pd 
from map_util import get_map_layer, MapLayer, map_layers

from google.cloud import bigquery 
import os 
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = '/Users/AnthonyMoser/Dev/public_data_tools/.keys/cloud_function_invoker.json'
bq = bigquery.Client()                              
aqi_table = pd.read_csv('data/aqi_table.csv')

app_ui = ui.page_auto( 
    ui.output_image("logo", inline=True),
    ui.div( ui.help_text("a tool from Neighbors For Environmental Justice"), id="attribution", style="text-align: right;"),
    # ui.input_select( id="language_choice", label='Language', choices=["English", "Español", "中文"], selected="English", width="120px"),
    ui.navset_card_underline(

        ui.nav_panel( "Suggest a location",
            ui.div( 
            ui.tags.h4("Where should the air monitors go?"),
            ui.p("As part of a federal agreement, ", ui.tags.b("Chicago promised to install 220 air monitors, "), "mostly in neighborhoods with a lot of pollution."), 
            ui.p(" The city hasn't decided where to put them yet, and we want to make sure they pick useful locations: maybe a place you see kids playing, or trucks idling, or smell something funky."),
            ui.p("Where do you think they should go?"),
            
            output_widget(id = "map"),
            ui.row(
                ui.layout_column_wrap(
                    ui.card(
                        ui.card_header("1. PICK A SPOT ON THE MAP"),
                        ui.tags.p("There are four ways to choose:"), 
                        ui.tags.ul(
                            ui.tags.li("Click on the map"),
                            ui.tags.li("Drag the marker"),
                            ui.tags.li(ui.TagList("Search for an address (click ", ui.HTML("&#x1F50D;"), " on the map)")),
                            ui.tags.li("Find your current location")
                        ),
                        ui.card_footer(ui.input_action_button("btn_use_location", label="Find my location", width="100%"),)
                    ),
                    ui.card(
                        ui.card_header("2. TELL US ABOUT IT (optional)"),
                        ui.input_text(id="suggested_label", label="What would you call this spot?", width="100%", placeholder="example: McKinley Park / MAT Asphalt / the playground"),
                        ui.input_text_area(id="reason", label="Why put an air monitor there?", width="100%", placeholder="example: I live nearby / it always smells bad"),
                        ui.card_footer(ui.input_action_button("btn_submit", label="Submit", width="100%"))
                    ),
                ),
                ),
            ),
        ),

        ui.nav_panel( "Why we're doing this",
            ui.div( 
            ui.accordion(
                ui.accordion_panel( "Air monitors",
                    ui.p(ui.tags.b("Why do we need air monitors?")),
                    ui.tags.ul(
                        ui.tags.li("In Chicago, how much pollution you breathe depends a lot on where you live"),
                        ui.tags.li("Air monitors help us know what we're breathing"), 
                        ui.tags.li("On days with the worst air pollution, we can take actions to stay safe, like running air filters and wearing masks"),
                        ui.tags.li("We can use this data to push the city to take action")
                         ),
                    ui.p(ui.tags.b("Does it matter where they go?")),
                    ui.tags.ul(
                        ui.tags.li("Yes! Air monitors can only measure what's nearby"), 
                        ui.tags.li("Depending on weather and nearby sources of pollution, even a few blocks can make a big difference"),
                        ui.tags.li("The places that have the most pollution in Chicago (South and Southwest Chicago) do not have air monitors installed by the government to measure the air quality")
                    ),
                    ui.p(ui.tags.b("What kind of air monitors are they?")),
                    ui.tags.ul( 
                        ui.tags.li(ui.a("Clarity Node-S monitors", href="https://www.clarity.io/products/clarity-node-s"), target="_blank"),
                        ui.tags.li("They use solar panels, and will be installed on light poles"),
                        ui.tags.li("They measure particulate matter (PM) and nitrogen dioxide (NO₂)"),
                        ui.tags.li("They will upload data to a public dashboard")
                    ),
                    ui.p(ui.tags.b("Doesn't the city have air monitors already?")),
                    ui.tags.ul(
                        ui.tags.li("There are only a few government-owned air monitors in or near Chicago"),
                        ui.tags.li("They're mostly not owned by the city, and mostly not in neighborhoods with the worst pollution"),
                        ui.tags.li("A study found the US EPA puts more air monitors", ui.a(" in white neighborhoods", href="https://www.theguardian.com/environment/2024/dec/14/epa-air-quality-monitors-white-neighborhoods", target="_blank")),
                        ui.tags.li("You can see readings from the ", ui.a("six Illinois EPA monitors", href="https://www.airnow.gov/?city=Chicago&state=IL&country=USA", target="_blank")),
                        ui.tags.li("Community groups and residents have also put up air monitors ", ui.a("on their own", href="https://map.purpleair.com/air-quality-standards-us-epa-aqi?opt=%2F1%2Flp%2Fa0%2Fp604800%2FcC0#10.6/41.8697/-87.674", target="_blank"))
                    )

                ),                    
                ui.accordion_panel( "Pollution", 
                    ui.p(ui.tags.b("What is air pollution?")),
                    ui.tags.ul(
                        ui.tags.li("Pollution is tiny bits of stuff we inhale when we breathe"), 
                        ui.tags.li("It can be made of gases, or tiny particles that are 100 times thinner than a human hair"),
                        ui.tags.li("Sometimes you can smell, see, or feel pollution, but mostly we don’t know what we’re breathing")
                    ),
                    ui.p(ui.tags.b("Where does air pollution come from?")),
                    ui.tags.ul(
                        ui.tags.li("Transportation: cars, trucks, and trains"), 
                        ui.tags.li("Industry: factories, asphalt plants, construction equipment and diesel vehicles"),
                        ui.tags.li("Natural sources: smoke from wildfires, dust blown by the wind"),
                        ui.tags.li("In Chicago, city policies put pollution in communities of color and low-income communities."),
                        ui.tags.li("This practice is called environmental racism"),
                        ui.tags.li("These new air monitors are part of an contract signed by the city promising to address environmental racism"),
                    ),
                    ui.p(ui.tags.b("How bad is it for your health?")),
                    ui.tags.ul(
                        ui.tags.li("It makes existing health problems worse"), 
                        ui.tags.li("It causes new health problems, like asthma, headaches, and chest pain"),
                        ui.tags.li("The combined effect of of outdoor air pollution and indoor air pollution ", ui.a("kills about 6.7 million people", href="https://www.who.int/data/gho/data/indicators/indicator-details/GHO/ambient-air-pollution-attributable-deaths", target="_blank"), " around the world every year."),
                    ),
                    ui.p(ui.tags.b("How is air pollution measured?")),
                    ui.tags.ul(
                        ui.tags.li("Different sensors detect different types of air pollution. Most air monitors measure one or two"), 
                        ui.tags.li("The most common air monitors measure particulate matter (PM 2.5), a mixture of the tiny things that get into your lungs when you breathe"),
                        ui.tags.li("PM 2.5 is counted in micrograms per cubic meter of air (µg/m³) "),
                    ),
                    ui.p(ui.tags.b("How can you tell when the air quality is bad?")),
                    ui.tags.ul(
                        ui.tags.li("There is no safe level of air pollution"),
                        ui.tags.li("To make air quality easier to understand, the US EPA uses PM2.5 readings to calculate the Air Quality Index (AQI)"),
                        ui.tags.li("AQI is a scale that goes from zero (no pollution) to 500 (extremely high amounts of pollution)"),
                        ui.tags.li("People from “sensitive groups” (children, the elderly, or people with heart and lung conditions) should often stay inside if the AQI is high")
                    ),
                    ui.output_table("aqi_ranges")
                ),
                ui.accordion_panel( "About this project",
                    ui.p(ui.tags.b("What will happen to the suggestions people submit?")),
                    ui.div(
                        ui.p("Neighbors For Environmental Justice (",ui.a("N4EJ", href="http://n4ej.org", target="_blank"),") is collecting this data."),
                        ui.p("Suggestions are public as soon as they are submitted (you can see them on the 'Explore the data' page). N4EJ will share them with the Department of Public Health, which has the final say on where monitors are installed."),
                        class_="faq_answer"
                    ),

                    ui.p(ui.tags.b("When will the monitors go up?")),
                    ui.div(
                        ui.p("We don't really know."),
                        ui.p("""As of January 2025, the city has signed contracts with a non-profit "to help coordinate community engagement and identify members for an advisory group to inform sensor placement." """),
                        ui.p("Currently the city's plan is: "),
                            ui.tags.ol(
                                ui.tags.li("The non-profit will suggest members of an advisory group"),
                                ui.tags.li("The group will advise the city on taking community input and placing sensors"),
                                ui.tags.li("The city will ask people where monitors should go"),
                                ui.tags.li("The city will decide where to put the sensors"),
                                ui.tags.li("Then they can start putting them up.")
                            ),
                        ui.p("However, the city staffer coordinating the project was ", 
                             ui.a("asked to resign", href="https://chicago.suntimes.com/the-watchdogs/2024/12/13/raed-mansour-air-pollution-environmental-justice-brandon-johnson-horace-smith-chicago-climate-change", target="_blank"),
                             " in November, and since then not much has happened."),
                        ui.p("Instead of waiting for the city to act, N4EJ built this tool and we are taking suggestions now."),
                        class_="faq_answer"
                    ),
                    ui.p(ui.tags.b("Why is the city installing air monitors?")),
                    ui.div(
                        ui.p("The air monitors are required by a ", ui.a("federal agreement", href="https://chicago.suntimes.com/2023/5/12/23720343/hud-environmental-racism-lightfoot-general-iron-environmental-justice-housing-urban-development", target="_blank"), " the city signed in 2023."),
                        class_="faq_answer"
                    )                
                ),    
                id = "accordion_faq",
                open = ["Air monitors", "Pollution", "About this project"]                       
            ),
            id="faq"
            ),
        ),
        ui.nav_panel("Explore data",
            ui.output_code(id="explore_details"),
            output_widget(id="explore_data")
        ),
        selected="Explore data"
    ),
    ui.tags.style("""
                  
        .nav .nav-underline {
            background-color: #efefef;
        }

        .card-header { background-color: #f9f9f9; }
        .ul .li { margin-bottom: 10px; }
        .faq_answer {
            padding-left: 1.5rem;
            padding-bottom: 1.5rem;
        }
        #attribution { margin-bottom: 1rem; }
        #map { margin-bottom: 15px; }
        #language_choice-label {display:None;}
        #page_container { max-width: 1000px; }
        #explore_data {height:1000px;}
        
    """),
    # .card-body { padding: None;}
            # .nav-underline .nav-link { 
            # margin-bottom: 15px; 
        # }
    id="page_container"
)

def server(input, output, session):


    center = (41.8228883909135, -87.6771203648879)
    drag_marker = Marker(location=center, draggable=True)
    search_marker = Marker()

    the_map = Map(center=center, zoom=12).add(drag_marker)
    data_map = reactive.Value(Map(center=center, zoom=11))
    hover_details = reactive.Value("")

    suggestion_id = reactive.Value(None) 
    session_id = str(uuid4())

    @render.table
    def aqi_ranges():
        return aqi_table
    
    @render.image 
    def clarity():
        img: ImgData = {"src": str("assets/clarity_s_node.png"), "width": "50%"}
        return img  
    
    @render.image
    def logo():
        img: ImgData = {"src": str("assets/chicagoaqi.png"), "width": "100%"}
        return img
                
    @reactive.effect 
    @reactive.event(input.btn_use_location)
    def _():
        ui.insert_ui(
            ui.include_js('locate.js'),
            selector = "#map",
            where = "afterEnd"
        )
        if input.lat() is not None:
            mark_user_location()
    
    @reactive.effect 
    @reactive.event(input.btn_submit)
    def _():

        if drag_marker.visible:
            suggested_location = drag_marker.location 
        elif search_marker.visible:
            suggested_location = search_marker.location 
        
        suggestion_id.set(str(uuid4()))

        query = """
            INSERT INTO chicago_aqi.suggested_locations(id, session_id, lat, long, label, reason, time_submitted)
            VALUES(@suggestion_id, @session_id, @lat, @long, @label, @reason, CURRENT_TIMESTAMP);
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("suggestion_id", "STRING", suggestion_id()),
                bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
                bigquery.ScalarQueryParameter("lat", "FLOAT64", suggested_location[0]),
                bigquery.ScalarQueryParameter("long", "FLOAT64", suggested_location[1]),
                bigquery.ScalarQueryParameter("label", "STRING", input.suggested_label()),
                bigquery.ScalarQueryParameter("reason", "STRING", input.reason()),
            ]
        )
        query_job = bq.query(query, job_config=job_config)  # Make an API request.

        m = get_modal(
            title="Thank you!",
            prompt=ui.TagList(
                ui.p("Do you want to get updates about city air monitoring from Neighbors For Environmental Justice?"),
                ui.input_text(id="email_address", label="Email address", width="100%")
            ),
            buttons = [ui.modal_button("No thanks"), ui.input_action_button("email_signup", "Sign me up!")]
        )
        ui.modal_show(m)
    
    @reactive.effect 
    @reactive.event(input.email_signup)
    def _():

        ui.modal_remove()

        query = """
            INSERT INTO chicago_aqi.email_list(session_id, suggestion_id, email, time_submitted)
            VALUES(@session_id, @suggestion_id, @email, CURRENT_TIMESTAMP);
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
                bigquery.ScalarQueryParameter("suggestion_id", "STRING", suggestion_id()),
                bigquery.ScalarQueryParameter("email", "STRING", input.email_address()),
            ]
        )
        
        job = bq.query(query, job_config=job_config) 


    def mark_user_location():
        user_location = (input.lat(), input.long())
        drag_marker.location = user_location 
        the_map.center = user_location 
        the_map.zoom = 17 

    @reactive.effect
    @reactive.event(input.geolocation)
    def _():
        print(input.lat(), input.long())
        mark_user_location()

    def on_found(**kwargs):
        # Print the result of the search (text, location etc)
        print(kwargs)
        drag_marker.visible = False
        search_marker.visible = True 
        search_marker.location = kwargs['location']

    def handle_click(**kwargs):
        if kwargs.get('type') == 'click':
            drag_marker.visible = True 
            search_marker.visible = False 
            drag_marker.location=kwargs.get('coordinates')
            

    the_map.on_interaction(handle_click)

    @render_widget  
    def map():
        search = SearchControl(
                position="topleft",
                url='https://nominatim.openstreetmap.org/search?format=json&q={s}',
                zoom=17,
                marker=search_marker
        )
        the_map.add(search)
        search.on_location_found(on_found)
        return the_map
    
    def update_html(feature, **kwargs):
        print(feature["properties"]["name"])
        hover_details.set(feature["properties"]["name"])

    @render.code
    def explore_details():
        return hover_details()

    @render_widget
    def explore_data():
        search = SearchControl(
                position="topleft",
                url='https://nominatim.openstreetmap.org/search?format=json&q={s}',
                zoom=17,
                marker=search_marker
        )
        explore_map = data_map()
        explore_map.add(search)
        search.on_location_found(on_found)

        control = LayersControl(position='topright')
        explore_map.add(control)

        data_layers = [
            {
                "label": "Industrial corridors", 
                "filename": "Boundaries - Industrial Corridors (current).geojson", 
                "style": {
                    "color": "red", 
                    "fillOpacity": 0.25
                }
            },
            {
                "label": "Community areas", 
                "filename": "Boundaries - Community Areas (current).geojson", 
                "style": {"color": "blue"}
            }
            
        ]


        for dl in map_layers:
            # ml = get_map_layer(filename=dl['filename'], style_overrides=dl['style'])
            ml = get_map_layer(filename=dl['filename'], style_overrides=dl['style'])
            ml.name = dl['label']
            explore_map.add(ml)
            ml.on_hover(update_html)

        data_map.set(explore_map)
        return data_map()

    @reactive.effect
    @reactive.event(input.marker_coordinates)
    def _():
        if drag_marker.visible:
            print("Drag marker: ", drag_marker.location)
        elif search_marker.location is not None: 
            print("Search marker: ", search_marker.location)

    def get_modal(title:str|None = None, prompt:str|ui.TagList|None = None, buttons:list = [], size = "m", easy_close=False):
        ui.modal_remove()
        return ui.modal(
            prompt, 
            title=title,
            size=size,
            footer=ui.TagList([b for b in buttons]) if len(buttons) > 0 else None,
            easy_close = False if len(buttons) > 0 else True
        )

app = App(app_ui, server)
    