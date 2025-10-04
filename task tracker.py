import streamlit as st
import pandas as pd
import os
import hashlib
import time
from datetime import datetime, date
from glob import glob

# ------------------ UTILITY FUNCTIONS ------------------
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
    if val == "Done":
        return 'background-color: lightgreen'
    elif val == "Pending":
        return 'background-color: yellow'
    elif val == "Not Done":
        return 'background-color: red'

today_date = str(date.today())

# ------------------ SESSION STATE ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "pomo_running" not in st.session_state:
    st.session_state.pomo_running = False

# ------------------ RESET APP BUTTON ------------------
st.sidebar.title("⚙️ App Controls")
if st.sidebar.button("🧹 Reset App / Clear All Data"):
    files_to_delete = glob("tasks_*.csv") + glob("timer_*.csv") + glob("pomo_*.csv") + ["users.csv","groups.csv","group_tasks.csv","group_chat.csv"]
    for f in files_to_delete:
        if os.path.exists(f):
            os.remove(f)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("All data cleared. Please refresh the page.")
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
        if username_input.strip() == "" or password_input.strip() == "":
            st.warning("Please fill both fields.")
        elif username_input in users["Username"].values:
            st.error("Username already exists!")
        else:
            users = pd.concat([users, pd.DataFrame([{
                "Username":username_input.strip(),
                "Password":hash_password(password_input.strip())
            }])], ignore_index=True)
            save_csv(users, users_file)
            st.success("Registered! Now login.")
            
    if choice=="Login" and st.button("Login"):
        if username_input.strip() in users["Username"].values:
            stored_pass = users.loc[users["Username"]==username_input.strip(), "Password"].values[0]
            if stored_pass == hash_password(password_input.strip()):
                st.session_state.logged_in = True
                st.session_state.username = username_input.strip()
                st.success(f"Welcome {st.session_state.username}!")
            else:
                st.error("Wrong password!")
        else:
            st.error("Username not found!")

