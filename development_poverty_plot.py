import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_agriculture_insights(cleaned_data):
    # 1. Merge Economy + Geography
    # We need Real_GDP_per_Capita_USD from economy
    # And Agricultural_Land, Arable_Land, Permanent_Crops, Permanent_Pasture, Irrigated_Land from geography

    economy_df = cleaned_data.get("economy", pd.DataFrame())
    geography_df = cleaned_data.get("geography", pd.DataFrame())

    if economy_df.empty or geography_df.empty:
        return go.Figure().update_layout(title="Missing Data for Agriculture Plots")

    # Select relevant columns
    eco_cols = ["Country", "Real_GDP_per_Capita_USD"]
    geo_cols = [
        "Country",
        "Agricultural_Land",
        "Arable_Land (percentage of Total Agricultural Land)",
        "Permanent_Crops (percentage of Total Agricultural Land)",
        "Permanent_Pasture (percentage of Total Agricultural Land)",
        "Irrigated_Land"
    ]

    # Check if columns exist (handle potential naming mismatches or missing cols)
    # The user provided specific column names, but let's be safe with intersection
    eco_cols = [c for c in eco_cols if c in economy_df.columns]
    geo_cols = [c for c in geo_cols if c in geography_df.columns]

    merged = pd.merge(
        economy_df[eco_cols],
        geography_df[geo_cols],
        on="Country"
    )

    # 2. Data Cleaning & Type Conversion
    # clean_data.py might have already done some, but let's ensure numeric
    cols_to_numeric = [
        "Real_GDP_per_Capita_USD",
        "Agricultural_Land",
        "Arable_Land (percentage of Total Agricultural Land)",
        "Permanent_Crops (percentage of Total Agricultural Land)",
        "Permanent_Pasture (percentage of Total Agricultural Land)",
        "Irrigated_Land"
    ]

    for col in cols_to_numeric:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce')

    # Drop rows where essential data is missing
    merged = merged.dropna(subset=["Real_GDP_per_Capita_USD", "Agricultural_Land"])

    # 3. Bin GDP into Groups
    # Define bins: Low (<1000), Lower-Middle (1000-4000), Upper-Middle (4000-12000), High (>12000)
    # Adjusting bins for better distribution if needed, but standard World Bank approx is fine
    bins = [0, 2500, 10000, 25000, 1000000]
    labels = ["Low Income (<$2.5k)", "Lower-Middle ($2.5k-10k)", "Upper-Middle ($10k-25k)", "High Income (>$25k)"]

    merged["GDP_Group"] = pd.cut(merged["Real_GDP_per_Capita_USD"], bins=bins, labels=labels)

    # 4. Create Visualizations

    # Plot 1: Bar Chart - Average Agricultural Land % by GDP Group
    avg_agri = merged.groupby("GDP_Group", observed=False)["Agricultural_Land"].mean().reset_index()

    fig1 = px.bar(
        avg_agri,
        x="GDP_Group",
        y="Agricultural_Land",
        title="Average Agricultural Land (%) by GDP Group",
        labels={"Agricultural_Land": "Avg Agricultural Land (%)", "GDP_Group": "Income Group"},
        color="GDP_Group",
        color_discrete_sequence=px.colors.sequential.Greens
    )

    # Plot 2: Scatter Plot - GDP vs Agricultural Land
    fig2 = px.scatter(
        merged,
        x="Real_GDP_per_Capita_USD",
        y="Agricultural_Land",
        hover_name="Country",
        color="GDP_Group",
        log_x=True,
        title="GDP per Capita vs. Agricultural Land (%)",
        labels={"Real_GDP_per_Capita_USD": "GDP per Capita (Log Scale)", "Agricultural_Land": "Agricultural Land (%)"}
    )

    # Plot 3: Stacked Bar - Composition of Agricultural Land
    # Arable + Permanent Crops + Permanent Pasture should approx sum to 100% of Ag Land usage
    # We want to see how this composition changes by GDP Group

    comp_cols = [
        "Arable_Land (percentage of Total Agricultural Land)",
        "Permanent_Crops (percentage of Total Agricultural Land)",
        "Permanent_Pasture (percentage of Total Agricultural Land)"
    ]

    # Check if these columns exist
    valid_comp_cols = [c for c in comp_cols if c in merged.columns]

    if valid_comp_cols:
        avg_comp = merged.groupby("GDP_Group", observed=False)[valid_comp_cols].mean().reset_index()

        # Melt for stacked bar
        avg_comp_melted = avg_comp.melt(id_vars="GDP_Group", value_vars=valid_comp_cols, var_name="Land Type",
                                        value_name="Percentage")

        # Shorten names for legend
        avg_comp_melted["Land Type"] = avg_comp_melted["Land Type"].replace({
            "Arable_Land (percentage of Total Agricultural Land)": "Arable",
            "Permanent_Crops (percentage of Total Agricultural Land)": "Crops",
            "Permanent_Pasture (percentage of Total Agricultural Land)": "Pasture"
        })

        fig3 = px.bar(
            avg_comp_melted,
            x="GDP_Group",
            y="Percentage",
            color="Land Type",
            title="Composition of Agricultural Land by GDP Group",
            barmode="stack",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
    else:
        fig3 = go.Figure()

    # Combine into subplots
    # Layout:
    # Row 1: Bar Chart (Fig 1) | Stacked Bar (Fig 3)
    # Row 2: Scatter Plot (Fig 2) (Full Width)

    final_fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"type": "xy"}, {"type": "xy"}],
               [{"colspan": 2, "type": "xy"}, None]],
        subplot_titles=("Avg Agricultural Land % by Income", "Agri Land Composition",
                        "GDP vs Agricultural Land Distribution"),
        vertical_spacing=0.15
    )

    # Add traces from Fig 1
    for trace in fig1.data:
        final_fig.add_trace(trace, row=1, col=1)

    # Add traces from Fig 3
    for trace in fig3.data:
        final_fig.add_trace(trace, row=1, col=2)

    # Add traces from Fig 2
    for trace in fig2.data:
        # We need to handle legend groups to avoid duplicates if we want,
        # but for simplicity let's just add them.
        # To avoid legend clutter, we can hide legend for scatter if it's redundant with bar,
        # but they use different color mappings (one is discrete seq, one is same categories).
        trace.showlegend = False  # Hide scatter legend to avoid duplicates with Fig 1
        final_fig.add_trace(trace, row=2, col=1)

    final_fig.update_layout(
        template="plotly_dark",
        height=900,
        title_text="Agriculture & Economic Insights",
        showlegend=True
    )

    return final_fig

