import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time
from io import BytesIO

# ---------------- Username input ----------------
st.sidebar.subheader("👤 Enter your username")
username = st.sidebar.text_input("Username", key="username_input")

if not username:
    st.warning("Please enter a username to start using the app.")
    st.stop()  # stop execution until username is provided

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

st.set_page_config(page_title="TaskUni Premium", layout="wide")
st.title("📌 TaskUni — Your personal Task tracker")

# ---------------- Today date ----------------
today_date = datetime.now().strftime("%d-%m-%Y")

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer"])

# ---------------- Button functions ----------------
def mark_done(idx):
    st.session_state.tasks.at[idx, "Status"] = "Done"
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)
    st.experimental_rerun()

def mark_notdone(idx):
    st.session_state.tasks.at[idx, "Status"] = "Not Done"
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)
    st.experimental_rerun()

def delete_task(idx):
    st.session_state.tasks = st.session_state.tasks.drop(idx).reset_index(drop=True)
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)
    st.experimental_rerun()

# ---------------- Task Tracker ----------------
with tab1:
    # Add new task
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input.strip():
        new_task = {
            "Task": task_name_input.strip(),
            "Status": "Pending",
            "Date": today_date
        }
        st.session_state.tasks = pd.concat([st.session_state.tasks, pd.DataFrame([new_task])], ignore_index=True)
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)
        st.experimental_rerun()

    # Tasks for today
    st.subheader(f"Tasks on {today_date}")
    tasks_today = st.session_state.tasks[st.session_state.tasks['Date'] == today_date]

    if tasks_today.empty:
        st.write("No tasks recorded for today.")
    else:
        # Colored table
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

        # Buttons below table
        st.markdown("### Update Tasks")
        for i, row in tasks_today.iterrows():
            cols = st.columns([3,1,1,1])
            cols[0].write(f"{row['Task']}:")
            cols[1].button("Done", key=f"done_{i}", on_click=mark_done, args=(i,))
            cols[2].button("Not Done", key=f"notdone_{i}", on_click=mark_notdone, args=(i,))
            cols[3].button("Delete", key=f"delete_{i}", on_click=delete_task, args=(i,))

# ---------------- Countdown Timer ----------------
with tab2:
    st.write("Set countdown time")
    col_h, col_m, col_s = st.columns(3)
    with col_h:
        init_hours = st.number_input("Hours", min_value=0, max_value=23, value=0, step=1, key="input_hours")
    with col_m:
        init_minutes = st.number_input("Minutes", min_value=0, max_value=59, value=0, step=1, key="input_minutes")
    with col_s:
        init_seconds = st.number_input("Seconds", min_value=0, max_value=59, value=0, step=1, key="input_seconds")

    task_for_timer = st.text_input("Task name for this countdown (optional)", key="countdown_task")
    start_col, stop_col = st.columns([1,1])
    start_btn = start_col.button("Start Countdown")
    stop_btn = stop_col.button("Stop Countdown")
    display_box = st.empty()

    # Start countdown
    if start_btn:
        total_seconds = init_hours*3600 + init_minutes*60 + init_seconds
        if total_seconds <= 0:
            st.warning("Set a time greater than 0.")
        else:
            st.session_state.countdown_running = True
            st.session_state.countdown_seconds = total_seconds
            st.session_state.current_countdown_task = task_for_timer if task_for_timer else "Unnamed"
            st.success(f"Countdown started for {st.session_state.current_countdown_task}")

    # Stop countdown
    if stop_btn and st.session_state.countdown_running:
        elapsed_seconds = (init_hours*3600 + init_minutes*60 + init_seconds) - st.session_state.countdown_seconds
        focused_h = elapsed_seconds // 3600
        focused_m = (elapsed_seconds % 3600) // 60
        focused_s = elapsed_seconds % 60
        focused_hms = f"{focused_h}h {focused_m}m {focused_s}s"
        st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
            "Task": st.session_state.get("current_countdown_task","Unnamed"),
            "Target_HMS": f"{init_hours}h {init_minutes}m {init_seconds}s",
            "Focused_HMS": focused_hms
        }])], ignore_index=True)
        st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
        st.session_state.countdown_running = False
        st.success(f"Countdown stopped. Focused: {focused_hms}")

    # Countdown display (non-blocking)
    if st.session_state.countdown_running:
        h = st.session_state.countdown_seconds // 3600
        m = (st.session_state.countdown_seconds % 3600) // 60
        s = st.session_state.countdown_seconds % 60
        display_box.markdown(f"### ⏱️ {h:02d}:{m:02d}:{s:02d}  \n**Task:** {st.session_state.current_countdown_task}")
        # Decrease seconds on next rerun
        st.session_state.countdown_seconds -= 1
        if st.session_state.countdown_seconds <= 0:
            focused_hms = f"{init_hours}h {init_minutes}m {init_seconds}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.get("current_countdown_task", "Unnamed"),
                "Target_HMS": focused_hms,
                "Focused_HMS": focused_hms
            }])], ignore_index=True)
            st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
            st.session_state.countdown_running = False
            display_box.success("🎯 Countdown Finished!")
        st.experimental_rerun()

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
        pdf_bytes = BytesIO()
        pdf.output(pdf_bytes)
        pdf_bytes.seek(0)
        return pdf_bytes

    if st.sidebar.button("💾 Download Timer PDF"):
        pdf_bytes = generate_timer_pdf(st.session_state.timer_data)
        st.sidebar.download_button("⬇️ Download Timer PDF", pdf_bytes, file_name="timer_report.pdf", mime="application/pdf")

# ---------------- Sidebar: Clear Timer Data ----------------
if st.sidebar.button("🧹 Clear Timer Data"):
    st.session_state.timer_data = pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS"])
    if os.path.exists(TIMER_FILE):
        os.remove(TIMER_FILE)
    st.success("Timer data cleared!")
