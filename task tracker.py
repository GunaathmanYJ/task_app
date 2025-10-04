import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time
from io import BytesIO
import hashlib
from streamlit_autorefresh import st_autorefresh

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
        st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_HMS", "Focused_HMS"])
        st.session_state.countdown_running = False
        st.session_state.pomo_running = False
        st.session_state.group_update = 0
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
    st.title("📌 TaskUni — Task Tracker & Pomodoro App")
    today_date = datetime.now().strftime("%d-%m-%Y")

    # ---------------- Tabs ----------------
    tab1, tab2, tab3, group_tab = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer", "🍅 Pomodoro Timer", "👥 Group Workspace"])

    # ---------------- Utility: Convert HMS to seconds ----------------
    def hms_to_seconds(hms_str):
        try:
            h, m, s = 0, 0, 0
            parts = hms_str.split()
            for part in parts:
                if "h" in part:
                    h = int(part.replace("h",""))
                elif "m" in part:
                    m = int(part.replace("m",""))
                elif "s" in part:
                    s = int(part.replace("s",""))
            return h*3600 + m*60 + s
        except:
            return 0

    # ---------------- Helper Functions for Tasks ----------------
    def mark_done(idx):
        st.session_state.tasks.at[idx, "Status"] = "Done"
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

    def mark_notdone(idx):
        st.session_state.tasks.at[idx, "Status"] = "Not Done"
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

    def delete_task(idx):
        st.session_state.tasks = st.session_state.tasks.drop(idx).reset_index(drop=True)
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

    # ---------------- Tab 1: Task Tracker ----------------
    with tab1:
        st.subheader("📝 Personal Tasks")
        task_name_input = st.text_input("Enter your task")
        if st.button("Add Task") and task_name_input.strip():
            new_task = {"Task": task_name_input.strip(), "Status": "Pending", "Date": today_date}
            st.session_state.tasks = pd.concat([st.session_state.tasks, pd.DataFrame([new_task])], ignore_index=True)
            st.session_state.tasks.to_csv(TASKS_FILE, index=False)

        st.subheader(f"Tasks on {today_date}")
        tasks_today = st.session_state.tasks[st.session_state.tasks['Date'] == today_date]
        if not tasks_today.empty:
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
        else:
            st.write("No tasks for today.")

    # ---------------- Tab 2: Countdown Timer ----------------
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
                f"<h1 style='text-align:center;font-size:160px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1>"
                f"<h3 style='text-align:center;font-size:48px;'>Task: {st.session_state.countdown_task_name}</h3>", 
                unsafe_allow_html=True
            )
            if remaining == 0:
                st.session_state.countdown_running = False
                st.success("🎯 Countdown Finished!")

        # Total Focused Time
        if not st.session_state.timer_data.empty:
            total_seconds_calc = sum(hms_to_seconds(t) for t in st.session_state.timer_data['Focused_HMS'])
            total_h = total_seconds_calc // 3600
            total_m = (total_seconds_calc % 3600) // 60
            total_s = total_seconds_calc % 60
            st.markdown(f"### 🎯 Total Focused Time: {total_h}h {total_m}m {total_s}s")

    # ---------------- Tab 3: Pomodoro Timer ----------------
    with tab3:
        st.subheader("🍅 Pomodoro Timer")
        pomo_minutes = st.number_input("Pomodoro Duration (minutes)", 5, 180, 25, key="pomo_minutes")
        start_pomo, stop_pomo = st.columns([1,1])
        start_pomo_btn = start_pomo.button("Start Pomodoro")
        stop_pomo_btn = stop_pomo.button("Stop Pomodoro")
        display_pomo = st.empty()

        if start_pomo_btn:
            st.session_state.pomo_running = True
            st.session_state.pomo_start_time = time.time()
            st.session_state.pomo_total_seconds = pomo_minutes*60

        if stop_pomo_btn and st.session_state.pomo_running:
            elapsed = int(time.time() - st.session_state.pomo_start_time)
            focused = min(elapsed, st.session_state.pomo_total_seconds)
            h = focused // 3600
            m = (focused % 3600) // 60
            s = focused % 60
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": f"Pomodoro {today_date}",
                "Target_HMS": f"{pomo_minutes}m",
                "Focused_HMS": f"{h}h {m}m {s}s"
            }])], ignore_index=True)
            st.session_state.timer_data.to_csv(TIMER_FILE, index=False)
            st.session_state.pomo_running = False
            st.success(f"Pomodoro stopped. Focused: {h}h {m}m {s}s")

        if st.session_state.get("pomo_running", False):
            st_autorefresh(interval=1000, key="pomo_refresh")
            elapsed = int(time.time() - st.session_state.pomo_start_time)
            remaining = max(st.session_state.pomo_total_seconds - elapsed, 0)
            m = remaining // 60
            s = remaining % 60
            display_pomo.markdown(
                f"<h1 style='text-align:center;font-size:120px;'>🍅 {m:02d}:{s:02d}</h1>",
                unsafe_allow_html=True
            )

    # ---------------- Tab 4: Group Workspace ----------------
    with group_tab:
        st.subheader("👥 Group Tasks & Chat")
        GROUP_TASKS_FILE = "group_tasks.csv"
        GROUP_CHAT_FILE = "group_chat.csv"

        # Load group tasks and chat if exists
        if os.path.exists(GROUP_TASKS_FILE):
            group_tasks = pd.read_csv(GROUP_TASKS_FILE)
        else:
            group_tasks = pd.DataFrame(columns=["Task","Status","AddedBy","Date"])

        if os.path.exists(GROUP_CHAT_FILE):
            group_chat = pd.read_csv(GROUP_CHAT_FILE)
        else:
            group_chat = pd.DataFrame(columns=["Username","Message","Time"])

        st.markdown("### 📝 Group Tasks")
        new_group_task = st.text_input("Enter a new task for the group")
        if st.button("Add Task to Group"):
            if new_group_task.strip():
                group_tasks = pd.concat([group_tasks, pd.DataFrame([{
                    "Task": new_group_task.strip(),
                    "Status": "Pending",
                    "AddedBy": username,
                    "Date": today_date
                }])], ignore_index=True)
                group_tasks.to_csv(GROUP_TASKS_FILE, index=False)
                st.session_state.group_update += 1  # triggers rerun
                st.success("✅ Task added to group!")

        # Display group tasks
        if not group_tasks.empty:
            def highlight_group_status(s):
                if s == "Done":
                    return 'background-color:#00C853;color:white'
                elif s == "Not Done":
                    return 'background-color:#D50000;color:white'
                else:
                    return 'background-color:#FFA500;color:white'

            st.dataframe(group_tasks.style.applymap(highlight_group_status, subset=["Status"]), use_container_width=True)

            # Buttons to mark tasks
            for i, row in group_tasks.iterrows():
                cols = st.columns([3,1,1,1])
                cols[0].write(f"{row['Task']} (by {row['AddedBy']}):")
                if cols[1].button("Done", key=f"group_done_{i}"):
                    group_tasks.at[i,"Status"]="Done"
                    group_tasks.to_csv(GROUP_TASKS_FILE, index=False)
                    st.session_state.group_update += 1
                if cols[2].button("Not Done", key=f"group_notdone_{i}"):
                    group_tasks.at[i,"Status"]="Not Done"
                    group_tasks.to_csv(GROUP_TASKS_FILE, index=False)
                    st.session_state.group_update += 1
                if cols[3].button("Delete", key=f"group_delete_{i}"):
                    group_tasks = group_tasks.drop(i).reset_index(drop=True)
                    group_tasks.to_csv(GROUP_TASKS_FILE, index=False)
                    st.session_state.group_update += 1

        # ---------------- Group Chat ----------------
        st.markdown("### 💬 Group Chat")
        chat_msg = st.text_input("Type your message here")
        if st.button("Send Message"):
            if chat_msg.strip():
                group_chat = pd.concat([group_chat, pd.DataFrame([{
                    "Username": username,
                    "Message": chat_msg.strip(),
                    "Time": datetime.now().strftime("%H:%M:%S")
                }])], ignore_index=True)
                group_chat.to_csv(GROUP_CHAT_FILE, index=False)
                st.session_state.group_update += 1
                st.success("✅ Message sent!")

        # Display chat messages
        if not group_chat.empty:
            st.markdown("#### Chat Messages")
            for _, row in group_chat.iterrows():
                st.markdown(f"**{row['Username']} [{row['Time']}]:** {row['Message']}")
