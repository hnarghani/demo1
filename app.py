import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from io import BytesIO

# Initialize Database
def init_db():
    with sqlite3.connect("saleasy_db.sqlite") as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (username TEXT PRIMARY KEY, password TEXT, analysis_type TEXT, report_schedule TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS reports 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, report_time TEXT, report_file TEXT)''')
        conn.commit()

# Generate Excel Report
def generate_excel(df, top_product):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sales Report', index=False)
    workbook = writer.book
    worksheet = writer.sheets['Sales Report']
    worksheet.write(len(df) + 2, 0, f"Top Selling Product: {top_product['product']} (Sales: {top_product['price']})")
    writer.close()
    return output.getvalue()

# App UI
st.set_page_config(page_title="Saleasy - Sales Dashboard", layout="wide")
st.markdown("<h1 style='text-align: center; color: blue;'>Saleasy - داشبورد فروش</h1>", unsafe_allow_html=True)

# Login System
if "logged_in" not in st.session_state:
    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")
    if st.button("ورود"):
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.success(f"خوش آمدید {username}!")
        st.rerun()
else:
    st.sidebar.write(f"👤 {st.session_state['username']}")
    st.sidebar.button("خروج", on_click=lambda: st.session_state.clear())

    file = st.file_uploader("فایل CSV خود را آپلود کنید", type=["csv"])
    if file:
        df = pd.read_csv(file)
        selected_columns = st.multiselect("انتخاب ستون‌های مورد نظر", df.columns, default=df.columns[:3])
        if selected_columns:
            df_clean = df[selected_columns].copy()
            st.write("داده‌های انتخاب‌شده:")
            st.dataframe(df_clean)

            product_col = st.selectbox("ستون محصول", selected_columns)
            price_col = st.selectbox("ستون قیمت", selected_columns)
            date_col = st.selectbox("ستون تاریخ", selected_columns)

            df_clean = df[[product_col, price_col, date_col]].copy()
            df_clean.columns = ["product", "price", "date"]
            df_clean["price"] = pd.to_numeric(df_clean["price"], errors="coerce")
            df_clean["date"] = pd.to_datetime(df_clean["date"], errors="coerce")
            df_clean = df_clean.dropna()

            # Compute sales summary
            sales_summary = df_clean.groupby("product")["price"].sum().reset_index()

            if not sales_summary.empty:
                top_product = sales_summary.sort_values(by="price", ascending=False).iloc[0]
                st.markdown(f"### 🏆 پرفروش‌ترین محصول: {top_product['product']} (فروش: {top_product['price']:,.0f} تومان)")
            else:
                top_product = {"product": "N/A", "price": 0}
                st.warning("⚠️ داده‌ای برای تحلیل وجود ندارد!")

            # Display Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 مجموع فروش", f"{df_clean['price'].sum():,.0f} تومان")
            col2.metric("📦 تعداد محصولات", f"{df_clean['product'].nunique()}")
            col3.metric("📅 اولین تاریخ", f"{df_clean['date'].min()}")

            # Additional Charts
            fig_pie = px.pie(sales_summary, names="product", values="price", title="🔹 سهم فروش هر محصول")
            st.plotly_chart(fig_pie, use_container_width=True)

            sales_trend = df_clean.groupby("date")["price"].sum().reset_index()
            fig_line = px.line(sales_trend, x="date", y="price", title="📈 روند فروش در طول زمان")
            st.plotly_chart(fig_line, use_container_width=True)

            df_clean["day"] = df_clean["date"].dt.day_name()
            sales_heatmap = df_clean.pivot_table(index="day", columns=df_clean["date"].dt.month, values="price", aggfunc="sum")
            plt.figure(figsize=(10, 6))
            sns.heatmap(sales_heatmap, cmap="Blues", annot=True, fmt=".0f")
            st.pyplot(plt)

            # Download Reports
            if st.button("📥 دانلود Excel"):
                excel_data = generate_excel(df_clean, top_product)
                st.download_button("دانلود", excel_data, "sales_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            st.success("✅ تحلیل انجام شد!")