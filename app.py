import io
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# PAGE SETUP & STYLE
# ------------------------------------------------------------------
st.set_page_config(page_title="Used Car Market Analysis & Price Exploration", page_icon="🚗", layout="wide")

ACCENT = "#FF7A3D"
TEAL = "#2EC4B6"
PALETTE = [TEAL, ACCENT, "#FFC857", "#8E7DFF", "#FF5D8F"]

st.markdown(
    f"""
    <style>
    .hero {{
        padding: 28px 32px; border-radius: 18px; margin-bottom: 18px;
        background: linear-gradient(120deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        border-left: 8px solid {ACCENT};
    }}
    .hero h1 {{ color: #fff; margin: 0; font-size: 2.2rem; }}
    .hero p  {{ color: #cfe8ef; margin: 6px 0 0 0; font-size: 1.05rem; }}
    .kpi {{
        padding: 18px 20px; border-radius: 16px; text-align: center;
        background: linear-gradient(135deg, #1b2a35, #24404f);
        border-top: 4px solid {TEAL}; box-shadow: 0 4px 14px rgba(0,0,0,.25);
    }}
    .kpi .label {{ color: #9fc3cf; font-size: .85rem; letter-spacing: .08em; text-transform: uppercase; }}
    .kpi .value {{ color: #fff; font-size: 1.9rem; font-weight: 700; margin-top: 4px; }}
    .finding {{
        padding: 14px 18px; margin: 8px 0; border-radius: 12px;
        background: rgba(46,196,182,.10); border-left: 5px solid {TEAL};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

REQUIRED_COLS = [
    "name", "year", "selling_price", "km_driven",
    "fuel", "seller_type", "transmission", "owner",
]


# ------------------------------------------------------------------
# LOAD & CLEAN DATA 
# ------------------------------------------------------------------
@st.cache_data
def load_data(file_bytes: bytes | None = None) -> pd.DataFrame:
    if file_bytes is None:
        df = pd.read_csv(Path(__file__).parent / "CARDataSet.csv")
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))

    for col in ["year", "selling_price", "km_driven"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=REQUIRED_COLS).drop_duplicates().reset_index(drop=True)
    df["year"] = df["year"].astype(int)
    df["brand"] = df["name"].astype(str).str.split().str[0]
    df["price_lakh"] = df["selling_price"] / 100000
    return df


def apply_dark_theme(fig, height=380):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="",
    )
    return fig


# ------------------------------------------------------------------
# SIDEBAR DATA & FILTERS
# ------------------------------------------------------------------
st.sidebar.header("📁 Data")
uploaded = st.sidebar.file_uploader("Upload CSV (optional)", type="csv")

try:
    df = load_data(uploaded.getvalue() if uploaded else None)
    data_label = uploaded.name if uploaded else "default CarDekho dataset"
except Exception as e:
    st.sidebar.error(f"Could not read file ({e}). Using default dataset.")
    df = load_data(None)
    data_label = "default CarDekho dataset"

st.sidebar.markdown("---")
st.sidebar.header("🔎 Filters")

year_min, year_max = int(df["year"].min()), int(df["year"].max())
year_range = st.sidebar.slider("Manufacturing year", year_min, year_max, (year_min, year_max))

fuels = st.sidebar.multiselect("Fuel type", sorted(df["fuel"].unique()), default=sorted(df["fuel"].unique()))
trans = st.sidebar.multiselect("Transmission", sorted(df["transmission"].unique()), default=sorted(df["transmission"].unique()))
sellers = st.sidebar.multiselect("Seller type", sorted(df["seller_type"].unique()), default=sorted(df["seller_type"].unique()))

max_price = round(float(df["price_lakh"].max()), 1)
price_range = st.sidebar.slider("Price range ($ Lakh)", 0.0, max_price, (0.0, max_price))

filtered = df[
    df["year"].between(*year_range)
    & df["fuel"].isin(fuels)
    & df["transmission"].isin(trans)
    & df["seller_type"].isin(sellers)
    & df["price_lakh"].between(*price_range)
]

st.sidebar.markdown("---")
st.sidebar.metric("Cars matching filters", f"{len(filtered):,}")

if filtered.empty:
    st.warning("No cars match these filters. Please adjust the sidebar filters.")
    st.stop()

# ------------------------------------------------------------------
# HEADER & 4 KPI CARDS
# ------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero">
        <h1>🚗 Used Car Market Analysis & Price Exploration</h1>
        <p>Interactive exploration of {len(df):,} cleaned car listings ({data_label}) —
        see how year, mileage, fuel, transmission, and ownership affect selling prices.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

auto_pct = (filtered["transmission"] == "Automatic").mean() * 100
kpis = [
    ("Total Cars", f"{len(filtered):,}"),
    ("Average Price", f"${filtered['price_lakh'].mean():,.2f} L"),
    ("Median KM Driven", f"{filtered['km_driven'].median():,.0f} km"),
    ("Automatic Share", f"{auto_pct:.1f}%"),
]
for col, (label, value) in zip(st.columns(4), kpis):
    col.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div></div>', unsafe_allow_html=True)

st.write("")

# ------------------------------------------------------------------
# TABS & CHARTS
# ------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Univariate", "🔗 Bivariate", "⚖️ Comparison"])

with tab1:
    c1, c2 = st.columns(2)

    top_models = filtered["name"].value_counts().head(10).sort_values().reset_index()
    top_models.columns = ["name", "count"]
    fig1 = px.bar(top_models, x="count", y="name", orientation="h",
                  title="Top 10 most listed car models", color_discrete_sequence=[TEAL])
    c1.plotly_chart(apply_dark_theme(fig1, 420), use_container_width=True)

    fig2 = px.histogram(filtered, x="price_lakh", nbins=40,
                        title="Selling price distribution ($ Lakh)",
                        labels={"price_lakh": "Selling price ($ Lakh)"},
                        color_discrete_sequence=[ACCENT])
    fig2.update_layout(yaxis_title="Number of cars")
    c2.plotly_chart(apply_dark_theme(fig2, 420), use_container_width=True)

    c3, c4 = st.columns(2)

    fuel_counts = filtered["fuel"].value_counts().reset_index()
    fuel_counts.columns = ["fuel", "count"]
    fig3 = px.pie(fuel_counts, names="fuel", values="count", hole=0.55,
                  title="Fuel type share", color_discrete_sequence=PALETTE)
    c3.plotly_chart(apply_dark_theme(fig3), use_container_width=True)

    brand_counts = filtered["brand"].value_counts().head(8).reset_index()
    brand_counts.columns = ["brand", "count"]
    fig4 = px.bar(brand_counts, x="brand", y="count", title="Most popular brands",
                  color="count", color_continuous_scale="Tealgrn")
    fig4.update_coloraxes(showscale=False)
    c4.plotly_chart(apply_dark_theme(fig4), use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    sample = filtered.sample(min(len(filtered), 1500), random_state=1)

    fig5 = px.scatter(sample, x="year", y="price_lakh", color="fuel", opacity=0.65,
                      hover_name="name", title="Manufacturing year vs Selling price",
                      labels={"price_lakh": "Price ($ Lakh)", "year": "Manufacturing year"},
                      color_discrete_sequence=PALETTE)
    c1.plotly_chart(apply_dark_theme(fig5, 420), use_container_width=True)

    fig6 = px.scatter(sample, x="km_driven", y="price_lakh", color="transmission", opacity=0.65,
                      hover_name="name", title="KM driven vs Selling price",
                      labels={"price_lakh": "Price ($ Lakh)", "km_driven": "KM driven"},
                      color_discrete_sequence=[TEAL, ACCENT])
    c2.plotly_chart(apply_dark_theme(fig6, 420), use_container_width=True)

    corr = filtered[["year", "km_driven", "selling_price"]].corr().round(2)
    fig7 = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                     title="Correlation heatmap (numeric features)")
    st.plotly_chart(apply_dark_theme(fig7, 360), use_container_width=True)

with tab3:
    c1, c2 = st.columns(2)

    avg_fuel = filtered.groupby("fuel", as_index=False)["price_lakh"].mean().sort_values("price_lakh", ascending=False)
    fig8 = px.bar(avg_fuel, x="fuel", y="price_lakh", text_auto=".2f",
                  title="Average price by fuel type ($ Lakh)",
                  labels={"price_lakh": "Avg price ($ Lakh)"},
                  color="fuel", color_discrete_sequence=PALETTE)
    fig8.update_layout(showlegend=False)
    c1.plotly_chart(apply_dark_theme(fig8), use_container_width=True)

    fig9 = px.box(filtered, x="transmission", y="price_lakh", color="transmission",
                  title="Automatic vs Manual price spread",
                  labels={"price_lakh": "Price ($ Lakh)"},
                  color_discrete_sequence=[TEAL, ACCENT])
    fig9.update_layout(showlegend=False)
    c2.plotly_chart(apply_dark_theme(fig9), use_container_width=True)


# ------------------------------------------------------------------
# RAW DATA & KEY FINDINGS
# ------------------------------------------------------------------
st.markdown("---")
if st.checkbox("📄 Show raw data"):
    st.dataframe(filtered.drop(columns=["brand", "price_lakh"]), use_container_width=True)

st.header("💡 Key Findings")

corr_year = filtered["year"].corr(filtered["selling_price"])
corr_km = filtered["km_driven"].corr(filtered["selling_price"])
top_fuel = filtered["fuel"].value_counts().idxmax()
top_model = filtered["name"].value_counts().idxmax()
priciest_fuel = filtered.groupby("fuel")["price_lakh"].mean().idxmax()

findings = [
    f"**Popularity:** **{top_fuel}** is the most common fuel type and **{top_model}** is the most listed model; Diesel and Petrol dominate overall.",
    f"**Manufacturing Year:** Year and price have a **{corr_year:.2f}** correlation — newer cars sell for more.",
    f"**KM Driven:** KM driven vs price correlation is **{corr_km:.2f}** — age and model matter more than mileage alone.",
    f"**Fuel & Ownership:** **{priciest_fuel}** has the highest average price, and prices drop as previous owners increase.",
    "**Price Distribution:** Most cars sit in lower-to-mid price ranges with right-skewed luxury outliers.",
]

for item in findings:
    st.markdown(f'<div class="finding">{item}</div>', unsafe_allow_html=True)