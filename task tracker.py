import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, date
from fpdf import FPDF
from streamlit_autorefresh import st_autorefresh

# ------------------ Utility Functions ------------------
def load_or_create_csv(file, columns):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)

def save_csv(df, file):
    df.to_csv(file, index=False)

today_date = str(date.today())

# ------------------ Authentication ------------------
USERS_FILE = "users.csv"
users_df = load_or_create_csv(USERS_FILE, ["Username", "Password"])

st.title("🔑 TaskUni Login / Register")

auth_choice = st.radio("Choose action", ["Login", "Register"])

username = st.text_input("Username", key="auth_username")
password = st.text_input("Password", type="password", key="auth_password")

if auth_choice == "Register":
    if st.button("Register"):
        if username.strip() and password.strip():
            if username in users_df["Username"].values:
                st.error("Username already exists!")
            else:
                users_df = pd.concat([users_df, pd.DataFrame([{"Username": username, "Password": password}])], ignore_index=True)
                save_csv(users_df, USERS_FILE)
                st.success("Registered successfully! Please login.")
        else:
            st.warning("Enter valid username and password.")

if auth_choice == "Login":
    if st.button("Login"):
        if username in users_df["Username"].values and users_df.loc[users_df["Username"]==username, "Password"].values[0] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
        else:
            st.error("Invalid username or password.")

if not st.session_state.get("logged_in", False):
    st.stop()

username = st.session_state["username"]

# ------------------ Tabs ------------------
tab1, tab2, tab3, tab4 = st.tabs(["📋 Tasks", "⏳ Timer", "🍅 Pomodoro", "👥 Group Workspace"])

# ------------------ Personal Tasks ------------------
TASKS_FILE = f"tasks_{username}.csv"
tasks_df = load_or_create_csv(TASKS_FILE, ["Task", "Status", "Date"])

with tab1:
    st.subheader(f"📋 {username}'s Tasks")

    # Add Task
    new_task = st.text_input("Add Task", key="task_input")
    if st.button("➕ Add Task"):
        if new_task.strip():
            tasks_df = pd.concat([tasks_df, pd.DataFrame([{"Task": new_task.strip(), "Status": "Pending", "Date": today_date}])], ignore_index=True)
            save_csv(tasks_df, TASKS_FILE)
            st.success("Task added!")

    # Show Task Report (colored)
    if not tasks_df.empty:
        st.markdown("### Task Status")
        status_colors = {"Pending": "yellow", "Done": "green", "Not Done": "red"}
        tasks_df_display = tasks_df.copy()
        tasks_df_display["Status"] = tasks_df_display["Status"].apply(lambda x: f"{x}")
        st.dataframe(tasks_df_display.style.applymap(lambda x: f"background-color: {status_colors.get(x,'white')}", subset=["Status"]))

        # Buttons to update status or delete
        for i, row in tasks_df.iterrows():
            cols = st.columns([3,1,1,1])
            cols[0].write(f"{row['Task']} ({row['Date']})")
            if cols[1].button("Done", key=f"done_{i}"): tasks_df.at[i, "Status"] = "Done"; save_csv(tasks_df, TASKS_FILE)
            if cols[2].button("Not Done", key=f"notdone_{i}"): tasks_df.at[i, "Status"] = "Not Done"; save_csv(tasks_df, TASKS_FILE)
            if cols[3].button("Delete", key=f"delete_{i}"): tasks_df = tasks_df.drop(i).reset_index(drop=True); save_csv(tasks_df, TASKS_FILE)

# ------------------ Timer ------------------
TIMER_FILE = f"timer_{username}.csv"
timer_df = load_or_create_csv(TIMER_FILE, ["Task", "Duration(min)", "Date", "Start", "End"])

