import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date
from io import BytesIO
import requests
from requests.auth import HTTPBasicAuth
from streamlit_autorefresh import st_autorefresh
from io import StringIO

st.set_page_config(page_title="Jira Bugs Report Dashboard", layout="wide")

jql = "project = DiHDBiz AND type in (NewFeature,Bug,Task) ORDER BY created DESC"

AUTO_REFRESH_INTERVAL = 0  # đơn vị: giây (ví dụ: 60s)

# ================= FETCH JIRA =================
@st.cache_data(ttl=60, show_spinner=False)

def fetch_jira_data(email, api_token, domain, jql):

    url = f"https://{domain}.atlassian.net/rest/api/3/search/jql"

    auth = HTTPBasicAuth(email, api_token)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    all_issues = []
    next_token = None

    while True:

        payload = {
            "jql": jql,
            "maxResults": 50,
            "fields": [
                "summary",
                "status",
                "priority",
                "assignee",
                "reporter",
                "issuetype",
                "parent",
                "created",
                "updated",
                "customfield_10011",
                "customfield_10014"
            ]
        }

        if next_token:
            payload["nextPageToken"] = next_token

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            auth=auth
        )

        if response.status_code != 200:
            st.error(response.text)
            break

        data = response.json()

        issues = data.get("issues", [])

        #st.write(f"Fetched: {len(all_issues) + len(issues)}")

        if not issues:
            break

        all_issues.extend(issues)

        # 🔥 KEY POINT
        next_token = data.get("nextPageToken")

        if not next_token:
            break

        # Thành công sẽ hiển thị trên UI -> Bỏ, không cần
        #st.success(f"✅ Total fetched: {len(all_issues)}")

    def get_name(val):
        if isinstance(val, dict):
            return val.get("name")
        return val

    def get_user(val):
        if isinstance(val, dict):
            return val.get("displayName") or val.get("accountId")
        return val

    # parse
    rows = []

    for issue in all_issues:

        # 🔥 Support cả 2 format Jira
        fields = issue.get("fields", issue)

        def get_nested(field, sub=None):
            val = fields.get(field)
            if isinstance(val, dict):
                return val.get(sub) if sub else val
            return val

        parent = fields.get("parent") or {}

        rows.append({
            "key": issue.get("key"),
            "summary": fields.get("summary"),

            "status": get_name(fields.get("status")),
            "priority": get_name(fields.get("priority")),

            "assignee": get_user(fields.get("assignee")),
            "reporter": get_user(fields.get("reporter")),
            "issue_type": (
            fields.get("issuetype", {}).get("name")
            if isinstance(fields.get("issuetype"), dict)
            else fields.get("issuetype")
            ),

            # 🔥 lấy epic name
            "epic name": (parent.get("fields") or {}).get("summary"),

            # 🔥 NEW: parent key
            "parent key": parent.get("key"),
            # 🔥 NEW
            "created": fields.get("created"),
            "updated": fields.get("updated")
        })

    return pd.DataFrame(rows)

# ================= CONFIG =================

def load_mapping():
    url = "https://docs.google.com/spreadsheets/d/1psWXuucE_IX_JBi5iG_m96sKuvY5xzEXYLU5BE7ug7w/gviz/tq?tqx=out:csv"
    try:
        r = requests.get(url)
        r.raise_for_status()

        df = pd.read_csv(StringIO(r.text))

        df.columns = df.columns.str.strip().str.lower()
        return df

    except Exception as e:
        print("Load mapping error:", e)
        return pd.DataFrame(columns=["code", "name"])

mapping_df = load_mapping()
mapping_df.columns = mapping_df.columns.str.strip().str.lower()
MODULE_MAP = dict(zip(mapping_df["code"], mapping_df["name"]))

