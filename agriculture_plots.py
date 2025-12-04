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
    
    # Plot 4: Correlation Heatmap
    # Calculate correlation matrix for numeric columns
    corr_cols = [
        "Real_GDP_per_Capita_USD", 
        "Agricultural_Land", 
        "Arable_Land (percentage of Total Agricultural Land)",
        "Permanent_Crops (percentage of Total Agricultural Land)",
        "Permanent_Pasture (percentage of Total Agricultural Land)",
        "Irrigated_Land"
    ]
    # Filter for existing columns
    valid_corr_cols = [c for c in corr_cols if c in merged.columns]
    
    if len(valid_corr_cols) > 1:
        corr_matrix = merged[valid_corr_cols].corr()
        
        # Shorten names for better readability in heatmap
        short_names = {
            "Real_GDP_per_Capita_USD": "GDP/Capita",
            "Agricultural_Land": "Agri Land %",
            "Arable_Land (percentage of Total Agricultural Land)": "Arable %",
            "Permanent_Crops (percentage of Total Agricultural Land)": "Crops %",
            "Permanent_Pasture (percentage of Total Agricultural Land)": "Pasture %",
            "Irrigated_Land": "Irrigated"
        }
        
        corr_matrix.rename(index=short_names, columns=short_names, inplace=True)
        
        fig4 = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            title="Correlation Matrix",
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1
        )
    else:
        fig4 = go.Figure()

    # Return dictionary of figures
    figures = {}
    
    # Update layouts for individual figures
    fig1.update_layout(template="plotly_dark", title_text="Average Agricultural Land (%) by GDP Group")
    figures["bar"] = fig1
    
    fig2.update_layout(template="plotly_dark", title_text="GDP per Capita vs. Agricultural Land (%)")
    figures["scatter"] = fig2
    
    fig4.update_layout(template="plotly_dark", title_text="Correlation Matrix")
    figures["heatmap"] = fig4
    
    return figures
