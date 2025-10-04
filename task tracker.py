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
    if val=="Done": return 'background-color: lightgreen'
    elif val=="Pending": return 'background-color: yellow'
    elif val=="Not Done": return 'background-color: red'

def hms_to_seconds(hms_str):
    # expects "Hh Mm Ss"
    h,m,s=0,0,0
    parts = hms_str.split()
    for part in parts:
        if part.endswith('h'): h=int(part[:-1])
        elif part.endswith('m'): m=int(part[:-1])
        elif part.endswith('s'): s=int(part[:-1])
    return h*3600 + m*60 + s

today_date = str(date.today())

# ------------------ SESSION STATE DEFAULTS ------------------
for key in ["logged_in","username","task_updated","timer_running","timer_paused",
            "timer_start_time","timer_elapsed","timer_duration","timer_task_name",
            "pomo_running","pomo_paused","pomo_start_time","pomo_elapsed","pomo_duration",
            "pomo_task_name","countdown_running","countdown_total_seconds","countdown_start_time",
            "countdown_task_name","timer_data","pomo_sessions"]:
    if key not in st.session_state:
        if key=="timer_data":
            st.session_state[key] = pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS"])
        elif key=="pomo_sessions":
            st.session_state[key] = 0
        else:
            st.session_state[key] = False if "running" in key or "paused" in key else None

