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
    h, m, s = [int(x) for x in hms_str.replace("h","").replace("m","").replace("s","").split()]
    return h*3600 + m*60 + s

today_date = str(date.today())

# ------------------ SESSION STATE DEFAULTS ------------------
for key in ["logged_in","username","task_updated","timer_running","timer_paused",
            "timer_start_time","timer_elapsed","timer_duration","timer_task_name",
            "pomo_running","pomo_paused","pomo_start_time","pomo_elapsed",
            "pomo_duration","pomo_task_name","pomo_count",
            "timer_data","selected_group","show_create_group"]:
    if key not in st.session_state:
        if key=="pomo_count": st.session_state[key]=0
        elif key=="timer_data": st.session_state[key]=pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS"])
        elif key in ["selected_group","show_create_group"]: st.session_state[key]=None
        else: st.session_state[key] = False if "running" in key or "paused" in key else None

# ------------------ LOGIN / REGISTER ------------------
if not st.session_state.logged_in:
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
            st.success("Registered! Redirecting...")
            st.session_state.logged_in = True
            st.session_state.username = username_input.strip()
            st.rerun()   # 🔥 jump to main tabs
    
    if choice=="Login" and st.button("Login"):
        if username_input.strip() in users["Username"].values:
            stored_pass = users.loc[users["Username"]==username_input.strip(),"Password"].values[0]
            if stored_pass==hash_password(password_input.strip()):
                st.session_state.logged_in = True
                st.session_state.username = username_input.strip()
                st.success(f"Welcome {st.session_state.username}! Redirecting...")
                st.rerun()   # 🔥 jump to main tabs
            else:
                st.error("Wrong password!")
        else:
            st.error("Username not found!")

