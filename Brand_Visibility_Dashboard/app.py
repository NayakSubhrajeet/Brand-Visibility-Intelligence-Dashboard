from itertools import product
import duckdb
import streamlit as st
import pandas as pd
import numpy as np
import mysql
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

## Page Configuration
st.set_page_config(
    page_title="Brand Visibility Inteligence Dashboard",
    page_icon="🛒",
    layout="wide"
)

## CSS
st.markdown("""
<style>
.main_page {
    background-color:blue;
    padding:20px 20px;
    border-radius: 14px;
    color: white;
    margin-bottom: 20px;
}
</style>
""",unsafe_allow_html=True)

# Establish connection
import mysql.connector
conn=mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="Bishal@111",
    database="Brand_DB"
)

@st.cache_resource
def sql_con():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="Bishal@111",
            database="Brand_DB"
        )
    except mysql.connector.Error as err:
        st.error(f"❌ Database Connection Failed: {err}")
        st.stop()

@st.cache_data
def load_data():
    df=pd.read_sql("SELECT keyword, title, price, rating, reviews, platform, delivery FROM product",conn)

    df['title']=df['title'].astype(str).str.strip()
    df['platform']=df['platform'].astype(str).str.strip()
    df['keyword']=df['keyword'].astype(str).str.strip().str.title()

    case_fix={"Lg": "LG", "Hp": "HP", "Asus": "ASUS", "Jbl": "JBL", "Boat": "boAt", "Tv": "TV"}
    brand=df['title'].str.split().str[0].str.title()
    df['Brand']=brand.replace(case_fix)

    market={"amazon", "flipkart", "croma", "reliance digital", "reliance"}
    df['Data Source']=np.where(
        df['platform'].str.lower().isin(market),
        "Indian E-Commerce",
        "Global Brand Data",
    )

    df['Position']=df.groupby('keyword').cumcount() + 1

    return df
df=load_data()

#=================================================(Side Bar)==========================================================