with tab2:
    st.subheader("⏳ Focus Timer")

    timer_task = st.text_input("Task Name", key="timer_task")
    timer_duration = st.number_input("Duration (minutes)", min_value=1, max_value=180, value=25)

    if "timer_running" not in st.session_state:
        st.session_state["timer_running"] = False
        st.session_state["timer_start_time"] = 0
        st.session_state["timer_elapsed"] = 0

    start, pause, stop = st.columns(3)
    if start.button("▶ Start"):
        st.session_state["timer_running"] = True
        st.session_state["timer_start_time"] = time.time()
    if pause.button("⏸ Pause"):
        if st.session_state["timer_running"]:
            st.session_state["timer_elapsed"] += time.time() - st.session_state["timer_start_time"]
            st.session_state["timer_running"] = False
    if stop.button("⏹ Stop"):
        if st.session_state["timer_running"]:
            st.session_state["timer_elapsed"] += time.time() - st.session_state["timer_start_time"]
        if timer_task.strip():
            new_entry = {
                "Task": timer_task,
                "Duration(min)": int(st.session_state["timer_elapsed"] // 60),
                "Date": today_date,
                "Start": datetime.fromtimestamp(st.session_state["timer_start_time"]).strftime("%H:%M:%S"),
                "End": datetime.now().strftime("%H:%M:%S")
            }
            timer_df = pd.concat([timer_df, pd.DataFrame([new_entry])], ignore_index=True)
            save_csv(timer_df, TIMER_FILE)
        st.session_state["timer_running"] = False
        st.session_state["timer_elapsed"] = 0

    # Show timer
    if st.session_state["timer_running"]:
        elapsed = time.time() - st.session_state["timer_start_time"] + st.session_state["timer_elapsed"]
    else:
        elapsed = st.session_state["timer_elapsed"]
    mins, secs = divmod(int(elapsed), 60)
    st.metric("Time Elapsed", f"{mins:02d}:{secs:02d}")

    # Show today's timer history
    st.markdown("### Timer History Today")
    today_timer = timer_df[timer_df["Date"]==today_date]
    st.dataframe(today_timer, use_container_width=True)

# ------------------ Pomodoro ------------------
POMO_FILE = f"pomo_{username}.csv"
pomo_df = load_or_create_csv(POMO_FILE, ["Task", "Duration(min)", "Break(min)", "Date", "Start", "End"])

with tab3:
    st.subheader("🍅 Pomodoro Timer")

    pomo_task = st.text_input("Pomodoro Task", key="pomo_task")
    pomo_duration = st.number_input("Focus Duration (minutes)", min_value=1, max_value=120, value=25)
    break_duration = st.number_input("Break Duration (minutes)", min_value=1, max_value=60, value=5)

    if "pomo_running" not in st.session_state:
        st.session_state["pomo_running"] = False
        st.session_state["pomo_start"] = 0
        st.session_state["pomo_elapsed"] = 0

    start, pause, stop = st.columns(3)
    if start.button("▶ Start Pomodoro"):
        st.session_state["pomo_running"] = True
        st.session_state["pomo_start"] = time.time()
    if pause.button("⏸ Pause"):
        if st.session_state["pomo_running"]:
            st.session_state["pomo_elapsed"] += time.time() - st.session_state["pomo_start"]
            st.session_state["pomo_running"] = False
    if stop.button("⏹ Stop"):
        if st.session_state["pomo_running"]:
            st.session_state["pomo_elapsed"] += time.time() - st.session_state["pomo_start"]
        if pomo_task.strip():
            new_entry = {
                "Task": pomo_task,
                "Duration(min)": int(st.session_state["pomo_elapsed"] // 60),
                "Break(min)": break_duration,
                "Date": today_date,
                "Start": datetime.fromtimestamp(st.session_state["pomo_start"]).strftime("%H:%M:%S"),
                "End": datetime.now().strftime("%H:%M:%S")
            }
            pomo_df = pd.concat([pomo_df, pd.DataFrame([new_entry])], ignore_index=True)
            save_csv(pomo_df, POMO_FILE)
        st.session_state["pomo_running"] = False
        st.session_state["pomo_elapsed"] = 0

    # Show pomodoro timer
    if st.session_state["pomo_running"]:
        elapsed = time.time() - st.session_state["pomo_start"] + st.session_state["pomo_elapsed"]
    else:
        elapsed = st.session_state["pomo_elapsed"]
    mins, secs = divmod(int(elapsed), 60)
    st.metric("Pomodoro Elapsed", f"{mins:02d}:{secs:02d}")

    # Show today's pomodoro history
    st.markdown("### Pomodoro History Today")
    today_pomo = pomo_df[pomo_df["Date"]==today_date]
    st.dataframe(today_pomo, use_container_width=True)

# ------------------ Group Workspace ------------------
GROUPS_FILE = "groups.csv"
GROUP_TASKS_FILE = "group_tasks.csv"
GROUP_CHAT_FILE = "group_chat.csv"
groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName", "Members"])
group_tasks_df = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
group_chat_df = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])

