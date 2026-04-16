import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date
from io import BytesIO

# ================= CONFIG =================

def load_mapping():
    url = "https://docs.google.com/spreadsheets/d/1psWXuucE_IX_JBi5iG_m96sKuvY5xzEXYLU5BE7ug7w/gviz/tq?tqx=out:csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        st.warning("Mapping sheet not loaded → using empty mapping")
        return pd.DataFrame(columns=["code", "name"])

mapping_df = load_mapping()
mapping_df.columns = mapping_df.columns.str.strip().str.lower()
MODULE_MAP = dict(zip(mapping_df["code"], mapping_df["name"]))

STATUS_LIST = [
    "To Do", "IN DEV", "Deploy UAT", "UAT FPT Testing", "UAT HDB Testing",
    "Deploy STG", "STG FPT Testing", "STG HDB Testing",
    "Deploy Pilot", "PILOT FPT Testing", "PILOT HDB Testing",
    "Done", "Cancel", "Pending"
]

PRIORITY_MAP = {
    "highest": "Highest", "critical": "Highest", "p0": "Highest",
    "high": "High", "p1": "High",
    "medium": "Medium", "p2": "Medium",
    "low": "Low", "p3": "Low",
    "lowest": "Lowest",
}

# ================= HELPER =================
def capitalize_columns(df):
    df.columns = [col.strip().title() for col in df.columns]
    return df


# ================= CLEAN DATA =================
def clean_data(df):

    df.columns = df.columns.str.strip().str.lower()

    if "issue type" in df.columns:
        df = df[df["issue type"].astype(str).str.lower().str.contains("bug|defect", na=False)]

    # module detection
    if "epic name" in df.columns:
        df["module"] = df["epic name"]
    elif "parent summary" in df.columns:
        df["module"] = df["parent summary"]
    elif "epic link" in df.columns:
        df["module"] = df["epic link"]
    else:
        df["module"] = df.get("parent", pd.NA)

    df["module"] = df["module"].replace(["nan", "None", ""], pd.NA)

    def map_module(x):
        if pd.isna(x):
            return "No Epic"
        x = str(x).strip().upper()
        return f"{x} - {MODULE_MAP[x]}" if x in MODULE_MAP else x

    df["module"] = df["module"].apply(map_module)

    df["status"] = df["status"].fillna("Unknown").astype(str).str.strip()

    df["priority"] = df["priority"].fillna("Unknown")
    df["priority_norm"] = (
        df["priority"]
        .astype(str)
        .str.lower()
        .map(PRIORITY_MAP)
        .fillna("Other")
    )

    return df


# ================= SUMMARY =================
def build_summary(df):
    summary = pd.crosstab(df["module"], df["status"]).reindex(columns=STATUS_LIST, fill_value=0)
    summary["Total Bugs"] = summary.sum(axis=1)

    summary = summary.sort_values("Total Bugs", ascending=False)
    summary = summary[["Total Bugs"] + STATUS_LIST].reset_index()

    summary = summary.rename(columns={"module": "Module (Epic)"})
    summary = capitalize_columns(summary)

    total_row = summary.select_dtypes(include="number").sum()
    total_row["Module (Epic)"] = "TOTAL"

    summary = pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)

    return summary


# ================= CLASSIFICATION =================
def build_classification(df):
    cls = pd.crosstab(df["module"], df["priority_norm"])

    for c in ["Highest", "High", "Medium", "Low", "Lowest"]:
        if c not in cls.columns:
            cls[c] = 0

    cls["Total Bugs"] = cls.sum(axis=1)
    cls = cls.sort_values("Total Bugs", ascending=False)

    cls = cls[["Total Bugs", "Highest", "High", "Medium", "Low", "Lowest"]].reset_index()

    cls = cls.rename(columns={"module": "Module (Epic)"})
    cls = capitalize_columns(cls)

    total_row = cls.select_dtypes(include="number").sum()
    total_row["Module (Epic)"] = "TOTAL"

    cls = pd.concat([cls, pd.DataFrame([total_row])], ignore_index=True)

    return cls


# ================= EXCEL EXPORT =================
def to_excel(summary, cls):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        cls.to_excel(writer, sheet_name="Classification", index=False)
    return output.getvalue()


# ================= STREAMLIT =================
st.set_page_config(page_title="Jira Bugs Report Dashboard", layout="wide")
st.title("📊 Jira Bugs Report Dashboard")

file = st.file_uploader("Upload Excel file", type=["xlsx"])

