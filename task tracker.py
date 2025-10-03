import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time

st.set_page_config(page_title="TaskUni Stable", layout="wide")
st.title("📌 TaskUni — Your personal Task tracker")

# ---------------- Files for persistent storage ----------------
TASKS_FILE = "tasks_data.csv"
TIMER_FILE = "timer_data.csv"

# ---------------- Fresh start: ignore old tasks ----------------
if not os.path.exists(TASKS_FILE):
    pd.DataFrame(columns=["Task","Status","Date"]).to_csv(TASKS_FILE, index=False)
if not os.path.exists(TIMER_FILE):
    pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS","Date"]).to_csv(TIMER_FILE, index=False)

# ---------------- Initialize session state ----------------
if "tasks" not in st.session_state:
    st.session_state.tasks = pd.read_csv(TASKS_FILE)
if "timer_data" not in st.session_state:
    st.session_state.timer_data = pd.read_csv(TIMER_FILE)
if "countdown_running" not in st.session_state:
    st.session_state.countdown_running = False
if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.now().strftime("%d-%m-%Y")

today_date = datetime.now().strftime("%d-%m-%Y")

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer"])

# ---------------- Button functions ----------------
def mark_done(idx):
    st.session_state.tasks.at[idx, "Status"] = "Done"
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)

def mark_notdone(idx):
    st.session_state.tasks.at[idx, "Status"] = "Not Done"
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)

def delete_task(idx):
    st.session_state.tasks = st.session_state.tasks.drop(idx).reset_index(drop=True)
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)

# ---------------- Task Tracker ----------------
with tab1:
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input.strip():
        new_task = {
            "Task": task_name_input.strip(),
            "Status": "Pending",
            "Date": today_date
        }
        st.session_state.tasks = pd.concat([st.session_state.tasks, pd.DataFrame([new_task])], ignore_index=True)
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

# ---------------- Sidebar: Select Date ----------------
st.sidebar.subheader("📅 View Tasks by Date")
all_dates = sorted(st.session_state.tasks['Date'].unique(), reverse=True)
selected_date = st.sidebar.selectbox("Select a date", all_dates if all_dates else [today_date], key="selected_date")

# ---------------- Main panel: Tasks for selected date ----------------
st.subheader(f"Tasks on {selected_date}")
tasks_for_day = st.session_state.tasks[st.session_state.tasks['Date'] == selected_date]

if tasks_for_day.empty:
    st.write("No tasks recorded for this day.")
else:
    # Colored table display
    def highlight_status(s):
        if s == "Done":
            return 'background-color:#00C853;color:white'
        elif s == "Not Done":
            return 'background-color:#D50000;color:white'
        else:
            return 'background-color:#FFA500;color:white'

    df_display = tasks_for_day[["Task","Status"]].copy()
    df_display.index += 1
    st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]), use_container_width=True)

    # Buttons below table
    st.markdown("### Update Tasks")
    for i, row in tasks_for_day.iterrows():
        cols = st.columns([3,1,1,1])
        cols[0].markdown(f"**{row['Task']}**")
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

    if start_btn:
        total_seconds = init_hours*3600 + init_minutes*60 + init_seconds
        if total_seconds <= 0:
            st.warning("Set a time greater than 0.")
        else:
            st.session_state.countdown_running = True
            st.session_state.countdown_h = init_hours
            st.session_state.countdown_m = init_minutes
            st.session_state.countdown_s = init_seconds
            st.session_state.current_countdown_task = task_for_timer if task_for_timer else "Unnamed"
            st.success(f"Countdown started for {st.session_state.current_countdown_task}")

    if stop_btn:
        if st.session_state.countdown_running:
            elapsed_seconds = (init_hours*3600 + init_minutes*60 + init_seconds) - (st.session_state.countdown_h*3600 + st.session_state.countdown_m*60 + st.session_state.countdown_s)
            eh = elapsed_seconds // 3600
            em = (elapsed_seconds % 3600) // 60
            es = elapsed_seconds % 60
            focused_hms = f"{eh}h {em}m {es}s"
            new_entry = pd.DataFrame([{
                "Task": st.session_state.get("current_countdown_task","Unnamed"),
                "Target_HMS": f"{init_hours}h {init_minutes}m {init_seconds}s",
                "Focused_HMS": focused_hms,
                "Date": today_date
            }])
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, new_entry], ignore_index=True)
            st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
            st.session_state.countdown_running = False
            st.success(f"Countdown stopped. Focused logged: {focused_hms}")
        else:
            st.info("No countdown running.")

    if st.session_state.countdown_running:
        h = st.session_state.countdown_h
        m = st.session_state.countdown_m
        s = st.session_state.countdown_s
        while st.session_state.countdown_running and (h>0 or m>0 or s>0):
            display_box.markdown(f"<h1 style='text-align:center'>{h:02d}:{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
            time.sleep(1)
            if s>0:
                s -=1
            else:
                s=59
                if m>0:
                    m-=1
                else:
                    m=59
                    if h>0:
                        h-=1
                    else:
                        m=0
                        s=0
            st.session_state.countdown_h = h
            st.session_state.countdown_m = m
            st.session_state.countdown_s = s

        if st.session_state.countdown_running:
            st.session_state.countdown_running = False
            focused_hms = f"{init_hours}h {init_minutes}m {init_seconds}s"
            new_entry = pd.DataFrame([{
                "Task": st.session_state.get("current_countdown_task", "Unnamed"),
                "Target_HMS": focused_hms,
                "Focused_HMS": focused_hms,
                "Date": today_date
            }])
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, new_entry], ignore_index=True)
            st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
            display_box.success("🎯 Countdown Finished!")