with st.sidebar:
    st.markdown("""
    <div style="text-align: center;">
    <h6 style="font-size :40px" >🛒</h6>
    <h1 style="color :orange">Brand Visibility</h1>
    <p>Inteligence Dashboard</p>
    </div>

    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("🎛️ Filters")
    st.caption("All filters dynamically match records below")

    sel_keywords=st.multiselect("🔑 KEYWORD",
                               sorted(df['keyword'].unique()))

    sel_brands=st.multiselect("🏷️ BRAND",
                              sorted(df['Brand'].unique()))

    sel_platforms=st.multiselect("🏬 PLATFORM",
                                 sorted(df['platform'].unique()))

    price_min=float(df['price'].min())
    price_max=float(df['price'].max())
    price_range=st.slider("💰 PRICE RANGE",price_min,price_max,(price_min,price_max))

    rating_range=st.slider("⭐ RATING RANGE",0.0,5.0,(0.0,5.0))

    position_max=int(df['Position'].max())
    sel_position=st.slider("📍 MAX POSITION (RANKING)",max_value=position_max,value=min(40,position_max))

    sel_sources=st.selectbox("📁 DATA SOURCE",['All']+sorted(df['Data Source'].unique().tolist()))

f=df.copy()

if sel_keywords:
    f=f[f['keyword'].isin(sel_keywords)]
if sel_brands:
    f=f[f['Brand'].isin(sel_brands)]
if sel_platforms:
    f=f[f['platform'].isin(sel_platforms)]

f=f[(f['price']>=price_range[0]) & (f['price']<=price_range[1])]
f=f[(f['rating']>=rating_range[0]) & (f['rating']<=rating_range[1])]
f=f[f['Position']<=position_max]

if sel_sources!='All':
    f=f[f['Data Source']==sel_sources]

with st.sidebar:
    st.divider()
    st.markdown(f"**Total records:** {len(f):,}")


#=================================================== (Main Page) =======================================================

st.markdown(f"""
<div class="main_page">
<h2>🛒 E-Commerce Analytics Dashboard</h2>
<div>Indian E-Commerce + Global Brand Data :{len(f):,} records shown</div>
</div>
""",unsafe_allow_html=True)

con=duckdb.connect()
con.register('products',f)

def sql_expander(title, query):
    with st.expander(f"🗄️ SQL Query Used — {title}"):
        st.code(query, language="sql")


# Tabs
tab_overview, tab_brand, tab_pricing, tab_platform, tab_ranking = st.tabs(
    ["📊 Overview", "🏷️ Brand Insights", "💰 Pricing Analysis", "🏬 Platform Analysis", "📍 Visibility & Ranking"]
)
def kpi_card(col,icon,value,label):
    col.metric(f"{icon}{label}",value)

# ===============================================(OVERVIEW)=============================================================
with tab_overview:
    if len(f) == 0:
        st.warning("No records match the current filters")
    else:
        # KPI cards
        col1, col2, col3, col4, col5 = st.columns(5)
        kpi_card(col1, "📦", f"{len(f):,}", "Total Products")
        kpi_card(col2, "💰", f"{f['price'].mean():,.0f}", "Avg Price")
        kpi_card(col3, "⭐", f"{f['rating'].mean():,.2f}", "Avg Rating")
        kpi_card(col4, "💬", f"{f['reviews'].sum():,}", "Total Reviews")
        kpi_card(col5, "🏬", f"{f['platform'].nunique()}", "Platforms")

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("🏬 Platform Share")
            qr = """
                select platform,count(*) as cnt
                from products
                group by platform
                order by cnt desc
            """
            platform_counts = con.execute(qr).df()

            fig_platform = px.pie(platform_counts, names="platform", values="cnt", hole=0.4)
            st.plotly_chart(fig_platform, use_container_width=True, key="overview_platform_pie")
            sql_expander("Platform Share", "SELECT platform, count(*) AS cnt\nFROM products\nGROUP BY platform\nORDER BY cnt DESC;")

        with col_right:
            st.subheader("📁 Data Source Split")
            src_counts = con.execute('select "Data Source", count(*) as cnt from products group by "Data Source"').df()
            fig_src = px.pie(src_counts, names="Data Source", values="cnt", hole=0.4)
            st.plotly_chart(fig_src, use_container_width=True, key="overview_source_pie")
            sql_expander("Data Source Split", 'SELECT "Data Source", count(*) AS cnt\nFROM products\nGROUP BY "Data Source";')

        col_bottom_left, col_bottom_right = st.columns(2)

        with col_bottom_left:
            st.subheader("📊 Price Distribution")
            fig_price = px.histogram(f, x="price", nbins=40, marginal="box")
            st.plotly_chart(fig_price, use_container_width=True, key="overview_price_hist")

        with col_bottom_right:
            st.subheader("🔑 Products per Keyword")
            pr_counts = con.execute("""
                SELECT keyword, COUNT(*) AS products 
                FROM products 
                GROUP BY keyword 
                ORDER BY products DESC
            """).df()

            fig_kw = px.bar(pr_counts,x="keyword",y="products",color="products",color_continuous_scale="Blues")
            fig_kw.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_kw, use_container_width=True, key="overview_keyword_bar")
            sql_expander("Products per Keyword", "SELECT keyword, count(*) as products\nFROM products\nGROUP BY keyword\nORDER BY products DESC;")

# =================================================(Brand Insights)==================================================
with tab_brand:
    if len(f) == 0:
        st.warning("No records match the current filters")
    else:
        if "Visibility_Score" not in f.columns:
            f["Visibility_Score"] = np.round(np.maximum(1.0, 100 - (f["Position"] * 2.2)), 1)

        con.register('products',f)

        top_brand_row = f["Brand"].value_counts().reset_index().iloc[0] if not f.empty else None
        top_brand_name = top_brand_row["Brand"] if top_brand_row is not None else "N/A"
        top_brand_cnt = top_brand_row["count"] if top_brand_row is not None else 0

        col_b1, col_b2, col_b3 = st.columns(3)
        kpi_card(col_b1, "🏆 ", top_brand_name, f"Top Brand ({top_brand_cnt:,} products)")
        kpi_card(col_b2, "👁️ ", f"{f['Visibility_Score'].mean():.1f}", "Avg Visibility Score")
        kpi_card(col_b3, "🏷️ ", f"{f['Brand'].nunique():,}", "Unique Brands")

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("🏷️ Brand vs Product Count (Top 15)")
            top_count = con.execute(
                'SELECT "Brand", COUNT(*) AS products FROM products GROUP BY "Brand" ORDER BY products DESC LIMIT 15'
            ).df()

            fig_count = px.bar(top_count,x="Brand",y="products",color="products",color_continuous_scale="Blues")
            fig_count.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_count, use_container_width=True, key="brand_product_count_bar")
            sql_expander(
                "Brand vs Product Count",
                'SELECT "Brand", COUNT(*) AS products\nFROM products\nGROUP BY "Brand"\nORDER BY products DESC\nLIMIT 15;'
            )

        with col_right:
            st.subheader("⭐ Brand vs Avg Rating (Top 15)")
            top_rating = con.execute(
                'SELECT "Brand", AVG(rating) AS avg_rating FROM products GROUP BY "Brand" ORDER BY avg_rating DESC LIMIT 15'
            ).df()

            fig_rating = px.bar( top_rating.sort_values("avg_rating"), x="avg_rating",y="Brand",orientation="h",color="avg_rating",
                color_continuous_scale="Greens")
            fig_rating.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_rating, use_container_width=True, key="brand_avg_rating_bar")
            sql_expander(
                "Brand vs Avg Rating",
                'SELECT "Brand", AVG(rating) AS avg_rating\nFROM products\nGROUP BY "Brand"\nORDER BY avg_rating DESC\nLIMIT 15;'
            )

        col_b_bottom1, col_b_bottom2 = st.columns(2)

        with col_b_bottom1:
            st.subheader("📍 Average Ranking per Brand (Top 15)")
            brand_rank = con.execute(
                'SELECT "Brand", AVG("Position") AS avg_rank FROM products GROUP BY "Brand" HAVING COUNT(*) >= 2 ORDER BY avg_rank ASC LIMIT 15'
            ).df()

            fig_rank = px.bar(
                brand_rank.sort_values("avg_rank", ascending=False),
                x="avg_rank",
                y="Brand",
                orientation="h",
                color="avg_rank",
                color_continuous_scale="Purples_r"
            )
            fig_rank.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_rank, use_container_width=True, key="brand_avg_rank_bar")
            sql_expander(
                "Average Ranking per Brand",
                'SELECT "Brand", AVG("Position") AS avg_rank\nFROM products\nGROUP BY "Brand"\nHAVING COUNT(*) >= 2\nORDER BY avg_rank ASC\nLIMIT 15;'
            )

        with col_b_bottom2:
            st.subheader("👁️ Highest Average Visibility Score by Brand (Top 15)")
            brand_vis = con.execute(
                'SELECT "Brand", AVG("Visibility_Score") AS avg_visibility FROM products GROUP BY "Brand" ORDER BY avg_visibility DESC LIMIT 15'
            ).df()

            fig_vis = px.bar(
                brand_vis,
                x="Brand",
                y="avg_visibility",
                color="avg_visibility",
                color_continuous_scale="Teal"
            )
            fig_vis.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_vis, use_container_width=True, key="brand_avg_visibility_bar")
            sql_expander(
                "Highest Average Visibility Score",
                'SELECT "Brand", AVG("Visibility_Score") AS avg_visibility\nFROM products\nGROUP BY "Brand"\nORDER BY avg_visibility DESC\nLIMIT 15;'
            )

#==================================================(Pricing)=========================================================
with tab_pricing:
    if len(f)==0:
        st.warning("No records match the current filters")
    else:
        con.register('products', f)

        col_p1, col_p2, col_p3 = st.columns(3)
        kpi_card(col_p1, "🏷️", f"${f['price'].min():,.2f}", "Min Price")
        kpi_card(col_p2, "💰", f"${f['price'].mean():,.2f}", "Avg Price")
        kpi_card(col_p3, "💎", f"${f['price'].max():,.2f}", "Max Price")

        st.divider()

        col1,col2=st.columns(2)

        with col1:
            st.subheader("📊 Price Distribution")
            fig=px.histogram(f,x='price',nbins=40)
            st.plotly_chart(fig,use_container_width=True)

        with col2:
            st.subheader("🏬 Average Price per Platform")
            avg_price_platform = con.execute("""
                SELECT platform, AVG(price) AS avg_price 
                FROM products 
                GROUP BY platform 
                ORDER BY avg_price DESC
            """).df()

            fig_avg_price = px.bar(
                avg_price_platform,
                x="platform",
                y="avg_price",
                color="platform",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_avg_price.update_layout(
                xaxis_title="Platform",
                yaxis_title="Average Price ($)",
                showlegend=False
            )
            st.plotly_chart(fig_avg_price, use_container_width=True, key="pricing_avg_price_platform_bar")
            sql_expander(
                "Average Price per Platform",
                "SELECT platform, AVG(price) AS avg_price\nFROM products\nGROUP BY platform\nORDER BY avg_price DESC;"
            )

            st.subheader("🔝 Highest Priced Product per Keyword")

            highest_price_keyword = con.execute("""
                    SELECT keyword, MAX(price) AS max_price 
                    FROM products 
                    GROUP BY keyword 
                    ORDER BY max_price DESC
                """).df()

            fig_max_price_kw = px.bar(
                highest_price_keyword,
                x="keyword",
                y="max_price",
                color="max_price",
                color_continuous_scale="Viridis",
                labels={"keyword": "Keyword", "max_price": "Highest Price ($)"}
            )
            fig_max_price_kw.update_layout(coloraxis_showscale=False)

            st.plotly_chart(fig_max_price_kw, use_container_width=True, key="pricing_max_price_per_keyword_bar")
            sql_expander(
                "Highest Price per Keyword",
                "SELECT keyword, MAX(price) AS max_price\nFROM products\nGROUP BY keyword\nORDER BY max_price DESC;"
            )

#================================================(Platform Analysis)=================================================
with tab_platform:
    if len(f)==0:
        st.warning("No records match the current filters")
    else:
        con.register('products', f)

        top_platform_row = f["platform"].value_counts().reset_index().iloc[0] if not f.empty else None
        top_plat_name = top_platform_row["platform"] if top_platform_row is not None else "N/A"
        top_plat_cnt = top_platform_row["count"] if top_platform_row is not None else 0

        col_p1, col_p2, col_p3 = st.columns(3)
        kpi_card(col_p1, "🏬 ", top_plat_name, f"Top Platform ({top_plat_cnt:,} products)")
        kpi_card(col_p2, "⭐ ", f"{f['rating'].mean():.2f}", "Avg Rating Across Platforms")
        kpi_card(col_p3, "📊 ", f"{f['platform'].nunique()}", "Active Platforms")

        st.divider()
        col1,col2=st.columns(2)

        with col1:
            st.subheader("💰 Avg Price by Platform (Top 15)")
            plat_price=con.execute("SELECT platform,AVG(price) AS avg_price,COUNT(*) AS n FROM products GROUP BY platform "
                                     "ORDER BY n DESC LIMIT 15").df()
            fig=px.bar(plat_price.sort_values("avg_price"),x="avg_price",y="platform",color="avg_price",color_continuous_scale="Oranges")
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig,use_container_width=True)
            sql_expander("Avg Price by Platform",
                         "SELECT platform, AVG(price) AS avg_price, COUNT(*) AS n\nFROM products\nGROUP BY platform\nORDER BY n DESC\nLIMIT 15;")


        with col2:
            st.subheader("💬 Total Reviews by Platform (Top 15)")
            plat_reviews=con.execute(
                "SELECT platform,SUM(reviews) AS total_reviews FROM products GROUP BY platform ORDER BY total_reviews DESC LIMIT 15"
            ).df()
            fig=px.bar(plat_reviews,x="platform",y="total_reviews",color="total_reviews",color_continuous_scale="Reds")
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig,use_container_width=True)
            sql_expander("Total Reviews by Platform",
                         "SELECT platform, SUM(reviews) AS total_reviews\nFROM products\nGROUP BY platform\nORDER BY total_reviews DESC\nLIMIT 15;")


        col_3,col_4=st.columns(2)
        with col_3:
            st.subheader("📦 Product Count per Platform")
            plat_count = con.execute("""
                            SELECT platform, COUNT(*) AS total_products 
                            FROM products 
                            GROUP BY platform 
                            ORDER BY total_products DESC
                        """).df()

            fig_plat_count = px.bar(
                plat_count,
                x="platform",
                y="total_products",
                color="platform",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_plat_count.update_layout(showlegend=False)
            st.plotly_chart(fig_plat_count, use_container_width=True, key="platform_product_count_bar")
            sql_expander(
                "Product Count per Platform",
                "SELECT platform, COUNT(*) AS total_products\nFROM products\nGROUP BY platform\nORDER BY total_products DESC;"
            )

            with col_4:
                st.subheader("🥧 Platform Market Share")
                fig_plat_share = px.pie(
                    plat_count,
                    names="platform",
                    values="total_products")
                st.plotly_chart(fig_plat_share, use_container_width=True, key="platform_market_share_pie")
                sql_expander(
                    "Platform Market Share",
                    "SELECT platform, COUNT(*) AS total_products\nFROM products\nGROUP BY platform;"
                )

#================================================(Visibility & Ranking)================================================
with tab_ranking:
    if len(f)==0:
        st.warning("No records match the current filters")
    else:


        col1,col2=st.columns(2)

        with col1:
            st.subheader("🏬 Average Visibility Score by Platform")
            plat_vis = con.execute("""
                            SELECT platform, AVG(Visibility_Score) AS avg_visibility 
                            FROM products 
                            GROUP BY platform 
                            ORDER BY avg_visibility DESC
                        """).df()

            fig_plat_vis = px.bar(
                plat_vis,
                x="platform",
                y="avg_visibility",
                color="avg_visibility",
                color_continuous_scale="Teal",
                labels={"platform": "Platform", "avg_visibility": "Avg Visibility Score"}
            )
            fig_plat_vis.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_plat_vis, use_container_width=True, key="visibility_avg_vis_platform_bar")
            sql_expander(
                "Avg Visibility Score by Platform",
                "SELECT platform, AVG(Visibility_Score) AS avg_visibility\nFROM products\nGROUP BY platform\nORDER BY avg_visibility DESC;"
            )


        with col2:
            st.subheader("🎯 Position vs Rating")
            fig=px.scatter(f,x="Position",y="rating",color="Data Source")
            st.plotly_chart(fig,use_container_width=True)


        col3,col4=st.columns(2)
        with col3:
            st.subheader("📊 Visibility Score Distribution")
            fig_vis_hist = px.histogram(f,x="Visibility_Score",nbins=30,
                labels={"Visibility_Score": "Visibility Score"})
            st.plotly_chart(fig_vis_hist, use_container_width=True, key="visibility_score_hist")
            sql_expander(
                "Visibility Score Distribution",
                "SELECT Visibility_Score FROM products;"
            )
        with col4:
            st.subheader("📍 Avg Position by Brand ")
            brand_pos = con.execute(
                'SELECT "Brand",AVG("Position")AS avg_position,COUNT(*)AS n FROM products GROUP BY "Brand" '
                'HAVING COUNT(*) >= 3 ORDER BY avg_position ASC LIMIT 15').df()
            fig = px.bar(brand_pos.sort_values("avg_position", ascending=False), x="avg_position", y="Brand",
                         color="avg_position", color_continuous_scale="Purples_r")
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
            sql_expander("Avg Position by Brand",
                         'SELECT "Brand", AVG("Position") AS avg_position, COUNT(*) AS n\nFROM products\n'
                         'GROUP BY "Brand"\nHAVING COUNT(*) >= 3\nORDER BY avg_position ASC\nLIMIT 15;')