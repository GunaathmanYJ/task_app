import streamlit as st
import pandas as pd
import os
from datetime import datetime
import time
from io import BytesIO
from fpdf import FPDF
from streamlit_autorefresh import st_autorefresh

# ---------------- Files ----------------
USERS_FILE = "users.csv"

# Create users file if not exists
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["username","password"]).to_csv(USERS_FILE,index=False)

# ---------------- Sidebar Logo ----------------
st.sidebar.image("taskuni.png", width=100)

# ---------------- Login/Register ----------------
st.title("📌 TaskUni Premium")
st.subheader("Login or Register to continue")

auth_tab = st.tabs(["Login","Register"])
with auth_tab[1]:
    st.subheader("Register")
    reg_username = st.text_input("Username", key="reg_username")
    reg_password = st.text_input("Password", key="reg_password", type="password")
    if st.button("Register"):
        if reg_username.strip()=="" or reg_password.strip()=="":
            st.warning("Username and Password cannot be empty")
        else:
            users = pd.read_csv(USERS_FILE)
            if reg_username in users["username"].values:
                st.error("Username already exists!")
            else:
                users = pd.concat([users, pd.DataFrame([{"username":reg_username,"password":reg_password}])], ignore_index=True)
                users.to_csv(USERS_FILE,index=False)
                st.success("Registration successful! You can now login.")

