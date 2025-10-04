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
            st.dataframe(tasks.style.applymap(color_status, subset=["Status"]), use_container_width=True)
            st.markdown("### Update Task Status")
            for i,row in tasks.iterrows():
                cols = st.columns([4,1,1,1])
                cols[0].write(f"{row['Task']}")
                if cols[1].button("Done", key=f"done_{i}"): tasks.at[i,"Status"]="Done"; save_csv(tasks,TASKS_FILE)
                if cols[2].button("Not Done", key=f"notdone_{i}"): tasks.at[i,"Status"]="Not Done"; save_csv(tasks,TASKS_FILE)
                if cols[3].button("Delete", key=f"delete_{i}"): tasks = tasks.drop(i).reset_index(drop=True); save_csv(tasks,TASKS_FILE)

    # ------------------ TAB 2: TIMER ------------------
    with tab2:
        st.subheader("Focus Timer")
        TIMER_FILE = f"timer_{username}.csv"
        timer_data = load_or_create_csv(TIMER_FILE, ["Task","Duration(min)","Date","Start","End"])

        timer_task = st.text_input("Task name for timer", key="timer_task")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=180, value=25)
        
        st_autorefresh(interval=1000, key="timer_refresh")  # real-time refresh

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
            new_entry={"Task":timer_task,"Duration(min)":round(elapsed/60,1),"Date":today_date,
                       "Start":datetime.fromtimestamp(st.session_state.timer_start_time).strftime("%H:%M:%S") if st.session_state.timer_start_time else "",
                       "End":datetime.now().strftime("%H:%M:%S")}
            timer_data = pd.concat([timer_data,pd.DataFrame([new_entry])], ignore_index=True)
            save_csv(timer_data,TIMER_FILE)
            st.session_state.timer_elapsed=0
            st.session_state.timer_start_time=None

        # --- Display metrics ---
        total_focus = round(timer_data["Duration(min)"].sum(), 2) if not timer_data.empty else 0
        st.metric("Total Focused Time (min)", total_focus)
        st.markdown("### Session History")
        st.dataframe(timer_data, use_container_width=True)

    # ------------------ TAB 3: POMODORO ------------------
    with tab3:
        st.subheader("Pomodoro Timer")
        POMO_FILE = f"pomo_{username}.csv"
        pomo_data = load_or_create_csv(POMO_FILE, ["Task","Duration(min)","Date","Start","End"])

        pomo_task = st.text_input("Pomodoro Task", key="pomo_task")
        pomo_duration = st.number_input("Focus Duration (minutes)", 1, 120, 25)
        break_duration = st.number_input("Break Duration (minutes)", 1, 60, 5)
        
        st_autorefresh(interval=1000, key="pomo_refresh")  # real-time refresh

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
            elapsed = st.session_state.pomo_elapsed + (time.time() - st.session_state.pomo_start_time if st.session_state.pomo_start_time else 0)
            new_entry={"Task":pomo_task,"Duration(min)":round(elapsed/60,1),"Date":today_date,
                       "Start":datetime.fromtimestamp(st.session_state.pomo_start_time).strftime("%H:%M:%S") if st.session_state.pomo_start_time else "",
                       "End":datetime.now().strftime("%H:%M:%S")}
            pomo_data = pd.concat([pomo_data,pd.DataFrame([new_entry])], ignore_index=True)
            save_csv(pomo_data,POMO_FILE)
            st.session_state.pomo_elapsed=0
            st.session_state.pomo_start_time=None

        # --- Display metrics ---
        total_focus = round(pomo_data["Duration(min)"].sum(), 2) if not pomo_data.empty else 0
        num_pomos = len(pomo_data)
        st.metric("Total Focused Time (min)", total_focus)
        st.metric("Total Pomodoros Completed", num_pomos)
        st.markdown("### Session History")
        st.dataframe(pomo_data, use_container_width=True)

    # ------------------ TAB 4: GROUP WORKSPACE ------------------
    with tab4:
        st.subheader("👥 Group Workspace")
        GROUPS_FILE="groups.csv"
        GROUP_TASKS_FILE="group_tasks.csv"
        GROUP_CHAT_FILE="group_chat.csv"

        groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Members"])
        group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
        group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])

        st.markdown("### 🏷️ Your Groups")
        my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]

        # Display group buttons
        for _,grp in my_groups.iterrows():
            if st.button(grp["GroupName"], key=f"group_btn_{grp['GroupName']}"):
                st.session_state.active_group = grp["GroupName"]

        if st.session_state.active_group:
            sel_group = st.session_state.active_group
            st.markdown(f"## Selected Group: **{sel_group}**")
            
            # Two-column layout
            col_tasks, col_chat = st.columns([2,3])

            with col_tasks:
                st.markdown("#### 📋 Group Tasks")
                task_input_grp = st.text_input("Add Task to Group", key="grp_task_input")
                if st.button("Add Task", key="add_grp_task"):
                    if task_input_grp.strip():
                        new_task={"GroupName":sel_group,"Task":task_input_grp.strip(),
                                  "Status":"Pending","AddedBy":username,"Date":today_date}
                        group_tasks=pd.concat([group_tasks,pd.DataFrame([new_task])],ignore_index=True)
                        save_csv(group_tasks,GROUP_TASKS_FILE)
                        st.session_state["grp_task_input"] = ""  # clear input

                grp_tasks_sel = group_tasks[group_tasks["GroupName"]==sel_group]
                if not grp_tasks_sel.empty:
                    for i,row in grp_tasks_sel.iterrows():
                        st.markdown(f"<div style='padding:6px;margin-bottom:4px;border-radius:6px;"
                                    f"background-color:{'lightgreen' if row['Status']=='Done' else 'yellow' if row['Status']=='Pending' else 'red'}'>"
                                    f"**{row['Task']}** (added by {row['AddedBy']})</div>", unsafe_allow_html=True)
                        cols = st.columns([3,1,1,1])
                        if cols[0].button("Done", key=f"grp_done_{i}"): group_tasks.at[i,"Status"]="Done"; save_csv(group_tasks,GROUP_TASKS_FILE)
                        if cols[1].button("Not Done", key=f"grp_notdone_{i}"): group_tasks.at[i,"Status"]="Not Done"; save_csv(group_tasks,GROUP_TASKS_FILE)
                        if cols[2].button("Delete", key=f"grp_delete_{i}"): group_tasks = group_tasks.drop(i).reset_index(drop=True); save_csv(group_tasks,GROUP_TASKS_FILE)

            with col_chat:
                st.markdown("#### 💬 Group Chat")
                chat_input = st.text_input("Message", key="grp_chat_input")
                if st.button("Send", key="grp_send_chat"):
                    if chat_input.strip():
                        new_msg={"GroupName":sel_group,"Username":username,"Message":chat_input.strip(),
                                 "Time":datetime.now().strftime("%H:%M:%S")}
                        group_chat=pd.concat([group_chat,pd.DataFrame([new_msg])], ignore_index=True)
                        save_csv(group_chat,GROUP_CHAT_FILE)
                        st.session_state["grp_chat_input"] = ""  # clear input

                st_autorefresh(interval=5000, key="grp_chat_refresh")
                chat_sel = group_chat[group_chat["GroupName"]==sel_group]
                for _,row in chat_sel.iterrows():
                    st.markdown(f"[{row['Time']}] *{row['Username']}*: {row['Message']}")
