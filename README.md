# ChicagoAQI
---
This is a tool for: 
- taking suggestions for air monitor locations
- exploring environmental data about Chicago neighborhoods (specifically the Environmental Justice Index measures compiled for the city's [cumulative impacts assessment](https://www.chicago.gov/city/en/depts/cdph/supp_info/Environment/cumulative-impact-assessment.html))


It uses Shiny for Python, with Google BigQuery for data storage and Cloud Run for the application.

**This repo excludes the rendered plots of EJ index values for each census tract** because there were ~20k files. You can generate the images using the included file `census_plots.py`  

Because Shiny uses string literals as both the name and ID for things like navigation panels, multi-language support required multiple copies of the app itself. If anybody has a better way to handle that, please let me know because I would love to use something more flexible.
