import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time
from io import BytesIO
from streamlit_autorefresh import st_autorefresh  # pip install streamlit-autorefresh

# ---------------- Logo ----------------
st.image("taskuni.png", width=200)  # Smaller, crisp logo at top

# ---------------- Username input in main area ----------------
st.subheader("👤 Enter your username to start")
username = st.text_input("Username", key="username_input")
if not username:
    st.warning("Please enter a username to start using the app.")
    st.stop()

# ---------------- Reset session state if username changed ----------------
if "last_username" not in st.session_state or st.session_state.last_username != username:
    st.session_state.tasks = pd.DataFrame(columns=["Task", "Status", "Date"])
    st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_HMS", "Focused_HMS"])
    st.session_state.countdown_running = False
    st.session_state.last_username = username

# ---------------- Files for persistent storage per user ----------------
TASKS_FILE = f"tasks_{username}.csv"
TIMER_FILE = f"timer_{username}.csv"

# ---------------- Load persistent data ----------------
if os.path.exists(TASKS_FILE):
    st.session_state.tasks = pd.read_csv(TASKS_FILE)
if os.path.exists(TIMER_FILE):
    st.session_state.timer_data = pd.read_csv(TIMER_FILE)

# ---------------- Page config ----------------
st.set_page_config(page_title="TaskUni Premium", layout="wide")
st.title("📌 TaskUni — Your personal Task tracker")
today_date = datetime.now().strftime("%d-%m-%Y")
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer"])

# ---------------- Task Tracker Functions ----------------
def mark_done(idx):
    st.session_state.tasks.at[idx, "Status"] = "Done"
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)

def mark_notdone(idx):
    st.session_state.tasks.at[idx, "Status"] = "Not Done"
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)

def delete_task(idx):
    st.session_state.tasks = st.session_state.tasks.drop(idx).reset_index(drop=True)
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)

# ---------------- Task Tracker Tab ----------------
with tab1:
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input.strip():
        new_task = {"Task": task_name_input.strip(), "Status": "Pending", "Date": today_date}
        st.session_state.tasks = pd.concat([st.session_state.tasks, pd.DataFrame([new_task])], ignore_index=True)
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

    st.subheader(f"Tasks on {today_date}")
    tasks_today = st.session_state.tasks[st.session_state.tasks['Date'] == today_date]

    if tasks_today.empty:
        st.write("No tasks recorded for today.")
    else:
        def highlight_status(s):
            if s == "Done":
                return 'background-color:#00C853;color:white'
            elif s == "Not Done":
                return 'background-color:#D50000;color:white'
            else:
                return 'background-color:#FFA500;color:white'

        df_display = tasks_today[["Task","Status"]].copy()
        df_display.index += 1
        st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]), use_container_width=True)

        st.markdown("### Update Tasks")
        for i, row in tasks_today.iterrows():
            cols = st.columns([3,1,1,1])
            cols[0].write(f"{row['Task']}:")
            cols[1].button("Done", key=f"done_{i}", on_click=mark_done, args=(i,))
            cols[2].button("Not Done", key=f"notdone_{i}", on_click=mark_notdone, args=(i,))
            cols[3].button("Delete", key=f"delete_{i}", on_click=delete_task, args=(i,))

