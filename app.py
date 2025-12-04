import os
import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import pycountry

from clean_data import load_and_clean_separate
from country_centers import country_center
from energy_environment_plot import electricity_vs_poverty
from agriculture_plots import plot_agriculture_insights

# Inject CSS
os.makedirs("assets", exist_ok=True)
with open("assets/style.css", "w") as f:
    f.write("""
        body, html {
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden;
            background-color: #121212 !important;
        }
        .dash-graph {
            margin: 0 !important;
            padding: 0 !important;
        }
    """)

def get_iso3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except:
        return None

def sidebar_style(display="none"):
    return {
        "position": "absolute",
        "top": "0",
        "left": "0",
        "height": "100%",
        "width": "40%",
        "backgroundColor": "white",
        "padding": "20px",
        "boxShadow": "2px 0 12px rgba(0,0,0,0.25)",
        "overflowX": "scroll",   # horizontal scroll
        "overflowY": "scroll",   # vertical scroll
        "display": display,
        "zIndex": 999
    }


cleaned_data = load_and_clean_separate()
for df in cleaned_data.values():
    df["ISO3"] = df["Country"].apply(get_iso3)

datasets = {
    "energy": cleaned_data.get("energy", pd.DataFrame()),
    "demographics": cleaned_data.get("demographics", pd.DataFrame()),
    "economy": cleaned_data.get("economy", pd.DataFrame()),
    "geography": cleaned_data.get("geography", pd.DataFrame())
}

all_countries = (
    pd.concat([
        datasets["energy"][["Country", "ISO3"]],
        datasets["demographics"][["Country", "ISO3"]],
        datasets["economy"][["Country", "ISO3"]],
        datasets["geography"][["Country", "ISO3"]]
    ], axis=0)
    .drop_duplicates(subset=["ISO3"])
    .dropna(subset=["ISO3"])
)
all_countries["dummy"] = 1

metric_categories = [
    "Energy & Environment",
    "Development & Poverty",
    "Digital & Infrastructure Economy",
    "Demographics & Labor",
    "Agriculture & Economy"
]

category_mapping = {
    "Energy & Environment": [
        {"dataset": "energy", "metrics": ["natural_gas_cubic_meters", "petroleum_bbl_per_day", "electricity_access_percent", "carbon_dioxide_emissions_Mt"]},
        {"dataset": "economy", "metrics": ["Real_GDP_per_Capita_USD"]}
    ],
    "Development & Poverty": [
        {"dataset": "economy", "metrics": ["Real_GDP_per_Capita_USD", "Population_Below_Poverty_Line_percent"]},
        {"dataset": "energy", "metrics": ["electricity_access_percent"]},
        {"dataset": "demographics", "metrics": ["Total_Population"]}
    ],
    "Digital & Infrastructure Economy": [
        {"dataset": "economy", "metrics": ["Exports_billion_USD", "Imports_billion_USD"]}
    ],
    "Demographics & Labor": [
        {"dataset": "demographics", "metrics": ["Median_Age", "Youth_Unemployment_Rate"]},
        {"dataset": "economy", "metrics": ["Unemployment_Rate_percent"]}
    ],
    "Agriculture & Economy": [
        {"dataset": "geography", "metrics": ["Agricultural_Land", "Arable_Land (percentage of Total Agricultural Land)"]},
        {"dataset": "economy", "metrics": ["Real_GDP_per_Capita_USD"]}
    ]
}

geojson_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
geojson = requests.get(geojson_url).json()

app = dash.Dash(__name__)
app.title = "Global Data Dashboard"

app.layout = html.Div(style={"backgroundColor": "#121212", "height": "100vh"}, children=[
    dcc.Graph(id="world-map", style={"height": "100%", "width": "100%"}),

    html.Div([
        html.Label("Dataset:", style={"color": "white"}),
        dcc.Dropdown(
            id="dataset-dropdown",
            options=[
                {"label": "Choose a dataset", "value": "choose_dataset"},
                {"label": "Energy", "value": "energy"},
                {"label": "Demographics", "value": "demographics"},
                {"label": "Economy", "value": "economy"},
            ],
            value="choose_dataset",
            clearable=False
        ),
        html.Br(),
        html.Label("Category:", style={"color": "white"}),
        dcc.Dropdown(
            id="metric-dropdown",
            options=[{"label": "Choose a category", "value": "choose_category"}] + [
                {"label": cat, "value": cat} for cat in metric_categories
            ],
            value="choose_category",
            clearable=False
        ),
        html.Br(),
        html.Button(
            "Reset Selection",
            id="reset-btn",
            n_clicks=0,
            style={
                "width": "100%",
                "padding": "10px",
                "backgroundColor": "#444",
                "color": "white",
                "borderRadius": "6px",
                "border": "none",
                "cursor": "pointer"
            }
        )
    ], style={
        "position": "absolute",
        "top": "20px",
        "right": "20px",
        "padding": "15px",
        "backgroundColor": "rgba(0,0,0,0.6)",
        "borderRadius": "10px",
        "width": "300px",
        "zIndex": 1000
    }),

    html.Div(id="sidebar", style=sidebar_style("none"))
])

