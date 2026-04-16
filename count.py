import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date
from io import BytesIO

# ================= CONFIG =================

MAPPING_URL = "https://docs.google.com/spreadsheets/d/1psWXuucE_IX_JBi5iG_m96sKuvY5xzEXYLU5BE7ug7w/export?format=csv"
mapping_df = pd.read_csv(MAPPING_URL)
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

def highlight_total(row):
    if row.get("Module (Epic)") == "TOTAL":
        return ["background-color: #ffeeba; font-weight: bold"] * len(row)
    return [""] * len(row)

# ================= CLEAN DATA =================
def clean_data(df):

    df.columns = df.columns.str.strip().str.lower()

    issue_col = "issue type" if "issue type" in df.columns else None
    if issue_col:
        df = df[df[issue_col].astype(str).str.lower().str.contains("bug|defect", na=False)]

    if "epic name" in df.columns:
        df["module"] = df["epic name"]
    elif "parent summary" in df.columns:
        df["module"] = df["parent summary"]
    elif "epic link" in df.columns:
        df["module"] = df["epic link"]
    else:
        df["module"] = df.get("parent", "Unknown")

    df["module"] = df["module"].astype(str).str.strip().str.upper()
    df["module"] = df["module"].apply(
        lambda x: f"{x} - {MODULE_MAP[x]}" if x in MODULE_MAP else x
    )

    df["status"] = df["status"].fillna("Unknown").astype(str).str.strip()

    df["priority"] = df["priority"].fillna("Unknown")
    df["priority_norm"] = (
        df["priority"].astype(str).str.lower().map(PRIORITY_MAP).fillna("Other")
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

    # ===== ADD TOTAL ROW =====
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

    cls = cls.rename(columns={
        "module": "Module (Epic)",
        "Highest": "Critical",
        "Lowest": "Trivial"
    })

    cls = capitalize_columns(cls)

    # ===== ADD TOTAL ROW =====
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

# ================= UI =================
st.set_page_config(page_title="Jira Bugs Report Dashboard", layout="wide")
st.title("📊 Jira Bugs Report Dashboard")

file = st.file_uploader("Upload Excel file", type=["xlsx"])

if file:
    df = pd.read_excel(file)
    df = clean_data(df)

    col1, col2, col3 = st.columns(3)

    with col1:
        module_list = (
            df["module"]
            .dropna()
            .astype(str)
            .sort_values()
            .unique()
        )
        module_filter = st.multiselect("Module", module_list)
    with col2:
        status_filter = st.multiselect("Status", sorted(df["status"].unique()))
    with col3:
        priority_filter = st.multiselect("Priority", sorted(df["priority_norm"].unique()))

    filtered = df.copy()
    if module_filter:
        filtered = filtered[filtered["module"].isin(module_filter)]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if priority_filter:
        filtered = filtered[filtered["priority_norm"].isin(priority_filter)]

    summary = build_summary(filtered)
    cls = build_classification(filtered)

    # ===== REMOVE TOTAL FOR CHART =====
    summary_chart = summary[summary["Module (Epic)"] != "TOTAL"]

    # KPI
    st.subheader("📌 Overview")
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Bugs", len(filtered))
    k2.metric("Modules", filtered["module"].nunique())
    k3.metric("Statuses", filtered["status"].nunique())

    # ===== SUMMARY =====
    st.subheader("📊 Summary")
    summary_display = summary.copy()
    summary_display.insert(0, "No.", range(1, len(summary_display) + 1))

    st.dataframe(
        summary_display,
        use_container_width=True,
        hide_index=True
    )

    # ===== CLASSIFICATION =====
    st.subheader("📊 Classification")
    cls_display = cls.copy()
    cls_display.insert(0, "No.", range(1, len(cls_display) + 1))

    st.dataframe(
        cls_display,
        use_container_width=True,
        hide_index=True
    )

    # ===== CHARTS =====
    st.subheader("📈 Charts")
    c1, c2 = st.columns(2)

    with c1:
        fig1 = px.bar(
            summary_chart,
            x="Module (Epic)",
            y="Total Bugs",
            title="Total Bugs per Module",
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
            title="Bug Flow (To Do → Done)",
            color="Status"
        )
        st.plotly_chart(fig2, use_container_width=True)

    # DOWNLOAD
    st.download_button(
        "📥 Download Excel Report",
        data=to_excel(summary, cls),
        file_name=f"jira_report_{date.today()}.xlsx"
    )