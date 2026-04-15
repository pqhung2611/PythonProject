import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date
from io import BytesIO


# ================= CONFIG =================
STATUS_LIST = [
    "To Do", "IN DEV", "Deploy UAT", "UAT FPT Testing", "UAT HDB Testing",
    "Deploy STG", "STG FPT Testing", "STG HDB Testing",
    "Deploy Pilot", "PILOT FPT Testing", "PILOT HDB Testing",
    "Done", "Cancel", "Pending"
]

PRIORITY_MAP = {
    "highest": "Highest",
    "critical": "Highest",
    "p0": "Highest",

    "high": "High",
    "p1": "High",

    "medium": "Medium",
    "p2": "Medium",

    "low": "Low",
    "p3": "Low",

    "lowest": "Lowest",
}


# ================= CLEAN DATA =================
def clean_data(df):

    df.columns = df.columns.str.strip().str.lower()

    # detect issue type column
    issue_col = "issue type" if "issue type" in df.columns else None

    if issue_col:
        df[issue_col] = df[issue_col].astype(str).str.lower().str.strip()
        df = df[df[issue_col].str.contains("bug|defect", na=False)]

    # module = parent
    df["module"] = df["parent"].astype(str).fillna("Unknown")

    # normalize status
    df["status"] = df["status"].astype(str).str.strip()

    # normalize priority
    df["priority_norm"] = df["priority"].astype(str).str.lower().map(PRIORITY_MAP).fillna("Other")

    return df


# ================= SUMMARY =================
def build_summary(df):
    summary = pd.crosstab(df["module"], df["status"]).reindex(columns=STATUS_LIST, fill_value=0)
    summary["Tổng"] = summary.sum(axis=1)
    summary = summary[["Tổng"] + STATUS_LIST].reset_index()
    return summary


# ================= CLASSIFICATION =================
def build_classification(df):
    cls = pd.crosstab(df["module"], df["priority_norm"])
    for c in ["Highest", "High", "Medium", "Low", "Lowest"]:
        if c not in cls.columns:
            cls[c] = 0
    cls["Tổng"] = cls.sum(axis=1)
    cls = cls[["Tổng", "Highest", "High", "Medium", "Low", "Lowest"]]
    cls = cls.reset_index()
    return cls


# ================= EXCEL EXPORT =================
def to_excel(summary, cls):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        cls.to_excel(writer, sheet_name="Classification", index=False)

    return output.getvalue()


# ================= STREAMLIT UI =================
st.set_page_config(page_title="Jira Report Dashboard", layout="wide")

st.title("📊 Jira-like Bug Report Dashboard")

file = st.file_uploader("Upload Excel file", type=["xlsx"])

if file:

    df = pd.read_excel(file, header=0)

    df = clean_data(df)

    summary = build_summary(df)
    cls = build_classification(df)

    # ================= FILTER =================
    col1, col2, col3 = st.columns(3)

    with col1:
        module_filter = st.multiselect("Module", df["module"].unique())

    with col2:
        status_filter = st.multiselect("Status", df["status"].unique())

    with col3:
        priority_filter = st.multiselect("Priority", df["priority"].unique())

    filtered = df.copy()

    if module_filter:
        filtered = filtered[filtered["module"].isin(module_filter)]

    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]

    if priority_filter:
        filtered = filtered[filtered["priority"].isin(priority_filter)]

    st.subheader("📌 Raw Data")
    st.dataframe(filtered, use_container_width=True)

    st.subheader("📊 Summary")
    st.dataframe(summary, use_container_width=True)

    st.subheader("📊 Classification")
    st.dataframe(cls, use_container_width=True)

    # ================= CHARTS =================
    st.subheader("📈 Charts")

    c1, c2 = st.columns(2)

    with c1:
        fig1 = px.bar(summary, x="module", y="Tổng", title="Total Bugs per Module")
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        status_count = df["status"].value_counts().reset_index()
        status_count.columns = ["Status", "Count"]
        fig2 = px.pie(status_count, names="Status", values="Count", title="Status Distribution")
        st.plotly_chart(fig2, use_container_width=True)

    # ================= DOWNLOAD =================
    st.download_button(
        "📥 Download Excel Report",
        data=to_excel(summary, cls),
        file_name=f"jira_report_{date.today()}.xlsx"
    )