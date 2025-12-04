# app.py
import os
import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import pycountry
from clean_data import load_and_clean_separate
from country_centers import country_center  # assumed present in your project

# -------------------------
# Minor helper utilities
# -------------------------
def safe_get_column(df, col, default=None):
    """Return a column if present else default series of NaNs."""
    if col in df.columns:
        return df[col]
    else:
        return pd.Series([default] * len(df), index=df.index)

def get_iso3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except Exception:
        return None

def clean_numeric_columns(df, exclude_cols=("Country", "ISO3")):
    for col in df.columns:
        if col in exclude_cols:
            continue
        # attempt to strip commas, percent, and whitespace
        try:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", "")
                .str.replace("%", "")
                .str.strip()
                .replace("", np.nan)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
        except Exception:
            # if conversion fails, leave as-is
            pass
    return df

def make_card(title, graph_component):
    """Simple visual card wrapper."""
    return html.Div(
        children=[
            html.Div(title, style={"fontWeight": "600", "marginBottom": "6px", "color":"white"}),
            graph_component
        ],
        style={
            "backgroundColor": "#1e1e1e",
            "padding": "10px",
            "borderRadius": "8px",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.5)",
            "marginBottom":"10px"
        },
    )

# -------------------------
# Load and prepare datasets
# -------------------------
cleaned_data = load_and_clean_separate()

# ensure we have the expected datasets keys
for required in ["energy", "demographics", "economy"]:
    if required not in cleaned_data:
        cleaned_data[required] = pd.DataFrame()

# Add ISO3 to all datasets (if Country present)
for k, df in cleaned_data.items():
    if "Country" in df.columns:
        df["ISO3"] = df["Country"].apply(get_iso3)
    else:
        # create placeholder Country and ISO3 columns to avoid KeyError
        df["Country"] = df.get("Country", pd.Series([None]*len(df)))
        df["ISO3"] = df.get("ISO3", pd.Series([None]*len(df)))
    cleaned_data[k] = clean_numeric_columns(df)

# For convenience, create a combined dataset for socio-economic analysis.
# We'll do a left-join on Country (prioritizing economy columns for GDP)
economy = cleaned_data.get("economy", pd.DataFrame()).copy()
demographics = cleaned_data.get("demographics", pd.DataFrame()).copy()
energy = cleaned_data.get("energy", pd.DataFrame()).copy()

# Standard column names expected (as you confirmed)
# Country, Agricultural_Land, Real_GDP_per_Capita_USD, Income_Group,
# Population_Below_Poverty_Line_percent, electricity_access_percent, Land_Use_Category (optional)

# Merge on Country (best-effort)
merged = economy.copy()
# ensure Country exists
if "Country" not in merged.columns:
    merged["Country"] = economy.index.astype(str)

for src in [demographics, energy]:
    if "Country" in src.columns:
        cols_to_take = [c for c in src.columns if c not in merged.columns or c in (
            "Agricultural_Land", "Population_Below_Poverty_Line_percent",
            "electricity_access_percent", "Land_Use_Category", "Income_Group"
        )]
        # prefer columns that exist in src
        cols_to_take = [c for c in cols_to_take if c in src.columns and c != "ISO3"]
        if cols_to_take:
            merged = merged.merge(src[["Country"] + cols_to_take], on="Country", how="left", suffixes=("", "_y"))

# Clean numeric conversions on merged
merged = clean_numeric_columns(merged)

# Ensure ISO3 exists
if "ISO3" not in merged.columns or merged["ISO3"].isna().all():
    merged["ISO3"] = merged["Country"].apply(get_iso3)

# Dataset dictionary for map and other uses
datasets = {
    "energy": energy,
    "demographics": demographics,
    "economy": economy,
    "merged": merged
}

# -------------------------
# Load world geojson
# -------------------------
geojson_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
try:
    geojson = requests.get(geojson_url, timeout=10).json()
except Exception:
    geojson = None

