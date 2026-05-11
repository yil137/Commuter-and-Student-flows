from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget
from ipyleaflet import Map, basemaps, GeoJSON, Popup, LegendControl
from ipywidgets import HTML
from pathlib import Path
import json

import matplotlib.pyplot as plt
import geopandas as gpd


# =========================
# Load cleaned data
# =========================

DATA_DIR = Path("data/cleaned")

flows_gdf = gpd.read_file(
    DATA_DIR / "flows_detailed.gpkg",
    layer="flows_detailed"
)

flows_summary_gdf = gpd.read_file(
    DATA_DIR / "flows_summary.gpkg",
    layer="flows_summary"
)

sa2_akl = gpd.read_file(
    DATA_DIR / "sa2_akl.gpkg",
    layer="sa2_akl"
)


# =========================
# Helper functions
# =========================

def filter_by_direction(df, direction, selected_area):

    if direction == "Origin":
        return df[df["origin_name"] == selected_area].copy()

    return df[df["destination_name"] == selected_area].copy()


def empty_message_plot(message):

    fig, ax = plt.subplots(figsize=(7, 4))

    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center"
    )

    ax.set_axis_off()

    return fig


def get_internal_flow(area_name):

    internal_flow = flows_summary_gdf[
        (flows_summary_gdf["origin_name"] == area_name)
        & (flows_summary_gdf["destination_name"] == area_name)
    ]["Total"].sum()

    return internal_flow


def make_route_popup_text(df):

    return (
        "<b>From:</b> " + df["origin_name"].astype(str)
        + "<br><b>To:</b> " + df["destination_name"].astype(str)
        + "<br><b>Student:</b> " + df["Student"].astype(int).astype(str)
        + "<br><b>Commuter:</b> " + df["Commuter"].astype(int).astype(str)
        + "<br><b>Total:</b> " + df["Total"].astype(int).astype(str)
    )


def make_region_summary(area_name, direction):

    if direction == "Origin":

        df = flows_summary_gdf[
            flows_summary_gdf["origin_name"] == area_name
        ]

        direction_text = "Total outflow"

    else:

        df = flows_summary_gdf[
            flows_summary_gdf["destination_name"] == area_name
        ]

        direction_text = "Total inflow"

    student_total = df["Student"].sum()

    commuter_total = df["Commuter"].sum()

    total = student_total + commuter_total

    connected_regions = len(df)

    internal_flow = get_internal_flow(area_name)

    return (
        "<b>Selected area:</b> " + area_name
        + "<br><b>Student:</b> " + f"{int(student_total):,}"
        + "<br><b>Commuter:</b> " + f"{int(commuter_total):,}"
        + "<br><b>Total:</b> " + f"{int(total):,}"
        + "<br><b>Connected regions:</b> " + f"{connected_regions:,}"
        + "<br><b>Internal flow:</b> " + f"{int(internal_flow):,}"
        + "<br><b>Direction:</b> " + direction_text
    )


def make_summary_sentence(df, selected_area, direction):

    if len(df) == 0:
        return (
            f"No flows are shown for {selected_area} "
            f"with the current filter settings."
        )

    student_total = df["Student"].sum()

    commuter_total = df["Commuter"].sum()

    total = df["Total"].sum()

    connected_regions = len(df)

    internal_flow = get_internal_flow(selected_area)

    if direction == "Origin":
        direction_text = "outflow from"

    else:
        direction_text = "inflow to"

    return (
        f"Showing {direction_text} {selected_area}: "
        f"{int(student_total):,} students, "
        f"{int(commuter_total):,} commuters, "
        f"{int(total):,} people in total "
        f"across {connected_regions:,} connected regions. "
        f"Internal flow: {int(internal_flow):,} people both live and work/study in {selected_area}."
    )


def show_popup(m, feature, coordinates, property_name="popup_text"):

    if feature is None or coordinates is None:
        return

    popup = Popup(
        location=coordinates,
        child=HTML(
            value=feature["properties"][property_name]
        ),
        close_button=True,
        auto_close=True
    )

    m.add(popup)


# =========================
# Colours
# =========================

# Flow line colours
BLUE_LOW = "#deebf7"
BLUE_MED = "#9ecae1"
BLUE_HIGH = "#3182bd"

ORANGE_LOW = "#fee6ce"
ORANGE_MED = "#fdae6b"
ORANGE_HIGH = "#e6550d"

# Internal flow region colours
REGION_LOW = "#efedf5"
REGION_MED = "#bcbddc"
REGION_HIGH = "#756bb1"

# Region outline colour
REGION_OUTLINE = "#4a1486"

# Chart colours
STUDENT_COLOUR = "#a1d76a"
COMMUTER_COLOUR = "#e9a3c9"


def get_flow_colour(total, direction):

    if direction == "Origin":

        if total < 25:
            return BLUE_LOW

        elif total < 100:
            return BLUE_MED

        else:
            return BLUE_HIGH

    else:

        if total < 25:
            return ORANGE_LOW

        elif total < 100:
            return ORANGE_MED

        else:
            return ORANGE_HIGH


