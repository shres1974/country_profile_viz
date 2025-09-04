
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from functools import lru_cache
from pathlib import Path
HERE = Path(__file__).parent

st.set_page_config(page_title="Country Profile Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ------------------ Styling ------------------
st.markdown(
    """
    <style>
    /* Compact top padding */
    .block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; }
    /* KPI cards */
    .kpi { border:1px solid rgba(0,0,0,0.08); border-radius:16px; padding:16px; background:var(--secondary-bg, #F4F6F8); }
    .kpi h3 { font-size:0.9rem; margin:0; color:#374151 }
    .kpi .value { font-size:1.6rem; font-weight:700; margin-top:6px; color:#111827 }
    /* Sticky header */
    .sticky { position: sticky; top: 0; z-index: 50; padding: 10px 0; background: rgba(255,255,255,0.96); backdrop-filter: blur(6px); border-bottom: 1px solid rgba(0,0,0,0.06); }
    .footer-note{ color:#6B7280; font-size:0.85rem; }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------ Helpers ------------------

@st.cache_data
def load_csv(uploaded_file, fallback_path=None):
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    if fallback_path is not None:
        return pd.read_csv(fallback_path)
    return pd.DataFrame()

def fmt_int(x):
    try:
        return f"{int(x):,}"
    except Exception:
        return "—"

# ------------------ Sidebar ------------------
st.sidebar.title("⚙️ Controls")

st.sidebar.write("Upload your data files (CSV). If omitted, sample data will be used. Hover each uploader for the expected schema.")

flows_csv = st.sidebar.file_uploader(
    "IP activity between two countries",
    type=["csv"],
    help='Required cols: year, origin_country, dest_country, ip_type, applications'
)
topfilers_csv = st.sidebar.file_uploader(
    "Top filers (origin → destination)",
    type=["csv"],
    help='Required cols: filer, origin_country, dest_country, ip_type, filings'
)
gender_csv = st.sidebar.file_uploader(
    "Gender inventors split",
    type=["csv"],
    help='Required cols: year, origin_country, dest_country, female_inventors, male_inventors'
)
pph_csv = st.sidebar.file_uploader(
    "PPH requests",
    type=["csv"],
    help='Required cols: year, direction, requests  (direction examples: CIPO→JPO, JPO→CIPO)'
)
importance_csv = st.sidebar.file_uploader(
    "Patent importance (by jurisdiction)",
    type=["csv"],
    help='Required cols: year, jurisdiction, importance_score'
)

# ------------------ Load Data ------------------
flows      = load_csv(flows_csv,      HERE / "sample_data" / "flows.csv")
topfilers  = load_csv(topfilers_csv,  HERE / "sample_data" / "top_filers.csv")
gender     = load_csv(gender_csv,     HERE / "sample_data" / "gender_split.csv")
pph        = load_csv(pph_csv,        HERE / "sample_data" / "pph.csv")
importance = load_csv(importance_csv, HERE / "sample_data" / "importance.csv")


all_countries = sorted(set(flows["origin_country"]).union(set(flows["dest_country"])))
default_pair = ("Canada", "Japan") if {"Canada","Japan"}.issubset(all_countries) else (all_countries[0], all_countries[min(1, len(all_countries)-1)])

c1 = st.sidebar.selectbox("Origin country", all_countries, index=all_countries.index(default_pair[0]) if default_pair[0] in all_countries else 0)
c2 = st.sidebar.selectbox("Destination country", all_countries, index=all_countries.index(default_pair[1]) if default_pair[1] in all_countries else 1)

ip_options = sorted(flows["ip_type"].dropna().unique().tolist()) if not flows.empty else []
selected_ip = st.sidebar.multiselect("IP types", ip_options, default=ip_options)

if flows.empty:
    st.warning("No data found. Using built-in samples. Upload your CSVs in the left sidebar to replace them.")
else:
    st.success("Loaded your data.")

# Year range
if not flows.empty:
    min_year = int(flows["year"].min())
    max_year = int(flows["year"].max())
else:
    min_year, max_year = 2019, 2024
yr_from, yr_to = st.sidebar.slider("Year range", min_value=min_year, max_value=max_year, value=(min_year, max_year))

# Filters applied
def apply_filters(df, ip_types=None, year_min=None, year_max=None):
    if df is None or df.empty:
        return df
    out = df.copy()
    if "year" in out.columns and year_min is not None and year_max is not None:
        out = out[(out["year"] >= year_min) & (out["year"] <= year_max)]
    if ip_types and "ip_type" in out.columns:
        out = out[out["ip_type"].isin(ip_types)]
    return out

flows_f = apply_filters(flows, selected_ip, yr_from, yr_to)
topfilers_f = apply_filters(topfilers, selected_ip, yr_from, yr_to)
gender_f = apply_filters(gender, None, yr_from, yr_to)
pph_f = apply_filters(pph, None, yr_from, yr_to)
importance_f = apply_filters(importance, None, yr_from, yr_to)

# ------------------ Header ------------------
st.markdown('<div class="sticky">', unsafe_allow_html=True)
title_col1, title_col2 = st.columns([0.7, 0.3])
with title_col1:
    st.subheader("Country Profile — Interactive One‑Pager")
    st.caption("Use the controls on the left to filter by year and IP types. Click/hover charts for details; everything updates live.")
with title_col2:
    st.write("")
    st.write("")
    st.download_button("⬇️ Download filtered flows CSV", data=flows_f.to_csv(index=False), file_name="flows_filtered.csv", mime="text/csv")
st.markdown('</div>', unsafe_allow_html=True)

# ------------------ KPIs ------------------
k1,k2,k3,k4 = st.columns(4)
def kpi_card(container, title, value):
    with container:
        st.markdown(f'<div class="kpi"><h3>{title}</h3><div class="value">{value}</div></div>', unsafe_allow_html=True)

# Compute totals
def sum_apps(df, o, d):
    if df.empty: return 0
    mask = (df["origin_country"]==o) & (df["dest_country"]==d)
    return int(df.loc[mask, "applications"].sum())

total_o_to_d = sum_apps(flows_f, c1, c2)
total_d_to_o = sum_apps(flows_f, c2, c1)

def yoy_change(df, o, d, end_year):
    if df.empty: return None
    df2 = df[(df["origin_country"]==o) & (df["dest_country"]==d)].groupby("year")["applications"].sum().sort_index()
    if end_year not in df2.index or (end_year-1) not in df2.index: return None
    prev = df2.loc[end_year-1]
    if prev == 0: return None
    return 100*(df2.loc[end_year]-prev)/prev

yoy_o_to_d = yoy_change(flows_f, c1, c2, yr_to)
yoy_d_to_o = yoy_change(flows_f, c2, c1, yr_to)

kpi_card(k1, f"{c1} → {c2} applications", fmt_int(total_o_to_d))
kpi_card(k2, f"{c2} → {c1} applications", fmt_int(total_d_to_o))
kpi_card(k3, f"YoY change ({c1}→{c2})", f"{yoy_o_to_d:+.1f}%" if yoy_o_to_d is not None else "—")
kpi_card(k4, f"YoY change ({c2}→{c1})", f"{yoy_d_to_o:+.1f}%" if yoy_d_to_o is not None else "—")

st.divider()

# ------------------ Layout Tabs ------------------
t1, t2, t3, t4, t5 = st.tabs(["Overview", "Flows & PPH", "Top Filers", "Gender", "Annex"])

with t1:
    col1, col2 = st.columns([0.62, 0.38])
    with col1:
        st.subheader("Applications over time")
        df_line = flows_f[(flows_f["origin_country"].isin([c1,c2])) & (flows_f["dest_country"].isin([c1,c2]))]
        if not selected_ip:
            df_line = df_line.copy()
        fig = px.line(
            df_line,
            x="year",
            y="applications",
            color="ip_type",
            line_group="origin_country",
            facet_row="origin_country",
            category_orders={"origin_country":[c1,c2]},
            markers=True
        )
        fig.update_layout(height=400, margin=dict(l=10,r=10,b=10,t=30))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("By IP type (latest year)")
        latest = flows_f[flows_f["year"]==yr_to]
        latest_pair = latest[((latest["origin_country"]==c1)&(latest["dest_country"]==c2)) | ((latest["origin_country"]==c2)&(latest["dest_country"]==c1))]
        if latest_pair.empty:
            st.info("No rows for the selected year.")
        else:
            figb = px.bar(latest_pair, x="ip_type", y="applications", color="origin_country", barmode="group")
            figb.update_layout(height=400, margin=dict(l=10,r=10,b=10,t=30))
            st.plotly_chart(figb, use_container_width=True)

with t2:
    st.subheader("Origin → Destination flow (Sankey)")
    df_sankey = flows_f[((flows_f["origin_country"]==c1)&(flows_f["dest_country"]==c2)) | ((flows_f["origin_country"]==c2)&(flows_f["dest_country"]==c1))]
    if df_sankey.empty:
        st.info("No flow data for the chosen filters.")
    else:
        # Build basic Sankey: nodes are countries + ip types concatenated to show breakdown
        nodes = list({c1, c2} | set(df_sankey["ip_type"].unique()))
        node_index = {n:i for i,n in enumerate(nodes)}
        links = {"source":[], "target":[], "value":[], "label":[]}
        for _, row in df_sankey.iterrows():
            links["source"].append(node_index[row["origin_country"]])
            links["target"].append(node_index[row["dest_country"]])
            links["value"].append(float(row["applications"]))
            links["label"].append(f'{row["origin_country"]}→{row["dest_country"]} ({row["ip_type"]})')
        sankey = go.Figure(data=[go.Sankey(
            node=dict(label=nodes, pad=20, thickness=14),
            link=dict(source=links["source"], target=links["target"], value=links["value"], label=links["label"])
        )])
        sankey.update_layout(height=450, margin=dict(l=10,r=10,b=10,t=30))
        st.plotly_chart(sankey, use_container_width=True)

    st.subheader("PPH requests")
    if pph_f.empty:
        st.info("No PPH data.")
    else:
        df_pph = pph_f[pph_f["direction"].isin([f"{c1}→{c2}", f"{c2}→{c1}"])]
        figp = px.bar(df_pph, x="year", y="requests", color="direction", barmode="group")
        figp.update_layout(height=350, margin=dict(l=10,r=10,b=10,t=30))
        st.plotly_chart(figp, use_container_width=True)

with t3:
    st.subheader("Top filers")
    df_top = topfilers_f[(topfilers_f["origin_country"]==c1) & (topfilers_f["dest_country"]==c2)]
    if df_top.empty:
        st.info(f"No filers from {c1} to {c2} for the selected filters.")
    else:
        topn = st.slider("How many to show", min_value=5, max_value=20, value=10, step=1)
        df_topn = df_top.sort_values("filings", ascending=False).head(topn)
        figt = px.bar(df_topn, x="filings", y="filer", color="ip_type", orientation="h")
        figt.update_layout(height=480, margin=dict(l=10,r=10,b=10,t=30), yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(figt, use_container_width=True)

with t4:
    st.subheader("Inventor gender split")
    df_g = gender_f[(gender_f["origin_country"]==c1) & (gender_f["dest_country"]==c2)]
    if df_g.empty:
        st.info("No gender data for this pair.")
    else:
        df_g = df_g.copy()
        df_g["total"] = df_g["female_inventors"] + df_g["male_inventors"]
        df_g["female_share"] = (df_g["female_inventors"]/df_g["total"]).replace([float('inf'), -float('inf')], 0).fillna(0)
        colg1, colg2 = st.columns([0.55, 0.45])
        with colg1:
            figg = px.area(df_g, x="year", y=["female_inventors","male_inventors"], labels={"value":"inventors","variable":"gender"})
            figg.update_layout(height=380, margin=dict(l=10,r=10,b=10,t=30))
            st.plotly_chart(figg, use_container_width=True)
        with colg2:
            latest = df_g[df_g["year"]==df_g["year"].max()].tail(1)
            female_share = float(latest["female_share"].iloc[0])*100 if not latest.empty else None
            st.metric("Female share (latest year)", f"{female_share:.1f}%" if female_share is not None else "—")
            st.dataframe(df_g.sort_values("year"), use_container_width=True, hide_index=True)

with t5:
    st.subheader("Patent importance trend (by jurisdiction)")
    if importance_f.empty:
        st.info("No importance data.")
    else:
        selected_jurs = st.multiselect("Jurisdictions", sorted(importance_f["jurisdiction"].unique().tolist()), default=sorted(importance_f["jurisdiction"].unique().tolist())[:4])
        df_imp = importance_f[importance_f["jurisdiction"].isin(selected_jurs)]
        figi = px.line(df_imp, x="year", y="importance_score", color="jurisdiction", markers=True)
        figi.update_layout(height=420, margin=dict(l=10,r=10,b=10,t=30))
        st.plotly_chart(figi, use_container_width=True)

st.divider()

