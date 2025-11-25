import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import pycountry

import plotly.express as px   # <-- this line fixes the NameError


# --------------------------
# Data loading and cleaning
# --------------------------
df = pd.read_csv("/Users/varshinir/Desktop/viz/CIA Global Statistical Database/energy_data.csv")

df.columns = [c.strip() for c in df.columns]
df = df[df["Country"].notna()].copy()
df["Country"] = df["Country"].str.replace('"', '').str.strip()

# Convert country names to ISO-3 codes
def get_iso3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except:
        return None

df["ISO3"] = df["Country"].apply(get_iso3)
df = df[df["ISO3"].notna()]

# Load GeoJSON for world countries
geojson_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
geojson = requests.get(geojson_url).json()

# Metrics
metrics = [
    "natural_gas_cubic_meters",
    "petroleum_bbl_per_day",
    "electricity_access_percent",
    "carbon_dioxide_emissions_Mt"
]
metric_labels = {
    "natural_gas_cubic_meters": "Natural Gas (m³)",
    "petroleum_bbl_per_day": "Petroleum (bbl/day)",
    "electricity_access_percent": "Electricity Access (%)",
    "carbon_dioxide_emissions_Mt": "CO₂ Emissions (Mt)"
}

for m in metrics:
    df[m] = pd.to_numeric(df[m], errors="coerce")

# --------------------------
# Country centroid lookup
# --------------------------
country_coords = {
    "IND": {"lat": 20.5937, "lon": 78.9629},
    "USA": {"lat": 37.0902, "lon": -95.7129},
    "AUS": {"lat": -25.2744, "lon": 133.7751},
    "BRA": {"lat": -14.2350, "lon": -51.9253},
    "CHN": {"lat": 35.8617, "lon": 104.1954},
    "RUS": {"lat": 61.5240, "lon": 105.3188},
    "GBR": {"lat": 55.3781, "lon": -3.4360},
    "CAN": {"lat": 56.1304, "lon": -106.3468},
    "ZAF": {"lat": -30.5595, "lon": 22.9375},
    "FRA": {"lat": 46.2276, "lon": 2.2137},
    "DEU": {"lat": 51.1657, "lon": 10.4515},
    "JPN": {"lat": 36.2048, "lon": 138.2529},
    # Add more ISO3 codes as needed
}

# --------------------------
# App setup
# --------------------------
app = dash.Dash(__name__)
app.title = "Global Energy Dashboard"
app.layout = html.Div(style={"height": "100vh", "width": "100vw", "overflow": "hidden", "backgroundColor": "#121212"}, children=[
    dcc.Graph(id="energy-map", style={"position": "absolute", "top": 0, "left": 0, "right": 0, "bottom": 0}),
    html.Div([
        html.Label("Select Energy Metric:", style={"color": "#eaeaea", "fontWeight": "bold"}),
        dcc.Dropdown(
            id="metric-dropdown",
            options=[{"label": metric_labels[m], "value": m} for m in metrics],
            value="natural_gas_cubic_meters",
            style={"width": "280px", "color": "#111"},
            clearable=False
        )
    ], style={
        "position": "absolute", "top": "20px", "right": "20px", "backgroundColor": "rgba(0,0,0,0.6)",
        "padding": "12px", "borderRadius": "8px", "zIndex": 1000
    }),
    html.Div([
        html.Div([
            html.Div("Country", style={"fontSize": "14px", "color": "#cccccc"}),
            html.Div(id="selected-country", style={"fontSize": "18px", "fontWeight": "bold", "color": "#ffffff"})
        ], style={
            "backgroundColor": "#3a3a3a",
            "padding": "12px 16px",
            "borderRadius": "10px",
            "marginBottom": "10px",
            "border": "1px solid black",
            "boxShadow": "0 0 10px rgba(0,0,0,0.4)"
        }),
        html.Div([
            html.Div("Energy Value", style={"fontSize": "14px", "color": "#cccccc"}),
            html.Div(id="energy-value", style={"fontSize": "18px", "fontWeight": "bold", "color":"#ffffff"})
        ], style={
            "backgroundColor": "#3a3a3a",
            "padding": "12px 16px",
            "borderRadius": "10px",
            "border": "1px solid black",
            "boxShadow": "0 0 10px rgba(0,0,0,0.4)"
        })
    ], style={
        "position": "absolute",
        "top": "20px",
        "left": "20px",
        "zIndex": 1000
    })
])
# --------------------------
# Map callback with zoom-to-country
# --------------------------
@app.callback(
    Output("energy-map", "figure"),
    Input("metric-dropdown", "value"),
    Input("energy-map", "clickData")
)
def update_map(metric, clickData):
    data = df[df[metric].notna()]
    selected_iso = None
    if clickData and "points" in clickData:
        selected_iso = clickData["points"][0].get("location")

    fig = px.choropleth_mapbox(
        data,
        geojson=geojson,
        locations="ISO3",
        color=metric,
        hover_name="Country",
        color_continuous_scale="Viridis",
        mapbox_style="carto-darkmatter",
        zoom=1.2,
        center={"lat": 20, "lon": 0},
        opacity=0.7,
        height=800
    )

    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        paper_bgcolor="#121212",
        font_color="#eaeaea",
        uirevision="metric"
    )

    fig.update_coloraxes(showscale=False)  # Remove colorbar

    # Zoom in and highlight selected country
    if selected_iso and selected_iso in country_coords:
        coords = country_coords[selected_iso]
        fig.update_layout(
            mapbox_zoom=3,
            mapbox_center={"lat": coords["lat"], "lon": coords["lon"]}
        )
        fig.add_trace(go.Choroplethmapbox(
            geojson=geojson,
            locations=[selected_iso],
            z=[1],
            colorscale=[[0, "#00a3ff"], [1, "#00a3ff"]],
            marker_line_width=1.5,
            marker_line_color="white",
            showscale=False,
            hoverinfo="skip"
        ))

    return fig

# --------------------------
# Text callback
# --------------------------
@app.callback(
    Output("selected-country", "children"),
    Output("energy-value", "children"),
    Input("energy-map", "clickData"),
    Input("metric-dropdown", "value")
)
def update_energy_value(clickData, metric):
    if clickData and "points" in clickData:
        iso = clickData["points"][0].get("location")
        row = df[df["ISO3"] == iso]
        if not row.empty:
            country = row["Country"].values[0]
            val = row[metric].values[0]
            if pd.isna(val):
                return f"{country}", f"{metric_labels.get(metric, metric)}: No data available"
            return f"{country}", f"{metric_labels.get(metric, metric)}: {val:,.0f}"
    return "", ""

# --------------------------
# Run
# --------------------------
if __name__ == "__main__":
    app.run(debug=True)
