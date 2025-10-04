import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
import hashlib

# ---------------- USERS FILE ----------------
USERS_FILE = "users.csv"
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["username", "password_hash"]).to_csv(USERS_FILE, index=False)

# ---------------- Password hashing ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------- Auth Flow ----------------
st.sidebar.image("taskuni.png", width=100)
auth_choice = st.sidebar.radio("Choose action:", ["Login", "Register"])

users_df = pd.read_csv(USERS_FILE)

if auth_choice == "Register":
    st.subheader("📝 Register a new account")
    reg_username = st.text_input("Username", key="reg_username")
    reg_password = st.text_input("Password", type="password", key="reg_password")
    if st.button("Register"):
        if reg_username in users_df["username"].values:
            st.warning("Username already exists! Try login.")
        elif reg_username.strip() == "" or reg_password.strip() == "":
            st.warning("Username and password cannot be empty.")
        else:
            users_df = pd.concat([users_df, pd.DataFrame([{
                "username": reg_username,
                "password_hash": hash_password(reg_password)
            }])], ignore_index=True)
            users_df.to_csv(USERS_FILE, index=False)
            st.success("✅ Registered successfully! You can now login.")

elif auth_choice == "Login":
    st.subheader("🔑 Login to your account")
    login_username = st.text_input("Username", key="login_username")
    login_password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        user_row = users_df[users_df["username"] == login_username]
        if not user_row.empty and user_row.iloc[0]["password_hash"] == hash_password(login_password):
            st.success(f"Welcome back, {login_username}!")
            st.session_state.logged_in_user = login_username
        else:
            st.error("❌ Invalid username or password")

