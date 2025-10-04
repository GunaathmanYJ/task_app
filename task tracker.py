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
    h, m, s = [int(x[:-1]) for x in hms_str.split()]
    return h*3600 + m*60 + s

today_date = str(date.today())

# ------------------ SESSION STATE DEFAULTS ------------------
for key in ["logged_in","username","timer_data","pomo_sessions",
            "timer_running","timer_paused","timer_start_time","timer_elapsed","timer_duration","timer_task_name",
            "pomo_running","pomo_paused","pomo_start_time","pomo_elapsed","pomo_duration","pomo_task_name",
            "countdown_running","countdown_total_seconds","countdown_start_time","countdown_task_name",
            "show_create_group","selected_group","selected_tab"]:
    if key not in st.session_state:
        if key in ["timer_running","timer_paused","pomo_running","pomo_paused","countdown_running","show_create_group"]:
            st.session_state[key] = False
        elif key=="timer_data":
            st.session_state[key] = pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS"])
        elif key=="pomo_sessions":
            st.session_state[key] = 0
        elif key=="selected_tab":
            st.session_state[key] = 0
        else:
            st.session_state[key] = None

# ------------------ LOGIN / REGISTER ------------------
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.title("🔐 TaskUni Login / Register")
    users_file = "users.csv"
    users = load_or_create_csv(users_file, ["Username","Password"])

    choice = st.radio("Login or Register", ["Login","Register"])
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")

    if choice=="Register" and st.button("Register"):
        if username_input.strip()=="" or password_input.strip()=="":
            st.warning("Fill both fields")
        elif username_input in users["Username"].values:
            st.error("Username exists!")
        else:
            users = pd.concat([users, pd.DataFrame([{
                "Username":username_input.strip(),
                "Password":hash_password(password_input.strip())
            }])], ignore_index=True)
            save_csv(users, users_file)
            st.success("Registered! Login now.")

    if choice=="Login" and st.button("Login"):
        if username_input.strip() in users["Username"].values:
            stored_pass = users.loc[users["Username"]==username_input.strip(),"Password"].values[0]
            if stored_pass==hash_password(password_input.strip()):
                st.session_state.logged_in = True
                st.session_state.username = username_input.strip()
            else:
                st.error("Wrong password!")
        else:
            st.error("Username not found!")

# ------------------ MAIN APP ------------------
if st.session_state.logged_in:
    username = st.session_state.username
    st.title(f"TaskUni - {username}")

    if os.path.exists("taskuni.png"):
        st.sidebar.image("taskuni.png", use_container_width=True)

    # Tab selection preservation
    tabs = ["📋 Tasks","⏳ Timer","🍅 Pomodoro","👥 Group Workspace"]
    st.session_state.selected_tab = st.tabs(tabs, index=st.session_state.selected_tab)[0] if "selected_tab" not in st.session_state else st.session_state.selected_tab
    tab1, tab2, tab3, tab4 = st.tabs(tabs)

    # ------------------ TAB 1: TASKS ------------------
    with tab1:
        st.session_state.selected_tab = 0
        st.subheader("Your Tasks")
        TASKS_FILE = f"tasks_{username}.csv"
        tasks = load_or_create_csv(TASKS_FILE, ["Task","Status","Date"])

        task_input = st.text_input("Add a new task", key="task_input")
        if st.button("➕ Add Task"):
            if task_input.strip():
                tasks = pd.concat([tasks, pd.DataFrame([{
                    "Task":task_input.strip(),
                    "Status":"Pending",
                    "Date":today_date
                }])], ignore_index=True)
                save_csv(tasks,TASKS_FILE)

        if not tasks.empty:
            st.dataframe(tasks.style.applymap(color_status, subset=["Status"]), use_container_width=True)
            st.markdown("### Update Task Status")
            for i,row in tasks.iterrows():
                cols = st.columns([4,1,1,1])
                cols[0].write(f"{row['Task']}")
                if cols[1].button("Done", key=f"done_{i}"):
                    tasks.at[i,"Status"]="Done"
                    save_csv(tasks,TASKS_FILE)
                if cols[2].button("Not Done", key=f"notdone_{i}"):
                    tasks.at[i,"Status"]="Not Done"
                    save_csv(tasks,TASKS_FILE)
                if cols[3].button("Delete", key=f"delete_{i}"):
                    tasks = tasks.drop(i).reset_index(drop=True)
                    save_csv(tasks,TASKS_FILE)

    # ------------------ TAB 2: TIMER ------------------
    with tab2:
        st.session_state.selected_tab = 1
        # Timer code (unchanged) ...

    # ------------------ TAB 3: POMODORO ------------------
    with tab3:
        st.session_state.selected_tab = 2
        # Pomodoro code (unchanged) ...

    # ------------------ TAB 4: GROUP WORKSPACE ------------------
    with tab4:
        st.session_state.selected_tab = 3
        st.subheader("👥 Group Workspace")
        GROUPS_FILE="groups.csv"
        GROUP_TASKS_FILE="group_tasks.csv"
        GROUP_CHAT_FILE="group_chat.csv"

        # Reload groups dynamically to get latest memberships
        groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Members"])
        group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
        group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])

        # --- CREATE GROUP ---
        with st.expander("➕ Create New Group"):
            new_group_name = st.text_input("Group Name", key="new_group_name")
            if st.button("Create Group"):
                if new_group_name.strip():
                    if new_group_name in groups_df["GroupName"].values:
                        st.error("Group already exists!")
                    else:
                        groups_df = pd.concat([groups_df, pd.DataFrame([{
                            "GroupName": new_group_name.strip(),
                            "Members": username
                        }])], ignore_index=True)
                        save_csv(groups_df, GROUPS_FILE)
                        st.success(f"Group '{new_group_name.strip()}' created!")
                        st.experimental_rerun()  # Immediately reload to reflect new group

        # Reload user's groups dynamically
        my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]

        # Group selection buttons
        for idx, grp in my_groups.iterrows():
            if st.button(grp["GroupName"], key=f"group_btn_{grp['GroupName']}"):
                st.session_state.selected_group = grp["GroupName"]
                st.experimental_rerun()  # Reload tab without switching

        if st.session_state.selected_group:
            selected_group = st.session_state.selected_group
            # Group tasks, add member, chat code (unchanged) ...
