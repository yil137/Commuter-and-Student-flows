from pathlib import Path

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString


# =========================
# File paths
# =========================

DATA_DIR = Path("data")
OUTPUT_DIR = Path("data/cleaned")

OUTPUT_DIR.mkdir(exist_ok=True)


# =========================
# Clean flow data
# =========================

def clean_flow_data(df, flow_type, dest_name_col):

    df = df.replace(-999, pd.NA)

    df = df.rename(columns={
        "SA22023_V1_00_NAME_usual_residence_address": "origin_name",
        dest_name_col: "destination_name"
    })

    df["flow_type"] = flow_type

    return df


def tidy_transport_columns(df):

    df = df.drop(
        columns=[col for col in df.columns if "NAME_ASCII" in col],
        errors="ignore"
    )

    df = df.rename(columns={

        "2023_Work_at_home": "2023_home",
        "2023_Study_at_home": "2023_home",

        # Commuter dataset
        "2023_Drive_a_private_car_truck_or_van": "2023_drive_private",
        "2023_Drive_a_company_car_truck_or_van": "2023_drive_company",
        "2023_Passenger_in_a_car_truck_van_or_company_bus": "2023_passenger",

        # Student dataset
        "2023_Drive_a_car_truck_or_van": "2023_drive_private",
        "2023_Passenger_in_a_car_truck_or_van": "2023_passenger",

        "2023_Public_bus": "2023_bus",
        "2023_Train": "2023_train",
        "2023_Bicycle": "2023_bicycle",
        "2023_Walk_or_jog": "2023_walk",
        "2023_Ferry": "2023_ferry",
        "2023_Other": "2023_other",
        "2023_Total_stated": "2023_total",
    })

    df = df.dropna(
        subset=["origin_name", "destination_name"]
    ).copy()

    numeric_cols = [
        col for col in df.columns
        if col.startswith("2023_")
    ]

    df[numeric_cols] = df[numeric_cols].apply(
        pd.to_numeric,
        errors="coerce"
    ).fillna(0)

    return df


# =========================
# Prepare data
# =========================

def prepare_flow_data():

    # =========================
    # Load data
    # =========================

    edu = pd.read_csv(DATA_DIR / "2023-education.csv")
    work = pd.read_csv(DATA_DIR / "2023-work.csv")

    sa2 = gpd.read_file(DATA_DIR / "2023-sa2.gpkg")
    rc = gpd.read_file(DATA_DIR / "2023-rc.gpkg")

    # =========================
    # Clean datasets
    # =========================

    work_clean = tidy_transport_columns(
        clean_flow_data(
            work,
            "Commuter",
            "SA22023_V1_00_NAME_workplace_address"
        )
    )

    edu_clean = tidy_transport_columns(
        clean_flow_data(
            edu,
            "Student",
            "SA22023_V1_00_NAME_educational_institution_address"
        )
    )

    combined = pd.concat(
        [work_clean, edu_clean],
        ignore_index=True
    )

    combined["origin_name"] = combined["origin_name"].str.strip()
    combined["destination_name"] = combined["destination_name"].str.strip()

    sa2["SA22023_V1_00_NAME"] = (
        sa2["SA22023_V1_00_NAME"].str.strip()
    )

    rc["REGC2023_V1_00_NAME"] = (
        rc["REGC2023_V1_00_NAME"].str.strip()
    )

    # =========================
    # Filter to Auckland Region
    # =========================

    akl_region = rc[
        rc["REGC2023_V1_00_NAME"] == "Auckland Region"
    ].copy()

    sa2_nztm = sa2.to_crs(epsg=2193)
    akl_region = akl_region.to_crs(epsg=2193)

    sa2_akl = gpd.sjoin(
        sa2_nztm,
        akl_region[["geometry"]],
        how="inner",
        predicate="intersects"
    ).copy()

    sa2_akl = sa2_akl.drop(
        columns=["index_right"],
        errors="ignore"
    )

    sa2_centroids = sa2_akl.copy()
    sa2_centroids["geometry"] = sa2_centroids.geometry.centroid

    sa2_akl = sa2_akl.to_crs(epsg=4326)
    sa2_centroids = sa2_centroids.to_crs(epsg=4326)

    centroid_lookup = dict(
        zip(
            sa2_centroids["SA22023_V1_00_NAME"],
            sa2_centroids.geometry
        )
    )

    # =========================
    # Create flow lines
    # =========================

    combined["origin_point"] = (
        combined["origin_name"].map(centroid_lookup)
    )

    combined["destination_point"] = (
        combined["destination_name"].map(centroid_lookup)
    )

    combined = combined.dropna(
        subset=["origin_point", "destination_point"]
    ).copy()

    combined["geometry"] = combined.apply(
        lambda row: LineString([
            row["origin_point"],
            row["destination_point"]
        ]),
        axis=1
    )

    flows_gdf = gpd.GeoDataFrame(
        combined,
        geometry="geometry",
        crs="EPSG:4326"
    )

    # =========================
    # One route per OD pair
    # =========================

    flows_summary = (
        flows_gdf
        .groupby(["origin_name", "destination_name", "flow_type"])
        .agg({
            "2023_total": "sum",
            "geometry": "first"
        })
        .reset_index()
    )

    flows_summary_wide = (
        flows_summary
        .pivot_table(
            index=["origin_name", "destination_name"],
            columns="flow_type",
            values="2023_total",
            aggfunc="sum",
            fill_value=0
        )
        .reset_index()
    )

    if "Student" not in flows_summary_wide.columns:
        flows_summary_wide["Student"] = 0

    if "Commuter" not in flows_summary_wide.columns:
        flows_summary_wide["Commuter"] = 0

    flows_summary_wide["Total"] = (
        flows_summary_wide["Student"]
        + flows_summary_wide["Commuter"]
    )

    route_geometry = (
        flows_summary
        .drop_duplicates(
            ["origin_name", "destination_name"]
        )
        [["origin_name", "destination_name", "geometry"]]
    )

    flows_summary_gdf = flows_summary_wide.merge(
        route_geometry,
        on=["origin_name", "destination_name"],
        how="left"
    )

    flows_summary_gdf = gpd.GeoDataFrame(
        flows_summary_gdf,
        geometry="geometry",
        crs="EPSG:4326"
    )

    flows_summary_gdf = flows_summary_gdf[
        flows_summary_gdf["Total"] > 0
    ].copy()

    # =========================
    # Save cleaned outputs
    # =========================

    flows_gdf.to_file(
        OUTPUT_DIR / "flows_detailed.gpkg",
        layer="flows_detailed",
        driver="GPKG"
    )

    flows_summary_gdf.to_file(
        OUTPUT_DIR / "flows_summary.gpkg",
        layer="flows_summary",
        driver="GPKG"
    )

    sa2_akl.to_file(
        OUTPUT_DIR / "sa2_akl.gpkg",
        layer="sa2_akl",
        driver="GPKG"
    )

    print("Cleaned files saved to data/cleaned/")


# =========================
# Run script
# =========================

if __name__ == "__main__":
    prepare_flow_data()