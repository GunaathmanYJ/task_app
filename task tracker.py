import streamlit as st
import pandas as pd
import os
import hashlib
import time
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# ------------------ UTILITIES ------------------
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
defaults = ["logged_in","username","task_updated",
            "timer_running","timer_paused","timer_start_time","timer_elapsed","timer_duration","timer_task_name",
            "pomo_running","pomo_paused","pomo_start_time","pomo_elapsed","pomo_duration","pomo_task_name",
            "creating_group","new_group_name","add_member_name"]
for key in defaults:
    if key not in st.session_state:
        st.session_state[key] = False if "running" in key or "paused" in key or key=="creating_group" else None

# ------------------ RESET APP ------------------
st.sidebar.title("⚙️ App Controls")
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
                st.experimental_rerun()

        if not tasks.empty:
            st.dataframe(tasks.style.applymap(color_status, subset=["Status"]), use_container_width=True)
            st.markdown("### Update Task Status")
            for i,row in tasks.iterrows():
                cols = st.columns([4,1,1,1])
                cols[0].write(f"{row['Task']}")
                if cols[1].button("Done", key=f"done_{i}"): tasks.at[i,"Status"]="Done"; save_csv(tasks,TASKS_FILE); st.experimental_rerun()
                if cols[2].button("Not Done", key=f"notdone_{i}"): tasks.at[i,"Status"]="Not Done"; save_csv(tasks,TASKS_FILE); st.experimental_rerun()
                if cols[3].button("Delete", key=f"delete_{i}"): tasks = tasks.drop(i).reset_index(drop=True); save_csv(tasks,TASKS_FILE); st.experimental_rerun()

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

        if st.session_state.timer_running:
            if st.session_state.timer_paused:
                remaining = st.session_state.timer_duration - st.session_state.timer_elapsed
            else:
                elapsed = (time.time() - st.session_state.timer_start_time) + st.session_state.timer_elapsed
                remaining = max(0, st.session_state.timer_duration - elapsed)
            mins, secs = divmod(int(remaining), 60)
            st.metric("Time Remaining", f"{mins:02d}:{secs:02d}")
            if remaining<=0:
                st.success("⏰ Time’s up!")
                st.session_state.timer_running=False

        st.markdown("### Today's Timer History")
        today_timer = timer_data[timer_data["Date"]==today_date]
        if not today_timer.empty:
            st.dataframe(today_timer, use_container_width=True)

    # ------------------ TAB 3: POMODORO ------------------
    with tab3:
        st.subheader("Pomodoro Timer")
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
            elapsed = st.session_state.pomo_elapsed + (time.time() - st.session_state.pomo_start_time if st.session_state.pomo_start_time else 0)
            pomo_file = f"pomo_{username}.csv"
            pomo_data = load_or_create_csv(pomo_file, ["Task","Duration(min)","Date","Start","End"])
            new_entry={"Task":pomo_task,"Duration(min)":round(elapsed/60,1),"Date":today_date,
                       "Start":datetime.fromtimestamp(st.session_state.pomo_start_time).strftime("%H:%M:%S") if st.session_state.pomo_start_time else "",
                       "End":datetime.now().strftime("%H:%M:%S")}
            pomo_data = pd.concat([pomo_data,pd.DataFrame([new_entry])], ignore_index=True)
            save_csv(pomo_data,pomo_file)
            st.session_state.pomo_elapsed=0
            st.session_state.pomo_start_time=None

        if st.session_state.pomo_running:
            if st.session_state.pomo_paused:
                remaining = st.session_state.pomo_duration - st.session_state.pomo_elapsed
            else:
                elapsed = (time.time() - st.session_state.pomo_start_time) + st.session_state.pomo_elapsed
                remaining = max(0, st.session_state.pomo_duration - elapsed)
            mins, secs = divmod(int(remaining), 60)
            st.metric("Pomodoro Remaining", f"{mins:02d}:{secs:02d}")
            if remaining<=0:
                st.success("🍅 Pomodoro finished! Take a break.")
                st.session_state.pomo_running=False

        st.markdown("### Today's Pomodoro History")
        pomo_file = f"pomo_{username}.csv"
        pomo_data = load_or_create_csv(pomo_file, ["Task","Duration(min)","Date","Start","End"])
        today_pomo = pomo_data[pomo_data["Date"]==today_date]
        if not today_pomo.empty:
            st.dataframe(today_pomo, use_container_width=True)

    # ------------------ TAB 4: GROUP ------------------
    with tab4:
        st.subheader("Group Workspace")
        GROUPS_FILE="groups.csv"
        GROUP_TASKS_FILE="group_tasks.csv"
        GROUP_CHAT_FILE="group_chat.csv"

        users = load_or_create_csv("users.csv", ["Username","Password"])
        groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Members"])
        group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
        group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])

        if st.button("➕ Create New Group"):
            st.session_state.creating_group=True
            st.session_state.new_group_name=None
            st.session_state.add_member_name=None

        if st.session_state.creating_group:
            group_name = st.text_input("Enter Group Name", key="new_group_name")
            if group_name and st.button("OK", key="group_ok"):
                if (groups_df["GroupName"]==group_name.strip()).any():
                    st.error("Group exists!")
                else:
                    groups_df=pd.concat([groups_df,pd.DataFrame([{"GroupName":group_name.strip(),"Members":username}])], ignore_index=True)
                    save_csv(groups_df,GROUPS_FILE)
                    st.success(f"Group '{group_name.strip()}' created!")
                    st.session_state.new_group_name=group_name.strip()

            if st.session_state.new_group_name:
                member_input = st.text_input("Add Member by Username", key="add_member_name")
                if st.button("Add Member", key="add_member_btn"):
                    if member_input.strip() in users["Username"].values and member_input.strip()!=username:
                        idx = groups_df[groups_df["GroupName"]==st.session_state.new_group_name].index[0]
                        current_members = groups_df.at[idx,"Members"].split(",")
                        if member_input.strip() not in current_members:
                            current_members.append(member_input.strip())
                            groups_df.at[idx,"Members"] = ",".join(current_members)
                            save_csv(groups_df,GROUPS_FILE)
                            st.success(f"{member_input.strip()} added!")
                    else:
                        st.warning("Invalid username")

        # Show all user's groups
        my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]
        for _,grp in my_groups.iterrows():
            st.markdown(f"## {grp['GroupName']}")
            st.markdown("### Tasks")
            grp_tasks_sel = group_tasks[group_tasks["GroupName"]==grp['GroupName']]
            task_input = st.text_input("Add Task", key=f"task_{grp['GroupName']}")
            if st.button("Add Task", key=f"add_task_btn_{grp['GroupName']}") and task_input.strip():
                new_task={"GroupName":grp['GroupName'],"Task":task_input.strip(),
                          "Status":"Pending","AddedBy":username,"Date":today_date}
                group_tasks=pd.concat([group_tasks,pd.DataFrame([new_task])],ignore_index=True)
                save_csv(group_tasks,GROUP_TASKS_FILE)
            if not grp_tasks_sel.empty:
                st.dataframe(grp_tasks_sel.style.applymap(color_status, subset=["Status"]), use_container_width=True)

            st.markdown("### Chat")
            chat_input = st.text_input("Message", key=f"chat_{grp['GroupName']}")
            if st.button("Send", key=f"send_{grp['GroupName']}"):
                if chat_input.strip():
                    new_msg={"GroupName":grp['GroupName'],"Username":username,
                             "Message":chat_input.strip(),
                             "Time":datetime.now().strftime("%H:%M:%S")}
                    group_chat=pd.concat([group_chat,pd.DataFrame([new_msg])], ignore_index=True)
                    save_csv(group_chat,GROUP_CHAT_FILE)

            st_autorefresh(interval=5000, key=f"grp_refresh_{grp['GroupName']}")
            chat_sel = group_chat[group_chat["GroupName"]==grp['GroupName']]
            for _,row in chat_sel.iterrows():
                st.write(f"[{row['Time']}] **{row['Username']}**: {row['Message']}")
