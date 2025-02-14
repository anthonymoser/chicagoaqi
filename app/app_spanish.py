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
from map_util import map_layer_config_spanish as mlc, MapLayer, locate_point
import base64 
import io 
import requests 

from google.cloud import bigquery 
import os 

# try:
    # bq = bigquery.Client()                              
# except Exception as e:
#     print(e)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'cloud_function_invoker.json'
bq = bigquery.Client()                              
aqi_table = pd.read_csv('data/aqi_table_spanish.csv')

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
    ui.a(ui.output_image("logo", inline=True), href="/"),
    ui.div( ui.help_text("una herramienta de Neighbor for Environmental Justice (Vecinos por la Justicia Ambiental)"), id="attribution", style="text-align: right;"),
    
    ui.navset_card_underline(

        # ui.nav_panel( "Suggest a location",
        ui.nav_panel( "Sugerir una ubicación",
            ui.div( 
            # ui.tags.h4("Where should the air monitors go?"),
            ui.tags.h4("¿Dónde deberían colocarse los monitores de aire?"),
            # ui.p("As part of a federal agreement, ", ui.tags.b("Chicago promised to install 220 air monitors, "), "mostly in neighborhoods with a lot of pollution."), 
            ui.p("Como parte de un acuerdo federal, ", ui.tags.b("Chicago prometió instalar 220 monitores de aire, "), "principalmente en vecindarios con mucha contaminación."), 
            # ui.p(" The city hasn't decided where to put them yet, and we want to make sure they pick useful locations: maybe a place you see kids playing, or trucks idling, or smell something bad."),
            ui.p(" La ciudad aún no ha decidido dónde colocarlos, y queremos asegurarnos de que elijan ubicaciones apropiadas: tal vez un lugar donde veas niños jugando, camiones con el motor encendido o donde huela mal."),
            # ui.p("Where do you think they should go?"),
            ui.p("¿Dónde crees que deberían colocarse?"),
            
            output_widget(id = "map"),
            ui.row(
                ui.layout_column_wrap(
                    ui.card(
                        # ui.card_header("1. PICK A SPOT ON THE MAP"),
                        ui.card_header("1. ELIGE UN LUGAR EN EL MAPA"),
                        # ui.tags.p("There are four ways to choose:"), 
                        ui.tags.p("Hay cuatro formas de elegir:"), 
                        ui.tags.ul(
                            # ui.tags.li("Click on the map"),
                            ui.tags.li("Haz clic en el mapa"),
                            # ui.tags.li("Drag the marker"),
                            ui.tags.li("Mueve el marcador"),
                            # ui.tags.li("Find your current location"),
                            ui.tags.li("Encuentra tu ubicación actual"),
                            # ui.tags.li(ui.TagList("Search for an address")),
                            ui.tags.li(ui.TagList("Busca una dirección")), 
                            ui.input_text(id="address_lookup", label=""),
                            # ui.input_action_button(id="btn_address_lookup", label="Search")
                            ui.input_action_button(id="btn_address_lookup", label="Busca")
                        ),
                        # ui.card_footer(ui.input_action_button("btn_use_location", label="Find my location", width="100%"),)
                        ui.card_footer(ui.input_action_button("btn_use_location", label="Buscar mi ubicación", width="100%"),)
                    ),
                    ui.card(
                        # ui.card_header("2. TELL US ABOUT IT (optional)"),
                        ui.card_header("2.CUÉNTENOS (opcional)"),
                        # ui.input_text(id="suggested_label", label="What would you call this spot?", width="100%", placeholder="example: McKinley Park / MAT Asphalt / the playground"),
                        ui.input_text(id="suggested_label", label="¿Qué nombre le pondría a este lugar?", width="100%", placeholder = "ej. McKinley Park, MAT Asphalt, la escuela"),
                        # ui.input_text_area(id="reason", label="Why put an air monitor there?", width="100%", placeholder="example: I live nearby / it always smells bad"),
                        ui.input_text_area(id="reason", label="¿Por qué poner un monitor de aire allí?", width="100%", placeholder="ej. cerca de un parque, hay niños que juegan aquí, hay muchas tiendas locales allá"),
                        # ui.card_footer(ui.input_action_button("btn_submit", label="Submit", width="100%"))
                        ui.card_footer(ui.input_action_button("btn_submit", label="Enviar", width="100%"))
                    ),
                ),
                ),
            ),
        ),
        ui.nav_panel( "Por qué lo estamos haciendo", # Why we're doing this
            ui.div( 
            ui.accordion(
                ui.accordion_panel( "Monitores de aire", # Air monitors
                    ui.p(ui.tags.b("¿Por qué necesitamos monitores de aire?")), #Why do we need air monitors?
                    ui.tags.ul(
                        # ui.tags.li("In Chicago, how much pollution you breathe depends a lot on where you live"),
                        ui.tags.li("En Chicago, cuánta contaminación respira depende mucho de dónde vive"),
                        # ui.tags.li("Air monitors help us know what we're breathing"),
                        ui.tags.li("Los monitores de aire nos ayudan a saber qué estamos respirando"), 
                        # ui.tags.li("On days with the worst air pollution, we can take actions to stay safe, like running air filters and wearing masks"),
                        ui.tags.li("En los días con peor contaminación del aire, podemos tomar medidas para mantenernos a salvo, como correr los filtros de aire y usar máscaras"),
                        # ui.tags.li("We can use this data to push the city to take action"),
                        ui.tags.li("Podemos usar estos datos para presionar a la ciudad para que tome medidas")
                         ),
                    # ui.p(ui.tags.b("Does it matter where they go?")),
                    ui.p(ui.tags.b("¿Importa dónde los pongan?")),
                    ui.tags.ul(
                        # ui.tags.li("Yes! Air monitors can only measure what's nearby"), 
                        ui.tags.li("¡Sí! Los monitores de aire solo pueden medir lo que está cerca"), 
                        # ui.tags.li("Depending on weather and nearby sources of pollution, even a few blocks can make a big difference"),
                        ui.tags.li("Dependiendo del clima y de las fuentes de contaminación cercanas, incluso unas pocas cuadras pueden hacer una gran diferencia"),
                        # ui.tags.li("The places that have the most pollution in Chicago (South and Southwest Chicago) do not have air monitors installed by the government to measure the air quality")
                        ui.tags.li("Los lugares que tienen más contaminación en Chicago (sur y suroeste de Chicago) no tienen monitores de aire instalados por el gobierno para medir la calidad del aire")
                    ),
                    # ui.p(ui.tags.b("What kind of air monitors are they?")),
                    ui.p(ui.tags.b("¿Qué tipo de monitores de aire son?")),
                    ui.tags.ul( 
                        # ui.tags.li(ui.a("Clarity Node-S monitors", href="https://www.clarity.io/products/clarity-node-s"), target="_blank"),
                        ui.tags.li(ui.a("Monitores Clarity Node-S", href="https://www.clarity.io/products/clarity-node-s"), target="_blank"),
                        # ui.tags.li("They use solar panels, and will be installed on light poles"),
                        ui.tags.li("Utilizan paneles solares y se instalarán en postes de luz"),
                        # ui.tags.li("They measure particulate matter (PM) and nitrogen dioxide (NO₂)"),
                        ui.tags.li("Miden las partículas en suspensión (PM) y el dióxido de nitrógeno (NO₂)"),
                        # ui.tags.li("They will upload data to a public dashboard"),
                        ui.tags.li("Los datos se subirán a un panel de control público")
                    ),
                    # ui.p(ui.tags.b("Doesn't the city have air monitors already?")),
                    ui.p(ui.tags.b("¿No tiene la ciudad ya monitores de aire?")),
                    ui.tags.ul(
                        # ui.tags.li("There are only a few government-owned air monitors in or near Chicago"),
                        ui.tags.li("Solo hay unos pocos monitores de aire propiedad del gobierno en Chicago o cerca de ella"),
                        # ui.tags.li("They're mostly not owned by the city, and mostly not in neighborhoods with the worst pollution"),
                        ui.tags.li("La mayoría no son propiedad de la ciudad y la mayoría no están en los vecindarios con peor contaminación"),
                        # ui.tags.li("A study found the US EPA puts more air monitors", ui.a(" in white neighborhoods", href="https://www.theguardian.com/environment/2024/dec/14/epa-air-quality-monitors-white-neighborhoods", target="_blank")),
                        ui.tags.li("Un estudio descubrió que la EPA de EE. UU. ", ui.a(" pone más monitores de aire en los vecindarios blancos", href="https://www.theguardian.com/environment/2024/dec/14/epa-air-quality-monitors-white-neighborhoods", target="_blank")),
                        # ui.tags.li("You can see readings from the ", ui.a("six Illinois EPA monitors", href="https://www.airnow.gov/?city=Chicago&state=IL&country=USA", target="_blank")),
                        ui.tags.li("Puedes ver las lecturas de los ", ui.a("seis monitores de la EPA de Illinois ", href="https://www.airnow.gov/?city=Chicago&state=IL&country=USA", target="_blank")),
                        # ui.tags.li("Community groups and residents have also put up air monitors ", ui.a("on their own", href="https://map.purpleair.com/air-quality-standards-us-epa-aqi?opt=%2F1%2Flp%2Fa0%2Fp604800%2FcC0#10.6/41.8697/-87.674", target="_blank"))
                        ui.tags.li("Los grupos comunitarios y los residentes ", ui.a("también han instalado monitores de aire", href="https://map.purpleair.com/air-quality-standards-us-epa-aqi?opt=%2F1%2Flp%2Fa0%2Fp604800%2FcC0#10.6/41.8697/-87.674", target="_blank"))
                    )

                ),                    
                # ui.accordion_panel( "Pollution",
                ui.accordion_panel( "Contaminación", 
                    # ui.p(ui.tags.b("What is air pollution?")),
                    ui.p(ui.tags.b("¿Qué es la contaminación del aire?")),
                    ui.tags.ul(
                        # ui.tags.li("Pollution is tiny bits of stuff we inhale when we breathe"), 
                        ui.tags.li("La contaminación son pequeñas partículas que inhalamos cuando respiramos."), 
                        # ui.tags.li("It can be made of gases, or tiny particles that are 100 times thinner than a human hair"),
                        ui.tags.li("Puede estar formada por gases o partículas diminutas que son 100 veces más finas que un cabello humano."),
                        # ui.tags.li("Sometimes you can smell, see, or feel pollution, but mostly we don’t know what we’re breathing")
                        ui.tags.li("A veces podemos oler, ver o notar la contaminación, pero la mayoría de las veces no sabemos que lo estamos respirando.")
                    ),
                    # ui.p(ui.tags.b("Where does air pollution come from?")),
                    ui.p(ui.tags.b("¿De dónde viene la contaminación del aire?")),
                    ui.tags.ul(
                        # ui.tags.li("Transportation: cars, trucks, and trains"), 
                        ui.tags.li("Transporte: coches, camiones y trenes."), 
                        # ui.tags.li("Industry: factories, asphalt plants, construction equipment and diesel vehicles"),
                        ui.tags.li("Industria: fábricas, plantas de asfalto, equipos de construcción y vehículos diésel"),
                        # ui.tags.li("Natural sources: smoke from wildfires, dust blown by the wind"),
                        ui.tags.li("Fuentes naturales: humo de incendios forestales, polvo que corre por el viento"),
                        # ui.tags.li("In Chicago, city policies put pollution in communities of color and low-income communities."),
                        ui.tags.li("En Chicago, las decisiones políticas de la ciudad han provocado que la contaminación afecte principalmente a comunidades de color y de bajos ingresos."),
                        # ui.tags.li("This practice is called environmental racism"),
                        ui.tags.li("Esta práctica está motivada por el racismo medioambiental"),
                        # ui.tags.li("These new air monitors are part of an contract signed by the city promising to address environmental racism"),
                        ui.tags.li("Estos nuevos monitores de aire son parte de un contrato firmado por la ciudad que promete abordar el racismo medioambiental"),
                    ),
                    # ui.p(ui.tags.b("How bad is it for your health?")),
                    ui.p(ui.tags.b("Cómo afecta a la salud")),
                    ui.tags.ul(
                        # ui.tags.li("It makes existing health problems worse"), 
                        ui.tags.li("Empeora los problemas de salud existentes"), 
                        # ui.tags.li("It causes new health problems, like asthma, headaches, and chest pain"),
                        ui.tags.li("Causa nuevos problemas de salud, como asma, dolores de cabeza y dolor en el pecho."),
                        # ui.tags.li("The combined effect of of outdoor air pollution and indoor air pollution ", ui.a("kills about 6.7 million people", href="https://www.who.int/news-room/fact-sheets/detail/ambient-(outdoor)-air-quality-and-health", target="_blank"), " around the world every year."),
                        ui.tags.li("El efecto combinado de la contaminación del aire exterior y la contaminación del aire interior ", ui.a("mata a unos 6.7 millones de personas", href="https://www.who.int/news-room/fact-sheets/detail/ambient-(outdoor)-air-quality-and-health", target="_blank"), " en todo el mundo cada año."),
                    ),
                    # ui.p(ui.tags.b("How is air pollution measured?")),
                    ui.p(ui.tags.b("¿Cómo se mide la contaminación del aire?")),
                    ui.tags.ul(
                        # ui.tags.li("Different sensors detect different types of air pollution. Most air monitors measure one or two"), 
                        ui.tags.li("Diferentes sensores detectan diferentes tipos de contaminación del aire. La mayoría de los monitores de aire miden uno o dos."), 
                        # ui.tags.li("The most common air monitors measure particulate matter (PM 2.5), a mixture of the tiny things that get into your lungs when you breathe"),
                        ui.tags.li("Los monitores de aire más comunes miden las partículas en suspensión (PM 2.5), una mezcla de las cosas diminutas que pueden llegar a los pulmones cuando se respira."),
                        # ui.tags.li("PM 2.5 is counted in micrograms per cubic meter of air (µg/m³) "),
                        ui.tags.li("Las PM 2.5 se cuentan en microgramos por metro cúbico de aire (µg/m³)"),
                    ),
                    # ui.p(ui.tags.b("How can you tell when the air quality is bad?")),
                    ui.p(ui.tags.b("¿Cómo se sabe si la calidad del aire es mala?")),
                    ui.tags.ul(
                        # ui.tags.li("There is no safe level of air pollution"),
                        ui.tags.li("No existe un nivel seguro de contaminación atmosférica"),
                        # ui.tags.li("To make air quality easier to understand, the US EPA uses PM2.5 readings to calculate the Air Quality Index (AQI)"),
                        ui.tags.li("Para que la calidad del aire sea más sencilla de entender, la EPA de EE. UU. utiliza las lecturas de PM2.5 para calcular el Índice de Calidad del Aire (AQI, por sus siglas en inglés)."),
                        # ui.tags.li("AQI is a scale that goes from zero (no pollution) to 500 (extremely high amounts of pollution)"),
                        ui.tags.li("El AQI es una escala que va de cero (sin contaminación) a 500 (cantidades extremadamente altas de contaminación)."),
                        # ui.tags.li("People from “sensitive groups” (children, the elderly, or people with heart and lung conditions) should often stay inside if the AQI is high")
                        ui.tags.li("Las personas de “grupos sensibles” (niños, ancianos o personas con afecciones cardíacas y pulmonares) deben permanecer en el interior si el AQI es alto.")
                    ),
                    ui.output_table("aqi_ranges")
                ),
                # ui.accordion_panel( "About this project",
                ui.accordion_panel( "Acerca de este proyecto",
                                   
                    # ui.p(ui.tags.b("What will happen to the suggestions people submit?")),
                    ui.p(ui.tags.b("¿Qué pasará con las sugerencias que envíen las personas?")),
                    ui.div(
                        # ui.p("Neighbors For Environmental Justice (",ui.a("N4EJ", href="http://n4ej.org", target="_blank"),") is collecting this data."),
                        ui.p("Neighbors For Environmental Justice (",ui.a("N4EJ", href="http://n4ej.org", target="_blank"),") está recopilando estos datos."),
                        # ui.p("Suggestions are public as soon as they are submitted (you can see them on the 'Explore the data' page). N4EJ will share them with the Department of Public Health, which has the final say on where monitors are installed."),
                        ui.p("Las sugerencias son públicas tan pronto como se envían (puedes verlas en la página “Explorar los datos”). N4EJ las compartirá con el Departamento de Salud Pública, cuál tiene la última palabra sobre dónde se instalan los monitores."),
                        class_="faq_answer"
                    ),

                    # ui.p(ui.tags.b("Who is this tool for? Do I have to be part of N4EJ to use it or share it?")),
                    ui.p(ui.tags.b("¿Para quién es esta herramienta? ¿Tengo que ser parte de N4EJ para usarla o compartirla?")),
                    ui.div(
                        # ui.p("This tool is for everyone! You don't have to be part of N4EJ to suggest air monitor locations, or to share this with others. This is just a way for people to learn about their neighborhood and offer feedback."),
                        ui.p("¡Esta herramienta es para todos! No tienes que ser parte de N4EJ para sugerir ubicaciones de monitores de aire o para compartir esto con otros. Esta es una manera en la que las personas pueden aprender sobre su vecindario y ofrecer comentarios."),
                        # ui.p("If you have questions or ideas and want to get in touch, email us at info@n4ej.org"),
                        ui.p("Si tienes preguntas o ideas y quieres ponerte en contacto, envíanos un correo electrónico a info@n4ej.org"),
                        class_="faq_answer"
                    ),

                    # ui.p(ui.tags.b("When will the monitors go up?")),
                    ui.p(ui.tags.b("¿Cuándo se instalarán los monitores?")),
                    ui.div(
                        # ui.p("We don't really know."),
                        ui.p("La verdad es que no lo sabemos."),
                        # ui.p("""As of January 2025, the city has signed contracts with a non-profit called the Illinois Public Health Initiative to "help coordinate community engagement and identify members for an advisory group to inform sensor placement." """),
                        ui.p("""En enero de 2025, la ciudad firmó contratos con una organización sin fines de lucro, llamada Illinois Public Health Initiative con el objetivo de «ayudar a coordinar la participación de la comunidad e identificar a los miembros de un grupo asesor para informar sobre la ubicación de los sensores»."""),
                        # ui.p("Currently the city's plan is: "),
                        ui.p("Actualmente, el plan de la ciudad es el siguiente: "),
                            ui.tags.ol(
                                # ui.tags.li("The non-profit will suggest members of an advisory group"),
                                ui.tags.li("La organización sin fines de lucro sugerirá a los miembros de un grupo asesor."),
                                # ui.tags.li("The group will advise the city on taking community input and placing sensors"),
                                ui.tags.li(" El grupo asesorará a la ciudad sobre cómo tomar en cuenta las opiniones de la comunidad y colocar los sensores."),
                                # ui.tags.li("The city will ask people where monitors should go"),
                                ui.tags.li("La ciudad preguntará a la gente dónde deberían ir los monitores."),
                                # ui.tags.li("The city will decide where to put the sensors"),
                                ui.tags.li("La ciudad decidirá dónde colocar los sensores. Entonces podrán empezar a instalarlos."),
                                # ui.tags.li("Then they can start putting them up.")
                                ui.tags.li("Entonces iniciarán su instalación.")
                            ),
                        # ui.p("However, the city staffer coordinating the project was ", 
                        ui.p("Sin embargo, en noviembre se le", 
                            #  ui.a("asked to resign", href="https://chicago.suntimes.com/the-watchdogs/2024/12/13/raed-mansour-air-pollution-environmental-justice-brandon-johnson-horace-smith-chicago-climate-change", target="_blank"),
                             ui.a(" pidió al empleado municipal que coordinaba el proyecto que renunciara", href="https://chicago.suntimes.com/the-watchdogs/2024/12/13/raed-mansour-air-pollution-environmental-justice-brandon-johnson-horace-smith-chicago-climate-change", target="_blank"),
                            #  " in November. Nobody has been hired to replace him, and his projects have not been reassigned to any one staff member."),
                             " No se ha contratado a nadie para sustituirlo y sus proyectos no se han reasignado a ningún miembro del personal."),
                        # ui.p("Instead of waiting for the city to act, N4EJ built this tool and we are taking suggestions now."),
                        ui.p("En lugar de esperar a que la ciudad actúe, N4EJ creó esta herramienta y ahora estamos aceptando sugerencias."),
                        class_="faq_answer"
                    ),

                    # ui.p(ui.tags.b("Why is the city installing air monitors?")),
                    ui.p(ui.tags.b("¿Por qué está instalando la ciudad monitores de aire?")),

                    ui.div(
                        # ui.p("The air monitors are required by a ", ui.a("federal agreement", href="https://chicago.suntimes.com/2023/5/12/23720343/hud-environmental-racism-lightfoot-general-iron-environmental-justice-housing-urban-development", target="_blank"), " the city signed in 2023."),
                        ui.p("Los monitores de aire son exigidos por un ", ui.a("acuerdo federal", href="https://chicago.suntimes.com/2023/5/12/23720343/hud-environmental-racism-lightfoot-general-iron-environmental-justice-housing-urban-development", target="_blank"), " que la ciudad firmó en 2023."),
                        class_="faq_answer"
                    ), 

                    # ui.p(ui.tags.b("How is N4EJ involved?")),
                    ui.p(ui.tags.b("¿Cómo está involucrado N4EJ?")),
                    ui.div(
                        # ui.p("N4EJ is a member of the city's Environmental Equity Working Group. We helped to complete the city's ", ui.a("Cumulative Impacts Assessment", href="https://www.chicago.gov/city/en/depts/cdph/supp_info/Environment/cumulative-impact-assessment.html", target="_blank"),
                        ui.p("N4EJ es miembro del Grupo de Trabajo de Equidad Ambiental de la ciudad. Ayudamos a completar la ", ui.a("Evaluación de Impactos Acumulativos", href="https://www.chicago.gov/city/en/depts/cdph/supp_info/Environment/cumulative-impact-assessment.html", target="_blank"),
                            #  " and co-chaired the assessment's Communications & Engagement Working Group.",),
                            " de la ciudad y copresidimos el Grupo de Trabajo de Comunicaciones y Compromiso de la evaluación. Sin embargo, esta herramienta no es un proyecto oficial de la ciudad, es algo que hicimos para ayudar a que más personas se involucren.",),
                        # ui.p("It has been challenging to work with the city because Chicago has a long history of environmental racism, and of making promises it does not keep. But we believe these projects are important, and we are committed to seeing them happen. We are also determined to hold the city to its promises."),
                        ui.p("Ha sido un reto trabajar con la ciudad porque Chicago tiene una larga historia de racismo ambiental y de hacer promesas que no cumple. Pero creemos que estos proyectos son importantes y estamos comprometidos a verlos realizados. También estamos decididos a hacer que la ciudad mantenga sus promesas."),
                        class_="faq_answer"
                    ), 

                    # ui.p(ui.tags.b("Will this make the air better?")),
                    ui.p(ui.tags.b("¿Esto mejorará el aire?")),
                    ui.div(
                        # ui.p("Data by itself is never enough to change things. Change takes people, and we need your help! Talk with people you know, help us pressure the city and state, and together we can make the air cleaner and safer for everyone."),
                        ui.p("Los datos por sí solos nunca son suficientes para cambiar las cosas. El cambio requiere de las personas, ¡y necesitamos su ayuda! Juntos podemos seguir presionando a la ciudad y al estado para que hagan cumplir las normas existentes, aprueben otras nuevas, dejen de contaminar los vecindarios y hagan que el aire sea más limpio y seguro para todos."),
                        class_="faq_answer"
                    ), 


                ),    
                id = "accordion_faq",
                open = ["Monitores de aire"]                       
            ),
            id="faq"
            ),
        ),
        # ui.nav_panel("Explore data",
        ui.nav_panel("Explorar los datos",
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
                            # ui.accordion_panel("About this data",
                            ui.accordion_panel("Acerca de estos datos",
                                # ui.p("This data was compiled by the Chicago Department of Public Health for the city's 2023 Cumulative Impacts Assessment."),
                                ui.p("Estos datos fueron recopilados por el Departamento de Salud Pública de Chicago para la Evaluación de Impactos Acumulativos de la ciudad de 2023."),
                                # ui.p("This ", ui.a("summary", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_MethodologyPoster_Updated-11.14.2023.pdf", target="_blank"),
                                ui.p("Este ", ui.a("resumen de", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_MethodologyPoster_Updated-11.14.2023.pdf", target="_blank"),
                                #  " explains how the EJ Index Score was calculated. ", ui.a("Read more", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_ChicagoEnvironmentalJusticeIndexMethodology_Updated_11.21.2023.pdf", target = "_blank"),
                                " datos explica cómo se calculó la puntuación del Índice de Justicia Ambiental. ", ui.a("Lea más", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_ChicagoEnvironmentalJusticeIndexMethodology_Updated_11.21.2023.pdf", target = "_blank"),
                                # " about the data they used, or ", ui.a("download a copy.", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/Chicago-EJ-Index-Values_2023.10.04.xlsx", target="_blank")),
                                " sobre los datos que utilizaron o ", ui.a("descargue una copia.", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/Chicago-EJ-Index-Values_2023.10.04.xlsx", target="_blank")),
                                # ui.download_link("download_suggestions", label = "Download suggested locations"),
                                ui.download_link("download_suggestions", label = "Descargar ubicaciones sugeridas"),
                                # ui.input_checkbox(id="show_suggestions", label="Show suggestions on map", value=False)
                                ui.input_checkbox(id="show_suggestions", label="Mostrar sugerencias en el mapa", value=False)
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
        ui.nav_spacer(),
        ui.nav_control(ui.div(ui.a("English", href="https://chicagoaqi.com", target="_blank"), style="margin-top: .5rem;")),
        ui.nav_control(ui.div(ui.a("汉语", href="https://cn.chicagoaqi.com", target="_blank"), style="margin-top: .5rem;")),

        selected="Sugerir una ubicación",
        id="primary_nav"
    ),
    ui.include_css('app_css.css'),
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

    @reactive.Effect
    @reactive.event(input.btn_address_lookup)
    def _():
        address = input.address_lookup()
        headers = {"User-Agent": "ChicagoAQI"}
        response = requests.get(f"https://nominatim.openstreetmap.org/search?format=json&q={address}", headers=headers)
        try:
            results = [r for r in response.json() if "Chicago" in r['display_name'] ]
            if len(results) > 0:
                top_result = results[0]
                search_location = [float(top_result['lat']), float(top_result['lon'])]
                print(search_location)
                drag_marker.location = search_location
                the_map.center = search_location
                the_map.zoom = 16
            else:
                m = get_modal(
                    title="No results",
                    prompt=ui.TagList(ui.p("Try searching a different address, using your location, or clicking on the map.")),
                    buttons = [])
                ui.modal_show(m)
        except Exception as e:
            print("Error searching address")


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


    @reactive.effect # Explorar los datos choropleth layers
    @reactive.event(input.index_layers)
    def _():
        print(input.index_layers())
        if input.primary_nav == "Explorar los datos": 
            
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
            if(input.primary_nav()) == "Explorar los datos":
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
        img_src = f"{census_tract()}_{measure}"
        with open(f"assets/ej_index_strips/{img_src}.png", 'rb') as image_file:
            base64_bytes = base64.b64encode(image_file.read())
            base64_string = base64_bytes.decode()
       
        
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
        if input.primary_nav() == "Explorar los datos":
            new_details = {}
            for ml in mlc:
                print(f"locating point in {mlc[ml].label}")
                area = locate_point(lat = [ coordinates()[0] ], long = [ coordinates()[1] ], bounds = mlc[ml].gdf)
                print("located")
                if area:
                    new_details[mlc[ml].point_label] = area 

            if 'distrito censal' in new_details:
                census_tract.set(new_details['distrito censal'])

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
        
        coordinates.set(suggested_location)
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
            title="¡Gracias!",
            prompt=ui.TagList(
                # ui.p("Your suggestion has been submitted. (Feel free to suggest more locations)"),
                ui.p("¿Desea recibir actualizaciones sobre el control del aire de la ciudad de Neighbors For Environmental Justice?"),
                ui.input_text(id="email_address", label="Dirección de correo electrónico", width="100%")
            ),
            buttons = [ui.modal_button("No, gracias"), ui.input_action_button("email_signup", "¡Inscríbame!")]
        )
        ui.modal_show(m)
        
        ui.update_navs("primary_nav", selected="Explorar los datos")
    
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
        if input.primary_nav() == "Explorar los datos": 
            
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
        if input.primary_nav() == "Explorar los datos":
            explore_map_layers = [layer.name for layer in explore_map.layers]
            if "corredor industrial" not in explore_map_layers:
                explore_map.add(get_map_layer(
                            layer_name = mlc['corridors'].label,
                            filename = mlc['corridors'].filename, 
                            style_overrides = mlc['corridors'].style
                        ), index=1
                )
                     
    @reactive.effect 
    @reactive.event(current_choro_layer)
    def get_communities():
        if input.primary_nav() == "Explorar los datos":
            explore_map_layers = [layer.name for layer in explore_map.layers]
            if "zona comunidad" not in explore_map_layers:
                explore_map.add(get_map_layer(
                            layer_name = mlc['communities'].label,
                            filename = mlc['communities'].filename, 
                            style_overrides = mlc['communities'].style
                        ), index = 1
                )

    @reactive.effect 
    @reactive.event(census_tract)
    def get_tracts():
        if input.primary_nav() == "Explorar los datos":
            explore_map_layers = [layer.name for layer in explore_map.layers]
            print(explore_map_layers)
            for layer in explore_map.layers:
                if layer.name == "distrito censal":
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
        
        query = "SELECT lat, long, label, reason, datetime(time_submitted, 'America/Chicago') as time_submitted, session_id FROM chicago_aqi.suggested_locations"
        df = bq.query(query).to_dataframe()
    
        with io.BytesIO() as buf:
            df.to_csv(buf, index=False)
            yield buf.getvalue()

app = App(app_ui, server)
    