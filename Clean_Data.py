import pandas as pd
import numpy as np


def load_clean_data():
    # Load data
    df_CIA_communications = pd.read_csv("CIA Global Statistical Database\\communications_data.csv", delimiter=",", low_memory=False)
    df_CIA_demographics = pd.read_csv("CIA Global Statistical Database\\demographics_data.csv", delimiter=",", low_memory=False)
    df_CIA_economy = pd.read_csv("CIA Global Statistical Database\\economy_data.csv", delimiter=",", low_memory=False)
    df_CIA_energy = pd.read_csv("CIA Global Statistical Database\\energy_data.csv", delimiter=",", low_memory=False)
    df_CIA_geography = pd.read_csv("CIA Global Statistical Database\\geography_data.csv", delimiter=",", low_memory=False)
    df_CIA_government_and_civics = pd.read_csv("CIA Global Statistical Database\\government_and_civics_data.csv", delimiter=",", low_memory=False)
    df_CIA_transportation = pd.read_csv("CIA Global Statistical Database\\transportation_data.csv", delimiter=",", low_memory=False)

    # Merge data
    df_total = pd.merge(df_CIA_communications, df_CIA_demographics, on="Country")
    df_total = pd.merge(df_total, df_CIA_economy, on="Country")
    df_total = pd.merge(df_total, df_CIA_energy, on="Country")
    df_total = pd.merge(df_total, df_CIA_geography, on="Country")
    df_total = pd.merge(df_total, df_CIA_government_and_civics, on="Country", how="left")
    df_total = pd.merge(df_total, df_CIA_transportation, on="Country")

    # Fix faulty data function
    def data_cleaner(df: pd.DataFrame, cat: list):
        fail_counter = 0
        fail_counter_2 = 0
        for i in cat:
            for idx, val in df[i].items():
                if not pd.isnull(val):
                    try:
                        df.loc[idx, i] = float(val)
                    except:
                        fail_counter += 1
                        v = str(val)
                        try:
                            v = v.replace("%", "")
                            v = v.replace(" sq km", "")
                            v = v.replace(" km", "")
                            v = v.replace(" m", "")
                            v = v.replace(",", "")

                            if "illion" in v:
                                # Replace million and multiply by a million
                                v = v.replace("illion", "")
                                v = float(v)
                                v = v * 1000000
                                df.loc[idx, i] = v

                            elif "(percentage)" in v:
                                # Replace percentage and turn into chance and multiply by Total_Population
                                v = v.replace(" (percentage)", "")
                                v = float(v)
                                v = round(v * 0.01 * float(df["Total_Population"][idx]))
                                df.loc[idx, i] = v

                            elif "NEGL" in v or "negligible" in v or "Ile Amsterdam" in v:
                                # Set invalid entries to NaNs
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
                            print(f"Category: {i:<50} Country: {df["Country"][idx]:<50} Value: {v:>5}")
                            fail_counter_2 += 1
            df_total[i] = df_total[i].astype(float)
        # print(f"{fail_counter_2} out of {fail_counter} faulty variables left")

    # Get float columns
    columns = list(df_total.columns)
    remove = ["Country", "internet_country_code", "Fiscal_Year", "Geographic_Coordinates", "Capital",
              "Capital_Coordinates"]
    for i in remove:
        if i in columns:
            columns.remove(i)

    # Clean float columns
    data_cleaner(df_total, columns)

    # Delete outliers function
    def clean_outliers(df: pd.DataFrame, clean_list: list, del_list: list):
        for country, cat in clean_list:
            idx = df[df["Country"] == country].index
            df.loc[idx, cat] = np.nan
        for country in del_list:
            idx = df[df["Country"] == country].index
            df.drop(idx, inplace=True)

    # List of faulty data
    clean_list = [["EUROPEAN UNION", "Birth_Rate"],
                  ["EUROPEAN UNION", "Death_Rate"],
                  ["EUROPEAN UNION", "Total_Fertility_Rate"],
                  ["EUROPEAN UNION", "Male_Literacy_Rate"],
                  ["EUROPEAN UNION", "Female_Literacy_Rate"],
                  ["TOKELAU", "Death_Rate"],
                  ["TOKELAU", "Real_GDP_PPP_billion_USD"],
                  ["TOKELAU", "Budget_billion_USD"],
                  ["TOKELAU", "Exports_billion_USD"]]
    del_list = []

    # Delete outliers
    clean_outliers(df_total, clean_list, del_list)

    return df_total


# communications_data, demographics_data, economy_data, energy_data, geography_data, government_and_civics_data, transportation_data
df_total = load_clean_data()
print(df_total.sample(5))
