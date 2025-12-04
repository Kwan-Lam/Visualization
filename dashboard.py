import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import pycountry
import os
from country_centers import country_center
from clean_data import load_and_clean_separate

# ============================================================
# LOAD CLEANED DATA
# ============================================================
cleaned_data = load_and_clean_separate()

# Attach ISO3 codes
def get_iso3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except:
        return None

for df in cleaned_data.values():
    df["ISO3"] = df["Country"].apply(get_iso3)

datasets = {
    "energy": cleaned_data["energy"],
    "people": cleaned_data["demographics"],
    "geography": cleaned_data["geography"],
    "economy": cleaned_data["economy"]
}

# ============================================================
# ORIGINAL METRIC OPTIONS
# ============================================================
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

# ============================================================
# MERGED MULTILEVEL DASHBOARD DATASET
# ============================================================
df_multi = (
    datasets["energy"]
    .merge(datasets["people"], on="Country", how="left")
    .merge(datasets["geography"], on="Country", how="left")
    .merge(datasets["economy"], on="Country", how="left")
)

df_multi = df_multi.rename(columns={
    "Electricity_access_percent": "Electricity Access (%)",
    "Poverty_percent": "Poverty Rate (%)",
    "Agricultural_land_percent": "Agricultural Land (%)",
    "GDP_per_capita_USD": "GDP per Capita (USD)"
})

# ============================================================
# LOAD GEOJSON FOR WORLD MAP
# ============================================================
geojson_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
geojson = requests.get(geojson_url).json()

# ============================================================
# DASH APP + TABS
# ============================================================
app = dash.Dash(__name__)
app.title = "Global Data Dashboard"

app.layout = html.Div([
    dcc.Tabs(id="tabs", value="tab-map", children=[
        dcc.Tab(label="Global Map Dashboard", value="tab-map"),
        dcc.Tab(label="Multilevel Socio-Economic Dashboard", value="tab-multi")
    ]),

    html.Div(id="tab-content")
])


# ============================================================
# RENDER TAB CONTENT
# ============================================================
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value")
)
def render_tab(tab):

    if tab == "tab-map":
        return html.Div([
            dcc.Graph(id="world-map", style={"height": "90vh"}),

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
                        "border": "none"
                    }
                )
            ], style={
                "position": "absolute",
                "top": "80px",
                "right": "20px",
                "padding": "15px",
                "backgroundColor": "rgba(0,0,0,0.6)",
                "borderRadius": "10px",
                "width": "260px",
                "zIndex": 1000
            })
        ])

    # -----------------------------------------
    # MULTILEVEL DASHBOARD TAB (YOUR NEW CODE)
    # -----------------------------------------
    return html.Div(style={"padding": "30px"}, children=[
        html.H1("Multilevel Socio-Economic Visualization Dashboard"),

        html.H3("Scatterplot: Electricity Access vs Poverty"),
        dcc.Dropdown(
            id="land-category",
            options=[{"label": "Agricultural Land (%)", "value": "Agricultural Land (%)"}],
            value="Agricultural Land (%)",
            clearable=False
        ),
        dcc.Graph(id="scatter-plot"),

        html.Hr(),

        html.H3("Bar Chart: Agricultural Land vs GDP Per Capita Groups"),
        dcc.Slider(
            id="income-groups",
            min=3,
            max=7,
            step=1,
            value=4,
            marks={i: str(i) for i in range(3, 8)}
        ),
        dcc.Graph(id="bar-chart")
    ])


# ============================================================
# METRIC DROPDOWN CALLBACK (Original)
# ============================================================
@app.callback(
    Output("metric-dropdown", "options"),
    Output("metric-dropdown", "value"),
    Input("dataset-dropdown", "value")
)
def update_metric_dropdown(dataset_key):
    opts = metric_options[dataset_key]
    return [{"label": v, "value": k} for k, v in opts.items()], list(opts.keys())[0]


# ============================================================
# ORIGINAL WORLD MAP CALLBACK
# ============================================================
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
    if trigger == "world-map" and clickData:
        selected_iso = clickData["points"][0]["location"]
    elif trigger == "reset-btn":
        selected_iso = None

    fig = px.choropleth_mapbox(
        df, geojson=geojson, locations="ISO3", color=metric,
        hover_name="Country",
        mapbox_style="carto-darkmatter",
        color_continuous_scale="Sunset",
        zoom=1, center={"lat": 20, "lon": 0}, opacity=0.75
    )

    if selected_iso:
        fig.add_trace(
            go.Choroplethmapbox(
                geojson=geojson,
                locations=[selected_iso],
                z=[1],
                colorscale=[[0, "rgba(255,0,0,0.35)"], [1, "rgba(255,0,0,0.35)"]],
                marker=dict(line=dict(width=4, color="#FF0000")),
                showscale=False
            )
        )

        if selected_iso in country_center:
            fig.update_layout(
                mapbox_zoom=2.5,
                mapbox_center=country_center[selected_iso]
            )

    return fig


# ============================================================
# MULTILEVEL DASHBOARD CALLBACKS
# ============================================================

@app.callback(
    Output("scatter-plot", "figure"),
    Input("land-category", "value")
)
def update_scatter(land_col):

    fig = px.scatter(
        df_multi,
        x="GDP per Capita (USD)",
        y="Poverty Rate (%)",
        size="Electricity Access (%)",
        color="Poverty Rate (%)",
        symbol=land_col,
        hover_name="Country",
        template="plotly_white"
    )

    fig.update_layout(
        title="Electricity Access vs Poverty (Design: Position=GDP, Color=Poverty, Shape=Land Use)"
    )
    return fig


@app.callback(
    Output("bar-chart", "figure"),
    Input("income-groups", "value")
)
def update_bar(num_groups):

    df2 = df_multi.copy()
    df2["GDP Group"] = pd.qcut(
        df2["GDP per Capita (USD)"],
        num_groups,
        labels=[f"Group {i+1}" for i in range(num_groups)]
    )

    fig = px.bar(
        df2.groupby("GDP Group")["Agricultural Land (%)"].mean().reset_index(),
        x="GDP Group",
        y="Agricultural Land (%)",
        template="plotly_white"
    )

    fig.update_layout(
        title="Agricultural Land % Across GDP Income Groups"
    )
    return fig


# ============================================================
# RUN APP
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