# ---------------- Sidebar ----------------
st.sidebar.subheader("⏳ Focused Sessions Log")

# Total focused today
today_timers = st.session_state.timer_data[st.session_state.timer_data["Date"] == today_date]

def hms_to_seconds(hms_str):
    h, m, s = 0,0,0
    parts = hms_str.split()
    for part in parts:
        if part.endswith('h'):
            h=int(part[:-1])
        elif part.endswith('m'):
            m=int(part[:-1])
        elif part.endswith('s'):
            s=int(part[:-1])
    return h*3600 + m*60 + s

def seconds_to_hms(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}h {m}m {s}s"

total_seconds_today = today_timers["Focused_HMS"].apply(hms_to_seconds).sum()
st.sidebar.markdown(f"**🎯 Total Focused Today: {seconds_to_hms(total_seconds_today)}**")

if not st.session_state.timer_data.empty:
    st.sidebar.dataframe(st.session_state.timer_data, use_container_width=True)
    if st.sidebar.button("🗑️ Clear Timer Data"):
        st.session_state.timer_data = pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS","Date"])
        st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
else:
    st.sidebar.write("No focused sessions logged yet.")

# ---------------- Generate Task PDF in Sidebar ----------------
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Task Report Card", ln=True, align="C")
        self.ln(10)

def generate_task_pdf(tasks_df, filename="task_report.pdf"):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "", 12)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(10, 10, "#", border=1, fill=True)
    pdf.cell(100, 10, "Task", border=1, fill=True)
    pdf.cell(40, 10, "Status", border=1, fill=True)
    pdf.ln()
    for i, row in tasks_df.iterrows():
        pdf.cell(10, 10, str(i+1), border=1)
        pdf.cell(100, 10, row["Task"], border=1)
        if row["Status"] == "Done":
            pdf.set_text_color(0, 200, 0)
        elif row["Status"] == "Not Done":
            pdf.set_text_color(255, 0, 0)
        else:
            pdf.set_text_color(255, 165, 0)
        pdf.cell(40, 10, row["Status"], border=1)
        pdf.set_text_color(0,0,0)
        pdf.ln()
    pdf.output(filename)
    return filename

if st.sidebar.button("💾 Download Task Report"):
    if not st.session_state.tasks.empty:
        pdf_file = generate_task_pdf(st.session_state.tasks)
        with open(pdf_file, "rb") as f:
            st.sidebar.download_button("⬇️ Download Task PDF", f, file_name=pdf_file, mime="application/pdf")
    else:
        st.sidebar.warning("⚠️ No tasks to generate PDF!")