# ---------------- Countdown Timer Tab ----------------
with tab2:
    st.write("Set countdown time")
    col_h, col_m, col_s = st.columns(3)
    with col_h:
        hours = st.number_input("Hours", 0, 23, 0, key="hours_input")
    with col_m:
        minutes = st.number_input("Minutes", 0, 59, 0, key="minutes_input")
    with col_s:
        seconds = st.number_input("Seconds", 0, 59, 0, key="seconds_input")

    countdown_task_name = st.text_input("Task name (optional)", key="countdown_task_input")
    start_col, stop_col = st.columns([1,1])
    start_btn = start_col.button("Start Countdown")
    stop_btn = stop_col.button("Stop Countdown")
    display_box = st.empty()

    # Start countdown
    if start_btn:
        total_seconds = hours*3600 + minutes*60 + seconds
        if total_seconds <= 0:
            st.warning("Set a time greater than 0.")
        else:
            st.session_state.countdown_running = True
            st.session_state.countdown_total_seconds = total_seconds
            st.session_state.countdown_start_time = time.time()
            st.session_state.countdown_task_name = countdown_task_name if countdown_task_name else "Unnamed"

    # Stop countdown
    if stop_btn and st.session_state.countdown_running:
        elapsed = int(time.time() - st.session_state.countdown_start_time)
        focused = min(elapsed, st.session_state.countdown_total_seconds)
        h = focused // 3600
        m = (focused % 3600) // 60
        s = focused % 60
        st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
            "Task": st.session_state.countdown_task_name,
            "Target_HMS": f"{hours}h {minutes}m {seconds}s",
            "Focused_HMS": f"{h}h {m}m {s}s"
        }])], ignore_index=True)
        st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
        st.session_state.countdown_running = False
        st.success(f"Countdown stopped. Focused: {h}h {m}m {s}s")

    # Display countdown (auto-refresh every second, double size)
    if st.session_state.get("countdown_running", False):
        st_autorefresh(interval=1000, key="timer_refresh")
        elapsed = int(time.time() - st.session_state.countdown_start_time)
        remaining = max(st.session_state.countdown_total_seconds - elapsed, 0)
        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60

        display_box.markdown(
            f"<h1 style='text-align:center;font-size:160px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1>"
            f"<h3 style='text-align:center;font-size:48px;'>Task: {st.session_state.countdown_task_name}</h3>", 
            unsafe_allow_html=True
        )

        if remaining == 0:
            st.session_state.countdown_running = False
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.countdown_task_name,
                "Target_HMS": f"{hours}h {minutes}m {seconds}s",
                "Focused_HMS": f"{hours}h {minutes}m {seconds}s"
            }])], ignore_index=True)
            st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
            display_box.success("🎯 Countdown Finished!")

    # ---------------- Total Focused Time ----------------
    if not st.session_state.timer_data.empty:
        total_seconds = 0
        for t in st.session_state.timer_data['Focused_HMS']:
            parts = t.split()
            h = int(parts[0].replace('h',''))
            m = int(parts[1].replace('m',''))
            s = int(parts[2].replace('s',''))
            total_seconds += h*3600 + m*60 + s

        total_h = total_seconds // 3600
        total_m = (total_seconds % 3600) // 60
        total_s = total_seconds % 60

        st.markdown(f"### 🎯 Total Focused Time: {total_h}h {total_m}m {total_s}s")

# ---------------- Sidebar: Timer log & PDF ----------------
st.sidebar.subheader("⏳ Focused Sessions Log")
if not st.session_state.timer_data.empty:
    st.sidebar.dataframe(st.session_state.timer_data, use_container_width=True)

    class TimerPDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 16)
            self.cell(0, 10, "Focused Timer Report", ln=True, align="C")
            self.ln(10)

    def generate_timer_pdf(timer_df):
        pdf = TimerPDF()
        pdf.add_page()
        pdf.set_font("Arial", "", 12)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(10, 10, "#", border=1, fill=True)
        pdf.cell(80, 10, "Task", border=1, fill=True)
        pdf.cell(50, 10, "Target Time", border=1, fill=True)
        pdf.cell(50, 10, "Focused Time", border=1, fill=True)
        pdf.ln()
        for i, row in timer_df.iterrows():
            pdf.cell(10, 10, str(i+1), border=1)
            pdf.cell(80, 10, row["Task"], border=1)
            pdf.cell(50, 10, row["Target_HMS"], border=1)
            pdf.cell(50, 10, row["Focused_HMS"], border=1)
            pdf.ln()
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        return BytesIO(pdf_bytes)

    if st.sidebar.button("💾 Download Timer PDF"):
        pdf_bytes = generate_timer_pdf(st.session_state.timer_data)
        st.sidebar.download_button("⬇️ Download Timer PDF", pdf_bytes, file_name="timer_report.pdf", mime="application/pdf")

# ---------------- Sidebar: Tasks PDF ----------------
st.sidebar.subheader("📝 Tasks Report")
if not st.session_state.tasks.empty:
    class TaskPDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 16)
            self.cell(0, 10, "Tasks Report", ln=True, align="C")
            self.ln(10)

    def generate_task_pdf(tasks_df):
        pdf = TaskPDF()
        pdf.add_page()
        pdf.set_font("Arial", "", 12)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(10, 10, "#", border=1, fill=True)
        pdf.cell(100, 10, "Task", border=1, fill=True)
        pdf.cell(30, 10, "Status", border=1, fill=True)
        pdf.cell(40, 10, "Date", border=1, fill=True)
        pdf.ln()
        for i, row in tasks_df.iterrows():
            pdf.cell(10, 10, str(i+1), border=1)
            pdf.cell(100, 10, row["Task"], border=1)
            pdf.cell(30, 10, row["Status"], border=1)
            pdf.cell(40, 10, row["Date"], border=1)
            pdf.ln()
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        return BytesIO(pdf_bytes)

    if st.sidebar.button("💾 Download Tasks PDF"):
        pdf_bytes = generate_task_pdf(st.session_state.tasks)
        st.sidebar.download_button("⬇️ Download Tasks PDF", pdf_bytes, file_name="tasks_report.pdf", mime="application/pdf")

# ---------------- Sidebar: Clear Timer Data ----------------
if st.sidebar.button("🧹 Clear Timer Data"):
    st.session_state.timer_data = pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS"])
    if os.path.exists(TIMER_FILE):
        os.remove(TIMER_FILE)
    st.success("Timer data cleared!")
