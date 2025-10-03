import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time

# ---------------- Page config ----------------
st.set_page_config(page_title="TaskUni Stable", layout="wide")
st.title("📌 TaskUni — Your personal Task tracker")

# ---------------- File paths ----------------
TASKS_FILE = "tasks.csv"
TIMER_FILE = "timer_data.csv"

# ---------------- Helpers: load/save ----------------
def load_csv(file, cols):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
            return df[cols]
        except Exception:
            return pd.DataFrame(columns=cols)
    else:
        return pd.DataFrame(columns=cols)

def save_csv(df, file):
    df.to_csv(file, index=False)

# ---------------- Session state init ----------------
if "tasks" not in st.session_state:
    st.session_state.tasks = load_csv(TASKS_FILE, ["Task", "Status", "Date"])

if "timer_data" not in st.session_state:
    st.session_state.timer_data = load_csv(TIMER_FILE, ["Task", "Target_HMS", "Focused_HMS"])

if "countdown_running" not in st.session_state:
    st.session_state.countdown_running = False
if "current_timer" not in st.session_state:
    st.session_state.current_timer = None

# ---------------- Utility: formatted time ----------------
def fmt_hms_from_seconds(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h}h {m}m {s}s"

def fmt_hms_display(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer"])

# ---------------- Task Tracker tab ----------------
with tab1:
    st.subheader("Add a Task")
    task_input = st.text_input("Enter your task", key="task_input")
    if st.button("Add Task"):
        if task_input and task_input.strip():
            today = datetime.now().strftime("%d-%m-%Y")
            new_row = pd.DataFrame([[task_input.strip(), "Pending", today]], columns=["Task", "Status", "Date"])
            st.session_state.tasks = pd.concat([st.session_state.tasks, new_row], ignore_index=True)
            save_csv(st.session_state.tasks, TASKS_FILE)
            st.session_state.task_input = ""
            st.rerun()  # 🔥 instant update after add
        else:
            st.warning("Type a task first.")

    st.write("---")

    # Sidebar date filter
    st.sidebar.subheader("📅 View Tasks by Date")
    all_dates = sorted(st.session_state.tasks["Date"].unique(), reverse=True) if not st.session_state.tasks.empty else []
    today_default = datetime.now().strftime("%d-%m-%Y")
    if not all_dates:
        all_dates = [today_default]
    selected_date = st.sidebar.selectbox("Select date", all_dates, index=0, key="selected_date_sidebar")

    st.subheader(f"Tasks on {selected_date}")

    tasks_for_day = st.session_state.tasks[st.session_state.tasks["Date"] == selected_date]

    if tasks_for_day.empty:
        st.info("No tasks recorded for this day.")
    else:
        def color_status(val):
            if val == "Done":
                return "background-color: #00C853; color: white"
            elif val == "Not Done":
                return "background-color: #D50000; color: white"
            else:  # Pending
                return "background-color: #2196F3; color: white"

        df_display = tasks_for_day[["Task", "Status", "Date"]].copy()
        df_display.index = range(1, len(df_display) + 1)
        st.dataframe(df_display.style.applymap(color_status, subset=["Status"]), use_container_width=True)

        st.markdown("### Update tasks for this day")
        for i, row in tasks_for_day.iterrows():
            cols = st.columns([6, 1, 1, 1])
            cols[0].write(row["Task"])
            if cols[1].button("✅ Done", key=f"done_{i}"):
                st.session_state.tasks.at[i, "Status"] = "Done"
                save_csv(st.session_state.tasks, TASKS_FILE)
                st.rerun()  # 🔥 fix double-click
            if cols[2].button("❌ Not Done", key=f"notdone_{i}"):
                st.session_state.tasks.at[i, "Status"] = "Not Done"
                save_csv(st.session_state.tasks, TASKS_FILE)
                st.rerun()
            if cols[3].button("🗑️ Delete", key=f"delete_{i}"):
                st.session_state.tasks = st.session_state.tasks.drop(i).reset_index(drop=True)
                save_csv(st.session_state.tasks, TASKS_FILE)
                st.rerun()

# ---------------- Countdown Timer tab ----------------
with tab2:
    st.subheader("Countdown Timer (separate tab)")
    timer_task = st.text_input("Task name for timer", key="timer_task")
    col1, col2, col3 = st.columns(3)
    with col1:
        hours = st.number_input("Hours", min_value=0, max_value=23, value=0, key="timer_hours")
    with col2:
        minutes = st.number_input("Minutes", min_value=0, max_value=59, value=25, key="timer_minutes")
    with col3:
        seconds = st.number_input("Seconds", min_value=0, max_value=59, value=0, key="timer_seconds")

    start_btn = st.button("Start Countdown")
    stop_btn = st.button("Stop Countdown")

    timer_placeholder = st.empty()

    if start_btn and not st.session_state.countdown_running:
        total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        if total_seconds <= 0:
            st.warning("Set a time greater than 0.")
        elif not timer_task or timer_task.strip() == "":
            st.warning("Enter a task name for the timer.")
        else:
            st.session_state.countdown_running = True
            st.session_state.current_timer = {
                "Task": timer_task,
                "Target_HMS": fmt_hms_from_seconds(total_seconds),
                "Focused_HMS": "Running..."
            }
            # Log immediately 🔥
            st.session_state.timer_data = pd.concat(
                [st.session_state.timer_data, pd.DataFrame([st.session_state.current_timer])],
                ignore_index=True
            )
            save_csv(st.session_state.timer_data, TIMER_FILE)

            remaining = total_seconds
            while st.session_state.countdown_running and remaining >= 0:
                display = fmt_hms_display(remaining)
                timer_placeholder.markdown(f"### ⏱️ {display}  \n**Task:** {timer_task}")
                time.sleep(1)
                remaining -= 1

            if st.session_state.countdown_running:  # finished naturally
                st.success("🎯 Countdown Finished!")
                st.session_state.timer_data.at[len(st.session_state.timer_data) - 1, "Focused_HMS"] = fmt_hms_from_seconds(total_seconds)
                save_csv(st.session_state.timer_data, TIMER_FILE)
                st.session_state.countdown_running = False
                st.session_state.current_timer = None

    if stop_btn and st.session_state.countdown_running:
        st.session_state.countdown_running = False
        st.info("⏸️ Countdown stopped.")
        # Update log with time actually focused
        st.session_state.timer_data.at[len(st.session_state.timer_data) - 1, "Focused_HMS"] = "Stopped early"
        save_csv(st.session_state.timer_data, TIMER_FILE)
        st.session_state.current_timer = None

# ---------------- Timer logs ----------------
st.sidebar.subheader("⏳ Focused Sessions Log")
if not st.session_state.timer_data.empty:
    st.sidebar.table(st.session_state.timer_data)
else:
    st.sidebar.info("No focused sessions yet!")