# ------------------ RESET APP ------------------
st.sidebar.title("⚙ App Controls")
if st.sidebar.button("🧹 Reset App / Clear All Data"):
    files_to_delete = ["users.csv"] + list(pd.io.common.glob("tasks_*.csv")) + \
                      list(pd.io.common.glob("timer_*.csv")) + list(pd.io.common.glob("pomo_*.csv")) + \
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
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Tasks","⏱️ Timer","🍅 Pomodoro","👥 Group Workspace"])

    # ------------------ TAB 1: PERSONAL TASKS ------------------
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
            def color_personal_status(val):
                if val=="Done": return 'background-color: lightgreen'
                elif val=="Not Done": return 'background-color: red'
                else: return ''
            st.dataframe(tasks.style.applymap(color_personal_status, subset=["Status"]), use_container_width=True)
            st.markdown("### Update Task Status")
            for i,row in tasks.iterrows():
                cols = st.columns([4,1,1,1])
                cols[0].write(f"{row['Task']}")
                if cols[1].button("Done", key=f"done_{i}"): tasks.at[i,"Status"]="Done"; save_csv(tasks,TASKS_FILE)
                if cols[2].button("Not Done", key=f"notdone_{i}"): tasks.at[i,"Status"]="Not Done"; save_csv(tasks,TASKS_FILE)
                if cols[3].button("Delete", key=f"delete_{i}"): tasks = tasks.drop(i).reset_index(drop=True); save_csv(tasks,TASKS_FILE)

    # ------------------ TAB 2: TIMER ------------------
    with tab2:
        st.subheader("⏱️ Countdown Timer")
        col_h, col_m, col_s = st.columns(3)
        with col_h: hours = st.number_input("Hours", 0, 23, 0, key="hours_input")
        with col_m: minutes = st.number_input("Minutes", 0, 59, 0, key="minutes_input")
        with col_s: seconds = st.number_input("Seconds", 0, 59, 0, key="seconds_input")

        countdown_task_name = st.text_input("Task name (optional)", key="countdown_task_input")
        start_col, stop_col = st.columns([1,1])
        start_btn = start_col.button("Start Countdown")
        stop_btn = stop_col.button("Stop Countdown")
        display_box = st.empty()

        TIMER_FILE = f"timer_{username}.csv"
        if not hasattr(st.session_state, "timer_data") or st.session_state.timer_data is None:
            st.session_state.timer_data = load_or_create_csv(TIMER_FILE, ["Task","Target_HMS","Focused_HMS"])

        if start_btn:
            total_seconds = hours*3600 + minutes*60 + seconds
            if total_seconds > 0:
                st.session_state.countdown_running = True
                st.session_state.countdown_total_seconds = total_seconds
                st.session_state.countdown_start_time = time.time()
                st.session_state.countdown_task_name = countdown_task_name if countdown_task_name else "Unnamed"
            else:
                st.warning("Set a time greater than 0.")

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

        if st.session_state.get("countdown_running", False):
            st_autorefresh(interval=1000, key="timer_refresh")
            elapsed = int(time.time() - st.session_state.countdown_start_time)
            remaining = max(st.session_state.countdown_total_seconds - elapsed, 0)
            h = remaining // 3600
            m = (remaining % 3600) // 60
            s = remaining % 60
            display_box.markdown(
                f"<h1 style='text-align:center;font-size:120px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1>"
                f"<h3 style='text-align:center;font-size:32px;'>Task: {st.session_state.countdown_task_name}</h3>", 
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

        # Total Focused Time
        if not st.session_state.timer_data.empty:
            total_seconds_calc = sum([hms_to_seconds(t) for t in st.session_state.timer_data['Focused_HMS']])
            total_h = total_seconds_calc // 3600
            total_m = (total_seconds_calc % 3600) // 60
            total_s = total_seconds_calc % 60
            st.markdown(f"### 🎯 Total Focused Time: {total_h}h {total_m}m {total_s}s")
            st.markdown("### ⏳ History")
            st.dataframe(st.session_state.timer_data, use_container_width=True)

    # ------------------ TAB 3: POMODORO ------------------
    with tab3:
        st.subheader("🍅 Pomodoro Timer")
        pomo_task = st.text_input("Pomodoro Task", key="pomo_task")
        pomo_duration = st.number_input("Focus Duration (minutes)", 1, 120, 25)
        break_duration = st.number_input("Break Duration (minutes)", 1, 60, 5)

        start_col, pause_col, stop_col = st.columns(3)
        start_btn = start_col.button("Start Pomodoro")
        pause_btn = pause_col.button("Pause/Resume Pomodoro")
        stop_btn = stop_col.button("Stop Pomodoro")
        display_box = st.empty()

        POMO_FILE = f"pomo_{username}.csv"
        if not hasattr(st.session_state, "pomo_data") or st.session_state.pomo_data is None:
            st.session_state.pomo_data = load_or_create_csv(POMO_FILE, ["Task","Duration(min)","Date"])

        if start_btn:
            st.session_state.pomo_running = True
            st.session_state.pomo_paused = False
            st.session_state.pomo_start_time = time.time()
            st.session_state.pomo_elapsed = 0
            st.session_state.pomo_task_name = pomo_task
            st.session_state.pomo_sessions +=1

        if pause_btn and st.session_state.pomo_running:
            if st.session_state.pomo_paused:
                st.session_state.pomo_paused=False
                st.session_state.pomo_start_time = time.time()
            else:
                st.session_state.pomo_paused=True
                st.session_state.pomo_elapsed += time.time() - st.session_state.pomo_start_time

        if stop_btn and st.session_state.pomo_running:
            elapsed = st.session_state.pomo_elapsed + (time.time() - st.session_state.pomo_start_time if not st.session_state.pomo_paused else 0)
            st.session_state.pomo_data = pd.concat([st.session_state.pomo_data, pd.DataFrame([{
                "Task": st.session_state.pomo_task_name,
                "Duration(min)": round(elapsed/60,1),
                "Date": today_date
            }])], ignore_index=True)
            st.session_state.pomo_data.to_csv(POMO_FILE, index=False)
            st.session_state.pomo_running=False
            st.session_state.pomo_elapsed=0
            st.success(f"Pomodoro recorded: {round(elapsed/60,1)} minutes")

        if st.session_state.pomo_running:
            st_autorefresh(interval=1000, key="pomo_refresh")
            elapsed = st.session_state.pomo_elapsed + (time.time() - st.session_state.pomo_start_time if not st.session_state.pomo_paused else 0)
            remaining = max(pomo_duration*60 - elapsed,0)
            mins, secs = divmod(int(remaining),60)
            display_box.markdown(f"<h1 style='text-align:center;font-size:80px;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)

        total_pomo_minutes = st.session_state.pomo_data["Duration(min)"].sum() if not st.session_state.pomo_data.empty else 0
        st.markdown(f"### Total Pomodoro Sessions: {st.session_state.pomo_sessions}")
        st.markdown(f"### Total Focused Time: {round(total_pomo_minutes,1)} minutes")
        if not st.session_state.pomo_data.empty:
            st.markdown("### History")
            st.dataframe(st.session_state.pomo_data, use_container_width=True)

    # ------------------ TAB 4: GROUP WORKSPACE ------------------
    with tab4:
        st.subheader("Group Workspace")
        GROUPS_FILE="groups.csv"
        GROUP_TASKS_FILE="group_tasks.csv"
        GROUP_CHAT_FILE="group_chat.csv"

        groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Members"])
        group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
        group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])

        st.markdown("### Your Groups")
        my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]
        selected_group = None
        for _, grp in my_groups.iterrows():
            if st.button(grp["GroupName"], key=f"group_btn_{grp['GroupName']}"):
                selected_group = grp["GroupName"]

        if selected_group:
            st.markdown(f"### {selected_group} Tasks")
            grp_tasks_sel = group_tasks[group_tasks["GroupName"]==selected_group]
            if not grp_tasks_sel.empty:
                st.dataframe(grp_tasks_sel[["Task","AddedBy","Date"]], use_container_width=True)

            st.markdown(f"### {selected_group} Chat")
            chat_input = st.text_input("Message", key="grp_chat_input")
            if st.button("Send Message"):
                if chat_input.strip():
                    new_msg={"GroupName":selected_group,"Username":username,"Message":chat_input.strip(),
                             "Time":datetime.now().strftime("%H:%M:%S")}
                    group_chat=pd.concat([group_chat,pd.DataFrame([new_msg])], ignore_index=True)
                    save_csv(group_chat,GROUP_CHAT_FILE)

            # Display chat safely
            chat_sel = group_chat[group_chat["GroupName"]==selected_group]
            chat_box = st.empty()
            with chat_box.container():
                for _, row in chat_sel.iterrows():
                    st.markdown(f"[{row['Time']}] *{row['Username']}*: {row['Message']}")
