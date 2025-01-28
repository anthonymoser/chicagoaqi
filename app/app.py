from datetime import datetime 
from ipyleaflet import AwesomeIcon, GeoJSON, Map, Marker, SearchControl, LayersControl, LayerGroup, WidgetControl
import ipyleaflet
from shiny import App, ui, render, reactive 
from shiny.types import ImgData
from shinywidgets import output_widget, render_widget, register_widget  
import branca 
import json
from uuid import uuid4 
import pandas as pd 
from map_util import map_layer_config as mlc, MapLayer, locate_point
import base64 
import io 
import copy 

from google.cloud import bigquery 
import os 

# try:
    # bq = bigquery.Client()                              
# except Exception as e:
#     print(e)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'cloud_function_invoker.json'
bq = bigquery.Client()                              
aqi_table = pd.read_csv('data/aqi_table.csv')

ej_indices = {
        "exposure": ['PM25', 'OZONE', 'DIESEL', 'CANCER', 'TRELEASES','TRAFFIC', 'HINDEX', 'LEAD'],
        "conditions": ['FREIGHT','TRI','RMP','PSITES','HWASTE','WATER','CONFACILITIES'], 
        "ses_factors": [ 'PEOPLEOFCOLOR','NOINSURANCE','HOUSING', 'LOWINCOME', 'HIGHSCHOOL','UNEMPLOYMENT','LINGISOLATION'],
        "sensitive_pop": ['CHD','ASTHMA','DISABILITY','YOUNG','OLD','LBW'], 
        "index_totals": ["ENV_EXPOSURES", "ENV_CONDITIONS", "POLLUTION_BURDEN", "POLLUTION_BURDEN_SCORE", "SES_FACTORS", "SENSITIVE_POP", "POP_CHARACTERISTICS", "POP_CHARACTERISTICS_SCORE", "CEJI_SCORE"]
}

ej_index_choices = {
    "Environmental Exposures": {
        "PM25": "Particulate Matter 2.5 (PM2.5)",
        "OZONE": "Ozone",
        "DIESEL": "Diesel Particulate Matter",
        "CANCER": "Air Toxics Cancer Risk",
        "TRELEASES": "Toxic Releases",
        "TRAFFIC": "Traffic Proximity and Volume",
        "HINDEX": "Air Toxics All-Organ Hazard Index",
        "LEAD": "Childhood Lead Poisoning",
    },
    "Environmental Conditions": {
        "FREIGHT": "Freight Rail Lines",
        "TRI": "TRI Facilities",
        "RMP": "Risk Management (RMP) Sites",
        "PSITES": "Polluted Sites",
        "HWASTE": "Hazardous Waste Facilities",
        "WATER": "Wastewater Discharge",
        "CONFACILITIES": "Consequential Facilities",
    },
    "Socioeconomic Factors": {
        "PEOPLEOFCOLOR": "People of Color",
        "NOINSURANCE": "No Health Insurance",
        "HOUSING": "Housing Burdened, Low Income Households",
        "LOWINCOME": "Low Income",
        "HIGHSCHOOL": "Less than High School Education",
        "UNEMPLOYMENT": "Unemployment",
        "LINGISOLATION": "Linguistic Isolation",
    },
    "Sensitive Populations": {
        "CHD": "Coronary Heart Disease",
        "ASTHMA": "Asthma",
        "DISABILITY": "Disability",
        "YOUNG": "Young ( <18 )",
        "OLD": "Old ( 65+ )",
        "LBW": "Low Birthweight",
    },
    "Environmental Indicator Averages": {
        "ENV_EXPOSURES": "Environmental Exposure Average", 
        "ENV_CONDITIONS": "Environmental Conditions Average",
        "POLLUTION_BURDEN": "Pollution Burden Average",
    },
    "Population Indicator Averages": {
        "SES_FACTORS": "Socioeconomic Factor Average", 
        "SENSITIVE_POP": "Sensitive Population Average", 
        "POP_CHARACTERISTICS": "Population Characteristics Average"
    },
    "EJ Index Score Totals": {
        "POLLUTION_BURDEN_SCORE": "Pollution Burden Score",
        "POP_CHARACTERISTICS_SCORE": "Population Characteristics Score", 
        "CEJI_SCORE": "Chicago EJ Index Score"
    }
}

eji_fields = pd.read_csv('data/ceji_field_key.csv')
eji_field_labels = dict(zip(eji_fields.var_name.to_list(), eji_fields.readable_name.to_list()))
eji_field_labels_reversed = dict(zip(eji_fields.readable_name.to_list(), eji_fields.var_name.to_list()))

