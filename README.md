# Auckland Commuter and Student Flow Dashboard

## Overview

This dashboard explores commuter and student movement patterns across Auckland using 2023 Census origin-destination data from Stats NZ. The dashboard compares how commuters and students travel between Auckland SA2 areas and highlights differences between inflow and outflow patterns.

Users can:
- Select an Auckland SA2 area
- Compare inflow and outflow movement
- Filter commuter and student flows
- Explore interactive flow lines on a map
- Compare the top transport modes used by commuters and students
- View internal flow intensity through the selected polygon colour

The selected SA2 polygon changes colour based on internal flow size, representing people who both live and work/study within the same area.

The dashboard is designed to help users understand how Auckland areas function as residential origins, employment destinations, and education destinations.

---

## Dashboard Question

The main question explored by this dashboard is:

> How do commuter and student movement patterns differ across Auckland SA2 areas?

The dashboard allows users to investigate whether areas mainly send out commuters and students, attract them, or both. It also highlights differences in transport mode use between commuters and students.

---

## Data Sources

The dashboard uses publicly available data from Stats NZ:

- 2023 Census main means of travel to work by Statistical Area 2  
  https://datafinder.stats.govt.nz/table/121988-2023-census-main-means-of-travel-to-work-by-statistical-area-2/

- 2023 Census main means of travel to education by Statistical Area 2  
  https://datafinder.stats.govt.nz/table/121971-2023-census-main-means-of-travel-to-education-by-statistical-area-2/

- Statistical Area 2 2023 Generalised boundaries  
  https://datafinder.stats.govt.nz/layer/111227-statistical-area-2-2023-generalised/

- Regional Council 2023 Generalised boundaries  
  https://datafinder.stats.govt.nz/layer/111182-regional-council-2023-generalised/

---

## Technologies Used

- Shiny for Python
- shinylive
- ipyleaflet
- pandas
- geopandas
- matplotlib
- shapely

---

## Running the App Locally

Create a virtual environment:

```bash
uv venv
```

Activate the environment:

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

Install required packages:

```bash
uv pip install shiny shinylive shinywidgets ipyleaflet pandas geopandas matplotlib shapely
```

Run the app:

```bash
shiny run --reload app.py
```

---

## Deployment

The dashboard is deployed using shinylive and GitHub Pages.

Export the app:

```bash
shinylive export . docs
```

Then commit and push the updated `docs/` folder to GitHub.

---

## Project Structure

```text
├── app.py
├── plan.qmd
├── README.md
├── data/
│   ├── 2023-education.csv
│   ├── 2023-work.csv
│   ├── 2023-sa2.gpkg
│   └── 2023-rc.gpkg
└── docs/
```

---

## Limitations

- Flow lines connect SA2 centroids rather than real travel routes
- The dashboard only uses 2023 Census data
- Small Census values may be rounded or suppressed
- Only Auckland SA2 areas are included

---

## Future Improvements

Possible future improvements include:
- Comparing 2018 and 2023 Census flows
- Adding net inflow and outflow indicators
- Adding transport-mode-specific filtering
- Supporting larger regional summaries