def get_flow_weight(total):

    if total < 25:
        return 2

    elif total < 100:
        return 4

    else:
        return 6


def get_region_colour(internal_flow):

    if internal_flow < 100:
        return REGION_LOW

    elif internal_flow < 500:
        return REGION_MED

    else:
        return REGION_HIGH


def make_legend(direction):

    if direction == "Origin":

        return {
            "Internal low: 0-99": REGION_LOW,
            "Internal medium: 100-499": REGION_MED,
            "Internal high: 500+": REGION_HIGH,
            "Outflow low: 1-24": BLUE_LOW,
            "Outflow medium: 25-99": BLUE_MED,
            "Outflow high: 100+": BLUE_HIGH
        }

    return {
        "Internal low: 0-99": REGION_LOW,
        "Internal medium: 100-499": REGION_MED,
        "Internal high: 500+": REGION_HIGH,
        "Inflow low: 1-24": ORANGE_LOW,
        "Inflow medium: 25-99": ORANGE_MED,
        "Inflow high: 100+": ORANGE_HIGH
    }


# =========================
# Transport labels
# =========================

transport_cols = {
    "2023_drive_private": "Private car",
    "2023_drive_company": "Company car",
    "2023_passenger": "Passenger",
    "2023_bus": "Bus",
    "2023_train": "Train",
    "2023_bicycle": "Bicycle",
    "2023_walk": "Walk or jog",
    "2023_ferry": "Ferry",
    "2023_other": "Other"
}


# =========================
# UI
# =========================

area_choices = sorted(
    set(flows_summary_gdf["origin_name"].dropna())
    | set(flows_summary_gdf["destination_name"].dropna())
)

app_ui = ui.page_sidebar(

    ui.sidebar(

        ui.input_select(
            "selected_area",
            "Select Auckland area",
            choices=area_choices,
            selected="Newmarket"
        ),

        ui.input_select(
            "direction",
            "Show movement",
            choices=["Origin", "Destination"],
            selected="Origin"
        ),

        ui.input_checkbox_group(
            "flow_types",
            "Flow type",
            choices=["Commuter", "Student"],
            selected=["Commuter", "Student"]
        ),

        ui.input_action_button(
            "apply",
            "Apply filters"
        ),

        ui.p(
            "Click 'Apply filters' after changing selections.",
            style=(
                "font-size:12px;"
                "color:#666666;"
                "margin-top:6px;"
                "margin-bottom:12px;"
            )
        ),

        # Warning if nothing selected
        ui.output_ui("flow_type_warning")
    ),

    ui.h3("Auckland commuter and student flows"),

    ui.p(
        "Select an Auckland SA2 area to compare commuter and student movement. "
        "The map shows origin-destination flows coloured by movement size. "
        "The selected polygon colour shows internal flow, meaning people who both live "
        "and work/study in the same selected area."
    ),

    ui.output_text("summary_text"),

    output_widget("flow_map"),

    ui.output_plot("transport_chart")
)


# =========================
# Server
# =========================