# ------------------ MAIN APP ------------------
if st.session_state.logged_in:
    username = st.session_state.username
    st.title(f"TaskUni - {username}")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Tasks", "⏳ Timer", "🍅 Pomodoro", "👥 Group Workspace"])
    
    # ------------------ TAB 1: TASKS ------------------
    with tab1:
        st.subheader("Your Tasks")
        TASKS_FILE = f"tasks_{username}.csv"
        tasks = load_or_create_csv(TASKS_FILE, ["Task","Status","Date"])
        
        task_input = st.text_input("Add a new task")
        if st.button("➕ Add Task"):
            if task_input.strip():
                tasks = pd.concat([tasks, pd.DataFrame([{"Task":task_input.strip(), "Status":"Pending", "Date":today_date}])], ignore_index=True)
                save_csv(tasks, TASKS_FILE)
                st.experimental_rerun()

        if not tasks.empty:
            st.dataframe(tasks.style.applymap(color_status, subset=["Status"]), use_container_width=True)
            st.markdown("### Update Task Status")
            for i, row in tasks.iterrows():
                cols = st.columns([4,1,1,1])
                cols[0].write(f"{row['Task']}")
                if cols[1].button("Done", key=f"done_{i}"):
                    tasks.at[i,"Status"]="Done"; save_csv(tasks,TASKS_FILE); st.experimental_rerun()
                if cols[2].button("Not Done", key=f"notdone_{i}"):
                    tasks.at[i,"Status"]="Not Done"; save_csv(tasks,TASKS_FILE); st.experimental_rerun()
                if cols[3].button("Delete", key=f"delete_{i}"):
                    tasks = tasks.drop(i).reset_index(drop=True); save_csv(tasks,TASKS_FILE); st.experimental_rerun()
    
    # ------------------ TAB 2: TIMER ------------------
    with tab2:
        st.subheader("Focus Timer")
        TIMER_FILE = f"timer_{username}.csv"
        timer_data = load_or_create_csv(TIMER_FILE, ["Task","Duration(min)","Date","Start","End"])

        timer_task = st.text_input("Task name for timer")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=180, value=25)
        
        if "timer_start_time" not in st.session_state:
            st.session_state.timer_start_time = None
        
        if st.button("▶ Start Timer"):
            st.session_state.timer_start_time = time.time()
            st.session_state.timer_duration = duration*60
            st.session_state.timer_task = timer_task
            st.session_state.timer_running = True
        
        if st.session_state.timer_running:
            elapsed = time.time() - st.session_state.timer_start_time
            remaining = max(0,int(st.session_state.timer_duration - elapsed))
            mins, secs = divmod(remaining,60)
            st.metric("Time Remaining", f"{mins:02d}:{secs:02d}")
            if remaining <= 0:
                st.success("⏰ Time’s up!")
                new_entry = {"Task":st.session_state.timer_task,"Duration(min)":duration,"Date":today_date,
                             "Start":datetime.fromtimestamp(st.session_state.timer_start_time).strftime("%H:%M:%S"),
                             "End":datetime.now().strftime("%H:%M:%S")}
                timer_data = pd.concat([timer_data,pd.DataFrame([new_entry])], ignore_index=True)
                save_csv(timer_data,TIMER_FILE)
                st.session_state.timer_running = False

        st.markdown("### Logged Sessions")
        st.dataframe(timer_data, use_container_width=True)

    # ------------------ TAB 3: POMODORO ------------------
    with tab3:
        st.subheader("Pomodoro Timer")
        pomo_task = st.text_input("Pomodoro Task", key="pomo_task")
        pomo_duration = st.number_input("Focus Duration (minutes)", 1, 120, 25)
        break_duration = st.number_input("Break Duration (minutes)", 1, 60, 5)
        
        if "pomo_start_time" not in st.session_state:
            st.session_state.pomo_start_time = None
        
        if st.button("▶ Start Pomodoro"):
            st.session_state.pomo_start_time = time.time()
            st.session_state.pomo_duration = pomo_duration*60
            st.session_state.break_duration = break_duration*60
            st.session_state.pomo_running = True
            st.session_state.pomo_task_name = pomo_task
        
        if st.session_state.pomo_running:
            elapsed = time.time() - st.session_state.pomo_start_time
            remaining = max(0, int(st.session_state.pomo_duration - elapsed))
            mins, secs = divmod(remaining, 60)
            st.metric(f"Pomodoro: {st.session_state.pomo_task_name}", f"{mins:02d}:{secs:02d}")
            if remaining <= 0:
                st.success(f"Pomodoro finished! Take a {break_duration} min break.")
                st.session_state.pomo_running = False

    # ------------------ TAB 4: GROUP WORKSPACE ------------------
    with tab4:
        st.subheader("Premium Group Workspace")
        GROUPS_FILE = "groups.csv"
        GROUP_TASKS_FILE = "group_tasks.csv"
        GROUP_CHAT_FILE = "group_chat.csv"
        
        groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Admin","Members"])
        group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
        group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])
        
        # --- Create group ---
        st.markdown("### ➕ Create New Group")
        new_group_name = st.text_input("Group Name")
        new_members_input = st.text_input("Add Members (comma-separated usernames)")
        if st.button("Create Group"):
            if new_group_name.strip():
                members = [username] + [m.strip() for m in new_members_input.split(",") if m.strip() != ""]
                new_group = {"GroupName":new_group_name.strip(),"Admin":username,"Members":",".join(members)}
                groups_df = pd.concat([groups_df,pd.DataFrame([new_group])], ignore_index=True)
                save_csv(groups_df,GROUPS_FILE)
                st.success("Group created!")

        # --- Show user groups ---
        my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]
        if not my_groups.empty:
            st.markdown("### Your Groups")
            selected_group = st.selectbox("Select Group", my_groups["GroupName"])
            
            # Add members to existing group
            st.markdown("#### ➕ Add Member")
            add_member_input = st.text_input("Enter username to add")
            if st.button("Add Member"):
                if add_member_input.strip() and add_member_input.strip() not in groups_df.loc[groups_df["GroupName"]==selected_group,"Members"].values[0]:
                    current = groups_df.loc[groups_df["GroupName"]==selected_group,"Members"].values[0]
                    groups_df.loc[groups_df["GroupName"]==selected_group,"Members"] = current + "," + add_member_input.strip()
                    save_csv(groups_df,GROUPS_FILE)
                    st.success(f"{add_member_input.strip()} added to the group!")

            # --- Group Tasks ---
            st.markdown("#### Group Tasks")
            group_tasks_sel = group_tasks[group_tasks["GroupName"]==selected_group]
            task_input = st.text_input("Add Group Task")
            if st.button("Add Task to Group"):
                if task_input.strip():
                    group_tasks = pd.concat([group_tasks,pd.DataFrame([{
                        "GroupName":selected_group,
                        "Task":task_input.strip(),
                        "Status":"Pending",
                        "AddedBy":username,
                        "Date":today_date
                    }])], ignore_index=True)
                    save_csv(group_tasks,GROUP_TASKS_FILE)
                    st.success("Task added to group!")
            if not group_tasks_sel.empty:
                st.dataframe(group_tasks_sel.style.applymap(color_status, subset=["Status"]), use_container_width=True)

            # --- Group Chat ---
            st.markdown("#### Group Chat (auto-refresh every 5 sec)")
            st_autorefresh = st.experimental_data_editor  # placeholder for auto-refresh later
            chat_input = st.text_input("Enter message", key="group_chat_input")
            if st.button("Send Message"):
                if chat_input.strip():
                    group_chat = pd.concat([group_chat,pd.DataFrame([{
                        "GroupName":selected_group,
                        "Username":username,
                        "Message":chat_input.strip(),
                        "Time":datetime.now().strftime("%H:%M:%S")
                    }])], ignore_index=True)
                    save_csv(group_chat,GROUP_CHAT_FILE)
                    st.success("Message sent!")
            chat_sel = group_chat[group_chat["GroupName"]==selected_group]
            for _,row in chat_sel.iterrows():
                st.write(f"[{row['Time']}] **{row['Username']}**: {row['Message']}")
