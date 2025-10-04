import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time
from io import BytesIO
from streamlit_autorefresh import st_autorefresh  # pip install streamlit-autorefresh

# ---------------- Files ----------------
USERS_FILE = "users.csv"
POMO_FILE = "pomo_data.csv"

# ---------------- Ensure users file exists ----------------
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["username","password"]).to_csv(USERS_FILE,index=False)

# Load users safely
users = pd.read_csv(USERS_FILE)
users.columns = users.columns.str.strip()

# ---------------- Sidebar: Login/Register ----------------
st.sidebar.subheader("👤 Login / Register")
option = st.sidebar.radio("Choose option", ["Login", "Register"])
username_input = st.sidebar.text_input("Username")
password_input = st.sidebar.text_input("Password", type="password")

if option=="Register":
    if st.sidebar.button("Register"):
        if username_input.strip()=="" or password_input.strip()=="":
            st.sidebar.warning("Fill both fields")
            st.stop()
        if username_input in users["username"].values:
            st.sidebar.error("Username already exists")
            st.stop()
        users = pd.concat([users, pd.DataFrame([{"username":username_input,"password":password_input}])],ignore_index=True)
        users.to_csv(USERS_FILE,index=False)
        st.sidebar.success("Registered! You can now login.")
        st.stop()
else:  # Login
    if st.sidebar.button("Login"):
        if username_input not in users["username"].values:
            st.sidebar.error("Username not found. Register first.")
            st.stop()
        correct_pass = users.loc[users["username"]==username_input,"password"].values[0]
        if password_input != correct_pass:
            st.sidebar.error("Incorrect password")
            st.stop()
        st.session_state.username=username_input
        st.sidebar.success("Login successful!")

# Stop app until login/register completed
if "username" not in st.session_state:
    st.stop()

username = st.session_state.username
st.title(f"📌 TaskUni — Welcome, {username}!")

today_date = datetime.now().strftime("%d-%m-%Y")

# ---------------- Reset session state if username changed ----------------
if "last_username" not in st.session_state or st.session_state.last_username != username:
    st.session_state.tasks = pd.DataFrame(columns=["Task", "Status", "Date"])
    st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_HMS", "Focused_HMS", "Date"])
    st.session_state.last_username = username
    st.session_state.countdown_running = False

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
tab1, tab2, tab3 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer", "🍅 Pomodoro & Group Study"])

# ---------------- Task Tracker Tab ----------------
with tab1:
    st.subheader("Add a Task")
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
            if s=="Done":
                return 'background-color:#00C853;color:white'
            elif s=="Not Done":
                return 'background-color:#D50000;color:white'
            else:
                return 'background-color:#FFA500;color:white'

        df_display = tasks_today[["Task","Status"]].copy()
        df_display.index += 1
        st.dataframe(df_display.style.applymap(highlight_status,subset=["Status"]),use_container_width=True)

        st.markdown("### Update Tasks")
        for i,row in tasks_today.iterrows():
            cols = st.columns([3,1,1,1])
            cols[0].write(f"{row['Task']}:")
            if cols[1].button("Done", key=f"done_{i}"):
                st.session_state.tasks.at[i,"Status"]="Done"
                st.session_state.tasks.to_csv(TASKS_FILE,index=False)
            if cols[2].button("Not Done", key=f"notdone_{i}"):
                st.session_state.tasks.at[i,"Status"]="Not Done"
                st.session_state.tasks.to_csv(TASKS_FILE,index=False)
            if cols[3].button("Delete", key=f"delete_{i}"):
                st.session_state.tasks = st.session_state.tasks.drop(i).reset_index(drop=True)
                st.session_state.tasks.to_csv(TASKS_FILE,index=False)
