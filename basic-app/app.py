from shiny import App, ui, render, reactive
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# Inline sample data (replace with real data next week)
DATA_DIR = Path("data")

education = pd.read_csv(DATA_DIR / "2023-education.csv")
work = pd.read_csv(DATA_DIR / "2023-work.csv")
sa2 = gpd.read_file(DATA_DIR / "2023-sa2.gpkg")
sa2 = sa2.to_crs(epsg=4326)

#Clean education data
education_clean = education.rename(columns={
    "SA22023_V1_00_NAME_usual_residence_address": "origin_sa2",
    "SA22023_V1_00_NAME_educational_institution_address": "destination_sa2",
})

education_long = education_clean.melt(
    id_vars=["origin_sa2", "destination_sa2"],
    value_vars=["2018_Total_stated", "2023_Total_stated"],
    var_name="year",
    value_name="count"
)

education_long["year"] = education_long["year"].str[:4]
education_long["flow_type"] = "Student"

# Clean work data
work_clean = work.rename(columns={
    "SA22023_V1_00_NAME_usual_residence_address": "origin_sa2",
    "SA22023_V1_00_NAME_workplace_address": "destination_sa2",
})

work_long = work_clean.melt(
    id_vars=["origin_sa2", "destination_sa2"],
    value_vars=["2018_Total_stated", "2023_Total_stated"],
    var_name="year",
    value_name="count"
)

work_long["year"] = work_long["year"].str[:4]
work_long["flow_type"] = "Commuter"

# Combine real OD data
flows = pd.concat([education_long, work_long], ignore_index=True)

flows["count"] = pd.to_numeric(flows["count"], errors="coerce")
flows = flows.dropna(subset=["origin_sa2", "destination_sa2", "count"])
flows = flows[flows["count"] > 0]

year_choices = sorted(flows["year"].unique())
flow_type_choices = sorted(flows["flow_type"].unique())
origin_choices = sorted(flows["origin_sa2"].unique())

# UI
app_ui = ui.page_fluid(
    ui.h2("Auckland OD flow explorer"),

    ui.p(
        "This dashboard uses real Stats NZ origin-destination data to compare "
        "student and commuter travel flows across Auckland."
    ),

    ui.input_select(
        "year",
        "Census year",
        choices=year_choices,
        selected="2023"
    ),

    ui.input_select(
        "flow_type",
        "Flow type",
        choices=flow_type_choices,
        selected="Commuter"
    ),

    ui.input_selectize(
        "origin",
        "Origin SA2",
        choices=origin_choices,
        selected=origin_choices[0]
    ),

    ui.output_text("summary"),
    ui.output_table("tbl"),
    ui.output_plot("chart"),
)


# Server
def server(input, output, session):

    @reactive.calc
    def filtered():
        df = flows.copy()

        df = df[df["year"] == input.year()]
        df = df[df["flow_type"] == input.flow_type()]
        df = df[df["origin_sa2"] == input.origin()]

        return df

    @render.text
    def summary():
        df = filtered()

        if len(df) == 0:
            return "No flows match the current filters."

        total_people = df["count"].sum()
        destination_count = df["destination_sa2"].nunique()

        return (
            f"In {input.year()}, {total_people:,.0f} {input.flow_type().lower()}s "
            f"travelled from {input.origin()} to {destination_count} destination SA2 areas."
        )

    @render.table
    def tbl():
        return (
            filtered()[["year", "flow_type", "origin_sa2", "destination_sa2", "count"]]
            .sort_values("count", ascending=False)
            .head(10)
        )

    @render.plot
    def chart():
        df = filtered()

        top_destinations = (
            df.groupby("destination_sa2", as_index=False)["count"]
            .sum()
            .sort_values("count", ascending=False)
            .head(10)
        )

        fig, ax = plt.subplots(figsize=(8, 5))

        ax.barh(
            top_destinations["destination_sa2"],
            top_destinations["count"]
        )

        ax.set_xlabel("Number of people")
        ax.set_ylabel("Destination SA2")
        ax.set_title("Top 10 destination areas")
        ax.invert_yaxis()

        plt.tight_layout()
        return fig


app = App(app_ui, server)