# -------------------------
# Dash app + layout
# -------------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Global Data Dashboard — Agricultural Dependence"

# add assets/style.css to remove white margins and dark theme (if missing)
os.makedirs("assets", exist_ok=True)
with open("assets/style.css", "w") as f:
    f.write("""
        body, html {
            margin: 0 !important;
            padding: 0 !important;
            background-color: #121212 !important;
            color: #eee;
        }
        .dash-graph {
            margin: 0 !important;
            padding: 0 !important;
        }
    """)

# Derive dropdown values
income_groups = merged["Income_Group"].dropna().unique().tolist() if "Income_Group" in merged.columns else []
income_groups.sort()
metric_options_agri = [
    {"label": "Agricultural Land (%)", "value": "Agricultural_Land"},
    {"label": "GDP per Capita (USD)", "value": "Real_GDP_per_Capita_USD"},
    {"label": "Poverty (%)", "value": "Population_Below_Poverty_Line_percent"},
    {"label": "Electricity Access (%)", "value": "electricity_access_percent"}
]

# Main layout
app.layout = html.Div(style={"backgroundColor": "#121212", "minHeight": "100vh", "padding":"6px"}, children=[
    html.Div([
        html.H2("Global Data Dashboard", style={"margin":"6px 0 6px 8px", "color":"white"}),
        html.Div("Multilevel Agricultural Dependence Dashboard — Agricultural land % vs GDP per capita", style={"color":"#cfcfcf", "marginBottom":"6px"})
    ]),

    dcc.Tabs(id="main-tabs", value="tab-world", children=[
        dcc.Tab(label="World Map", value="tab-world", style={"background":"#151515", "color":"#ddd"}, selected_style={"background":"#0f0f0f", "color":"white"}),
        dcc.Tab(label="Agricultural Dependence", value="tab-agri", style={"background":"#151515", "color":"#ddd"}, selected_style={"background":"#0f0f0f", "color":"white"}),
    ]),

    html.Div(id="tab-content", style={"padding":"10px"})
])

# -------------------------
# Tab content generator
# -------------------------
def world_map_layout():
    return html.Div([
        html.Div([
            html.Div([
                html.Label("Dataset:", style={"color":"white"}),
                dcc.Dropdown(
                    id="dataset-dropdown",
                    options=[
                        {"label": "Energy", "value": "energy"},
                        {"label": "Demographics", "value": "demographics"},
                        {"label": "Economy", "value": "economy"},
                        {"label": "Merged (analysis)", "value": "merged"}
                    ],
                    value="merged",
                    clearable=False,
                    style={"width":"260px"}
                ),
            ], style={"display":"inline-block", "verticalAlign":"top", "marginRight":"12px"}),

            html.Div([
                html.Label("Metric:", style={"color":"white"}),
                dcc.Dropdown(id="map-metric-dropdown", clearable=False, style={"width":"260px"})
            ], style={"display":"inline-block", "verticalAlign":"top", "marginRight":"12px"}),

            html.Button("Reset Selection", id="map-reset-btn", n_clicks=0, style={"marginLeft":"10px"})
        ], style={"marginBottom":"8px"}),

        dcc.Graph(id="world-map-graph", style={"height":"70vh"})
    ])