# ------------------ MAIN APP ------------------
if st.session_state.logged_in:
    username = st.session_state.username
    st.title(f"TaskUni - {username}")
    
    # Force default to first tab ("📋 Tasks") after login
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Tasks","⏳ Timer","🍅 Pomodoro","👥 Group Workspace"])
    
    with tab1:
        st.subheader("Your Tasks")
        # you can add task management code here
    
    with tab2:
        st.subheader("Timer")
        # timer code here
    
    with tab3:
        st.subheader("Pomodoro")
        # pomodoro code here
    
    with tab4:
        st.subheader("Group Workspace")
        # group workspace code here


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
                st.experimental_rerun()  # ensures the new task appears immediately

        if not tasks.empty:
            st.dataframe(tasks.style.applymap(color_status, subset=["Status"]), use_container_width=True)
            st.markdown("### Update Task Status")
            # Single-click update implementation
            for i,row in tasks.iterrows():
                if f"task_{i}" not in st.session_state:
                    st.session_state[f"task_{i}"] = row["Status"]
                cols = st.columns([4,1,1,1])
                cols[0].write(f"{row['Task']}")
                if cols[1].button("Done", key=f"done_{i}"):
                    st.session_state[f"task_{i}"] = "Done"
                if cols[2].button("Not Done", key=f"notdone_{i}"):
                    st.session_state[f"task_{i}"] = "Not Done"
                if cols[3].button("Delete", key=f"delete_{i}"):
                    tasks = tasks.drop(i).reset_index(drop=True)
                    save_csv(tasks, TASKS_FILE)
                    st.experimental_rerun()  # delete should reflect immediately
                    continue
                # Sync session_state back to DataFrame
                tasks.at[i,"Status"] = st.session_state[f"task_{i}"]
            save_csv(tasks,TASKS_FILE)

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
            st.session_state.timer_data.to_csv(f"timer_{username}.csv", index=False)
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
                st.session_state.timer_data.to_csv(f"timer_{username}.csv", index=False)
                display_box.success("🎯 Countdown Finished!")

        # Total Focused Time
        if not st.session_state.timer_data.empty:
            total_seconds_calc = sum([hms_to_seconds(t) for t in st.session_state.timer_data['Focused_HMS']])
            total_h = total_seconds_calc // 3600
            total_m = (total_seconds_calc % 3600) // 60
            total_s = total_seconds_calc % 60
            st.markdown(f"### 🎯 Total Focused Time: {total_h}h {total_m}m {total_s}s")

    # ------------------ TAB 3: POMODORO ------------------
    with tab3:
        st.subheader("🍅 Pomodoro Timer")
        pomo_task = st.text_input("Task Name", key="pomo_task_input")
        pomo_duration = st.number_input("Pomodoro Duration (minutes)", min_value=1, max_value=180, value=25, key="pomo_duration_input")
        start_pomo = st.button("Start Pomodoro")
        stop_pomo = st.button("Stop Pomodoro")
        display_pomo = st.empty()

        if start_pomo:
            st.session_state.pomo_running = True
            st.session_state.pomo_start_time = time.time()
            st.session_state.pomo_duration = pomo_duration * 60
            st.session_state.pomo_task_name = pomo_task if pomo_task else "Unnamed"

        if stop_pomo:
            st.session_state.pomo_running = False
            elapsed = int(time.time() - st.session_state.pomo_start_time)
            focused = min(elapsed, st.session_state.pomo_duration)
            st.session_state.pomo_count += 1
            st.success(f"Pomodoro Stopped. Focused: {focused//60}m {focused%60}s")

        if st.session_state.get("pomo_running", False):
            st_autorefresh(interval=1000, key="pomo_refresh")
            elapsed = int(time.time() - st.session_state.pomo_start_time)
            remaining = max(st.session_state.pomo_duration - elapsed, 0)
            display_pomo.markdown(
                f"<h1 style='text-align:center;font-size:120px;'>{remaining//60:02d}:{remaining%60:02d}</h1>"
                f"<h3 style='text-align:center;font-size:32px;'>Task: {st.session_state.pomo_task_name}</h3>",
                unsafe_allow_html=True
            )
            if remaining == 0:
                st.session_state.pomo_running = False
                st.session_state.pomo_count += 1
                display_pomo.success("🎯 Pomodoro Finished!")

        st.markdown(f"### Number of Pomodoros Completed: {st.session_state.pomo_count}")

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
        if "selected_group" not in st.session_state: st.session_state.selected_group=None

        for idx, grp in my_groups.iterrows():
            if st.button(grp["GroupName"], key=f"group_btn_{grp['GroupName']}"):
                st.session_state.selected_group = grp["GroupName"]

        selected_group = st.session_state.selected_group

        if selected_group:
            st.markdown(f"### {selected_group} Tasks")
            grp_tasks_sel = group_tasks[group_tasks["GroupName"]==selected_group]
            if not grp_tasks_sel.empty:
                st.dataframe(grp_tasks_sel[["Task","AddedBy","Date"]], use_container_width=True)

            new_task_input = st.text_input("Add Task", key=f"group_task_input_{selected_group}")
            if st.button("➕ Add Task", key=f"group_add_task_btn_{selected_group}"):
                if new_task_input.strip():
                    new_task={"GroupName":selected_group,"Task":new_task_input.strip(),
                              "Status":"Pending","AddedBy":username,"Date":today_date}
                    group_tasks=pd.concat([group_tasks,pd.DataFrame([new_task])], ignore_index=True)
                    save_csv(group_tasks,GROUP_TASKS_FILE)

            st.markdown(f"### {selected_group} Chat")
            chat_sel = group_chat[group_chat["GroupName"]==selected_group]
            chat_input = st.text_input("Message", key=f"grp_chat_input_{selected_group}")
            if st.button("Send Message", key=f"send_msg_{selected_group}"):
                if chat_input.strip():
                    new_msg={"GroupName":selected_group,"Username":username,"Message":chat_input.strip(),
                             "Time":datetime.now().strftime("%H:%M:%S")}
                    group_chat=pd.concat([group_chat,pd.DataFrame([new_msg])], ignore_index=True)
                    save_csv(group_chat,GROUP_CHAT_FILE)
            if not chat_sel.empty:
                for _,row in chat_sel.iterrows():
                    st.write(f"[{row['Time']}] *{row['Username']}*: {row['Message']}")

        # Create group toggle
        if st.button("➕ Create / Add Group"):
            st.session_state.show_create_group = not st.session_state.show_create_group
        if st.session_state.show_create_group:
            new_group_name = st.text_input("Group Name", key="grp_name")
            new_member = st.text_input("Add Member by username", key="grp_add_member")
            if st.button("Create / Add"):
                if new_group_name.strip():
                    if not (groups_df["GroupName"]==new_group_name.strip()).any():
                        groups_df=pd.concat([groups_df,pd.DataFrame([{"GroupName":new_group_name.strip(),
                                                                      "Members":username}])], ignore_index=True)
                        save_csv(groups_df,GROUPS_FILE)
                        st.success(f"Group '{new_group_name.strip()}' created!")
                    if new_member.strip() and new_member!=username:
                        idx = groups_df[groups_df["GroupName"]==new_group_name.strip()].index[0]
                        current_members = groups_df.at[idx,"Members"].split(",")
                        if new_member.strip() not in current_members:
                            current_members.append(new_member.strip())
                            groups_df.at[idx,"Members"] = ",".join(current_members)
                            save_csv(groups_df,GROUPS_FILE)
                            st.success(f"{new_member.strip()} added to '{new_group_name.strip()}'!")


