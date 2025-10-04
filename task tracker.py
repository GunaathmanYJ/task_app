import streamlit as st
import pandas as pd
import os
import hashlib
import time
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# ------------------ UTILITY ------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_or_create_csv(file, columns):
    if os.path.exists(file):
        df = pd.read_csv(file)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=columns)

def save_csv(df, file):
    df.to_csv(file, index=False)

def color_status(val):
    if val=="Done": return 'color: green; font-weight:bold'
    elif val=="Not Done": return 'color: red; font-weight:bold'
    return ''

today_date = str(date.today())

# ------------------ SESSION STATE DEFAULTS ------------------
session_keys = ["logged_in","username","task_updated","timer_running","timer_paused",
                "timer_start_time","timer_elapsed","timer_duration","timer_task_name",
                "pomo_running","pomo_paused","pomo_start_time","pomo_elapsed",
                "pomo_duration","pomo_task_name","active_group",
                "show_create_group","grp_chat_send",
                "start_timer_click","pause_timer_click","stop_timer_click",
                "start_pomo_click","pause_pomo_click","stop_pomo_click"]

for key in session_keys:
    if key not in st.session_state:
        st.session_state[key] = False if "running" in key or "paused" in key or "click" in key else None

# ------------------ RESET APP ------------------
st.sidebar.title("⚙ App Controls")
if st.sidebar.button("🧹 Reset App / Clear All Data"):
    files_to_delete = ["users.csv"] + list(pd.io.common.glob("tasks_*.csv")) + \
                      list(pd.io.common.glob("timer_.csv")) + list(pd.io.common.glob("pomo_.csv")) + \
                      ["groups.csv","group_tasks.csv","group_chat.csv"]
    for f in files_to_delete:
        if os.path.exists(f): os.remove(f)
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.success("All data cleared. Refresh page.")
    st.stop()

# ------------------ LOGIN / REGISTER ------------------
if not st.session_state.logged_in:
    st.title("🔐 TaskUni Login / Register")
    users_file = "users.csv"
    users = load_or_create_csv(users_file, ["Username","Password"])
    
    choice = st.radio("Login or Register", ["Login","Register"])
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    
    if choice=="Register" and st.button("Register"):
        if username_input.strip()=="" or password_input.strip()=="": st.warning("Fill both fields")
        elif username_input in users["Username"].values: st.error("Username exists!")
        else:
            users = pd.concat([users, pd.DataFrame([{"Username":username_input.strip(),
                                                     "Password":hash_password(password_input.strip())}])], ignore_index=True)
            save_csv(users, users_file)
            st.success("Registered! Login now.")
    
    if choice=="Login" and st.button("Login"):
        if username_input.strip() in users["Username"].values:
            stored_pass = users.loc[users["Username"]==username_input.strip(),"Password"].values[0]
            if stored_pass==hash_password(password_input.strip()):
                st.session_state.logged_in = True
                st.session_state.username = username_input.strip()
                st.success(f"Welcome {st.session_state.username}!")
            else: st.error("Wrong password!")
        else: st.error("Username not found!")

# ------------------ MAIN APP ------------------
if st.session_state.logged_in:
    username = st.session_state.username
    st.title(f"TaskUni - {username}")
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Tasks","⏳ Timer","🍅 Pomodoro","👥 Group Workspace"])

    # ------------------ TAB 1: TASKS ------------------
    with tab1:
        st.subheader("Your Tasks")
        TASKS_FILE = f"tasks_{username}.csv"
        tasks = load_or_create_csv(TASKS_FILE, ["Task","Status","Date"])

        task_input = st.text_input("Add a new task", key="task_input")
        if st.button("➕ Add Task"):
            if task_input.strip():
                tasks = pd.concat([tasks, pd.DataFrame([{"Task":task_input.strip(),"Status":"Pending","Date":today_date}])], ignore_index=True)
                save_csv(tasks,TASKS_FILE)

        if not tasks.empty:
            st.dataframe(tasks.style.applymap(color_status, subset=["Status"]), use_container_width=True)
            st.markdown("### Update Task Status")
            for i, row in tasks.iterrows():
                cols = st.columns([4,1,1,1])
                cols[0].write(row['Task'])
                if cols[1].button("Done", key=f"done_{i}"):
                    tasks.at[i, "Status"] = "Done"
                    save_csv(tasks, TASKS_FILE)
                if cols[2].button("Not Done", key=f"notdone_{i}"):
                    tasks.at[i, "Status"] = "Not Done"
                    save_csv(tasks, TASKS_FILE)
                if cols[3].button("Delete", key=f"delete_{i}"):
                    tasks = tasks.drop(i).reset_index(drop=True)
                    save_csv(tasks, TASKS_FILE)

    # ------------------ TAB 2: TIMER ------------------
    with tab2:
        st.subheader("Focus Timer")
        TIMER_FILE = f"timer_{username}.csv"
        timer_data = load_or_create_csv(TIMER_FILE, ["Task","Duration(min)","Date"])

        timer_task = st.text_input("Task name for timer", key="timer_task")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=180, value=25)
        st_autorefresh(interval=1000, key="timer_refresh")

        col1, col2, col3 = st.columns(3)

        # START TIMER
        if col1.button("▶ Start Timer") or st.session_state.start_timer_click:
            st.session_state.start_timer_click = True
            if not st.session_state.timer_running:
                st.session_state.timer_start_time = time.time()
                st.session_state.timer_duration = duration*60
                st.session_state.timer_task_name = timer_task
                st.session_state.timer_running=True
                st.session_state.timer_paused=False
                st.session_state.timer_elapsed=0

        # PAUSE TIMER
        if col2.button("⏸ Pause Timer") or st.session_state.pause_timer_click:
            st.session_state.pause_timer_click = True
            if st.session_state.timer_running and not st.session_state.timer_paused:
                st.session_state.timer_paused=True
                st.session_state.timer_elapsed += time.time() - st.session_state.timer_start_time

        # RESUME TIMER
        if col2.button("▶ Resume Timer"):
            if st.session_state.timer_running and st.session_state.timer_paused:
                st.session_state.timer_paused=False
                st.session_state.timer_start_time = time.time()

        # STOP TIMER
        if col3.button("⏹ Stop Timer") or st.session_state.stop_timer_click:
            st.session_state.stop_timer_click = True
            if st.session_state.timer_running:
                st.session_state.timer_running=False
                elapsed = st.session_state.timer_elapsed + (0 if st.session_state.timer_paused else time.time() - st.session_state.timer_start_time)
                new_entry={"Task":timer_task,"Duration(min)":round(elapsed/60,1),"Date":today_date}
                timer_data = pd.concat([timer_data,pd.DataFrame([new_entry])], ignore_index=True)
                save_csv(timer_data,TIMER_FILE)
                st.session_state.timer_elapsed=0
                st.session_state.timer_start_time=None

        # DISPLAY TIMER
        if st.session_state.timer_running:
            elapsed = st.session_state.timer_elapsed + (0 if st.session_state.timer_paused else time.time() - st.session_state.timer_start_time)
            remaining = max(0, st.session_state.timer_duration - elapsed)
            mins, secs = divmod(int(remaining), 60)
            st.markdown(f"<h1 style='font-size:100px;text-align:center'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            if remaining <= 0:
                st.success("⏰ Time’s up!")
                st.session_state.timer_running=False

        st.metric("Total Focused Time (min)", round(timer_data["Duration(min)"].sum(),2) if not timer_data.empty else 0)
        st.markdown("### Session History")
        st.dataframe(timer_data, use_container_width=True)