def agriculture_layout():
    # controls + 3 graphs (scatter, bar, heatmap)
    return html.Div([
        html.Div([
            # left controls
            html.Div([
                html.Label("Income Group (multi)", style={"color":"white"}),
                dcc.Dropdown(id="agri-income-dropdown", options=[{"label": ig, "value": ig} for ig in income_groups],
                             multi=True, placeholder="Filter by income group", value=income_groups[:]),
                html.Br(),
                html.Label("Color Metric (for heatmap / color scale)", style={"color":"white"}),
                dcc.Dropdown(id="agri-color-metric", options=metric_options_agri, value="Population_Below_Poverty_Line_percent", clearable=False),
                html.Br(),
                html.Label("Agricultural Land % range", style={"color":"white"}),
                dcc.RangeSlider(id="agri-land-range",
                                min=0, max=100, step=0.5,
                                value=[0, 100],
                                marks={0:"0", 25:"25", 50:"50", 75:"75", 100:"100"}),
                html.Br(),
                html.Label("GDP per Capita range (USD)", style={"color":"white"}),
                dcc.RangeSlider(id="agri-gdp-range",
                                min=0, max=100000, step=500,
                                value=[0, 50000],
                                marks={0:"0", 10000:"10k", 30000:"30k", 60000:"60k"}),
                html.Br(),
                html.Button("Reset Filters", id="agri-reset", n_clicks=0, style={"width":"100%"}),
                html.Br(), html.Br(),
                html.Div("Click on a scatter point to focus on a country (also highlights it on world map).", style={"color":"#cfcfcf", "fontSize":"12px"})
            ], style={"width":"320px", "display":"inline-block", "verticalAlign":"top", "paddingRight":"10px"}),

            # right: graphs
            html.Div([
                html.Div(id="agri-top-row", children=[
                    # two cards side-by-side
                    html.Div(make_card("Agricultural Land vs GDP per Capita", dcc.Graph(id="agri-scatter", config={"displayModeBar": False})), style={"width":"66%", "display":"inline-block", "paddingRight":"8px", "verticalAlign":"top"}),
                    html.Div(make_card("Agricultural Land By Income Group (mean)", dcc.Graph(id="agri-bar", config={"displayModeBar": False})), style={"width":"33%", "display":"inline-block", "verticalAlign":"top"})
                ], style={"display":"flex", "gap":"10px"}),

                # heatmap below
                html.Div(make_card("Correlation Heatmap (selected subset)", dcc.Graph(id="agri-heatmap", config={"displayModeBar": False})), style={"marginTop":"10px"})
            ], style={"display":"inline-block", "width":"calc(100% - 340px)", "verticalAlign":"top"})
        ], style={"display":"flex", "alignItems":"flex-start"})
    ])

# -------------------------
# Render tab content
# -------------------------
@app.callback(Output("tab-content", "children"), Input("main-tabs", "value"))
def render_tab(tab):
    if tab == "tab-world":
        return world_map_layout()
    elif tab == "tab-agri":
        return agriculture_layout()
    return html.Div("Unknown tab")

# -------------------------
# Populate map metric dropdown based on selected dataset
# -------------------------
@app.callback(
    Output("map-metric-dropdown", "options"),
    Output("map-metric-dropdown", "value"),
    Input("dataset-dropdown", "value")
)
def update_map_metrics(dataset_key):
    df = datasets.get(dataset_key, pd.DataFrame())
    # find numeric-ish columns for selection
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in ("ISO3",)]
    # fallback options
    if not numeric_cols:
        numeric_cols = ["Real_GDP_per_Capita_USD"] if "Real_GDP_per_Capita_USD" in merged.columns else []
    opts = [{"label": c, "value": c} for c in numeric_cols]
    val = numeric_cols[0] if numeric_cols else None
    return opts, val

