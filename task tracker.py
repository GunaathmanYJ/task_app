import streamlit as st
import pandas as pd
import os
from datetime import datetime
import time

st.set_page_config(page_title="TaskUni Premium", layout="wide")

TASKS_FILE = "tasks.csv"
TIMER_FILE = "timer_data.csv"

# ---------------- Load or Initialize ----------------
def load_data():
    if os.path.exists(TASKS_FILE):
        return pd.read_csv(TASKS_FILE)
    else:
        return pd.DataFrame(columns=["Task", "Status", "Date"])

def save_data():
    st.session_state.tasks.to_csv(TASKS_FILE, index=False)

def load_timer():
    if os.path.exists(TIMER_FILE):
        return pd.read_csv(TIMER_FILE)
    else:
        return pd.DataFrame(columns=["Date", "Duration", "Focused_HMS"])

def save_timer():
    st.session_state.timer_data.to_csv(TIMER_FILE, index=False)

if "tasks" not in st.session_state:
    st.session_state.tasks = load_data()

if "timer_data" not in st.session_state:
    st.session_state.timer_data = load_timer()

# ---------------- Sidebar Date Filter ----------------
st.sidebar.header("📅 Date-wise Tasks")
all_dates = st.session_state.tasks["Date"].unique() if not st.session_state.tasks.empty else []
selected_date = st.sidebar.selectbox("Select Date", options=all_dates)

if selected_date:
    st.sidebar.write("Tasks on", selected_date)
    filtered = st.session_state.tasks[st.session_state.tasks["Date"] == selected_date]
    st.sidebar.table(filtered[["Task", "Status"]])

# ---------------- Main Tabs ----------------
tab1, tab2 = st.tabs(["📋 Tasks", "⏳ Timer"])

# ---------------- Tab 1: Tasks ----------------
with tab1:
    st.title("📋 Task Manager")

    task_name = st.text_input("Enter your task")
    if st.button("Add Task") and task_name.strip() != "":
        new_task = {"Task": task_name, "Status": "Pending", "Date": datetime.today().strftime("%d-%m-%Y")}
        st.session_state.tasks = pd.concat([st.session_state.tasks, pd.DataFrame([new_task])], ignore_index=True)
        save_data()

    if not st.session_state.tasks.empty:
        st.subheader("Your Tasks")

        # Colored table
        def color_status(val):
            if val == "Done":
                return "background-color: lightgreen; color: black"
            elif val == "Not Done":
                return "background-color: lightcoral; color: white"
            elif val == "Pending":
                return "background-color: #FFA500; color: black"  # yellow-orange
            return ""
        
        st.dataframe(st.session_state.tasks.style.applymap(color_status, subset=["Status"]))

        # Status Dropdowns
        for i, row in st.session_state.tasks.iterrows():
            col1, col2 = st.columns([3, 2])
            with col1:
                st.write(f"**{row['Task']}**")
            with col2:
                # unique key ensures widget refreshes instantly
                key = f"status_{i}_{row['Status']}"
                status = st.selectbox(
                    "Status",
                    ["Pending", "Done", "Not Done", "Delete"],
                    index=["Pending", "Done", "Not Done"].index(row["Status"]) if row["Status"] in ["Pending", "Done", "Not Done"] else 0,
                    key=key
                )
                if status != row["Status"]:
                    if status == "Delete":
                        st.session_state.tasks = st.session_state.tasks.drop(i).reset_index(drop=True)
                    else:
                        st.session_state.tasks.at[i, "Status"] = status
                    save_data()

# ---------------- Tab 2: Timer ----------------
with tab2:
    st.title("⏳ Focused Timer")

    init_hours = st.number_input("Hours", min_value=0, max_value=5, value=0)
    init_minutes = st.number_input("Minutes", min_value=0, max_value=59, value=25)
    init_seconds = st.number_input("Seconds", min_value=0, max_value=59, value=0)

    if "countdown_running" not in st.session_state:
        st.session_state.countdown_running = False

    if st.button("Start Timer"):
        st.session_state.countdown_running = True
        total_seconds = init_hours * 3600 + init_minutes * 60 + init_seconds
        start_time = time.time()

        ph = st.empty()
        while st.session_state.countdown_running and total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            hours, mins = divmod(mins, 60)
            ph.metric("Time Left", f"{hours:02d}:{mins:02d}:{secs:02d}")
            time.sleep(1)
            total_seconds -= 1

        # Stop timer and calculate focused duration
        st.session_state.countdown_running = False
        end_time = time.time()
        focused_seconds = int(end_time - start_time)
        h, m, s = focused_seconds // 3600, (focused_seconds % 3600) // 60, focused_seconds % 60
        focused_hms = f"{h}h {m}m {s}s"

        st.success(f"✅ Focused for {focused_hms}")

        today = datetime.today().strftime("%d-%m-%Y")
        new_entry = {"Date": today, "Duration": f"{init_hours}h {init_minutes}m {init_seconds}s", "Focused_HMS": focused_hms}
        st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([new_entry])], ignore_index=True)
        save_timer()

    st.subheader("📊 Focused Sessions Log")
    if not st.session_state.timer_data.empty:
        st.table(st.session_state.timer_data)
