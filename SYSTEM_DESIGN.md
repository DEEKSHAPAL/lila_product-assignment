# System Design

## System Purpose

The system turns raw LILA BLACK gameplay telemetry into a browser-based map analysis tool. The design keeps the data pipeline, visualization logic, and app UI in one Python project so it is easy to review, run locally, and deploy for the written test.

## High-Level Design

```mermaid
flowchart TD
    subgraph RawData[Raw assignment data]
        A1[February_10 to February_14]
        A2[minimaps folder]
    end

    subgraph Processing[Processing layer]
        B1[data_loader.py]
        B2[preprocessing.py]
        B3[coordinate_mapping.py]
        B4[insights.py]
    end

    subgraph Storage[Local generated storage]
        C1[all_events.parquet]
        C2[match_summary.parquet]
        C3[player_summary.parquet]
        C4[processing_report.json]
    end

    subgraph App[Streamlit application]
        D1[Sidebar controls]
        D2[Metric cards]
        D3[Plotly map view]
        D4[Event table]
        D5[Match summary]
        D6[Data quality]
    end

    A1 --> B1
    A2 --> D3
    B1 --> B2
    B2 --> B3
    B2 --> C1
    C1 --> C2
    C1 --> C3
    C1 --> B4
    B4 --> E1[INSIGHTS.md]
    C1 --> D1
    C2 --> D5
    C3 --> D5
    C4 --> D6
    D1 --> D2
    D1 --> D3
    D1 --> D4
```

## Main Components

| Component | Responsibility |
|---|---|
| `src/config.py` | Map configs, known events, event groups, heatmap event definitions |
| `src/data_loader.py` | Find raw files, read extensionless parquet, load/save processed data |
| `src/preprocessing.py` | Decode events, classify players/events, normalize timestamps, create summaries |
| `src/coordinate_mapping.py` | Convert world x/z coordinates into minimap pixels |
| `src/visualization.py` | Build Plotly minimap, heatmap, paths, markers, and hover text |
| `src/insights.py` | Compute grid hotspots and write evidence-backed insights |
| `app.py` | Streamlit layout, filters, timeline, metrics, tabs, CSV download |
| `scripts/` | Repeatable inspection, preparation, and insight generation commands |
| `tests/` | Unit and smoke checks for the most fragile logic |

## User-Facing Feature Map

```mermaid
flowchart LR
    A[Level Designer] --> B[Select map]
    B --> C[Choose date]
    C --> D[Choose match or all matches]
    D --> E[Toggle humans and bots]
    E --> F[Toggle event markers]
    F --> G[Select heatmap]
    G --> H{Single match?}
    H -->|Yes| I[Use timeline controls]
    H -->|No| J[Review aggregate heatmap]
    I --> K[Inspect metrics and table]
    J --> K
    K --> L[Export CSV or review insights]
```

## Data Model

The main processed table is `data_processed/all_events.parquet`. Important columns include:

| Column | Meaning |
|---|---|
| `user_id`, `match_id`, `map_id` | Core identity fields |
| `source_date`, `source_file` | Raw file provenance |
| `x`, `y`, `z` | World coordinates, with `y` kept as elevation only |
| `event` | Decoded event string |
| `is_bot`, `player_type` | Human/bot classification |
| `event_group`, `event_category`, `event_display` | UI-friendly event taxonomy |
| `ts_raw`, `ts_ms`, `match_time_s`, `match_time_label` | Timeline fields |
| `u`, `v`, `pixel_x`, `pixel_y`, `in_minimap_bounds` | Minimap mapping fields |
| `plot_pixel_x`, `plot_pixel_y` | Clipped plotting coordinates |

## Deployment Shape

```mermaid
flowchart TD
    A[GitHub repository] --> B[Streamlit Community Cloud]
    A --> V[Vercel]
    B --> C[Install requirements.txt]
    C --> D[Run app.py]
    D --> E{Processed data exists?}
    E -->|Yes| F[Load data_processed parquet]
    E -->|No| G[Process raw February folders]
    G --> F
    F --> H[Public Streamlit URL]
    V --> I[Read vercel.json]
    I --> J[Serve public/index.html]
    J --> K[Static project landing page]
```

The Streamlit Cloud path is the production path for the interactive dashboard. The Vercel path is a static landing page because Vercel's serverless function model is not a good runtime for Streamlit's live browser connection.

## Failure Handling

- If a raw parquet file cannot be read, it is skipped and recorded in the processing report.
- If processed parquet is missing, the app attempts to process raw data automatically.
- If filters produce no rows, the app shows a warning instead of failing.
- If a minimap is missing, the visualization reports the missing image path.
- If unknown events appear, they are grouped as `Other` and counted in Data Quality.

## Why This Design Works for the Assignment

The assignment rewards end-to-end execution, correct coordinate mapping, clear visual analysis, and evidence-backed insights. This design keeps those concerns separated:

- Data correctness lives in preprocessing and tests.
- Spatial correctness lives in coordinate mapping.
- Product behavior lives in Streamlit filters and tabs.
- Visual clarity lives in Plotly layer ordering and marker styles.
- Evidence lives in generated insights and processed data summaries.
