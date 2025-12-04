import pandas as pd
import plotly.express as px
import country_converter as coco

def electricity_vs_poverty(cleaned_data):
    # Merge economy + energy + demographics
    merged = pd.merge(
        cleaned_data["economy"][["Country", "Population_Below_Poverty_Line_percent"]],
        cleaned_data["energy"][["Country", "electricity_access_percent"]],
        on="Country"
    )
    merged = pd.merge(
        merged,
        cleaned_data["demographics"][["Country", "Total_Population"]],
        on="Country",
        how="left"
    )

    merged["Total_Population"] = pd.to_numeric(merged["Total_Population"], errors="coerce")

    # Drop invalid entries
    invalid_entries = ["WORLD","EUROPEAN UNION","ARCTIC OCEAN","ATLANTIC OCEAN","INDIAN OCEAN","PACIFIC OCEAN"]
    merged = merged[~merged["Country"].str.upper().isin([x.upper() for x in invalid_entries])]

    # Add continent
    cc = coco.CountryConverter()
    merged["Region"] = cc.convert(names=merged["Country"], to="continent")

    # Bin population
    bins = [0, 10_000_000, 50_000_000, 200_000_000, 1_500_000_000]
    labels = ["Small (<10M)", "Medium (10–50M)", "Large (50–200M)", "Very Large (>200M)"]
    merged["Population_Group"] = pd.cut(merged["Total_Population"], bins=bins, labels=labels)

    # Drop rows with NaNs
    merged = merged.dropna(subset=[
        "Population_Below_Poverty_Line_percent",
        "electricity_access_percent",
        "Total_Population"
    ])

    # Plotly scatter with regression trendline
    fig = px.scatter(
        merged,
        x="Population_Below_Poverty_Line_percent",
        y="electricity_access_percent",
        color="Region",
        size="Total_Population",
        hover_name="Country",
        facet_col="Region",
        facet_col_wrap=2,   # fewer plots per row for readability
        trendline="ols",
        labels={
            "Population_Below_Poverty_Line_percent": "Population Below Poverty Line (%)",
            "electricity_access_percent": "Electricity Access (%)"
        },
        title="Electricity Access vs Poverty Levels by Region"
    )

    # Taller figure so each facet has space
    fig.update_layout(template="plotly_dark", legend_title="Region", height=900)
    return fig