def map_module(row):
    epic = row.get("epic name")
    parent_key = row.get("parent key")

    if pd.isna(parent_key) and pd.notna(epic):
        x = str(epic).strip().upper()
        return f"{x} - {MODULE_MAP[x]}" if x in MODULE_MAP else x

    if pd.notna(parent_key) and pd.notna(epic):
        return f"{parent_key} - {epic}"

    if pd.notna(parent_key):
        return str(parent_key)

    return "No Epic"

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

    # 🔥 chuẩn hoá column
    df.columns = df.columns.str.strip().str.lower()

    # 🔥 chuẩn hoá null
    df = df.replace(["nan", "None", ""], pd.NA)

    # 🔥 đảm bảo đủ cột
    for col in ["parent key", "epic name", "epic link", "parent"]:
        if col not in df.columns:
            df[col] = pd.NA

    # 🔥 build parent key (1 lần duy nhất)
    df["parent key"] = (
        df["parent key"]
        .fillna(df["epic link"])
        .fillna(df["parent"])
    )

    # 🔥 fill epic name từ mapping nếu thiếu
    df["epic name"] = df["epic name"].fillna(
        df["parent key"].map(lambda x: MODULE_MAP.get(str(x).upper()) if pd.notna(x) else None)
    )

    # 🔥 ưu tiên Excel trước
    if "issue type" in df.columns:
        df["issue_type"] = df["issue type"]

    elif "issuetype" in df.columns:
        df["issue_type"] = df["issuetype"]

    # ❌ XÓA cột cũ để tránh duplicate
    df = df.drop(columns=["issue type", "issuetype"], errors="ignore")

    # 🔥 map module chuẩn
    def map_module(row):
        parent_key = row["parent key"]
        epic = row["epic name"]

        if pd.notna(parent_key) and pd.notna(epic):
            return f"{parent_key} - {epic}"

        if pd.notna(parent_key):
            return str(parent_key)

        if pd.notna(epic):
            return str(epic)

        return "No Epic"

    df["module"] = df.apply(map_module, axis=1)

    # ================= OTHER CLEAN =================

    if "status" not in df.columns:
        raise ValueError(f"Missing column STATUS. Available columns: {df.columns.tolist()}")

    if "assignee" not in df.columns:
        df["assignee"] = "Unknown"

    if "reporter" not in df.columns:
        df["reporter"] = "Unknown"

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

# ================= Bổ sung Jira =================
st.markdown("## 📂 Data Source")

data_source = st.radio(
    "Select Data Source",
    ["📤 Upload Excel", "🔄 Sync Jira Realtime"]
)

email = st.secrets.get("email")
api_token = st.secrets.get("api_token")
domain = st.secrets.get("domain")

file = None

df = pd.DataFrame()

if data_source == "📤 Upload Excel":
    file = st.file_uploader("📤 Upload Excel file", type=["xlsx"], key="upload_excel")

    if file is not None:

        xls = pd.ExcelFile(file)
        target_sheet = "Your Jira Issues"

        if target_sheet in xls.sheet_names:

            temp_df = pd.read_excel(file, sheet_name=target_sheet, header=None)

            # 🔥 tìm dòng chứa header (có chữ "status")
            header_row = None
            for i, row in temp_df.iterrows():
                row_str = row.astype(str).str.lower()
                if row_str.str.contains("status").any():
                    header_row = i
                    break

            if header_row is None:
                st.error("❌ Không tìm thấy header chứa STATUS")
                st.stop()

            # 🔥 đọc lại với header đúng
            df = pd.read_excel(
                file,
                sheet_name=target_sheet,
                skiprows=header_row,
                header=0
            )

        else:
            st.error("❌ Không tìm thấy sheet 'Your Jira Issues'")
            st.stop()

elif data_source == "🔄 Sync Jira Realtime":
    df = st.session_state.get("jira_data", pd.DataFrame())

if AUTO_REFRESH_INTERVAL > 0:
    st_autorefresh(interval=AUTO_REFRESH_INTERVAL * 1000, key="auto_refresh")

if data_source == "🔄 Sync Jira Realtime":

    st.subheader("🔄 Jira Realtime Data")

    if st.button("🚀 Fetch Data from Jira"):
        with st.spinner("⏳ Uploading data from Jira..."):
            df = fetch_jira_data(email, api_token, domain, jql)
            st.session_state["jira_data"] = df

        st.success(f"✅ Loaded {len(df)} records")

    df = st.session_state.get("jira_data", pd.DataFrame())

    if st.button("♻️ Clear Cache"):
        st.cache_data.clear()
        st.session_state.pop("jira_data", None)  # 🔥 xoá data đã lưu
        st.success("✅ Cache cleared!")
        st.rerun()  # 🔥 reload app

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