with auth_tab[0]:
    st.subheader("Login")
    username_input = st.text_input("Username", key="login_username")
    password_input = st.text_input("Password", key="login_password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        users = pd.read_csv(USERS_FILE)
        if username_input not in users["username"].values:
            st.error("Username not found. Please register first.")
            st.stop()
        correct_pass = users.loc[users["username"]==username_input, "password"].values[0]
        if password_input == correct_pass:
            st.success(f"Welcome, {username_input}!")
            st.session_state.logged_in_user = username_input
        else:
            st.error("Incorrect password!")
            st.stop()

# Stop app if not logged in
if "logged_in_user" not in st.session_state:
    st.stop()

username = st.session_state.logged_in_user
today_date = datetime.now().strftime("%d-%m-%Y")

# ---------------- Files for user data ----------------
TASKS_FILE = f"tasks_{username}.csv"
TIMER_FILE = f"timer_{username}.csv"
POMO_FILE = f"pomodoro_{username}.csv"

# ---------------- Load data ----------------
if not os.path.exists(TASKS_FILE):
    pd.DataFrame(columns=["Task","Status","Date"]).to_csv(TASKS_FILE,index=False)
tasks_df = pd.read_csv(TASKS_FILE)

if not os.path.exists(TIMER_FILE):
    pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS","Date"]).to_csv(TIMER_FILE,index=False)
timer_df = pd.read_csv(TIMER_FILE)

if not os.path.exists(POMO_FILE):
    pd.DataFrame(columns=["Date","Focused_Minutes"]).to_csv(POMO_FILE,index=False)
pomo_df = pd.read_csv(POMO_FILE)

# ---------------- Page config ----------------
st.set_page_config(page_title="TaskUni Premium", layout="wide")

# ---------------- Tabs ----------------
tab1, tab2, tab3 = st.tabs(["📝 Task Tracker","⏱️ Countdown Timer","🍅 Pomodoro Timer"])

# ---------------- Task Tracker ----------------
with tab1:
    st.subheader(f"Tasks for {today_date}")
    task_name_input = st.text_input("Enter a task")
    if st.button("Add Task"):
        if task_name_input.strip() != "":
            new_task = {"Task":task_name_input.strip(),"Status":"Pending","Date":today_date}
            tasks_df = pd.concat([tasks_df,pd.DataFrame([new_task])],ignore_index=True)
            tasks_df.to_csv(TASKS_FILE,index=False)
            st.success("Task added!")

    tasks_today = tasks_df[tasks_df["Date"]==today_date]
    if not tasks_today.empty:
        def highlight_status(s):
            if s=="Done":
                return "background-color:#00C853;color:white"
            elif s=="Not Done":
                return "background-color:#D50000;color:white"
            else:
                return "background-color:#FFA500;color:white"

        df_display = tasks_today[["Task","Status"]].copy()
        df_display.index += 1
        st.dataframe(df_display.style.applymap(highlight_status,subset=["Status"]),use_container_width=True)

        st.markdown("### Update Tasks")
        for i,row in tasks_today.iterrows():
            cols = st.columns([3,1,1,1])
            cols[0].write(f"{row['Task']}:")
            if cols[1].button("Done", key=f"done_{i}"):
                tasks_df.at[i,"Status"]="Done"
                tasks_df.to_csv(TASKS_FILE,index=False)
                st.experimental_rerun()
            if cols[2].button("Not Done", key=f"notdone_{i}"):
                tasks_df.at[i,"Status"]="Not Done"
                tasks_df.to_csv(TASKS_FILE,index=False)
                st.experimental_rerun()
            if cols[3].button("Delete", key=f"delete_{i}"):
                tasks_df = tasks_df.drop(i).reset_index(drop=True)
                tasks_df.to_csv(TASKS_FILE,index=False)
                st.experimental_rerun()
# ---------------- Countdown Timer ----------------
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
    start_col, pause_col, stop_col = st.columns([1,1,1])
    start_btn = start_col.button("Start")
    pause_btn = pause_col.button("Pause/Resume")
    stop_btn = stop_col.button("Stop")
    display_box = st.empty()

    if "countdown_running" not in st.session_state:
        st.session_state.countdown_running = False
        st.session_state.countdown_paused = False
        st.session_state.countdown_seconds_left = 0

    if start_btn:
        total_seconds = hours*3600 + minutes*60 + seconds
        if total_seconds <=0:
            st.warning("Set a time greater than 0.")
        else:
            st.session_state.countdown_running = True
            st.session_state.countdown_paused = False
            st.session_state.countdown_seconds_left = total_seconds
            st.session_state.countdown_task_name = countdown_task_name if countdown_task_name else "Unnamed"
            st.session_state.countdown_start_time = time.time()

    if pause_btn and st.session_state.countdown_running:
        st.session_state.countdown_paused = not st.session_state.countdown_paused
        if st.session_state.countdown_paused:
            st.session_state.countdown_pause_time = time.time()

        else:
            paused_duration = time.time() - st.session_state.countdown_pause_time
            st.session_state.countdown_start_time += paused_duration

    if st.session_state.countdown_running and not st.session_state.countdown_paused:
        elapsed = int(time.time() - st.session_state.countdown_start_time)
        remaining = max(st.session_state.countdown_seconds_left - elapsed, 0)
        h = remaining//3600
        m = (remaining%3600)//60
        s = remaining%60
        display_box.markdown(
            f"<h1 style='text-align:center;font-size:100px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1>"
            f"<h3 style='text-align:center;font-size:36px;'>Task: {st.session_state.countdown_task_name}</h3>",
            unsafe_allow_html=True
        )
        if remaining == 0:
            st.session_state.countdown_running = False
            st.success(f"✅ Countdown Finished for {st.session_state.countdown_task_name}!")
            timer_df = pd.concat([timer_df, pd.DataFrame([{
                "Task": st.session_state.countdown_task_name,
                "Target_HMS": f"{hours}h {minutes}m {seconds}s",
                "Focused_HMS": f"{hours}h {minutes}m {seconds}s",
                "Date": today_date
            }])], ignore_index=True)
            timer_df.to_csv(TIMER_FILE,index=False)

    if stop_btn:
        if st.session_state.countdown_running:
            elapsed = int(time.time() - st.session_state.countdown_start_time)
            focused = min(elapsed, st.session_state.countdown_seconds_left)
            h = focused//3600
            m = (focused%3600)//60
            s = focused%60
            timer_df = pd.concat([timer_df, pd.DataFrame([{
                "Task": st.session_state.countdown_task_name,
                "Target_HMS": f"{hours}h {minutes}m {seconds}s",
                "Focused_HMS": f"{h}h {m}m {s}s",
                "Date": today_date
            }])], ignore_index=True)
            timer_df.to_csv(TIMER_FILE,index=False)
            st.success(f"Stopped. Focused: {h}h {m}m {s}s")
            st.session_state.countdown_running=False

# ---------------- Pomodoro Timer ----------------
with tab3:
    st.subheader("Pomodoro Timer")
    if "pomo_running" not in st.session_state:
        st.session_state.pomo_running = False
        st.session_state.pomo_paused = False
        st.session_state.pomo_pause_count = 0

    pomo_work_min = st.number_input("Work minutes", 5, 180, value=25)
    short_break_min = st.number_input("Short Break minutes", 1, 30, value=5)
    long_break_min = st.number_input("Long Break minutes", 1, 60, value=15)
    cycles = st.number_input("Number of Pomodoro cycles",1,20, value=4)
    daily_target_hr = st.number_input("Daily focus target hours",0,12,value=2)

    start_pomo_btn, pause_pomo_btn, cancel_pomo_btn = st.columns([1,1,1])
    if start_pomo_btn.button("Start Pomodoro"):
        st.session_state.pomo_running=True
        st.session_state.pomo_paused=False
        st.session_state.pomo_current_cycle=1
        st.session_state.pomo_total_cycles=cycles
        st.session_state.pomo_time_left=pomo_work_min*60
        st.session_state.pomo_mode="Work"
        st.session_state.pomo_start_time=time.time()
        st.session_state.pomo_pause_count=0
        st.success(f"Pomodoro started: Cycle 1/{cycles}")

    if pause_pomo_btn.button("Pause/Resume"):
        if st.session_state.pomo_running:
            st.session_state.pomo_paused = not st.session_state.pomo_paused
            if st.session_state.pomo_paused:
                st.session_state.pomo_pause_time = time.time()
                st.session_state.pomo_pause_count +=1
                if st.session_state.pomo_pause_count>2:
                    st.session_state.pomo_running=False
                    st.warning("Paused more than 2 times. Pomodoro canceled!")
            else:
                paused_duration = time.time() - st.session_state.pomo_pause_time
                st.session_state.pomo_start_time += paused_duration

    if cancel_pomo_btn.button("Cancel Pomodoro"):
        st.session_state.pomo_running=False
        st.warning("Pomodoro canceled!")

    # Pomodoro countdown
    if st.session_state.pomo_running and not st.session_state.pomo_paused:
        elapsed = int(time.time() - st.session_state.pomo_start_time)
        remaining = max(st.session_state.pomo_time_left - elapsed,0)
        mins = remaining//60
        secs = remaining%60
        st.markdown(f"<h1 style='text-align:center;font-size:100px;'>{mins:02d}:{secs:02d}</h1>",unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center'>Mode: {st.session_state.pomo_mode} | Cycle {st.session_state.pomo_current_cycle}/{st.session_state.pomo_total_cycles}</h3>",unsafe_allow_html=True)

        if remaining==0:
            # Switch mode
            if st.session_state.pomo_mode=="Work":
                st.session_state.pomo_mode="Break"
                if st.session_state.pomo_current_cycle%4==0:
                    st.session_state.pomo_time_left = long_break_min*60
                else:
                    st.session_state.pomo_time_left = short_break_min*60
            else:
                st.session_state.pomo_mode="Work"
                st.session_state.pomo_current_cycle +=1
                st.session_state.pomo_time_left = pomo_work_min*60

            st.session_state.pomo_start_time=time.time()

            if st.session_state.pomo_current_cycle>st.session_state.pomo_total_cycles:
                st.session_state.pomo_running=False
                st.success("Pomodoro complete!")

                # Save total focused minutes for the day
                today_total = int(pomo_work_min*st.session_state.pomo_total_cycles)
                if today_date in pomo_df["Date"].values:
                    pomo_df.loc[pomo_df["Date"]==today_date,"Focused_Minutes"]+=today_total
                else:
                    pomo_df = pd.concat([pomo_df,pd.DataFrame([{"Date":today_date,"Focused_Minutes":today_total}])],ignore_index=True)
                pomo_df.to_csv(POMO_FILE,index=False)

                # Daily target check
                total_focus_today = pomo_df.loc[pomo_df["Date"]==today_date,"Focused_Minutes"].sum()/60
                if total_focus_today>=daily_target_hr:
                    st.balloons()
                    st.info(f"🎯 You reached your daily focus target of {daily_target_hr} hr(s)!")
# ---------------- Tab 4: Take Break / Focus Tracker ----------------
with tab4:
    st.subheader("Take Break Tracker")
    
    # Check if user focused 30 mins for a break
    today_focus_seconds = 0
    if not timer_df.empty:
        today_timer_data = timer_df[timer_df["Date"]==today_date]
        for t in today_timer_data["Focused_HMS"]:
            parts = t.split()
            today_focus_seconds += int(parts[0].replace("h",""))*3600
            today_focus_seconds += int(parts[1].replace("m",""))*60
            today_focus_seconds += int(parts[2].replace("s",""))

    if today_focus_seconds >= 30*60:
        st.success("🎉 You've focused 30+ mins! Time for a 10 min break!")
    else:
        remaining = 30*60 - today_focus_seconds
        mins = remaining//60
        secs = remaining%60
        st.info(f"Focus {mins}m {secs}s more to unlock a 10-min break!")

# ---------------- Tab 5: Group Study ----------------
with tab5:
    st.subheader("Group Study Room")
    if "group_messages" not in st.session_state:
        st.session_state.group_messages = []
    if "group_notes" not in st.session_state:
        st.session_state.group_notes = ""

    # Show currently joined users
    join_name = st.text_input("Enter your username to join", key="group_username")
    if st.button("Join Room") and join_name.strip():
        if "group_users" not in st.session_state:
            st.session_state.group_users = []
        if join_name not in st.session_state.group_users:
            st.session_state.group_users.append(join_name)
        st.success(f"{join_name} joined the room!")

    if "group_users" in st.session_state:
        st.info("👥 Users in room: " + ", ".join(st.session_state.group_users))

    # Messages section
    msg_col1, msg_col2 = st.columns([4,1])
    message_input = msg_col1.text_input("Enter message", key="group_msg_input")
    if msg_col2.button("Send"):
        if message_input.strip():
            st.session_state.group_messages.append(f"{join_name}: {message_input.strip()}")

    if st.session_state.group_messages:
        st.subheader("💬 Chat Messages")
        for msg in st.session_state.group_messages[-20:]:
            st.write(msg)

    # Notes section (editable by everyone)
    st.subheader("📝 Shared Notes")
    shared_notes = st.text_area("Edit notes", value=st.session_state.group_notes, height=200)
    st.session_state.group_notes = shared_notes