with tab4:
    st.subheader("👥 Group Workspace")
    create_group = st.button("➕ Create New Group")
    if create_group:
        group_name = st.text_input("Enter Group Name", key="new_group_name")
        if group_name.strip():
            members_input = st.text_input("Add Members (username one by one, comma separated)", key="group_members")
            if st.button("✅ Create Group"):
                members = [m.strip() for m in members_input.split(",") if m.strip()]
                valid_members = []
                for m in members:
                    if m in users_df["Username"].values:
                        valid_members.append(m)
                    else:
                        st.warning(f"User {m} does not exist!")
                all_members = [username] + valid_members
                groups_df = pd.concat([groups_df, pd.DataFrame([{"GroupName": group_name, "Members": ",".join(all_members)}])], ignore_index=True)
                save_csv(groups_df, GROUPS_FILE)
                st.success(f"Group '{group_name}' created with members: {', '.join(all_members)}")

    # Show groups the user is in
    my_groups = groups_df[groups_df["Members"].str.contains(username)]
    for _, grp in my_groups.iterrows():
        group_key = grp["GroupName"].replace(" ","_")
        st.markdown(f"### **{grp['GroupName']}**")
        # Tasks in group
        group_tasks_sel = group_tasks_df[group_tasks_df["GroupName"]==grp["GroupName"]]
        task_input = st.text_input("Add Task", key=f"task_input_{group_key}")
        if st.button("Add Task", key=f"add_task_{group_key}"):
            if task_input.strip():
                group_tasks_df = pd.concat([group_tasks_df, pd.DataFrame([{"GroupName": grp["GroupName"], "Task": task_input.strip(), "Status": "Pending", "AddedBy": username, "Date": today_date}])], ignore_index=True)
                save_csv(group_tasks_df, GROUP_TASKS_FILE)
                st.success("Task added!")

        # Task table
        if not group_tasks_sel.empty:
            st.dataframe(group_tasks_sel[["Task","AddedBy","Status"]], use_container_width=True)

        # Chat
        st.markdown("#### Chat")
        chat_input = st.text_input("Enter message", key=f"chat_input_{group_key}")
        if st.button("Send", key=f"send_chat_{group_key}"):
            if chat_input.strip():
                group_chat_df = pd.concat([group_chat_df, pd.DataFrame([{"GroupName": grp["GroupName"], "Username": username, "Message": chat_input.strip(), "Time": datetime.now().strftime('%H:%M:%S')}])], ignore_index=True)
                save_csv(group_chat_df, GROUP_CHAT_FILE)
                st.success("Message sent!")
        group_chat_sel = group_chat_df[group_chat_df["GroupName"]==grp["GroupName"]]
        for _, row in group_chat_sel.iterrows():
            st.write(f"[{row['Time']}] **{row['Username']}**: {row['Message']}")

# ------------------ Auto Refresh every 1 sec ------------------
st_autorefresh(interval=1000, key="refresh")
