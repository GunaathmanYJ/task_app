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
# ---------------- Countdown Timer Tab ----------------
with tab2:
    st.subheader("Countdown Timer")
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
        if total_seconds<=0:
            st.warning("Set a time greater than 0.")
        else:
            st.session_state.countdown_running = True
            st.session_state.countdown_total_seconds = total_seconds
            st.session_state.countdown_start_time = time.time()
            st.session_state.countdown_task_name = countdown_task_name if countdown_task_name else "Unnamed"

    # Stop countdown
    if stop_btn and st.session_state.countdown_running:
        elapsed = int(time.time()-st.session_state.countdown_start_time)
        focused = min(elapsed, st.session_state.countdown_total_seconds)
        h = focused//3600
        m = (focused%3600)//60
        s = focused%60
        new_entry = {"Task": st.session_state.countdown_task_name,
                     "Target_HMS": f"{hours}h {minutes}m {seconds}s",
                     "Focused_HMS": f"{h}h {m}m {s}s",
                     "Date": today_date}
        st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([new_entry])],ignore_index=True)
        st.session_state.timer_data.to_csv(TIMER_FILE,index=False)
        st.session_state.countdown_running=False
        st.success(f"Countdown stopped. Focused: {h}h {m}m {s}s")

    # Display countdown
    if st.session_state.get("countdown_running",False):
        st_autorefresh(interval=1000,key="timer_refresh")
        elapsed = int(time.time()-st.session_state.countdown_start_time)
        remaining = max(st.session_state.countdown_total_seconds - elapsed,0)
        h = remaining//3600
        m = (remaining%3600)//60
        s = remaining%60
        display_box.markdown(f"<h1 style='text-align:center;font-size:160px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1>"
                             f"<h3 style='text-align:center;font-size:48px;'>Task: {st.session_state.countdown_task_name}</h3>",unsafe_allow_html=True)
        if remaining==0:
            st.session_state.countdown_running=False
            new_entry = {"Task": st.session_state.countdown_task_name,
                         "Target_HMS": f"{hours}h {minutes}m {seconds}s",
                         "Focused_HMS": f"{hours}h {minutes}m {seconds}s",
                         "Date": today_date}
            st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([new_entry])],ignore_index=True)
            st.session_state.timer_data.to_csv(TIMER_FILE,index=False)
            display_box.success("🎯 Countdown Finished!")

    # Total Focused Time
    if not st.session_state.timer_data.empty:
        total_seconds = 0
        for t in st.session_state.timer_data['Focused_HMS']:
            parts = t.split()
            h = int(parts[0].replace('h',''))
            m = int(parts[1].replace('m',''))
            s = int(parts[2].replace('s',''))
            total_seconds += h*3600 + m*60 + s
        total_h = total_seconds//3600
        total_m = (total_seconds%3600)//60
        total_s = total_seconds%60
        st.markdown(f"### 🎯 Total Focused Time Today: {total_h}h {total_m}m {total_s}s")

# ---------------- Pomodoro Tab ----------------
with tab3:
    st.subheader("🍅 Pomodoro Timer")

    if "pomo_running" not in st.session_state:
        st.session_state.pomo_running = False
        st.session_state.pomo_paused = False
        st.session_state.pomo_pauses = 0
        st.session_state.pomo_seconds = 0
        st.session_state.pomo_start_time = 0
        st.session_state.pomo_work_min = 25
        st.session_state.pomo_short_break_min = 5
        st.session_state.pomo_long_break_min = 15
        st.session_state.pomo_cycles = 4
        st.session_state.daily_target_min = 0
        st.session_state.daily_focused_min = 0
        st.session_state.pomo_data = pd.DataFrame(columns=["Date","Focused_Minutes"])

    # Pomodoro configuration
    st.session_state.pomo_work_min = st.number_input("Work minutes", 5, 180, value=st.session_state.pomo_work_min)
    st.session_state.pomo_short_break_min = st.number_input("Short break minutes",1,60,value=st.session_state.pomo_short_break_min)
    st.session_state.pomo_long_break_min = st.number_input("Long break minutes",5,60,value=st.session_state.pomo_long_break_min)
    st.session_state.pomo_cycles = st.number_input("Pomodoro cycles",1,12,value=st.session_state.pomo_cycles)
    st.session_state.daily_target_min = st.number_input("Daily focus target (minutes)",0,1440,value=st.session_state.daily_target_min)

    col_start,col_pause,col_cancel = st.columns([1,1,1])
    start_btn = col_start.button("Start Pomodoro")
    pause_btn = col_pause.button("Pause/Resume Pomodoro")
    cancel_btn = col_cancel.button("Cancel Pomodoro")

    # Start
    if start_btn:
        st.session_state.pomo_running = True
        st.session_state.pomo_paused = False
        st.session_state.pomo_pauses = 0
        st.session_state.pomo_seconds = st.session_state.pomo_work_min*60
        st.session_state.pomo_start_time = time.time()
        st.success("Pomodoro started!")

    # Countdown
    if st.session_state.pomo_running:
        if not st.session_state.pomo_paused:
            elapsed = int(time.time()-st.session_state.pomo_start_time)
            remaining = max(st.session_state.pomo_seconds - elapsed,0)
            h = remaining//3600
            m = (remaining%3600)//60
            s = remaining%60
            st.markdown(f"<h1 style='text-align:center;font-size:100px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1>",unsafe_allow_html=True)
            if remaining==0:
                st.session_state.pomo_running=False
                st.session_state.daily_focused_min += st.session_state.pomo_work_min
                st.success("Pomodoro finished! Time for a break 🍵")
                if st.session_state.daily_target_min>0 and st.session_state.daily_focused_min>=st.session_state.daily_target_min:
                    st.balloons()
                    st.info("🎉 You reached your daily focus target! Take a break.")

    # Pause/Resume
    if pause_btn and st.session_state.pomo_running:
        if not st.session_state.pomo_paused:
            st.session_state.pomo_seconds -= int(time.time() - st.session_state.pomo_start_time)
            st.session_state.pomo_paused=True
            st.session_state.pomo_pauses+=1
            st.warning("Pomodoro paused")
            if st.session_state.pomo_pauses>2:
                st.session_state.pomo_running=False
                st.error("Paused too many times. Pomodoro canceled!")
        else:
            st.session_state.pomo_start_time = time.time()
            st.session_state.pomo_paused=False
            st.success("Pomodoro resumed")

    # Cancel
    if cancel_btn and st.session_state.pomo_running:
        st.session_state.pomo_running=False
        st.warning("Pomodoro canceled")

    # Save Pomodoro
    if not st.session_state.pomo_running and st.session_state.pomo_work_min>0:
        new_entry = {"Date":today_date,"Focused_Minutes":st.session_state.daily_focused_min}
        st.session_state.pomo_data = pd.concat([st.session_state.pomo_data,pd.DataFrame([new_entry])],ignore_index=True)
        st.session_state.pomo_data.to_csv(POMO_FILE,index=False)

    st.markdown("### Pomodoro Data")
    if not st.session_state.pomo_data.empty:
        st.dataframe(st.session_state.pomo_data[st.session_state.pomo_data["Date"]==today_date],use_container_width=True)
