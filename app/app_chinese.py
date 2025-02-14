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
from map_util import map_layer_config_chinese as mlc, MapLayer, locate_point
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
aqi_table = pd.read_csv('data/aqi_table_chinese.csv')

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
    ui.div( ui.help_text("由 Neighbors For Environmental Justice (争取环境正义邻居团) 提供的应用"), id="attribution", style="text-align: right;"),
    # ui.input_select( id="language_choice", label='Language', choices=["English", "Español", "中文"], selected="English", width="120px"),
    ui.navset_card_underline(

        ui.nav_panel( "建议空气监测器安装地点",
            ui.div( 
            ui.tags.h4("空气监测器该安装在什么地点？"),
            ui.p("根据联邦政府协议，", ui.tags.b("市政府承诺安装220部空气监测器，"), "大部分安排安装在大量污染的地区。"), 
            ui.p(" 市政府现时还没确定空气监测器的安装地点，而本机构希望确保会安装在实用的地点：例如小孩玩耍的地方、货车停留的地方、或者散发异味的地方。"),
            ui.p("您认为哪里是最佳的安装地点？"),
            
            output_widget(id = "map"),
            ui.row(
                ui.layout_column_wrap(
                    ui.card(
                        ui.card_header("在地图上挑选安装地点"),
                        ui.tags.p("具有四种挑选安装地点的方式："), 
                        ui.tags.ul(
                            ui.tags.li("在地图上随意点击"),
                            ui.tags.li("点击地点挑选标志，拉动至所愿地点"),
                            ui.tags.li("使用您的定位"),
                            ui.tags.li(ui.TagList(" 搜寻某个地址")), # (click ", ui.HTML("&#x1F50D;"), " on the map)")),
                            ui.input_text(id="address_lookup", label=""),
                            ui.input_action_button(id="btn_address_lookup", label="Search")
                        ),
                        ui.card_footer(ui.input_action_button("btn_use_location", label="判断我的定位", width="100%"),)
                    ),
                    ui.card(
                        ui.card_header("简单介绍 (非规定）"),
                        ui.input_text(id="suggested_label", label="您会如何称呼这个地点？", width="100%"),
                        ui.input_text_area(id="reason", label="为什么该在这地点安装空气监测器？", width="100%"),
                        ui.card_footer(ui.input_action_button("btn_submit", label="递交", width="100%"))
                    ),
                ),
                ),
            ),
        ),
        ui.nav_panel( "项目目的", # Why we're doing this
            ui.div( 
            ui.accordion(
                ui.accordion_panel( "空气监测器", # Air monitors
                    ui.p(ui.tags.b("社区为什么需要安装空气监测器？")), #Why do we need air monitors?
                    ui.tags.ul(
                        # ui.tags.li("In Chicago, how much pollution you breathe depends a lot on where you live"),
                        ui.tags.li("作为芝加哥的居民，居住地区对空气污染度有重大的影响"),
                        # ui.tags.li("Air monitors help us know what we're breathing"),
                        ui.tags.li("空气监测器能告知我们环境的污染度"), 
                        # ui.tags.li("On days with the worst air pollution, we can take actions to stay safe, like running air filters and wearing masks"),
                        ui.tags.li("遇到严重污染时，就可以采取行动缓解污染，例如使用空气清新器以及戴上口罩"),
                        # ui.tags.li("We can use this data to push the city to take action"),
                        ui.tags.li("我们可以使用空气监测器的数据呼吁市政府作出改进")
                         ),
                    # ui.p(ui.tags.b("Does it matter where they go?")),
                    ui.p(ui.tags.b("空气监测器的地点重要吗")),
                    ui.tags.ul(
                        # ui.tags.li("Yes! Air monitors can only measure what's nearby"), 
                        ui.tags.li("当然！空气监测器只能测试附近环境的污染度"), 
                        # ui.tags.li("Depending on weather and nearby sources of pollution, even a few blocks can make a big difference"),
                        ui.tags.li("天气和附近污染源等因素、甚至仅仅几街头的距离都会影响监测器搜集的数据"),
                        # ui.tags.li("The places that have the most pollution in Chicago (South and Southwest Chicago) do not have air monitors installed by the government to measure the air quality")
                        ui.tags.li("芝加哥地区最高污染度的区域 (南部以及西南部) 并没有安装空气监测器")
                    ),
                    # ui.p(ui.tags.b("What kind of air monitors are they?")),
                    ui.p(ui.tags.b("什么是空气监测器？")),
                    ui.tags.ul( 
                        # ui.tags.li(ui.a("Clarity Node-S monitors", href="https://www.clarity.io/products/clarity-node-s"), target="_blank"),
                        ui.tags.li(ui.a("将使用 Clarity 公司制造的 Node-S 型号监测器", href="https://www.clarity.io/products/clarity-node-s"), target="_blank"),
                        # ui.tags.li("They use solar panels, and will be installed on light poles"),
                        ui.tags.li("监测器使用太阳能运行，将会安装在灯柱上"),
                        # ui.tags.li("They measure particulate matter (PM) and nitrogen dioxide (NO₂)"),
                        ui.tags.li("监测器将会测试空气的含微粒度和含二氧化氮度"),
                        # ui.tags.li("They will upload data to a public dashboard"),
                        ui.tags.li("监测器所搜集的数据将会上载至公开标版网页")
                    ),
                    # ui.p(ui.tags.b("Doesn't the city have air monitors already?")),
                    ui.p(ui.tags.b("城市里不是已经有安装空气监测器吗？")),
                    ui.tags.ul(
                        # ui.tags.li("There are only a few government-owned air monitors in or near Chicago"),
                        ui.tags.li("芝加哥市内和附近地区只安装少量的政府管控空气监测器"),
                        # ui.tags.li("They're mostly not owned by the city, and mostly not in neighborhoods with the worst pollution"),
                        ui.tags.li("大部分并非由市政府管控，也没有安装在最高污染度的地区"),
                        # ui.tags.li("A study found the US EPA puts more air monitors", ui.a(" in white neighborhoods", href="https://www.theguardian.com/environment/2024/dec/14/epa-air-quality-monitors-white-neighborhoods", target="_blank")),
                        ui.tags.li("研究发现美国 EPA (环境保护署)", ui.a(" 在白人邻里", href="https://www.theguardian.com/environment/2024/dec/14/epa-air-quality-monitors-white-neighborhoods", target="_blank"), "安装空气监测器的数量会高于其他种族的邻里"),
                        # ui.tags.li("You can see readings from the ", ui.a("six Illinois EPA monitors", href="https://www.airnow.gov/?city=Chicago&state=IL&country=USA", target="_blank")),
                        ui.tags.li("伊州具有 ", ui.a("六个 EPA (环境保护署) 监测器 ", href="https://www.airnow.gov/?city=Chicago&state=IL&country=USA", target="_blank"), "数据可以在公开网页参看"),
                        # ui.tags.li("Community groups and residents have also put up air monitors ", ui.a("on their own", href="https://map.purpleair.com/air-quality-standards-us-epa-aqi?opt=%2F1%2Flp%2Fa0%2Fp604800%2FcC0#10.6/41.8697/-87.674", target="_blank"))
                        ui.tags.li("某些社区团体以及独立居民也有 ", ui.a("私家安装监测器", href="https://map.purpleair.com/air-quality-standards-us-epa-aqi?opt=%2F1%2Flp%2Fa0%2Fp604800%2FcC0#10.6/41.8697/-87.674", target="_blank"))
                    )

                ),                    
                # ui.accordion_panel( "Pollution",
                ui.accordion_panel( "污染", 
                    # ui.p(ui.tags.b("What is air pollution?")),
                    ui.p(ui.tags.b("空气污染是什么？")),
                    ui.tags.ul(
                        # ui.tags.li("Pollution is tiny bits of stuff we inhale when we breathe"), 
                        ui.tags.li("空气污染是人类通过呼吸意外吸收的微小物体"), 
                        # ui.tags.li("It can be made of gases, or tiny particles that are 100 times thinner than a human hair"),
                        ui.tags.li("空气污染包含着气体，或者比头发稀薄100倍的微粒物体"),
                        # ui.tags.li("Sometimes you can smell, see, or feel pollution, but mostly we don’t know what we’re breathing")
                        ui.tags.li("偶尔空气污染是可以肉眼看到、嗅觉闻到、或能触碰，但大部分的时间人类的感官是无法察觉到空气污染")
                    ),
                    # ui.p(ui.tags.b("Where does air pollution come from?")),
                    ui.p(ui.tags.b("空气污染源于哪里？")),
                    ui.tags.ul(
                        # ui.tags.li("Transportation: cars, trucks, and trains"), 
                        ui.tags.li(" 交通：汽车、货车、火车"), 
                        # ui.tags.li("Industry: factories, asphalt plants, construction equipment and diesel vehicles"),
                        ui.tags.li("工业：工厂、柏油生产厂、施工工具、以及柴油汽车"),
                        # ui.tags.li("Natural sources: smoke from wildfires, dust blown by the wind"),
                        ui.tags.li("自然来源：野火的冒烟、风吹的微尘"),
                        # ui.tags.li("In Chicago, city policies put pollution in communities of color and low-income communities."),
                        ui.tags.li("芝加哥市政的政策把污染放置在非白人邻里以及低收入邻里"),
                        # ui.tags.li("This practice is called environmental racism"),
                        ui.tags.li("这样的做法叫做环境种族歧视"),
                        # ui.tags.li("These new air monitors are part of an contract signed by the city promising to address environmental racism"),
                        ui.tags.li("将会安装的空气监测器是市政府签了正视环境种族歧视合约的行动之一"),
                    ),
                    # ui.p(ui.tags.b("How bad is it for your health?")),
                    ui.p(ui.tags.b("空气污染有多损害健康？")),
                    ui.tags.ul(
                        # ui.tags.li("It makes existing health problems worse"), 
                        ui.tags.li("会恶化现有疾病"), 
                        # ui.tags.li("It causes new health problems, like asthma, headaches, and chest pain"),
                        ui.tags.li("会导致各种疾病，例如哮喘、头痛、胸痛"),
                        # ui.tags.li("The combined effect of of outdoor air pollution and indoor air pollution ", ui.a("kills about 6.7 million people", href="https://www.who.int/data/gho/data/indicators/indicator-details/GHO/ambient-air-pollution-attributable-deaths", target="_blank"), " around the world every year."),
                        ui.tags.li("室内室外的空气污染整体负面影响导致全球 ", ui.a("每年大约67万宗死亡", href="https://www.who.int/news-room/fact-sheets/detail/ambient-(outdoor)-air-quality-and-health", target="_blank")),
                    ),
                    # ui.p(ui.tags.b("How is air pollution measured?")),
                    ui.p(ui.tags.b("如何衡量空气污染？")),
                    ui.tags.ul(
                        # ui.tags.li("Different sensors detect different types of air pollution. Most air monitors measure one or two"), 
                        ui.tags.li("不同的监测器测试不同的空气污染。大部分的空气监测器能测试一至两种污染"), 
                        # ui.tags.li("The most common air monitors measure particulate matter (PM 2.5), a mixture of the tiny things that get into your lungs when you breathe"),
                        ui.tags.li("最常见的监测器测试微粒 (PM 2.5)，人类呼吸时吸进肺部的细小物体"),
                        # ui.tags.li("PM 2.5 is counted in micrograms per cubic meter of air (µg/m³) "),
                        ui.tags.li("是以 每立方米含多少微克 而衡量 "),
                    ),
                    # ui.p(ui.tags.b("How can you tell when the air quality is bad?")),
                    ui.p(ui.tags.b("如何分辨不良的空气素质？")),
                    ui.tags.ul(
                        # ui.tags.li("There is no safe level of air pollution"),
                        ui.tags.li("并没有安全的空气污染度"),
                        # ui.tags.li("To make air quality easier to understand, the US EPA uses PM2.5 readings to calculate the Air Quality Index (AQI)"),
                        ui.tags.li("为了让空气素质容易理解，美国 EPA (环境保护署) 使用 PM 2.5 数据判断 Air Quality Index 空气素质指标 (AQI)"),
                        # ui.tags.li("AQI is a scale that goes from zero (no pollution) to 500 (extremely high amounts of pollution)"),
                        ui.tags.li("AQI 空气素质指标 是一个从零 (没有污染) 至 500 (极高污染度) 的指数"),
                        # ui.tags.li("People from “sensitive groups” (children, the elderly, or people with heart and lung conditions) should often stay inside if the AQI is high")
                        ui.tags.li("当 AQI 指数甚高， 属于 “敏感群体” 的人群 (小孩、耆老、患有心脏或肺部疾病的人) 应该尽量避免外出")
                    ),
                    ui.output_table("aqi_ranges")
                ),
                # ui.accordion_panel( "About this project",
                ui.accordion_panel( "关于本项目",
                                   
                    # ui.p(ui.tags.b("What will happen to the suggestions people submit?")),
                    ui.p(ui.tags.b(" 递交至网页的建议地点会如何处理？")),
                    ui.div(
                        # ui.p("Neighbors For Environmental Justice (",ui.a("N4EJ", href="http://n4ej.org", target="_blank"),") is collecting this data."),
                        ui.p("Neighbors For Environmental Justice (争取环境正义邻居团",ui.a("N4EJ", href="http://n4ej.org", target="_blank"),") 会搜集所有建议地点。"),
                        # ui.p("Suggestions are public as soon as they are submitted (you can see them on the 'Explore the data' page). N4EJ will share them with the Department of Public Health, which has the final say on where monitors are installed."),
                        ui.p("建议地点被递交后便立刻公开 (可在 ’探察数据‘ 参看)。N4EJ 将会与公共卫生局分享，而卫生局拥有安装监测器地点的最后决定权。"),
                        class_="faq_answer"
                    ),

                    # ui.p(ui.tags.b("Who is this tool for? Do I have to be part of N4EJ to use it or share it?")),
                    ui.p(ui.tags.b("这个应用是为谁而设？应用是否只限 N4EJ 成员使用或分享？")),
                    ui.div(
                        # ui.p("This tool is for everyone! You don't have to be part of N4EJ to suggest air monitor locations, or to share this with others. This is just a way for people to learn about their neighborhood and offer feedback."),
                        ui.p(" 这应用是为大众而设！建议监测器地点以及分享应用网页、无需是 N4EJ 成员。应用的目的是帮助市民更加了解他们的邻里和提出建议。"),
                        # ui.p("If you have questions or ideas and want to get in touch, email us at info@n4ej.org"),
                        ui.p("您若想向我们提问或提议，请电邮至 info@n4ej.org。"),
                        class_="faq_answer"
                    ),

                    # ui.p(ui.tags.b("When will the monitors go up?")),
                    ui.p(ui.tags.b("空气监测器会在什么时候安装？")),
                    ui.div(
                        # ui.p("We don't really know."),
                        ui.p("现时还没确实。"),
                        # ui.p("""As of January 2025, the city has signed contracts with a non-profit called the Illinois Public Health Initiative to "help coordinate community engagement and identify members for an advisory group to inform sensor placement." """),
                        ui.p("""于 2025年1月，市政府已与一个叫 Illinois Public Health Initiative (伊州公共健康项目) 的非牟利机构签订合同 - 授权该机构 “安排社区外展活动以及为监测器安装地点建议委员会提名成员。” """),
                        # ui.p("Currently the city's plan is: "),
                        ui.p("市政府目前的计划程序是: "),
                            ui.tags.ol(
                                # ui.tags.li("The non-profit will suggest members of an advisory group"),
                                ui.tags.li("非牟利机构将会提名建议委员会成员"),
                                # ui.tags.li("The group will advise the city on taking community input and placing sensors"),
                                ui.tags.li(" 委员会将会至市政府作出关于社区民意以及监测器安装地点的建议"),
                                # ui.tags.li("The city will ask people where monitors should go"),
                                ui.tags.li("市政府会向市民咨询监测器该安装的地点"),
                                # ui.tags.li("The city will decide where to put the sensors"),
                                ui.tags.li("市政府会判断最后安装地点"),
                                # ui.tags.li("Then they can start putting them up.")
                                ui.tags.li("最后，市政府会开始安装监测器。")
                            ),
                        # ui.p("However, the city staffer coordinating the project was ", 
                        ui.p("- 可是，安装监测器项目的市政府组织员与 11月  ", 
                            #  ui.a("asked to resign", href="https://chicago.suntimes.com/the-watchdogs/2024/12/13/raed-mansour-air-pollution-environmental-justice-brandon-johnson-horace-smith-chicago-climate-change", target="_blank"),
                             ui.a("被要求辞职", href="https://chicago.suntimes.com/the-watchdogs/2024/12/13/raed-mansour-air-pollution-environmental-justice-brandon-johnson-horace-smith-chicago-climate-change", target="_blank"),
                            #  " in November. Nobody has been hired to replace him, and his projects have not been reassigned to any one staff member."),
                             "。至今，市政府还没聘请新组织员，项目也并没有分配给一位指定工作人员。"),
                        # ui.p("Instead of waiting for the city to act, N4EJ built this tool and we are taking suggestions now."),
                        ui.p("与其等待市政府采取行动，N4EJ 决定设立这个应用，主动征求安装地点提议。"),
                        class_="faq_answer"
                    ),

                    # ui.p(ui.tags.b("Why is the city installing air monitors?")),
                    ui.p(ui.tags.b("市政府为何要安装空气监测器？")),

                    ui.div(
                        # ui.p("The air monitors are required by a ", ui.a("federal agreement", href="https://chicago.suntimes.com/2023/5/12/23720343/hud-environmental-racism-lightfoot-general-iron-environmental-justice-housing-urban-development", target="_blank"), " the city signed in 2023."),
                        ui.p("市政府于 2023年 与 ", ui.a("联邦政府签订协议", href="https://chicago.suntimes.com/2023/5/12/23720343/hud-environmental-racism-lightfoot-general-iron-environmental-justice-housing-urban-development", target="_blank"), " 安装监测器。"),
                        class_="faq_answer"
                    ), 

                    # ui.p(ui.tags.b("How is N4EJ involved?")),
                    ui.p(ui.tags.b("N4EJ 在安装监测器项目有什么角色？")),
                    ui.div(
                        # ui.p("N4EJ is a member of the city's Environmental Equity Working Group. We helped to complete the city's ", ui.a("Cumulative Impacts Assessment", href="https://www.chicago.gov/city/en/depts/cdph/supp_info/Environment/cumulative-impact-assessment.html", target="_blank"),
                        ui.p("(争取环境正义工作队) 的成员之一。我们有助完成市政府的 ", ui.a("Cumulative Impacts Assessment", href="https://www.chicago.gov/city/en/depts/cdph/supp_info/Environment/cumulative-impact-assessment.html", target="_blank"),
                            #  " and co-chaired the assessment's Communications & Engagement Working Group.",),
                            " 这应用并非市政府的官方项目 - 是本机构为让社区居民能参与发声而制造的工具。",),
                        # ui.p("It has been challenging to work with the city because Chicago has a long history of environmental racism, and of making promises it does not keep. But we believe these projects are important, and we are committed to seeing them happen. We are also determined to hold the city to its promises."),
                        ui.p("与市政府合作并非一件简单的事情，因为市政府拥有一个容许环境种族歧视和不守诺言的往绩。但我们坚信这些项目的重大重要性，并坚定把项目实施。我们也下了决心让市政府遵守诺言。"),
                        class_="faq_answer"
                    ), 

                    # ui.p(ui.tags.b("Will this make the air better?")),
                    ui.p(ui.tags.b("这应用会改善空气素质吗？")),
                    ui.div(
                        # ui.p("Data by itself is never enough to change things. Change takes people, and we need your help! Talk with people you know, help us pressure the city and state, and together we can make the air cleaner and safer for everyone."),
                        ui.p("单凭数据是不足够改变事情。改变的动力是人力，众志成城！市民携手合作就能促进市政府州政府 执行现有法律、通过新法律、制止把污染重复遭受在最弱势的邻里、为大众争取更纯净更安全的空气。"),
                        class_="faq_answer"
                    ), 


                ),    
                id = "accordion_faq",
                open = ["空气监测器"]                       
            ),
            id="faq"
            ),
        ),
        # ui.nav_panel("Explore data",
        ui.nav_panel("探察数据",
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
                            ui.accordion_panel("关于这数据",
                                # ui.p("This data was compiled by the Chicago Department of Public Health for the city's 2023 Cumulative Impacts Assessment."),
                                ui.p("该数据是 由芝加哥公共卫生局，为市政府的长期环境污染累积影响评估 而搜集。"),
                                # ui.p("This ", ui.a("summary", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_MethodologyPoster_Updated-11.14.2023.pdf", target="_blank"),
                                ui.p("这 ", ui.a("概要", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_MethodologyPoster_Updated-11.14.2023.pdf", target="_blank"),
                                #  " explains how the EJ Index Score was calculated. ", ui.a("Read more", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_ChicagoEnvironmentalJusticeIndexMethodology_Updated_11.21.2023.pdf", target = "_blank"),
                                " 详细描述统计 EJ Index Score (环境正义指数) 的程序。 您可", ui.a("参考", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/2023-nov/CIA_ChicagoEnvironmentalJusticeIndexMethodology_Updated_11.21.2023.pdf", target = "_blank"),
                                # " about the data they used, or ", ui.a("download a copy.", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/Chicago-EJ-Index-Values_2023.10.04.xlsx", target="_blank")),
                                " 统计过程所采用的数据，或 ", ui.a("下载数据文档。", href="https://www.chicago.gov/content/dam/city/depts/cdph/environment/CumulativeImpact/Chicago-EJ-Index-Values_2023.10.04.xlsx", target="_blank")),
                                # ui.download_link("download_suggestions", label = "Download suggested locations"),
                                ui.download_link("download_suggestions", label = "下载安装地点建议列表"),
                                # ui.input_checkbox(id="show_suggestions", label="Show suggestions on map", value=False)
                                ui.input_checkbox(id="show_suggestions", label="在地图上显示地点建议", value=False)
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
        ui.nav_control(ui.div(ui.a("Español", href="https://es.chicagoaqi.com", target="_blank"), style="margin-top: .5rem;")),

        selected="建议空气监测器安装地点",
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


    @reactive.effect # 探察数据 choropleth layers
    @reactive.event(input.index_layers)
    def _():
        print(input.index_layers())
        if input.primary_nav == "探察数据": 
            
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
            if(input.primary_nav()) == "探察数据":
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
        if input.primary_nav() == "探察数据":
            new_details = {}
            for ml in mlc:
                print(f"locating point in {mlc[ml].label}")
                area = locate_point(lat = [ coordinates()[0] ], long = [ coordinates()[1] ], bounds = mlc[ml].gdf)
                print("located")
                if area:
                    new_details[mlc[ml].point_label] = area 

            if '人口普查调查区' in new_details:
                census_tract.set(new_details['人口普查调查区'])

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
            title="感谢您的建议！",
            prompt=ui.TagList(
                # ui.p("Your suggestion has been submitted. (Feel free to suggest more locations)"),
                ui.p("您希望从争取环境正义邻居团收到关于市政府安装空气监测器的定期讯息？"),
                ui.input_text(id="email_address", label="电子邮箱", width="100%")
            ),
            buttons = [ui.modal_button("不希望"), ui.input_action_button("email_signup", "订阅")]
        )
        ui.modal_show(m)
        
        ui.update_navs("primary_nav", selected="探察数据")
    
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
        if input.primary_nav() == "探察数据": 
            
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
        if input.primary_nav() == "探察数据":
            explore_map_layers = [layer.name for layer in explore_map.layers]
            if "工业区域" not in explore_map_layers:
                explore_map.add(get_map_layer(
                            layer_name = mlc['corridors'].label,
                            filename = mlc['corridors'].filename, 
                            style_overrides = mlc['corridors'].style
                        ), index=1
                )
                     
    @reactive.effect 
    @reactive.event(current_choro_layer)
    def get_communities():
        if input.primary_nav() == "探察数据":
            explore_map_layers = [layer.name for layer in explore_map.layers]
            if "邻里界线" not in explore_map_layers:
                explore_map.add(get_map_layer(
                            layer_name = mlc['communities'].label,
                            filename = mlc['communities'].filename, 
                            style_overrides = mlc['communities'].style
                        ), index = 1
                )

    @reactive.effect 
    @reactive.event(census_tract)
    def get_tracts():
        if input.primary_nav() == "探察数据":
            explore_map_layers = [layer.name for layer in explore_map.layers]
            print(explore_map_layers)
            for layer in explore_map.layers:
                if layer.name == "人口普查调查区":
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
    