# -------------------------
# World map callback (handles clicks, reset)
# -------------------------
@app.callback(
    Output("world-map-graph", "figure"),
    Input("dataset-dropdown", "value"),
    Input("map-metric-dropdown", "value"),
    Input("world-map-graph", "clickData"),
    Input("map-reset-btn", "n_clicks"),
    State("main-tabs", "value")
)
def update_world_map(dataset_key, metric, clickData, reset_clicks, current_tab):
    df = datasets.get(dataset_key, pd.DataFrame()).copy()
    # Safeguard columns
    if "ISO3" not in df.columns:
        df["ISO3"] = df.get("Country", pd.Series([None]*len(df))).apply(get_iso3)

    selected_iso = None
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    if trigger == "world-map-graph" and clickData and "points" in clickData:
        selected_iso = clickData["points"][0].get("location") or clickData["points"][0].get("customdata")
    elif trigger == "map-reset-btn":
        selected_iso = None

    # If metric missing, choose a fallback
    if metric is None or metric not in df.columns:
        metric = next((c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != "ISO3"), None)

    # Build choropleth map
    if geojson is None:
        # fallback: scatter mapbox using centers dict
        fig = go.Figure()
        lats = []
        lons = []
        texts = []
        vals = []
        for _, row in df.iterrows():
            iso = row.get("ISO3")
            if iso in country_center:
                latlon = country_center[iso]
                lats.append(latlon["lat"])
                lons.append(latlon["lon"])
                texts.append(f"{row.get('Country')}<br>{metric}: {row.get(metric)}")
                vals.append(row.get(metric))
        fig = px.scatter_mapbox(lat=lats, lon=lons, hover_name=texts, color=vals)
        fig.update_layout(mapbox_style="carto-positron", mapbox_zoom=1, mapbox_center={"lat":20,"lon":0})
    else:
        fig = px.choropleth_mapbox(
            df,
            geojson=geojson,
            locations="ISO3",
            color=metric,
            hover_name="Country",
            color_continuous_scale="Viridis",
            mapbox_style="carto-darkmatter",
            zoom=1,
            center={"lat": 20, "lon": 0},
            opacity=0.75,
        )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
    fig.update_traces(marker_line_width=0.4, marker_line_color="#222")
    # highlight selected country if any
    if selected_iso:
        fig.add_trace(
            go.Choroplethmapbox(
                geojson=geojson,
                locations=[selected_iso],
                z=[1],
                colorscale=[[0, "rgba(255,0,0,0.35)"], [1, "rgba(255,0,0,0.35)"]],
                marker=dict(line=dict(width=4, color="#ff0000")),
                showscale=False,
                hoverinfo="skip"
            )
        )
        if selected_iso in country_center:
            fig.update_layout(mapbox_zoom=2.5, mapbox_center=country_center[selected_iso])

    return fig

