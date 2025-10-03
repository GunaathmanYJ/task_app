import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
import time

st.set_page_config(page_title="TaskUni Stable", layout="wide")
st.title("📌 TaskUni — Your personal Task tracker")

# ---------------- Files for persistent storage ----------------
TASKS_FILE = "tasks_data.csv"
TIMER_FILE = "timer_data.csv"

# ---------------- Load or initialize data ----------------
if os.path.exists(TASKS_FILE):
    st.session_state.tasks = pd.read_csv(TASKS_FILE)
else:
    st.session_state.tasks = pd.DataFrame(columns=["Task", "Status", "Date"])

if os.path.exists(TIMER_FILE):
    st.session_state.timer_data = pd.read_csv(TIMER_FILE)
else:
    st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_HMS", "Focused_HMS"])

if "countdown_running" not in st.session_state:
    st.session_state.countdown_running = False

today_date = datetime.now().strftime("%d-%m-%Y")

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer"])

# ---------------- Functions ----------------
def save_tasks():
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)

def save_timer():
    st.session_state.timer_data.to_csv(TIMER_FILE, index=False)

def mark_done(idx):
    st.session_state.tasks.at[idx, "Status"] = "Done"
    save_tasks()

def mark_notdone(idx):
    st.session_state.tasks.at[idx, "Status"] = "Not Done"
    save_tasks()

def delete_task(idx):
    st.session_state.tasks = st.session_state.tasks.drop(idx).reset_index(drop=True)
    save_tasks()

# ---------------- Task Tracker Tab ----------------
with tab1:
    st.subheader("Add New Task")
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input.strip():
        new_task = {"Task": task_name_input.strip(), "Status": "Pending", "Date": today_date}
        st.session_state.tasks = pd.concat([st.session_state.tasks, pd.DataFrame([new_task])], ignore_index=True)
        save_tasks()

    # Sidebar date selector
    st.sidebar.subheader("📅 View Tasks by Date")
    all_dates = sorted(st.session_state.tasks['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("Select a date", all_dates if all_dates else [today_date])

    # Tasks for selected date
    st.subheader(f"Tasks on {selected_date}")
    tasks_for_day = st.session_state.tasks[st.session_state.tasks['Date'] == selected_date]

    if tasks_for_day.empty:
        st.write("No tasks recorded for this day.")
    else:
        # Colored table
        def highlight_status(s):
            if s == "Done":
                return 'background-color:#00C853;color:white'
            elif s == "Not Done":
                return 'background-color:#D50000;color:white'
            else:
                return 'background-color:#FFA500;color:white'

        df_display = tasks_for_day[["Task", "Status", "Date"]].copy()
        df_display.index += 1
        st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]), use_container_width=True)

        # Buttons
        st.markdown("### Update Tasks")
        for i, row in tasks_for_day.iterrows():
            col1, col2, col3 = st.columns([1,1,1])
            col1.button("✅ Done", key=f"done_{i}", on_click=mark_done, args=(i,))
            col2.button("❌ Not Done", key=f"notdone_{i}", on_click=mark_notdone, args=(i,))
            col3.button("🗑️ Delete", key=f"delete_{i}", on_click=delete_task, args=(i,))

# ---------------- Countdown Timer Tab ----------------
with tab2:
    st.subheader("Set Countdown Timer")
    col_h, col_m, col_s = st.columns(3)
    with col_h:
        init_hours = st.number_input("Hours", min_value=0, max_value=23, value=0, step=1, key="input_hours")
    with col_m:
        init_minutes = st.number_input("Minutes", min_value=0, max_value=59, value=25, step=1, key="input_minutes")
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
            st.session_state.countdown_h = init_hours
            st.session_state.countdown_m = init_minutes
            st.session_state.countdown_s = init_seconds
            st.session_state.current_countdown_task = task_for_timer if task_for_timer else "Unnamed"
            st.success(f"Countdown started for {st.session_state.current_countdown_task}")

    # Stop countdown
    if stop_btn:
        if st.session_state.countdown_running:
            elapsed_seconds = (init_hours*3600 + init_minutes*60 + init_seconds) - (st.session_state.countdown_h*3600 + st.session_state.countdown_m*60 + st.session_state.countdown_s)
            eh = elapsed_seconds // 3600
            em = (elapsed_seconds % 3600) // 60
            es = elapsed_seconds % 60
            focused_hms = f"{eh}h {em}m {es}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.get("current_countdown_task","Unnamed"),
                "Target_HMS": f"{init_hours}h {init_minutes}m {init_seconds}s",
                "Focused_HMS": focused_hms
            }])], ignore_index=True)
            save_timer()
            st.session_state.countdown_running = False
            st.success(f"Countdown stopped. Focused logged: {focused_hms}")
        else:
            st.info("No countdown running.")

    # Real-time countdown display
    if st.session_state.countdown_running:
        h = st.session_state.countdown_h
        m = st.session_state.countdown_m
        s = st.session_state.countdown_s
        while st.session_state.countdown_running and (h>0 or m>0 or s>0):
            display_box.markdown(f"### ⏱️ {h:02d}:{m:02d}:{s:02d}  \n**Task:** {st.session_state.current_countdown_task}")
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

        # Countdown finished naturally
        if st.session_state.countdown_running:
            st.session_state.countdown_running = False
            focused_hms = f"{init_hours}h {init_minutes}m {init_seconds}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.get("current_countdown_task","Unnamed"),
                "Target_HMS": focused_hms,
                "Focused_HMS": focused_hms
            }])], ignore_index=True)
            save_timer()
            display_box.success("🎯 Countdown Finished!")

# ---------------- Timer Report in Sidebar ----------------
st.sidebar.subheader("⏳ Focused Sessions Log")
if not st.session_state.timer_data.empty:
    st.sidebar.dataframe(st.session_state.timer_data, use_container_width=True)
else:
    st.sidebar.write("No focused sessions logged yet.")