@app.callback(
    Output("world-map", "figure"),
    Input("dataset-dropdown", "value"),
    Input("metric-dropdown", "value"),
    Input("world-map", "clickData"),
    Input("reset-btn", "n_clicks")
)
def update_map(dataset_key, category, clickData, reset_clicks):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    selected_iso = None
    if trigger == "world-map" and clickData and "points" in clickData:
        selected_iso = clickData["points"][0]["location"]
    elif trigger == "reset-btn":
        selected_iso = None

    
    if category == "choose_category":
        fig = px.choropleth_mapbox(
            all_countries,
            geojson=geojson,
            locations="ISO3",
            color="dummy",
            color_continuous_scale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            hover_name="Country",
            mapbox_style="carto-darkmatter",
            zoom=1,
            center={"lat": 20, "lon": 0},
            opacity=0.1,
        )
        fig.update_traces(marker_line_width=0.4, marker_line_color="#333")
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            font_color="white",
            clickmode="event",
            uirevision="map",
            dragmode="zoom",  # restore zoom
            mapbox=dict(
                style="carto-darkmatter",
                zoom=1,
                center={"lat": 20, "lon": 0}
            )
        )
        fig.update_coloraxes(showscale=False)
        return fig

    # pick first metric from category mapping
    first_section = category_mapping[category][0]
    dataset_name = first_section["dataset"]
    metric_to_use = first_section["metrics"][0]

    df = datasets.get(dataset_name, None)
    if df is None or metric_to_use not in df.columns:
        return px.choropleth_mapbox()

    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        locations="ISO3",
        color=metric_to_use,
        hover_name="Country",
        color_continuous_scale="Sunset",
        mapbox_style="carto-darkmatter",
        zoom=1,
        center={"lat": 20, "lon": 0},
        opacity=0.75,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        font_color="white",
        clickmode="event",
        uirevision="map",
        dragmode="zoom",  # restore zoom
        mapbox=dict(
            style="carto-darkmatter",
            zoom=1,
            center={"lat": 20, "lon": 0}
        )
    )
    fig.update_traces(marker_line_width=0.4, marker_line_color="#222")

    # Legend at bottom-right
    fig.update_coloraxes(
        showscale=True,
        colorbar=dict(
            title=dict(text=metric_to_use, font=dict(color="white", size=14)),
            tickfont=dict(color="white"),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            xanchor="right",
            x=0.98,
            y=0.02,
            len=0.30,
            thickness=10
        )
    )

    if selected_iso:
        fig.add_trace(
            go.Choroplethmapbox(
                geojson=geojson,
                locations=[selected_iso],
                z=[1],
                colorscale=[[0, "rgba(255,0,0,0.35)"], [1, "rgba(255,0,0,0.35)"]],
                marker=dict(line=dict(width=4, color="#FF0000")),
                showscale=False,
                hoverinfo="skip"
            )
        )
        if selected_iso in country_center:
            fig.update_layout(
                mapbox_zoom=2.5,
                mapbox_center=country_center[selected_iso]
            )

    return fig
# -------------------------------------------------
# Sidebar callback
# -------------------------------------------------
@app.callback(
    Output("sidebar", "children"),
    Output("sidebar", "style"),
    Input("metric-dropdown", "value"),
    Input("reset-btn", "n_clicks")
)
def toggle_sidebar(category, reset_clicks):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # Close sidebar if reset pressed or default category selected
    if trigger == "reset-btn" or category == "choose_category":
        return [], sidebar_style("none")

    # If Energy & Environment selected, show correlation plot
    if category == "Energy & Environment":
        fig = electricity_vs_poverty(cleaned_data)
        return [dcc.Graph(figure=fig, style={"height": "100%", "width": "100%"})], sidebar_style("block")

    # If Agriculture & Economy selected, show agriculture plots
    if category == "Agriculture & Economy":
        figures = plot_agriculture_insights(cleaned_data)
        
        # Create Tabs
        tabs = dcc.Tabs([
            dcc.Tab(label="Overview", children=[
                dcc.Graph(figure=figures["bar"], style={"height": "85vh", "width": "100%"})
            ], style={"color": "black"}, selected_style={"color": "black", "fontWeight": "bold"}),
            
            dcc.Tab(label="Correlation", children=[
                dcc.Graph(figure=figures["heatmap"], style={"height": "85vh", "width": "100%"})
            ], style={"color": "black"}, selected_style={"color": "black", "fontWeight": "bold"}),
            
            dcc.Tab(label="Distribution", children=[
                dcc.Graph(figure=figures["scatter"], style={"height": "85vh", "width": "100%"})
            ], style={"color": "black"}, selected_style={"color": "black", "fontWeight": "bold"})
        ], colors={"border": "white", "primary": "gold", "background": "#f9f9f9"})
        
        return [tabs], sidebar_style("block")

    # Otherwise open empty sidebar
    return [], sidebar_style("block")


# -------------------------------------------------
# Run app
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8051)