def server(input, output, session):

    # =========================
    # Applied input values
    # =========================

    @reactive.calc
    @reactive.event(input.apply, ignore_none=False)
    def applied_filters():

        return {
            "selected_area": input.selected_area(),
            "direction": input.direction(),
            "flow_types": input.flow_types()
        }


    # =========================
    # Warning message
    # =========================

    @output
    @render.ui
    def flow_type_warning():

        if len(input.flow_types()) == 0:

            return ui.div(
                "Please select at least one flow type.",
                style=(
                    "background-color:#fff3cd;"
                    "color:#856404;"
                    "padding:8px;"
                    "border-radius:6px;"
                    "margin-top:8px;"
                    "font-size:14px;"
                )
            )

        return None


    # =========================
    # Map data
    # =========================

    @reactive.calc
    def filtered_flow_lines():

        filters = applied_filters()

        df = flows_summary_gdf.copy()

        if len(filters["flow_types"]) == 0:
            return df.iloc[0:0].copy()

        df = filter_by_direction(
            df,
            filters["direction"],
            filters["selected_area"]
        )

        selected_types = filters["flow_types"]

        if "Student" not in selected_types:
            df["Student"] = 0

        if "Commuter" not in selected_types:
            df["Commuter"] = 0

        df["Total"] = (
            df["Student"] + df["Commuter"]
        )

        df = df[df["Total"] > 0].copy()

        return df


    # =========================
    # Chart data
    # =========================

    @reactive.calc
    def filtered_transport_data():

        filters = applied_filters()

        df = flows_gdf.copy()

        if len(filters["flow_types"]) == 0:
            return df.iloc[0:0].copy()

        df = df[
            df["flow_type"].isin(
                filters["flow_types"]
            )
        ].copy()

        df = filter_by_direction(
            df,
            filters["direction"],
            filters["selected_area"]
        )

        df = df[df["2023_total"] > 0].copy()

        return df


    # =========================
    # Summary text
    # =========================

    @output
    @render.text
    def summary_text():

        filters = applied_filters()

        df = filtered_flow_lines()

        return make_summary_sentence(
            df,
            filters["selected_area"],
            filters["direction"]
        )


    # =========================
    # Interactive map
    # =========================

    @output
    @render_widget
    def flow_map():

        filters = applied_filters()

        selected_area = filters["selected_area"]
        direction = filters["direction"]

        map_df = filtered_flow_lines().copy()

        if direction == "Origin":
            title = f"Outflow from {selected_area}"

        else:
            title = f"Inflow to {selected_area}"

        legend_colours = make_legend(
            direction
        )

        if len(map_df) > 0:
            map_df["popup_text"] = (
                make_route_popup_text(map_df)
            )

        m = Map(
            center=[-36.85, 174.76],
            zoom=11,
            basemap=basemaps.CartoDB.Positron,
            scroll_wheel_zoom=True
        )

        selected_region = sa2_akl[
            sa2_akl["SA22023_V1_00_NAME"]
            == selected_area
        ].copy()

        internal_flow = get_internal_flow(selected_area)
        region_fill_colour = get_region_colour(internal_flow)

        if len(selected_region) > 0:

            selected_region["popup_text"] = (
                make_region_summary(
                    selected_area,
                    direction
                )
            )

            region_layer = GeoJSON(

                data=json.loads(
                    selected_region.to_json()
                ),

                style={
                    "color": REGION_OUTLINE,
                    "fillColor": region_fill_colour,
                    "weight": 2,
                    "fillOpacity": 0.55
                },

                hover_style={
                    "color": REGION_OUTLINE,
                    "fillColor": region_fill_colour,
                    "weight": 3,
                    "fillOpacity": 0.75
                },

                name="Selected SA2 area"
            )

            def show_region_info(**kwargs):

                show_popup(
                    m,
                    kwargs.get("feature"),
                    kwargs.get("coordinates")
                )

            region_layer.on_click(
                show_region_info
            )

            m.add_layer(region_layer)

        if len(map_df) > 0:

            flow_layer = GeoJSON(

                data=json.loads(
                    map_df.to_json()
                ),

                style_callback=lambda feature: {

                    "color": get_flow_colour(
                        feature["properties"]["Total"],
                        direction
                    ),

                    "weight": get_flow_weight(
                        feature["properties"]["Total"]
                    ),

                    "opacity": 0.75
                },

                hover_style={
                    "color": "#000000",
                    "weight": 7,
                    "opacity": 1
                },

                name=title
            )

            def show_flow_info(**kwargs):

                show_popup(
                    m,
                    kwargs.get("feature"),
                    kwargs.get("coordinates")
                )

            flow_layer.on_click(
                show_flow_info
            )

            m.add_layer(flow_layer)

            xmin, ymin, xmax, ymax = (
                map_df.total_bounds
            )

            m.fit_bounds([
                [ymin, xmin],
                [ymax, xmax]
            ])

        m.add_control(
            LegendControl(
                legend_colours,
                name="Movement size",
                position="bottomright"
            )
        )

        return m


    # =========================
    # Transport chart
    # =========================

    @output
    @render.plot
    def transport_chart():

        df = filtered_transport_data()

        available_cols = [
            col for col in transport_cols
            if col in df.columns
        ]

        if len(df) == 0 or len(available_cols) == 0:

            return empty_message_plot(
                "Please select at least one flow type."
            )

        chart_data = (
            df.groupby("flow_type")[available_cols]
            .sum()
            .reset_index()
        )

        chart_long = chart_data.melt(
            id_vars="flow_type",
            value_vars=available_cols,
            var_name="transport_mode",
            value_name="total_number"
        )

        chart_long["transport_mode"] = (
            chart_long["transport_mode"]
            .map(transport_cols)
        )

        chart_long = chart_long[
            chart_long["total_number"] > 0
        ].copy()

        if len(chart_long) == 0:

            return empty_message_plot(
                "No transport data available."
            )

        top_modes = (
            chart_long
            .groupby("transport_mode")["total_number"]
            .sum()
            .sort_values(ascending=False)
            .head(3)
            .index
        )

        chart_long = chart_long[
            chart_long["transport_mode"]
            .isin(top_modes)
        ]

        colours = {
            "Commuter": COMMUTER_COLOUR,
            "Student": STUDENT_COLOUR
        }

        pivot = chart_long.pivot(
            index="transport_mode",
            columns="flow_type",
            values="total_number"
        ).fillna(0)

        fig, ax = plt.subplots(
            figsize=(7, 4)
        )

        pivot.plot(
            kind="bar",
            ax=ax,
            color=[
                colours.get(col, "grey")
                for col in pivot.columns
            ]
        )

        ax.set_xlabel(
            "Way of transport"
        )

        ax.set_ylabel(
            "Total number"
        )

        ax.set_title(
            "Top 3 ways of transport"
        )

        ax.legend(
            title="Flow type"
        )

        plt.xticks(rotation=0)

        plt.tight_layout()

        return fig


app = App(app_ui, server)