# -------------------------
# Agricultural dashboard callbacks
# -------------------------
@app.callback(
    Output("agri-scatter", "figure"),
    Output("agri-bar", "figure"),
    Output("agri-heatmap", "figure"),
    Input("agri-income-dropdown", "value"),
    Input("agri-color-metric", "value"),
    Input("agri-land-range", "value"),
    Input("agri-gdp-range", "value"),
    Input("agri-reset", "n_clicks"),
    Input("main-tabs", "value"),
    Input("agri-scatter", "clickData"),
    prevent_initial_call=False
)
def update_agriculture_widgets(selected_income, color_metric, land_range, gdp_range, reset_clicks, current_tab, scatter_click):
    # work on merged dataset
    df = merged.copy()
    # handle missing columns gracefully with defaults
    df["Agricultural_Land"] = safe_get_column(df, "Agricultural_Land", np.nan)
    df["Real_GDP_per_Capita_USD"] = safe_get_column(df, "Real_GDP_per_Capita_USD", np.nan)
    df["Population_Below_Poverty_Line_percent"] = safe_get_column(df, "Population_Below_Poverty_Line_percent", np.nan)
    df["electricity_access_percent"] = safe_get_column(df, "electricity_access_percent", np.nan)
    df["Income_Group"] = safe_get_column(df, "Income_Group", "Unknown")
    df["Land_Use_Category"] = safe_get_column(df, "Land_Use_Category", "Other")

    # Filters
    if isinstance(selected_income, list) and selected_income:
        df = df[df["Income_Group"].isin(selected_income)]
    # agricultural land range
    try:
        low_land, high_land = land_range
        df = df[(df["Agricultural_Land"].fillna(-999) >= low_land) & (df["Agricultural_Land"].fillna(999) <= high_land)]
    except Exception:
        pass
    # GDP range
    try:
        low_gdp, high_gdp = gdp_range
        df = df[(df["Real_GDP_per_Capita_USD"].fillna(-1) >= low_gdp) & (df["Real_GDP_per_Capita_USD"].fillna(1e12) <= high_gdp)]
    except Exception:
        pass

    # ---------------- Scatter ----------------
    # shape encoding via Land_Use_Category -> map to symbols
    unique_landcats = df["Land_Use_Category"].dropna().unique().tolist()
    symbol_map = {}
    symbols_available = ["circle","diamond","square","triangle-up","cross","x","pentagon","star"]
    for i, cat in enumerate(unique_landcats):
        symbol_map[cat] = symbols_available[i % len(symbols_available)]

    # Build scatter
    scatter_kwargs = dict(
        data_frame=df,
        x="Agricultural_Land",
        y="Real_GDP_per_Capita_USD",
        hover_name="Country",
        color="Income_Group",
        symbol="Land_Use_Category" if "Land_Use_Category" in df.columns else None,
        title="Agricultural Land vs GDP per Capita",
        labels={"Agricultural_Land":"Agricultural Land (%)", "Real_GDP_per_Capita_USD":"GDP per Capita (USD)"},
        template="plotly_dark",
        height=480
    )
    # remove None keys
    scatter_kwargs = {k:v for k,v in scatter_kwargs.items() if v is not None}
    fig_scatter = px.scatter(**scatter_kwargs)
    # apply symbol mapping if possible
    if "Land_Use_Category" in df.columns:
        for cat, sym in symbol_map.items():
            fig_scatter.update_traces(selector=dict(name=cat), marker_symbol=sym)

    fig_scatter.update_layout(paper_bgcolor="#2e2e2e", plot_bgcolor="#2e2e2e", legend=dict(itemsizing="constant"))
    fig_scatter.update_traces(marker=dict(size=9, line=dict(width=0.5, color="#222")))

    # if user clicked on a point, add highlight
    selected_iso = None
    if scatter_click and "points" in scatter_click:
        # scatter click may give hovertext with Country; try to read it
        p = scatter_click["points"][0]
        country_clicked = p.get("hovertext") or p.get("customdata") or p.get("text") or p.get("label")
        # find ISO3
        if country_clicked:
            matched = df[df["Country"] == country_clicked]
            if not matched.empty:
                selected_iso = matched.iloc[0].get("ISO3")

        # Add an annotation marker for clicked point on the scatter
        try:
            fig_scatter.add_trace(
                go.Scatter(
                    x=[p.get("x")],
                    y=[p.get("y")],
                    mode="markers",
                    marker=dict(size=16, color="rgba(255,0,0,0.8)", symbol="star"),
                    showlegend=False,
                    hoverinfo="skip"
                )
            )
        except Exception:
            pass

    # ---------------- Bar (mean agricultural land by Income Group) ----------------
    bar_df = df.groupby("Income_Group", dropna=False)["Agricultural_Land"].mean().reset_index().sort_values("Agricultural_Land", ascending=False)
    fig_bar = px.bar(bar_df, x="Income_Group", y="Agricultural_Land",
                     labels={"Agricultural_Land":"Mean Agricultural Land (%)", "Income_Group":"Income Group"},
                     template="plotly_dark", height=420)
    fig_bar.update_layout(paper_bgcolor="#2e2e2e", plot_bgcolor="#2e2e2e")

    # ---------------- Heatmap (correlations) ----------------
    # compute correlation among selected metrics
    hm_metrics = ["Agricultural_Land", "Real_GDP_per_Capita_USD", "Population_Below_Poverty_Line_percent", "electricity_access_percent"]
    hm_df = df[hm_metrics].copy()
    corr = hm_df.corr()
    fig_hm = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.index,
        zmin=-1, zmax=1,
        colorbar=dict(title="r")
    ))
    fig_hm.update_layout(title="Correlation Matrix", template="plotly_dark", paper_bgcolor="#2e2e2e", plot_bgcolor="#2e2e2e", height=420)

    return fig_scatter, fig_bar, fig_hm

# -------------------------
# Start server
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
