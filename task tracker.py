import streamlit as st
import pandas as pd
import os
import time
from fpdf import FPDF

# ---------------- Page Config ----------------
st.set_page_config(page_title="TaskUni Stable", layout="wide")
st.title("📌 TaskUni — Your personal Task tracker")

# ---------------- File Paths ----------------
TASKS_FILE = "tasks.csv"
TIMER_FILE = "timer_data.csv"

# ---------------- Load Data ----------------
def load_csv(file, cols):
    if os.path.exists(file):
        return pd.read_csv(file)
    else:
        return pd.DataFrame(columns=cols)

def save_csv(df, file):
    df.to_csv(file, index=False)

# ---------------- Session State Init ----------------
if "tasks" not in st.session_state:
    st.session_state.tasks = load_csv(TASKS_FILE, ["Task", "Status", "Date"])
if "timer_data" not in st.session_state:
    st.session_state.timer_data = load_csv(TIMER_FILE, ["Task", "Focused_HMS"])
if "countdown_running" not in st.session_state:
    st.session_state.countdown_running = False

# ---------------- Add Task ----------------
task_name = st.text_input("Enter your task")
if st.button("Add Task") and task_name:
    today = pd.Timestamp.today().strftime("%d-%m-%Y")
    new_task = pd.DataFrame([[task_name, "Pending", today]], columns=["Task", "Status", "Date"])
    st.session_state.tasks = pd.concat([st.session_state.tasks, new_task], ignore_index=True)
    save_csv(st.session_state.tasks, TASKS_FILE)

# ---------------- Show Tasks ----------------
st.subheader("📝 Your Tasks")
if not st.session_state.tasks.empty:
    for i, row in st.session_state.tasks.iterrows():
        cols = st.columns([6, 2, 2, 2])
        cols[0].write(row["Task"])

        if cols[1].button("✅ Done", key=f"done_{i}"):
            st.session_state.tasks.at[i, "Status"] = "Done"
            save_csv(st.session_state.tasks, TASKS_FILE)
            st.rerun()
        if cols[2].button("❌ Not Done", key=f"notdone_{i}"):
            st.session_state.tasks.at[i, "Status"] = "Not Done"
            save_csv(st.session_state.tasks, TASKS_FILE)
            st.rerun()
        if cols[3].button("🗑️ Delete", key=f"delete_{i}"):
            st.session_state.tasks = st.session_state.tasks.drop(i).reset_index(drop=True)
            save_csv(st.session_state.tasks, TASKS_FILE)
            st.rerun()

    # color-coded table
    def color_status(val):
        if val == "Done":
            return "background-color: lightgreen"
        elif val == "Not Done":
            return "background-color: salmon"
        else:
            return "background-color: lightyellow"

    st.dataframe(st.session_state.tasks.style.applymap(color_status, subset=["Status"]), use_container_width=True)
else:
    st.info("No tasks yet. Add one above!")

# ---------------- Sidebar: Date Filter ----------------
st.sidebar.subheader("📅 Tasks by Date")
if not st.session_state.tasks.empty:
    dates = st.session_state.tasks["Date"].unique()
    selected_date = st.sidebar.selectbox("Select date", dates)
    filtered = st.session_state.tasks[st.session_state.tasks["Date"] == selected_date]
    st.sidebar.write(filtered[["Task", "Status"]])
else:
    st.sidebar.info("No tasks to show yet!")

# ---------------- Timer ----------------
st.subheader("⏳ Focus Timer")
task_for_timer = st.text_input("Task for timer")
init_hours = st.number_input("Hours", 0, 23, 0)
init_minutes = st.number_input("Minutes", 0, 59, 25)
init_seconds = st.number_input("Seconds", 0, 59, 0)

if st.button("▶ Start Timer") and not st.session_state.countdown_running and task_for_timer:
    st.session_state.countdown_running = True
    total_seconds = init_hours * 3600 + init_minutes * 60 + init_seconds
    start_time = time.time()
    end_time = start_time + total_seconds

    while time.time() < end_time and st.session_state.countdown_running:
        remaining = int(end_time - time.time())
        hrs, rem = divmod(remaining, 3600)
        mins, secs = divmod(rem, 60)
        st.empty().write(f"{hrs:02}:{mins:02}:{secs:02}")
        time.sleep(1)

    if st.session_state.countdown_running:
        st.success(f"Time’s up for task: {task_for_timer}")
        focused_hms = f"{init_hours}h {init_minutes}m {init_seconds}s"
        new_entry = pd.DataFrame([[task_for_timer, focused_hms]], columns=["Task", "Focused_HMS"])
        st.session_state.timer_data = pd.concat([st.session_state.timer_data, new_entry], ignore_index=True)
        save_csv(st.session_state.timer_data, TIMER_FILE)

if st.button("⏹ Stop Timer") and st.session_state.countdown_running:
    st.session_state.countdown_running = False
    focused_hms = f"{init_hours}h {init_minutes}m {init_seconds}s"
    new_entry = pd.DataFrame([[task_for_timer, focused_hms]], columns=["Task", "Focused_HMS"])
    st.session_state.timer_data = pd.concat([st.session_state.timer_data, new_entry], ignore_index=True)
    save_csv(st.session_state.timer_data, TIMER_FILE)

# ---------------- Timer Logs ----------------
st.sidebar.subheader("⏳ Focused Sessions Log")
if not st.session_state.timer_data.empty:
    st.sidebar.table(st.session_state.timer_data)
else:
    st.sidebar.info("No focused sessions yet!")
