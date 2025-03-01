import streamlit as st
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
import sqlite3
from datetime import datetime


# دیتابیس SQLite
def init_db():
    try:
        conn = sqlite3.connect("saleasy_db.sqlite")
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (username TEXT PRIMARY KEY, password TEXT, 
                      analysis_type TEXT, report_schedule TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS reports 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, 
                      report_time TEXT, report_file TEXT,
                      FOREIGN KEY (username) REFERENCES users(username))''')
        conn.commit()
        conn.close()
        st.write("دیتابیس با موفقیت راه‌اندازی شد!")
    except Exception as e:
        st.error(f"خطا توی راه‌اندازی دیتابیس: {str(e)}")


def save_user_choice(username, analysis_type, report_schedule=None):
    try:
        conn = sqlite3.connect("saleasy_db.sqlite")
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO users (username, password, analysis_type, report_schedule) VALUES (?, ?, ?, ?)",
            (username, st.session_state.get("password", ""), analysis_type, report_schedule))
        conn.commit()
        conn.close()
        st.write(f"کاربر {username} با موفقیت توی دیتابیس ذخیره شد!")
    except Exception as e:
        st.error(f"خطا توی ذخیره انتخاب: {str(e)}")


def get_user_choice(username):
    try:
        conn = sqlite3.connect("saleasy_db.sqlite")
        c = conn.cursor()
        c.execute("SELECT analysis_type, report_schedule FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        conn.close()
        return (result[0] if result else "جمع فروش هر محصول", result[1] if result else "هفتگی")
    except Exception as e:
        st.error(f"خطا توی گرفتن انتخاب: {str(e)}")
        return ("جمع فروش هر محصول", "هفتگی")


def save_report(username, report_file):
    try:
        conn = sqlite3.connect("saleasy_db.sqlite")
        c = conn.cursor()
        report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO reports (username, report_time, report_file) VALUES (?, ?, ?)",
                  (username, report_time, report_file))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"خطا توی ذخیره گزارش: {str(e)}")


# شروع دیتابیس
init_db()

# عنوان
st.markdown("<h1 style='text-align: center; color: blue;'>Saleasy - تحلیل‌گر فروش ساده</h1>", unsafe_allow_html=True)

# ورود
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.subheader("ورود به سیستم")
    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")
    if st.button("ورود"):
        try:
            conn = sqlite3.connect("saleasy_db.sqlite")
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username = ?", (username,))
            result = c.fetchone()

            if result and result[0] == password:  # کاربر قدیمی
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success(f"خوش آمدی، {username}!")
            elif not result:  # کاربر جدید
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["password"] = password
                save_user_choice(username, "جمع فروش هر محصول", "هفتگی")
                st.success(f"خوش آمدی، {username}! حسابت ساخته شد.")
            else:
                st.error("رمز اشتباهه!")
            conn.close()
        except Exception as e:
            st.error(f"خطا توی ورود: {str(e)}")
else:
    # صفحه اصلی
    username = st.session_state["username"]
    st.write(f"سلام، {username}! داده‌های فروش رو وارد کن و تحلیل ببین!")

    file = st.file_uploader("انتخاب فایل CSV", type="csv")

    if file:
        try:
            df = pd.read_csv(file)

            st.subheader("تحلیل‌ها رو انتخاب کن:")
            show_total = st.checkbox("جمع فروش هر محصول", value=True)
            show_top = st.checkbox("محصول پرطرفدار")
            show_trend = st.checkbox("روند فروش روزانه")

            default_analysis, default_schedule = get_user_choice(username)
            analysis_type = st.selectbox("تحلیل پیش‌فرض", [
                "جمع فروش هر محصول", "محصول پرطرفدار", "روند فروش روزانه"
            ], index=["جمع فروش هر محصول", "محصول پرطرفدار", "روند فروش روزانه"].index(default_analysis))

            report_schedule = st.selectbox("گزارش خودکار کی بفرستیم؟", ["هفتگی", "روزانه", "ماهانه"],
                                           index=["هفتگی", "روزانه", "ماهانه"].index(default_schedule))

            if st.button("ذخیره انتخاب‌ها"):
                save_user_choice(username, analysis_type, report_schedule)
                st.success("انتخاب‌ها ذخیره شد!")

            if show_total:
                result = duckdb.query("SELECT product, SUM(price) as total FROM df GROUP BY product").df()
                st.write("جمع فروش:")
                st.bar_chart(result.set_index("product"))
                st.dataframe(result)

            if show_top:
                result = duckdb.query(
                    "SELECT product, SUM(price) as total FROM df GROUP BY product ORDER BY total DESC LIMIT 1").df()
                st.write(f"محصول پرطرفدار: {result['product'][0]} با فروش {result['total'][0]}")

            if show_trend:
                result = duckdb.query("SELECT date, SUM(price) as daily_total FROM df GROUP BY date").df()
                st.write("روند روزانه:")
                st.line_chart(result.set_index("date"))

            if st.button("ذخیره گزارش برای ارسال خودکار"):
                plt.figure(figsize=(10, 6))
                if show_trend:
                    result.plot(kind="line", x="date", y="daily_total")
                else:
                    result.plot(kind="bar", x="product", y="total")
                plt.savefig(f"report_{username}.png")
                save_report(username, f"report_{username}.png")
                st.success(f"گزارش ذخیره شد و طبق زمان‌بندی {report_schedule} در دسترسه!")

            if st.button("دانلود جدول به CSV"):
                result.to_csv(f"sales_export_{username}.csv", index=False)
                with open(f"sales_export_{username}.csv", "rb") as f:
                    st.download_button("دانلود CSV", f, file_name=f"sales_export_{username}.csv")

            st.success("تحلیل با موفقیت انجام شد!")
        except Exception as e:
            st.error(f"یه مشکلی پیش اومد: {str(e)}—لطفاً داده‌ها رو چک کن!")

    if st.button("خروج"):
        del st.session_state["logged_in"]
        del st.session_state["username"]
        st.rerun()