app_ui = ui.page_auto( 
    ui.output_image("logo", inline=True),
    ui.div( ui.help_text("a tool from Neighbors For Environmental Justice"), id="attribution", style="text-align: right;"),
    # ui.input_select( id="language_choice", label='Language', choices=["English", "Español", "中文"], selected="English", width="120px"),
    ui.navset_card_underline(

        ui.nav_panel( "Suggest a location",
            ui.div( 
            ui.tags.h4("Where should the air monitors go?"),
            ui.p("As part of a federal agreement, ", ui.tags.b("Chicago promised to install 220 air monitors, "), "mostly in neighborhoods with a lot of pollution."), 
            ui.p(" The city hasn't decided where to put them yet, and we want to make sure they pick useful locations: maybe a place you see kids playing, or trucks idling, or smell something bad."),
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

                     ui.p(ui.tags.b("Who is this tool for? Do I have to be part of N4EJ to use it or share it?")),
                    ui.div(
                        ui.p("This tool is for everyone! You don't have to be part of N4EJ to suggest air monitor locations, or to share this with others. This is just a way for people to learn about their neighborhood and offer feedback."),
                        ui.p("If you have questions or ideas and want to get in touch, email us at info@n4ej.org"),
                        class_="faq_answer"
                    ),

                    ui.p(ui.tags.b("When will the monitors go up?")),
                    ui.div(
                        ui.p("We don't really know."),
                        ui.p("""As of January 2025, the city has signed contracts with a non-profit called the Illinois Public Health Initiative to "help coordinate community engagement and identify members for an advisory group to inform sensor placement." """),
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
                             " in November. Nobody has been hired to replace him, and his projects have not been reassigned to any one staff member."),
                        ui.p("Instead of waiting for the city to act, N4EJ built this tool and we are taking suggestions now."),
                        class_="faq_answer"
                    ),

                    ui.p(ui.tags.b("Why is the city installing air monitors?")),
                    ui.div(
                        ui.p("The air monitors are required by a ", ui.a("federal agreement", href="https://chicago.suntimes.com/2023/5/12/23720343/hud-environmental-racism-lightfoot-general-iron-environmental-justice-housing-urban-development", target="_blank"), " the city signed in 2023."),
                        class_="faq_answer"
                    ), 

                    ui.p(ui.tags.b("How is N4EJ involved?")),
                    ui.div(
                        ui.p("N4EJ is a member of the city's Environmental Equity Working Group. We helped to complete the city's ", ui.a("Cumulative Impacts Assessment", href="https://www.chicago.gov/city/en/depts/cdph/supp_info/Environment/cumulative-impact-assessment.html", target="_blank"),
                             " and co-chaired the assessment's Communications & Engagement Working Group.",),
                        ui.p("It has been challenging to work with the city because Chicago has a long history of environmental racism, and of making promises it does not keep. But we believe these projects are important, and we are committed to seeing them happen. We are also determined to hold the city to its promises."),
                        class_="faq_answer"
                    ), 

                    ui.p(ui.tags.b("Will this make the air better?")),
                    ui.div(
                        ui.p("Data by itself is never enough to change things. Change takes people, and we need your help! Talk with people you know, help us pressure the city and state, and together we can make the air cleaner and safer for everyone."),
                        class_="faq_answer"
                    ), 


                ),    
                id = "accordion_faq",
                open = ["Air monitors"]                       
            ),
            id="faq"
            ),
        ),
        ui.nav_panel("Explore data",
            ui.row(
                ui.layout_columns(
                    ui.card(
                        ui.card_header(
                            ui.input_select(id="index_layers", label="Map shows", choices=ej_index_choices),
                        ),
                        
                        output_widget(id="explore_data"),
                        id = "explore_map_card"
                    ),
                    ui.div(
                        ui.output_code(id="explore_details"),
                        ui.accordion(
                            ui.accordion_panel("About this data",
                                ui.p("This data was compiled by the Chicago Department of Public Health for the city's 2023 Cumulative Impacts Assessment."),
                                ui.p("This ", ui.a("summary", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_MethodologyPoster_Updated-11.14.2023.pdf", target="_blank"),
                                " explains how the EJ Index Score was calculated. ", ui.a("Read more", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_ChicagoEnvironmentalJusticeIndexMethodology_Updated_11.21.2023.pdf", target = "_blank"),
                                " about the data they used, or ", ui.a("download a copy.", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/Chicago-EJ-Index-Values_2023.10.04.xlsx", target="_blank")),
                                ui.download_link("download_suggestions", label = "Download suggested locations"),
                                ui.input_checkbox(id="show_suggestions", label="Show suggestions on map", value=False)
                            ),
                            ui.accordion_panel("Environmental exposure",
                                ui.output_ui("env_exposure")
                            ),
                            ui.accordion_panel("Environmental conditions", 
                                ui.output_ui("env_conditions")
                            ),
                            ui.accordion_panel("Sensitive populations", 
                                ui.output_ui("sensitive_pop")
                            ),
                            ui.accordion_panel("Socioeconomic Factors", 
                                ui.output_ui("ses_factors")
                            ),
                            # ui.accordion_panel("Index Totals", 
                            #     ui.output_ui("index_totals")
                            # )
                            open=['About this data', 'Environmental exposure']
                        ),
                    ),
                    col_widths= (7,5),

                ),
            ),
            
        
        ),
        selected="Suggest a location",
        id="primary_nav"
    ),
    ui.tags.style("""
                  
        .nav .nav-underline {
            background-color: #efefef;
        }
        .points .point { fill: rgb(245, 245, 245); }
                  
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
        .main-svg { width:100%; }
        .strip-plot { width:100%; }
        #explore_map_card .form-group { display: block ruby; }
        """
    ),
    id="page_container"
)

def server(input, output, session):

    with open(f"data/tract_ids.json", "r") as f:
        tract_json = json.load(f)

    ejiv = pd.read_csv('data/ej_index_values.csv')
    center = (41.8228883909135, -87.6771203648879)

    with reactive.isolate():
        drag_marker = Marker(location=center, draggable=True, title="Suggested Location", name="SELECTED POINT")
        search_marker = Marker()
        coordinates = reactive.Value([41.8228883909135, -87.6771203648879])
        census_tract = reactive.Value()
        suggested_locations = reactive.Value()  
        point_details = reactive.Value({})

    map_sequence1 = reactive.value()
    map_sequence2 = reactive.value()
    map_sequence3 = reactive.value()
    map_sequence4 = reactive.value()

    current_choro_layer = reactive.Value()
    explore_map = Map(center=center, zoom=11)

    the_map = Map(center=center, zoom=12).add(drag_marker)
    control = LayersControl(position='topright', collapsed=False, id="layer_control")
    search = SearchControl(
        position="topleft",
        url='https://nominatim.openstreetmap.org/search?format=json&q={s}',
        zoom=17,
        marker=search_marker
    )
    
    print("server initialized")


    @render.image
    def logo():
        img: ImgData = {"src": str("assets/chicagoaqi.png"), "width": "100%"}
        return img
    
    def on_found(**kwargs):
        drag_marker.visible = False
        search_marker.visible = True 
        search_marker.location = kwargs['location']
        # coordinates.set(search_marker.location)

    search.on_location_found(on_found)
    suggestion_id = reactive.Value(None) 
    session_id = str(uuid4())

    @reactive.effect
    @reactive.event(input.show_suggestions)
    def _():
        try:
            if input.show_suggestions() is True:
                get_suggestions()

            # if input.show_suggestions() is False:
            #     for lay in explore_map.layers:
            #         if lay.name == "Suggestions":
            #             explore_map.remove(lay)
        except Exception as e:
            print("Error with suggestions layer")
            print(e)


    @reactive.effect # Explore data choropleth layers
    @reactive.event(input.index_layers)
    def _():
        print(input.index_layers())
        if input.primary_nav == "Explore data": 
            
            replace = None
            try:
                for lay in explore_map.layers:
                    if lay.name in eji_fields.readable_name.to_list():
                        print(f"Layer to replace: {lay.name}")
                        replace = lay   
            except Exception as e:
                print(e)
                print("Failed to identify old choro layer to replace")
            
            try:
                if replace is not None:
                    print("swapping layers")                
                    # print(replace)
                    explore_map.substitute(replace, layer)
                else:
                    explore_map.add(layer)
            except Exception as e:
                print(f"Failed to substitute choro layer: {e}")

    
    def handle_click(**kwargs):
        if kwargs.get('type') == 'click':
            drag_marker.visible = True 
            search_marker.visible = False 
            drag_marker.location=kwargs.get('coordinates')
            if(input.primary_nav()) == "Explore data":
                coordinates.set(drag_marker.location)

    the_map.on_interaction(handle_click)
    explore_map.on_interaction(handle_click)

    def get_ej_pctile(tract_id, category):
        try:
            tract_pct = float(ejiv[ejiv.measure == f"{category}_PCTILE"].pipe(lambda df: df[df.GEOID == tract_id])['value'].squeeze())
            if tract_pct <= 1:
                tract_pct = round(tract_pct * 100,2)
            return tract_pct 
        except Exception as e:
            pass
    
    def get_ej_header_row(label):
            return f"""
                    <table class="ej_index_table" style="font-size: small; ">
                        <tr style="border-bottom: #dfdfdf 1px solid;">
                            <th>{label}</th>
                            <th>Percentile</th>
                            <th></th>
                        </tr>
                """

    def get_ej_index_row(measure):
        pctile = get_ej_pctile(census_tract(), measure)
        img_src = f"{census_tract()}_{measure}.svg"
        with open(f"assets/ej/{img_src}.png", 'rb') as image_file:
            base64_bytes = base64.b64encode(image_file.read())
            base64_string = base64_bytes.decode()
        
        # ui.tooltip(
        #         ui.span("Card title ", question_circle_fill),
        #         "Additional info",
        #         placement="right",
        #         id="card_tooltip",
        #     ).get_html_string()
                    
        
        table_row = f"""
        <tr style="border-bottom: #dfdfdf 1px solid;">
            <td>{eji_field_labels.get(measure, measure)} </td>
            <td style="text-align: center;">{pctile}</td>
            <td><img src="data:image/png;base64,{base64_string}" class="strip-plot" ></td>
        </tr>
        """
        return table_row

    @render.ui 
    def env_exposure():
        if census_tract() is not None:
            table = get_ej_table(ej_indices['exposure'], "")
        return ui.HTML(table)
    
    @render.ui 
    def env_conditions():
        if census_tract() is not None:
            table = get_ej_table(ej_indices['conditions'], "")
        return ui.HTML(table)
    
    @render.ui 
    def sensitive_pop():
        if census_tract() is not None:
            table = get_ej_table(ej_indices['sensitive_pop'], "")
        return ui.HTML(table)
    
    @render.ui 
    def ses_factors():
        if census_tract() is not None:
            table = get_ej_table(ej_indices['ses_factors'], "")
        return ui.HTML(table)
    
    @render.ui 
    def index_totals():
        if census_tract() is not None:
            table = get_ej_table(ej_indices['index_totals'], "")
        return ui.HTML(table)
    
    def get_ej_table(measures:list, label:str):
        table = get_ej_header_row(label)
        for measure in measures:
            table += get_ej_index_row(measure)
        table += "</table>"
        return table 

    @reactive.effect 
    # @reactive.event(coordinates)
    def _():
        print("Coordinates: ", coordinates())
        if input.primary_nav() == "Explore data":
            new_details = {}
            for ml in mlc:
                print(f"locating point in {mlc[ml].label}")
                area = locate_point(lat = [ coordinates()[0] ], long = [ coordinates()[1] ], bounds = mlc[ml].gdf)
                print("located")
                if area:
                    new_details[mlc[ml].point_label] = area 

            if 'Census tract' in new_details:
                census_tract.set(new_details['Census tract'])

            point_details.set(new_details)

    @render.table
    def aqi_ranges():
        return aqi_table
    
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
    
    def get_suggestions():
        
        query = "SELECT lat, long, label, reason, datetime(time_submitted, 'America/Chicago') as time_submitted, session_id FROM chicago_aqi.suggested_locations"
        result = bq.query(query).to_dataframe()

        layer_group = LayerGroup()
        icon = AwesomeIcon(
            name='circle',
            marker_color='gray',
            # icon_color='black',
            spin=False
        )
        for r in result.to_dict('records'):
            spot = Marker(
                location=(r['lat'], r['long']),
                icon=icon,
                opacity=.5,
                draggable=False, 
            )

            layer_group.add(spot)
        layer_group.name = "Suggestions"
        explore_map.add(layer_group)
        suggested_locations.set(result)


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
                ui.p("Your suggestion has been submitted. (Feel free to suggest more locations)"),
                ui.p("Do you want to get updates about city air monitoring from Neighbors For Environmental Justice?"),
                ui.input_text(id="email_address", label="Email address", width="100%")
            ),
            buttons = [ui.modal_button("No thanks"), ui.input_action_button("email_signup", "Sign me up!")]
        )
        ui.modal_show(m)
        ui.update_checkbox("show_suggestions", value=True)
        ui.update_navs("primary_nav", selected="Explore data")
    
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
        # coordinates.set(drag_marker.location) 

        the_map.center = user_location 
        the_map.zoom = 17 

    @reactive.effect
    @reactive.event(input.geolocation)
    def _():
        print(input.lat(), input.long())
        mark_user_location()

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
    
    @render.code
    def explore_details():
        details = ""
        for key in point_details():
            details+= f"{key}: {point_details()[key]}\n"
        return details


    def is_feature_selected(feature):
        if 'GEOID' in feature['properties']:
            if feature['properties']['GEOID'] == census_tract():
                print("SELECTED TRACT!!!")
                return {
                    'fillOpacity': .1,
                    'color': "black",
                    'weight':3
                    }
            else:
                return {
                    'fillOpacity': 0,
                    'color': "black",
                    'weight':.1
                    }
        
    def get_map_layer(layer_name:str, filename:str, style_overrides:dict = {}):
        print(f"Getting map layer: {filename}")
        with open(f"data/{filename}", "r") as f:
            boundaries = json.load(f)
        
        layer = GeoJSON(  
            data=boundaries,  
            style=style_overrides,
            style_callback = is_feature_selected
        )  
        layer.name = layer_name
        return layer


    @reactive.effect
    @reactive.event(input.primary_nav, input.index_layers)
    def get_choro_layer():
        if input.primary_nav() == "Explore data": 
            
            for layer in explore_map.layers:
                # if layer.name != "OpenStreetMap.Mapnik":
                    # explore_map.remove(layer)
                if layer.name in eji_field_labels.values():
                    explore_map.remove(layer) 

            choro_data = dict(zip(ejiv['GEOID'].astype('str').to_list(), ejiv[ejiv.measure == input.index_layers()]['value'].astype('float').to_list()))
            choro_layer = ipyleaflet.Choropleth(
                id = "choro_layer",
                geo_data=tract_json,
                choro_data=choro_data,
                colormap=branca.colormap.LinearColormap(
                    colors = ['white', 'yellow', 'orange', 'red'], 
                ),
                border_color='black',
                style={
                    'fillOpacity': 0.6, 
                    'weight':.2
            })
            choro_layer.name = eji_field_labels[input.index_layers()]
            explore_map.add(choro_layer)
            current_choro_layer.set(choro_layer.name)
            
            try:
                explore_map.substitute(control, control)
            except Exception:
                explore_map.add(control)

    @reactive.effect 
    @reactive.event(input.primary_nav, input.index_layers)
    def get_corridors():
        if input.primary_nav() == "Explore data":
            explore_map_layers = [layer.name for layer in explore_map.layers]
            if "Industrial corridors" not in explore_map_layers:
                explore_map.add(get_map_layer(
                            layer_name = mlc['corridors'].label,
                            filename = mlc['corridors'].filename, 
                            style_overrides = mlc['corridors'].style
                        ), index=1
                )
                     
    @reactive.effect 
    @reactive.event(current_choro_layer)
    def get_communities():
        if input.primary_nav() == "Explore data":
            explore_map_layers = [layer.name for layer in explore_map.layers]
            if "Community areas" not in explore_map_layers:
                explore_map.add(get_map_layer(
                            layer_name = mlc['communities'].label,
                            filename = mlc['communities'].filename, 
                            style_overrides = mlc['communities'].style
                        ), index = 1
                )

    @reactive.effect 
    @reactive.event(census_tract)
    def get_tracts():
        if input.primary_nav() == "Explore data":
            explore_map_layers = [layer.name for layer in explore_map.layers]
            print(explore_map_layers)
            for layer in explore_map.layers:
                if layer.name == "Census tracts":
                    explore_map.remove(layer) 
            
            explore_map.add(
                get_map_layer(
                    layer_name = mlc['tracts'].label,
                    filename = mlc['tracts'].filename, 
                    style_overrides = mlc['tracts'].style
                )
            )
    
    @render_widget
    def explore_data():
        return explore_map    


    def get_modal(title:str|None = None, prompt:str|ui.TagList|None = None, buttons:list = [], size = "m", easy_close=False):
        ui.modal_remove()
        return ui.modal(
            prompt, 
            title=title,
            size=size,
            footer=ui.TagList([b for b in buttons]) if len(buttons) > 0 else None,
            easy_close = True
        )

    @render.download(filename=f"chicagoaqi_suggested_locations_{datetime.now().strftime("%Y%m%d")}.csv" )
    def download_suggestions():        
        with io.BytesIO() as buf:
            # df = bq.query("SELECT lat, long, label, reason, datetime(time_submitted, 'America/Chicago') as time_submitted, session_id FROM chicago_aqi.suggested_locations").to_dataframe()
            # print(f"Retrieved {len(df)} suggestions")
            print(len(suggested_locations()))
            suggested_locations().to_csv(buf, index=False)
            # df
            yield buf.getvalue()

app = App(app_ui, server)
    