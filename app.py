import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import pycountry

import plotly.express as px   # <-- this line fixes the NameError
from clean_data import load_and_clean_separate

# Load cleaned datasets
cleaned_data = load_and_clean_separate()

# --------------------------
# Data loading and cleaning
# --------------------------
#url_str = "/Users/varshinir/Desktop/viz/CIA Global Statistical Database/"

import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import pycountry
import os
from country_centers import country_center   # your external file


# -------------------------------------------------
# Inject CSS to remove white margins
# -------------------------------------------------
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


# -------------------------------------------------
# COUNTRY NAME → ISO3
# -------------------------------------------------
def get_iso3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except:
        return None


# -------------------------------------------------
# CLEAN NUMERIC COLUMNS
# -------------------------------------------------
def clean_numeric_columns(df):
    for col in df.columns:
        if col not in ["Country", "ISO3"]:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", "")
                .str.replace("%", "")
                .str.replace(" ", "")
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# -------------------------------------------------
# LOAD DATASETS
# -------------------------------------------------
def get_iso3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except:
        return None

for df in cleaned_data.values():
    df["ISO3"] = df["Country"].apply(get_iso3)

datasets = {
    "energy": cleaned_data["energy"],
    "demographics": cleaned_data["demographics"],
    "economy": cleaned_data["economy"]
}


# -------------------------------------------------
# DROPDOWN OPTIONS
# -------------------------------------------------
metric_options = {
    "energy": {
        "natural_gas_cubic_meters": "Natural Gas (m³)",
        "petroleum_bbl_per_day": "Petroleum (bbl/day)",
        "electricity_access_percent": "Electricity Access (%)",
        "carbon_dioxide_emissions_Mt": "CO₂ Emissions (Mt)"
    },
    "demographics": {
        "Total_Population": "Total Population",
        "Population_Growth_Rate": "Population Growth Rate (%)",
        "Birth_Rate": "Birth Rate (per 1000)",
        "Death_Rate": "Death Rate (per 1000)",
        "Median_Age": "Median Age",
        "Total_Literacy_Rate": "Literacy Rate (%)",
        "Infant_Mortality_Rate": "Infant Mortality (per 1000 births)",
        "Youth_Unemployment_Rate": "Youth Unemployment (%)"
    },
    "economy": {
        "Real_GDP_PPP_billion_USD": "GDP (PPP, billion USD)",
        "Real_GDP_Growth_Rate_percent": "GDP Growth Rate (%)",
        "Real_GDP_per_Capita_USD": "GDP per Capita (USD)",
        "Unemployment_Rate_percent": "Unemployment Rate (%)",
        "Budget_Deficit_percent_of_GDP": "Budget Deficit (% of GDP)",
        "Public_Debt_percent_of_GDP": "Public Debt (% of GDP)",
        "Exports_billion_USD": "Exports (billion USD)",
        "Imports_billion_USD": "Imports (billion USD)",
        "Population_Below_Poverty_Line_percent": "Poverty Rate (%)"
    }
}


# -------------------------------------------------
# WORLD GEOJSON
# -------------------------------------------------
geojson_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
geojson = requests.get(geojson_url).json()



# -------------------------------------------------
# DASH APP
# -------------------------------------------------
app = dash.Dash(__name__)
app.title = "Global Data Dashboard"

app.layout = html.Div(style={"backgroundColor": "#121212", "height": "100vh"}, children=[

    dcc.Graph(id="world-map", style={"height": "100%", "width": "100%"}),

    html.Div([

        html.Label("Dataset:", style={"color": "white"}),
        dcc.Dropdown(
            id="dataset-dropdown",
            options=[
                {"label": "Energy", "value": "energy"},
                {"label": "Demographics", "value": "demographics"},
                {"label": "Economy", "value": "economy"},
            ],
            value="energy",
            clearable=False
        ),

        html.Br(),

        html.Label("Metric:", style={"color": "white"}),
        dcc.Dropdown(id="metric-dropdown", clearable=False),

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
        "width": "280px",
        "zIndex": 1000
    })

])



# -------------------------------------------------
# UPDATE METRIC DROPDOWN
# -------------------------------------------------
@app.callback(
    Output("metric-dropdown", "options"),
    Output("metric-dropdown", "value"),
    Input("dataset-dropdown", "value")
)
def update_metric_dropdown(dataset_key):
    opts = metric_options[dataset_key]
    return [{"label": v, "value": k} for k, v in opts.items()], list(opts.keys())[0]



# -------------------------------------------------
# MAIN MAP CALLBACK (ZOOM + FILL + BORDER HIGHLIGHT)
# -------------------------------------------------
@app.callback(
    Output("world-map", "figure"),
    Input("dataset-dropdown", "value"),
    Input("metric-dropdown", "value"),
    Input("world-map", "clickData"),
    Input("reset-btn", "n_clicks")
)
def update_map(dataset_key, metric, clickData, reset_clicks):

    df = datasets[dataset_key]

    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    selected_iso = None

    if trigger == "world-map" and clickData and "points" in clickData:
        selected_iso = clickData["points"][0]["location"]
    elif trigger == "reset-btn":
        selected_iso = None

    # ------- BASE CHOROPLETH -------
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        locations="ISO3",
        color=metric,
        hover_name="Country",
        color_continuous_scale="Sunset",
        mapbox_style="carto-darkmatter",
        zoom=1,
        center={"lat": 20, "lon": 0},
        opacity=0.75,
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        clickmode="event",
        uirevision=True
    )

    fig.update_traces(marker_line_width=0.4, marker_line_color="#222")

    # ------- COLORBAR -------
    fig.update_coloraxes(
        showscale=True,
        colorbar=dict(
            title=dict(
                text=metric_options[dataset_key][metric],
                font=dict(color="white", size=14)
            ),
            tickfont=dict(color="white"),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            x=0.05,
            y=0.01,
            len=0.30,
            thickness=10
        )
    )

    # -------------------------------------------------
    # FILLED HIGHLIGHT + BORDER + ZOOM
    # -------------------------------------------------
    if selected_iso:

        fill_color   = "rgba(255, 0, 0, 0.35)"   # gold semi-transparent
        border_color = "#FF0000"                   # gold border

        fig.add_trace(
            go.Choroplethmapbox(
                geojson=geojson,
                locations=[selected_iso],
                z=[1],
                colorscale=[[0, fill_color], [1, fill_color]],
                marker=dict(line=dict(width=4, color=border_color)),
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
# RUN APP
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