# import pandas as pd
# import plotly.express as px
# import country_converter as coco
#
# def development_vs_poverty(cleaned_data):
#     # Merge economy + energy + demographics
#     merged = pd.merge(
#         cleaned_data["economy"][["Country", "Real_GDP_per_Capita_USD"]],
#         cleaned_data["geography"][["Country", "Agricultural_Land", "Arable_Land (%% of Total Agricultural Land)", "Permanent_Crops (%% of Total Agricultural Land)", "Permanent_Pasture (%% of Total Agricultural Land)", "Irrigated_Land"]],
#         on="Country"
#     )
#     # merged = pd.merge(
#     #     merged,
#     #     cleaned_data["demographics"][["Country", "Total_Population"]],
#     #     on="Country",
#     #     how="left"
#     # )
#     #
#     # merged["Total_Population"] = pd.to_numeric(merged["Total_Population"], errors="coerce")
#
#     # Drop invalid entries
#     invalid_entries = ["WORLD","EUROPEAN UNION","ARCTIC OCEAN","ATLANTIC OCEAN","INDIAN OCEAN","PACIFIC OCEAN"]
#     merged = merged[~merged["Country"].str.upper().isin([x.upper() for x in invalid_entries])]
#
#     # Add continent
#     cc = coco.CountryConverter()
#     merged["Region"] = cc.convert(names=merged["Country"], to="continent")
#
#     # # Bin population
#     # bins = [0, 10_000_000, 50_000_000, 200_000_000, 1_500_000_000]
#     # labels = ["Small (<10M)", "Medium (10–50M)", "Large (50–200M)", "Very Large (>200M)"]
#     # merged["Population_Group"] = pd.cut(merged["Total_Population"], bins=bins, labels=labels)
#
#     # Drop rows with NaNs
#     merged = merged.dropna(subset=[
#         "Real_GDP_per_Capita_USD",
#         "Agricultural_Land",
#         # "Total_Population"
#     ])
#
#     # Plotly scatter with regression trendline
#     fig = px.scatter(
#         merged,
#         x="Real_GDP_per_Capita_USD",
#         y="Agricultural_Land",
#         color="Region",
#         hover_name="Country",
#         facet_col="Region",
#         facet_col_wrap=2,   # fewer plots per row for readability
#         trendline="ols",
#         labels={
#             "Real_GDP_per_Capita_USD": "Real GDP per Capita (USD)",
#             "Agricultural_Land": "Agricultural Land"
#         },
#         title="Real GDP per Capita vs Agricultural Land"
#     )
#
#     # Taller figure so each facet has space
#     fig.update_layout(template="plotly_dark", legend_title="Region", height=900)
#     return fig