if not df.empty:
    st.title("🐞 Jira Bugs Report Dashboard")
    st.markdown("### 🔎 Filters")
    df = clean_data(df)

    # ================= FILTER UI =================
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        module_list = sorted(df["module"].dropna().unique())
        module_filter = st.multiselect("Module", module_list)

    with col2:
        status_filter = st.multiselect("Status", sorted(df["status"].dropna().unique()))

    with col3:
        priority_filter = st.multiselect("Priority", sorted(df["priority_norm"].dropna().unique()))

    with col4:
        assignee_filter = st.multiselect(
            "Assignee",
            sorted(df["assignee"].dropna().unique()) if "assignee" in df.columns else []
        )

    with col5:
        reporter_filter = st.multiselect(
            "Reporter",
            sorted(df["reporter"].dropna().unique()) if "reporter" in df.columns else []
        )

    with col6:
        issue_type_filter = st.multiselect(
            "Issue Type",
            sorted(df["issue_type"].dropna().unique()) if "issue_type" in df.columns else [],
            default=["Bug"]
        )

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
    if assignee_filter:
        filtered = filtered[filtered["assignee"].isin(assignee_filter)]
    if reporter_filter:
        filtered = filtered[filtered["reporter"].isin(reporter_filter)]
    if issue_type_filter:
        filtered = filtered[filtered["issue_type"].isin(issue_type_filter)]

    if "Overall" not in env_options:
        filtered = filtered[filtered["status"].isin(env_status_filter)]

    # ================= BUILD =================
    summary = build_summary(filtered)
    cls = build_classification(filtered)

    summary_chart = summary[summary["Module (Epic)"] != "TOTAL"]

    # ================= OVERVIEW =================
    st.subheader("🧭 Overview")

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
        "priority": "Priority",
        "priority_norm": "Priority (Raw)",
        "summary": "Title",
        "status": "Status",
        "assignee": "Assignee",
        "issue_type": "Issue Type"
    })

    raw_display = capitalize_columns(raw_display)

    columns_to_hide = [
        "Resolution",
        "Parent",
        "Epic Link",
        "Priority (Raw)",
        "Due Date",
        "Parent Key",
        "Epic Name",
        "Due_Date"
    ]

    raw_display = raw_display.drop(columns=columns_to_hide, errors="ignore")

    preferred_cols = [
        "No.",
        "Key",
        "Title",
        "Status",
        "Priority",
        "Reporter",
        "Assignee",
        "Created",
        "Updated",
        "Module (Epic)",
        "Issue Type"
    ]

    existing_cols = [c for c in preferred_cols if c in raw_display.columns]

    raw_display = raw_display[
        existing_cols + [c for c in raw_display.columns if c not in existing_cols]
        ]

    st.dataframe(raw_display, use_container_width=True, hide_index=True)

    # ================= OVERALL =================
    st.subheader("🧾 Summary")

    summary_display = summary.copy()
    summary_display.insert(0, "No.", range(1, len(summary_display) + 1))

    summary_display = summary_display.rename(columns={
        "Deploy Uat": "Deploy UAT",
        "Uat Fpt Testing": "UAT FPT Testing",
        "Uat Hdb Testing": "UAT HDB Testing",
        "Deploy Stg": "Deploy STG",
        "Stg Fpt Testing": "STG FPT Testing",
        "Stg Hdb Testing": "STG HDB Testing",
        "Deploy Pilot": "Deploy PILOT",
        "Pilot Fpt Testing": "PILOT FPT Testing",
        "Pilot Hdb Testing": "PILOT HDB Testing"
    })

    st.dataframe(summary_display, use_container_width=True, hide_index=True)

    st.subheader("🧮 Classification")

    cls_display = cls.copy()
    cls_display.insert(0, "No.", range(1, len(cls_display) + 1))
    st.dataframe(cls_display, use_container_width=True, hide_index=True)

    # ================= CHARTS =================
    st.subheader("📊 Charts")

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