# ---------------- Only show main app if logged in ----------------
if "logged_in_user" in st.session_state:
    username = st.session_state.logged_in_user

    # ---------------- Reset session state if username changed ----------------
    if "last_username" not in st.session_state or st.session_state.last_username != username:
        st.session_state.tasks = pd.DataFrame(columns=["Task", "Status", "Date"])
        st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_HMS", "Focused_HMS", "Date"])
        st.session_state.countdown_running = False
        st.session_state.countdown_total_seconds = 0
        st.session_state.countdown_start_time = 0
        st.session_state.countdown_task_name = ""
        st.session_state.pomodoro_running = False
        st.session_state.last_username = username

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
    st.title("📌 TaskUni — Your personal Task tracker")
    today_date = datetime.now().strftime("%d-%m-%Y")
    tab1, tab2, tab3 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer", "🍅 Pomodoro Timer"])

    # ---------------- Task Tracker Functions ----------------
    def mark_done(idx):
        st.session_state.tasks.at[idx, "Status"] = "Done"
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

    def mark_notdone(idx):
        st.session_state.tasks.at[idx, "Status"] = "Not Done"
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

    def delete_task(idx):
        st.session_state.tasks = st.session_state.tasks.drop(idx).reset_index(drop=True)
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

    # ---------------- Task Tracker Tab ----------------
    with tab1:
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
                if s == "Done":
                    return 'background-color:#00C853;color:white'
                elif s == "Not Done":
                    return 'background-color:#D50000;color:white'
                else:
                    return 'background-color:#FFA500;color:white'

            df_display = tasks_today[["Task","Status"]].copy()
            df_display.index += 1
            st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]), use_container_width=True)

            st.markdown("### Update Tasks")
            for i, row in tasks_today.iterrows():
                cols = st.columns([3,1,1,1])
                cols[0].write(f"{row['Task']}:")
                cols[1].button("Done", key=f"done_{i}", on_click=mark_done, args=(i,))
                cols[2].button("Not Done", key=f"notdone_{i}", on_click=mark_notdone, args=(i,))
                cols[3].button("Delete", key=f"delete_{i}", on_click=delete_task, args=(i,))

    # ---------------- Countdown Timer Tab ----------------
    with tab2:
        st.write("Set countdown time")
        col_h, col_m, col_s = st.columns(3)
        with col_h:
            hours = st.number_input("Hours", 0, 23, 0, key="hours_input")
        with col_m:
            minutes = st.number_input("Minutes", 0, 59, 0, key="minutes_input")
        with col_s:
            seconds = st.number_input("Seconds", 0, 59, 0, key="seconds_input")

        countdown_task_name = st.text_input("Task name (optional)", key="countdown_task_input")
        start_col, stop_col, break_col = st.columns([1,1,1])
        start_btn = start_col.button("Start Countdown")
        stop_btn = stop_col.button("Stop Countdown")
        break_btn = break_col.button("Take Break (10 min after 30 min focus)")

        display_box = st.empty()

        # ---------------- Total focused seconds today ----------------
        today_timer_data = st.session_state.timer_data[st.session_state.timer_data["Date"] == today_date]
        total_focused_seconds = sum([
            int(t.split()[0].replace('h',''))*3600 +
            int(t.split()[1].replace('m',''))*60 +
            int(t.split()[2].replace('s',''))
            for t in today_timer_data['Focused_HMS']
        ]) if not today_timer_data.empty else 0

        # ---------------- Take Break Logic ----------------
        if break_btn:
            if total_focused_seconds >= 1800:  # 30 min
                st.success("Starting 10-min break ⏱️")
                st.session_state.countdown_total_seconds = 10*60
                st.session_state.countdown_start_time = time.time()
                st.session_state.countdown_task_name = "Break"
                st.session_state.countdown_running = True
            else:
                st.warning("You need at least 30 minutes of focus today to take a break.")

        # Start countdown
        if start_btn:
            total_seconds = hours*3600 + minutes*60 + seconds
            if total_seconds <= 0:
                st.warning("Set a time greater than 0.")
            else:
                st.session_state.countdown_running = True
                st.session_state.countdown_total_seconds = total_seconds
                st.session_state.countdown_start_time = time.time()
                st.session_state.countdown_task_name = countdown_task_name if countdown_task_name else "Unnamed"

        # Stop countdown
        if stop_btn and st.session_state.countdown_running:
            elapsed = int(time.time() - st.session_state.countdown_start_time)
            focused = min(elapsed, st.session_state.countdown_total_seconds)
            h = focused // 3600
            m = (focused % 3600) // 60
            s = focused % 60
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.countdown_task_name,
                "Target_HMS": f"{hours}h {minutes}m {seconds}s",
                "Focused_HMS": f"{h}h {m}m {s}s",
                "Date": today_date
            }])], ignore_index=True)
            st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
            st.session_state.countdown_running = False
            st.success(f"Countdown stopped. Focused: {h}h {m}m {s}s")

        # Countdown display with notification
        if st.session_state.get("countdown_running", False):
            st_autorefresh(interval=1000, key="timer_refresh")
            elapsed = int(time.time() - st.session_state.countdown_start_time)
            remaining = max(st.session_state.countdown_total_seconds - elapsed, 0)
            h = remaining // 3600
            m = (remaining % 3600) // 60
            s = remaining % 60

            display_box.markdown(
                f"<h1 style='text-align:center;font-size:160px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1>"
                f"<h3 style='text-align:center;font-size:48px;'>Task: {st.session_state.countdown_task_name}</h3>", 
                unsafe_allow_html=True
            )

            if remaining == 0:
                st.session_state.countdown_running = False
                st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                    "Task": st.session_state.countdown_task_name,
                    "Target_HMS": f"{hours}h {minutes}m {seconds}s",
                    "Focused_HMS": f"{hours}h {minutes}m {seconds}s",
                    "Date": today_date
                }])], ignore_index=True)
                st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
                display_box.success("🎯 Countdown Finished! ⏳")

    # ---------------- Pomodoro Tab ----------------
    with tab3:
        st.subheader("🍅 Custom Pomodoro Timer")
        pomo_cycles = st.number_input("Number of Pomodoro cycles", min_value=1, value=4, step=1)
        work_min = st.number_input("Work duration (min)", min_value=1, value=25, step=1)
        short_break = st.number_input("Short break (min)", min_value=1, value=5, step=1)
        long_break = st.number_input("Long break (min)", min_value=1, value=15, step=1)
        start_pomo = st.button("Start Pomodoro")

        if start_pomo and not st.session_state.get("pomodoro_running", False):
            st.session_state.pomodoro_running = True
            st.session_state.current_cycle = 1
            st.session_state.pomo_phase = "Work"
            st.session_state.pomo_seconds = work_min*60
            st.session_state.pomo_work_min = work_min
            st.session_state.pomo_short_break = short_break
            st.session_state.pomo_long_break = long_break
            st.session_state.pomo_total_cycles = pomo_cycles
            st.session_state.pomo_start_time = time.time()

        if st.session_state.get("pomodoro_running", False):
            st_autorefresh(interval=1000, key="pomo_refresh")
            elapsed = int(time.time() - st.session_state.pomo_start_time)
            remaining = max(st.session_state.pomo_seconds - elapsed, 0)
            h = remaining // 3600
            m = (remaining % 3600) // 60
            s = remaining % 60

            st.markdown(f"<h1 style='text-align:center;font-size:120px;'>{st.session_state.pomo_phase}: {m:02d}:{s:02d}</h1>", unsafe_allow_html=True)

            if remaining == 0:
                # Store work session if phase was Work
                if st.session_state.pomo_phase == "Work":
                    st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                        "Task": f"Pomodoro Cycle {st.session_state.current_cycle}",
                        "Target_HMS": f"{st.session_state.pomo_work_min}m",
                        "Focused_HMS": f"{st.session_state.pomo_work_min}m",
                        "Date": today_date
                    }])], ignore_index=True)
                    st.session_state.timer_data.to_csv(TIMER_FILE, index=False)

                # Switch phase
                if st.session_state.pomo_phase == "Work":
                    if st.session_state.current_cycle % st.session_state.pomo_total_cycles == 0:
                        st.session_state.pomo_phase = "Long Break"
                        st.session_state.pomo_seconds = st.session_state.pomo_long_break*60
                        st.success("🟢 Long Break started!")
                    else:
                        st.session_state.pomo_phase = "Short Break"
                        st.session_state.pomo_seconds = st.session_state.pomo_short_break*60
                        st.info("🟡 Short Break started!")
                else:
                    st.session_state.pomo_phase = "Work"
                    st.session_state.pomo_seconds = st.session_state.pomo_work_min*60
                    st.session_state.current_cycle += 1
                    st.success(f"🔵 Work Session {st.session_state.current_cycle} started!")

                if st.session_state.current_cycle > st.session_state.pomo_total_cycles:
                    st.session_state.pomodoro_running = False
                    st.success("🎉 Pomodoro session complete!")
                else:
                    st.session_state.pomo_start_time = time.time()
