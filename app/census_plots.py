import plotly.express as px 
import pandas as pd

from tqdm import tqdm 
ejiv = pd.read_csv('data/ej_index_values.csv')
eji_fields = pd.read_csv('data/ceji_field_key.csv')
eji_field_labels = dict(zip(eji_fields.var_name.to_list(), eji_fields.readable_name.to_list()))
eji_field_labels_reversed = dict(zip(eji_fields.readable_name.to_list(), eji_fields.var_name.to_list()))
measure_columns = list(eji_field_labels.keys())

def get_strip_plot(tract_id, category):
    df = (
        ejiv
            [ejiv.measure == category]
            .assign(color = lambda df: df.GEOID.apply(lambda x: str(tract_id) if x == tract_id else "Other census tracts"))
            .sort_values('color', ascending=False)
            .astype({'value':'float'})
    )

    fig = px.strip(
        df, 
        x='value', 
        color='color', 
        stripmode='overlay',
        width=350,
        color_discrete_map={str(tract_id): "black", "Other census tracts": "#bbbbbb"}
    )
    this_tract = df.loc[df.GEOID == tract_id, 'value'].squeeze()

    fig.add_vline(
                x=this_tract,
                line_dash = "solid", 
                line_color="black"
    )
    fig.update_traces(jitter = .9)
    fig.update_layout(
        height = 30,
        # plot_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#ffffff',
        
        margin = {
            "b": 0,
            "t": 0,
            "l": 0, 
            "r": 0
        },
        margin_pad = 0,
        showlegend=False,
    )

    fig.update_xaxes(
        visible=False,
        title=None
    )
    fig.update_yaxes(
        visible = False,

    )
    return fig 

census_tracts = ejiv.GEOID.unique()
for tract in tqdm(census_tracts):
    for m in measure_columns:
        fig = get_strip_plot(tract, m)
        fig.write_image(f"assets/ej_index_strips/{tract}_{m}.png")
    