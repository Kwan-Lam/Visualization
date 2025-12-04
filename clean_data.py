import pandas as pd
import numpy as np

def data_cleaner(df: pd.DataFrame, cat: list):
    for i in cat:
        for idx, val in df[i].items():
            if not pd.isnull(val):
                try:
                    df.loc[idx, i] = float(val)
                except:
                    v = str(val)
                    try:
                        v = v.replace("%", "")
                        v = v.replace(" sq km", "")
                        v = v.replace(" km", "")
                        v = v.replace(" m", "")
                        v = v.replace(",", "")

                        if "illion" in v:
                            v = v.replace("illion", "")
                            v = float(v) * 1_000_000
                            df.loc[idx, i] = v

                        elif "(percentage)" in v and "Total_Population" in df.columns:
                            v = v.replace(" (percentage)", "")
                            v = float(v)
                            v = round(v * 0.01 * float(df["Total_Population"][idx]))
                            df.loc[idx, i] = v

                        elif any(x in v for x in ["NEGL", "negligible", "Ile Amsterdam"]):
                            df.loc[idx, i] = np.nan

                        elif "Democracy" in v:
                            df.loc[idx, i] = 0
                        elif "Republic" in v:
                            df.loc[idx, i] = 1
                        elif "Theocracy" in v:
                            df.loc[idx, i] = 2
                        elif "Monarchy" in v:
                            df.loc[idx, i] = 3
                        elif "Communist" in v:
                            df.loc[idx, i] = 4
                        elif "Territory" in v:
                            df.loc[idx, i] = 5
                        elif "Other" in v:
                            df.loc[idx, i] = 6
                        else:
                            df.loc[idx, i] = float(v)
                    except:
                        pass
        # Safely convert column to float
        df[i] = pd.to_numeric(df[i], errors='coerce')
    return df

def clean_outliers(df: pd.DataFrame, clean_list: list, del_list: list):
    for country, cat in clean_list:
        if cat in df.columns:
            df.loc[df["Country"] == country, cat] = np.nan
    for country in del_list:
        df.drop(df[df["Country"] == country].index, inplace=True)
    return df

def load_and_clean_separate():
    datasets = {
       "communications": pd.read_csv("CIA Global Statistical Database\\communications_data.csv", delimiter=",", low_memory=False),
        "demographics": pd.read_csv("CIA Global Statistical Database\\demographics_data.csv", delimiter=",", low_memory=False),
        "economy": pd.read_csv("CIA Global Statistical Database\\economy_data.csv", delimiter=",", low_memory=False),
        "energy": pd.read_csv("CIA Global Statistical Database\\energy_data.csv", delimiter=",", low_memory=False),
        "geography": pd.read_csv("CIA Global Statistical Database\\geography_data.csv", delimiter=",", low_memory=False),
        "government": pd.read_csv("CIA Global Statistical Database\\government_and_civics_data.csv", delimiter=",", low_memory=False),
        "transportation": pd.read_csv("CIA Global Statistical Database\\transportation_data.csv", delimiter=",", low_memory=False),
    }

    exclude_cols = ["Country", "internet_country_code", "Fiscal_Year", "Geographic_Coordinates", "Capital", "Capital_Coordinates"]

    clean_list = [
        ["EUROPEAN UNION", "Birth_Rate"],
        ["EUROPEAN UNION", "Death_Rate"],
        ["EUROPEAN UNION", "Total_Fertility_Rate"],
        ["EUROPEAN UNION", "Male_Literacy_Rate"],
        ["EUROPEAN UNION", "Female_Literacy_Rate"],
        ["TOKELAU", "Death_Rate"],
        ["TOKELAU", "Real_GDP_PPP_billion_USD"],
        ["TOKELAU", "Budget_billion_USD"],
        ["TOKELAU", "Exports_billion_USD"]
    ]
    del_list = []

    for name, df in datasets.items():
        columns = [col for col in df.columns if col not in exclude_cols]
        datasets[name] = data_cleaner(df, columns)
        datasets[name] = clean_outliers(datasets[name], clean_list, del_list)

    return datasets
