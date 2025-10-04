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

today_date = str(date.today())

# ------------------ SESSION STATE DEFAULTS ------------------
for key in ["logged_in","username","task_updated","timer_running","timer_paused",
            "timer_start_time","timer_elapsed","timer_duration","timer_task_name",
            "pomo_running","pomo_paused","pomo_start_time","pomo_elapsed",
            "pomo_duration","pomo_task_name","active_group"]:
    if key not in st.session_state:
        st.session_state[key] = False if "running" in key or "paused" in key else None

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
            st.dataframe(tasks, use_container_width=True)
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
        if col1.button("▶ Start Timer"):
            st.session_state.timer_start_time = time.time()
            st.session_state.timer_duration = duration*60
            st.session_state.timer_task_name = timer_task
            st.session_state.timer_running=True
            st.session_state.timer_paused=False
            st.session_state.timer_elapsed=0

        if col2.button("⏸ Pause Timer") and st.session_state.timer_running:
            st.session_state.timer_paused=True
            st.session_state.timer_elapsed += time.time() - st.session_state.timer_start_time

        if col2.button("▶ Resume Timer") and st.session_state.timer_running and st.session_state.timer_paused:
            st.session_state.timer_paused=False
            st.session_state.timer_start_time = time.time()

        if col3.button("⏹ Stop Timer") and st.session_state.timer_running:
            st.session_state.timer_running=False
            elapsed = st.session_state.timer_elapsed + (time.time() - st.session_state.timer_start_time if st.session_state.timer_start_time else 0)
            new_entry={"Task":timer_task,"Duration(min)":round(elapsed/60,1),"Date":today_date}
            timer_data = pd.concat([timer_data,pd.DataFrame([new_entry])], ignore_index=True)
            save_csv(timer_data,TIMER_FILE)
            st.session_state.timer_elapsed=0
            st.session_state.timer_start_time=None

        if st.session_state.timer_running:
            elapsed = st.session_state.timer_elapsed + (0 if st.session_state.timer_paused else time.time() - st.session_state.timer_start_time)
            remaining = max(0, st.session_state.timer_duration - elapsed)
            mins, secs = divmod(int(remaining), 60)
            st.metric("Time Remaining", f"{mins:02d}:{secs:02d}")
            if remaining <= 0:
                st.success("⏰ Time’s up!")
                st.session_state.timer_running=False

        total_focus = round(timer_data["Duration(min)"].sum(),2) if not timer_data.empty else 0
        st.metric("Total Focused Time (min)", total_focus)
        st.markdown("### Session History")
        st.dataframe(timer_data, use_container_width=True)

    # ------------------ TAB 3: POMODORO ------------------
    with tab3:
        st.subheader("Pomodoro Timer")
        POMO_FILE = f"pomo_{username}.csv"
        pomo_data = load_or_create_csv(POMO_FILE, ["Task","Duration(min)","Date"])

        pomo_task = st.text_input("Pomodoro Task", key="pomo_task")
        pomo_duration = st.number_input("Focus Duration (minutes)", 1, 120, 25)
        break_duration = st.number_input("Break Duration (minutes)", 1, 60, 5)
        
        st_autorefresh(interval=1000, key="pomo_refresh")

        col1, col2, col3 = st.columns(3)
        if col1.button("▶ Start Pomodoro"):
            st.session_state.pomo_start_time = time.time()
            st.session_state.pomo_duration = pomo_duration*60
            st.session_state.pomo_task_name = pomo_task
            st.session_state.pomo_running=True
            st.session_state.pomo_paused=False
            st.session_state.pomo_elapsed=0

        if col2.button("⏸ Pause Pomodoro") and st.session_state.pomo_running:
            st.session_state.pomo_paused=True
            st.session_state.pomo_elapsed += time.time() - st.session_state.pomo_start_time

        if col2.button("▶ Resume Pomodoro") and st.session_state.pomo_running and st.session_state.pomo_paused:
            st.session_state.pomo_paused=False
            st.session_state.pomo_start_time = time.time()

        if col3.button("⏹ Stop Pomodoro") and st.session_state.pomo_running:
            st.session_state.pomo_running=False
            elapsed = st.session_state.pomo_elapsed + (0 if st.session_state.pomo_start_time is None else time.time() - st.session_state.pomo_start_time)
            new_entry={"Task":pomo_task,"Duration(min)":round(elapsed/60,1),"Date":today_date}
            pomo_data = pd.concat([pomo_data,pd.DataFrame([new_entry])], ignore_index=True)
            save_csv(pomo_data,POMO_FILE)
            st.session_state.pomo_elapsed=0
            st.session_state.pomo_start_time=None

        if st.session_state.pomo_running:
            elapsed = st.session_state.pomo_elapsed + (0 if st.session_state.pomo_paused else time.time() - st.session_state.pomo_start_time)
            remaining = max(0, st.session_state.pomo_duration - elapsed)
            mins, secs = divmod(int(remaining), 60)
            st.metric("Pomodoro Remaining", f"{mins:02d}:{secs:02d}")
            if remaining<=0:
                st.success("🍅 Pomodoro finished! Take a break.")
                st.session_state.pomo_running=False

        total_focus = round(pomo_data["Duration(min)"].sum(),2) if not pomo_data.empty else 0
        st.metric("Total Focused Time (min)", total_focus)
        st.metric("Number of Pomodoros", len(pomo_data))
        st.markdown("### Pomodoro History")
        st.dataframe(pomo_data, use_container_width=True)

    # ------------------ TAB 4: GROUP WORKSPACE ------------------
    with tab4:
        st.subheader("Group Workspace")
        GROUPS_FILE="groups.csv"
        GROUP_TASKS_FILE="group_tasks.csv"
        GROUP_CHAT_FILE="group_chat.csv"

        groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Members"])
        group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
        group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])

        # ---- Create / Add Group ----
        st.markdown("### Create Group / Invite Member")
        new_group_name = st.text_input("Group Name", key="grp_name")
        new_member = st.text_input("Add Member by username", key="grp_add_member")
        if st.button("Create / Add"):
            if new_group_name.strip():
                # Create group if doesn't exist
                if not (groups_df["GroupName"]==new_group_name.strip()).any():
                    groups_df=pd.concat([groups_df,pd.DataFrame([{"GroupName":new_group_name.strip(),
                                                                  "Members":username}])], ignore_index=True)
                    save_csv(groups_df,GROUPS_FILE)
                    st.success(f"Group '{new_group_name.strip()}' created!")
                # Add member
                if new_member.strip() and new_member!=username:
                    idx = groups_df[groups_df["GroupName"]==new_group_name.strip()].index[0]
                    current_members = groups_df.at[idx,"Members"].split(",")
                    if new_member.strip() not in current_members:
                        current_members.append(new_member.strip())
                        groups_df.at[idx,"Members"] = ",".join(current_members)
                        save_csv(groups_df,GROUPS_FILE)
                        st.success(f"{new_member.strip()} added to '{new_group_name.strip()}'!")

        # ---- Show User's Groups as Buttons ----
        import hashlib
        st.markdown("### 🏷️ Your Groups")
        my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]
        for idx, grp in my_groups.iterrows():
            key_hash = hashlib.md5(grp["GroupName"].encode()).hexdigest()
            if st.button(grp["GroupName"], key=f"group_btn_{key_hash}"):
                st.session_state.active_group = grp["GroupName"]

        # ---- Active Group Details ----
        if st.session_state.active_group:
            sel_group = st.session_state.active_group
            st.markdown(f"### Group: {sel_group}")

            # Tasks (stacked, no color/status update)
            grp_tasks_sel = group_tasks[group_tasks["GroupName"]==sel_group]
            if not grp_tasks_sel.empty:
                st.markdown("#### Tasks")
                for _, row in grp_tasks_sel.iterrows():
                    st.write(f"- {row['Task']} (added by {row['AddedBy']})")

            # Add task to group
            task_input_grp = st.text_input("Add Task to Group", key="grp_task_input")
            if st.button("Add Task to Group", key="add_grp_task"):
                if task_input_grp.strip():
                    new_task={"GroupName":sel_group,"Task":task_input_grp.strip(),
                              "Status":"Pending","AddedBy":username,"Date":today_date}
                    group_tasks=pd.concat([group_tasks,pd.DataFrame([new_task])],ignore_index=True)
                    save_csv(group_tasks,GROUP_TASKS_FILE)
                    st.experimental_rerun()

            # Chat
            st.markdown("#### Group Chat")
            chat_input = st.text_input("Message", key="grp_chat_input")
            if st.button("Send Message"):
                if chat_input.strip():
                    new_msg={"GroupName":sel_group,"Username":username,"Message":chat_input.strip(),
                             "Time":datetime.now().strftime("%H:%M:%S")}
                    group_chat=pd.concat([group_chat,pd.DataFrame([new_msg])], ignore_index=True)
                    save_csv(group_chat,GROUP_CHAT_FILE)
                    st.session_state["grp_chat_input"] = ""
                    st.experimental_rerun()

            st_autorefresh(interval=5000, key="grp_chat_refresh")
            chat_sel = group_chat[group_chat["GroupName"]==sel_group]
            for _,row in chat_sel.iterrows():
                st.markdown(f"[{row['Time']}] *{row['Username']}*: {row['Message']}")