if file:

    df = pd.read_excel(file)
    df = clean_data(df)

    # ================= FILTER UI =================
    col1, col2, col3 = st.columns(3)

    with col1:
        module_list = sorted(df["module"].dropna().unique())
        module_filter = st.multiselect("Module", module_list)

    with col2:
        status_filter = st.multiselect("Status", sorted(df["status"].dropna().unique()))

    with col3:
        priority_filter = st.multiselect("Priority", sorted(df["priority_norm"].dropna().unique()))

    # ================= ENV FILTER =================
    env_options = st.multiselect(
        "Environment",
        ["Overall", "UAT", "STG", "PILOT"],
        default=["Overall"]
    )

    UAT_STATUS = [
        "To Do", "IN DEV", "Deploy UAT", "UAT FPT Testing", "UAT HDB Testing"
    ]

    STG_STATUS = [
        "Deploy STG", "STG FPT Testing", "STG HDB Testing"
    ]

    PILOT_STATUS = [
        "Deploy Pilot", "PILOT FPT Testing", "PILOT HDB Testing"
    ]

    env_status_filter = []

    if "UAT" in env_options:
        env_status_filter += UAT_STATUS
    if "STG" in env_options:
        env_status_filter += STG_STATUS
    if "PILOT" in env_options:
        env_status_filter += PILOT_STATUS

    # ================= APPLY FILTER =================
    filtered = df.copy()

    if module_filter:
        filtered = filtered[filtered["module"].isin(module_filter)]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if priority_filter:
        filtered = filtered[filtered["priority_norm"].isin(priority_filter)]

    if "Overall" not in env_options:
        filtered = filtered[filtered["status"].isin(env_status_filter)]

    # ================= BUILD =================
    summary = build_summary(filtered)
    cls = build_classification(filtered)

    summary_chart = summary[summary["Module (Epic)"] != "TOTAL"]

    # ================= OVERVIEW =================
    st.subheader("📌 Overview")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Bugs", len(filtered))
    k2.metric("Modules", filtered["module"].nunique())
    k3.metric("Statuses", filtered["status"].nunique())
    k4.metric("In Progress", len(filtered[~filtered["status"].isin(["Done", "Cancel", "Pending"])]))

    # ================= RAW DATA (NEW) =================
    st.subheader("📌 Raw Data")

    raw_display = filtered.copy().reset_index(drop=True)
    raw_display.insert(0, "No.", range(1, len(raw_display) + 1))

    raw_display = raw_display.rename(columns={
        "module": "Module (Epic)",
        "status": "Status",
        "priority_norm": "Priority",
        "summary": "Title",
        "assignee": "Assignee"
    })

    preferred_cols = [
        "No.",
        "Module (Epic)",
        "Status",
        "Priority",
        "Title",
        "Assignee"
    ]

    existing_cols = [c for c in preferred_cols if c in raw_display.columns]

    raw_display = raw_display[existing_cols + [
        c for c in raw_display.columns if c not in existing_cols
    ]]

    st.dataframe(raw_display, use_container_width=True, hide_index=True)

    # ================= OVERALL =================
    st.subheader("🟦 OVERALL - Summary")

    summary_display = summary.copy()
    summary_display.insert(0, "No.", range(1, len(summary_display) + 1))
    st.dataframe(summary_display, use_container_width=True, hide_index=True)

    st.subheader("🟦 OVERALL - Classification")

    cls_display = cls.copy()
    cls_display.insert(0, "No.", range(1, len(cls_display) + 1))
    st.dataframe(cls_display, use_container_width=True, hide_index=True)

    # ================= CHARTS =================
    st.subheader("🟦 OVERALL - Charts")

    c1, c2 = st.columns(2)

    with c1:
        fig1 = px.bar(
            summary_chart,
            x="Module (Epic)",
            y="Total Bugs",
            title="Overall Bugs per Module",
            color="Total Bugs",
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        status_flow = (
            filtered["status"]
            .value_counts()
            .reindex(STATUS_LIST, fill_value=0)
            .reset_index()
        )
        status_flow.columns = ["Status", "Count"]

        fig2 = px.funnel(
            status_flow,
            x="Count",
            y="Status",
            title="Overall Bug Flow",
            color="Status"
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ================= DOWNLOAD =================
    st.download_button(
        "📥 Download Excel Report",
        data=to_excel(summary, cls),
        file_name=f"jira_report_{date.today()}.xlsx"
    )