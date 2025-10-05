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
for key in ["logged_in","username","task_updated","timer_running","timer_paused",
            "timer_start_time","timer_elapsed","timer_duration","timer_task_name",
            "pomo_running","pomo_paused","pomo_start_time","pomo_elapsed",
            "pomo_duration","pomo_task_name","countdown_running","countdown_total_seconds",
            "countdown_start_time","countdown_task_name","timer_data","pomo_sessions",
            "show_create_group","selected_group"]:
    if key not in st.session_state:
        if key in ["timer_running","timer_paused","pomo_running","pomo_paused","countdown_running","show_create_group"]:
            st.session_state[key] = False
        elif key=="timer_data":
            st.session_state[key] = pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS"])
        elif key=="pomo_sessions":
            st.session_state[key] = 0
        else:
            st.session_state[key] = None

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

    # Display logo in sidebar
    if os.path.exists("taskuni.png"):
        st.sidebar.image("taskuni.png", use_container_width=True)

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
        st.subheader("⏱ Countdown Timer")
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
            save_csv(st.session_state.timer_data, f"timer_{username}.csv")
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
                f"<h1 style='text-align:center;font-size:120px;'>⏱ {h:02d}:{m:02d}:{s:02d}</h1>"
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
                save_csv(st.session_state.timer_data, f"timer_{username}.csv")
                display_box.success("🎯 Countdown Finished!")

        # Total Focused Time
        if not st.session_state.timer_data.empty:
            total_seconds_calc = sum([hms_to_seconds(t) for t in st.session_state.timer_data['Focused_HMS']])
            total_h = total_seconds_calc // 3600
            total_m = (total_seconds_calc % 3600) // 60
            total_s = total_seconds_calc % 60
            st.markdown(f"### 🎯 Total Focused Time: {total_h}h {total_m}m {total_s}s")
            st.dataframe(st.session_state.timer_data, use_container_width=True)

    # ------------------ TAB 3: POMODORO ------------------
    with tab3:
        st.subheader("🍅 Pomodoro Timer")
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
            st.session_state.pomo_elapsed=0
            st.session_state.pomo_start_time=None

        # --- Display Timer ---
        if st.session_state.pomo_running:
            if st.session_state.pomo_paused:
                remaining = st.session_state.pomo_duration - st.session_state.pomo_elapsed
            else:
                elapsed = (time.time() - st.session_state.pomo_start_time) + st.session_state.pomo_elapsed
                remaining = max(0, st.session_state.pomo_duration - elapsed)
            mins, secs = divmod(int(remaining), 60)
            st.markdown(
                f"<h1 style='text-align:center;font-size:120px;'>🍅 {mins:02d}:{secs:02d}</h1>", 
                unsafe_allow_html=True
            )
            if remaining<=0:
                st.success("🍅 Pomodoro finished! Take a break.")
                st.session_state.pomo_running=False
                st.session_state.pomo_sessions += 1

        st.markdown(f"### Total Pomodoros Completed: {st.session_state.pomo_sessions}")

    # ---------- TAB 4: GROUP WORKSPACE (stable, form-based, no-flicker) ----------
import re

def _safe_key(s: str) -> str:
    """convert arbitrary group names into safe widget keys"""
    return re.sub(r"\W+", "_", str(s)).strip("_") or "grp"

with tab4:
    st.subheader("👥 Group Workspace")
    GROUPS_FILE = "groups.csv"
    GROUP_TASKS_FILE = "group_tasks.csv"
    GROUP_CHAT_FILE = "group_chat.csv"

    # load data (these helper funcs should exist in your app)
    groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName", "Members"])
    group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName", "Task", "Status", "AddedBy", "Date"])
    group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName", "Username", "Message", "Time"])

    # ---------- session state defaults ----------
    if "selected_group" not in st.session_state:
        st.session_state.selected_group = None
    if "show_create_group" not in st.session_state:
        st.session_state.show_create_group = False

    # ---------- list user's groups ----------
    st.markdown("### Your Groups")
    # ensure Members column is string to avoid unexpected errors
    groups_df["Members"] = groups_df["Members"].astype(str)
    my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]

    if my_groups.empty:
        st.info("You are not part of any group yet. Create one below.")
    else:
        # display each group as a button (safe keys)
        for _, row in my_groups.iterrows():
            grp_name = row["GroupName"]
            safe = _safe_key(grp_name)
            if st.button(grp_name, key=f"group_btn_{safe}"):
                st.session_state.selected_group = grp_name

    # If previously-selected group was removed externally, clear it to avoid stale references
    if st.session_state.selected_group and st.session_state.selected_group not in groups_df["GroupName"].values:
        st.session_state.selected_group = None

    selected_group = st.session_state.selected_group

    # ---------- selected group view ----------
    if selected_group:
        st.markdown(f"### {selected_group} — Tasks & Chat")
        safe = _safe_key(selected_group)

        # show tasks
        grp_tasks_sel = group_tasks[group_tasks["GroupName"] == selected_group]
        if grp_tasks_sel.empty:
            st.info("No tasks yet. Add one below.")
        else:
            st.dataframe(grp_tasks_sel[["Task", "AddedBy", "Status", "Date"]], use_container_width=True)

        # --- Add Task (form to prevent intermediate reruns) ---
        with st.form(key=f"add_task_form_{safe}", clear_on_submit=True):
            task_text = st.text_input("Add Task", placeholder="Enter new task...")
            add_submitted = st.form_submit_button("➕ Add Task")
            if add_submitted:
                t = task_text.strip()
                if t:
                    new_task = {
                        "GroupName": selected_group,
                        "Task": t,
                        "Status": "Pending",
                        "AddedBy": username,
                        "Date": today_date,
                    }
                    try:
                        group_tasks = pd.concat([group_tasks, pd.DataFrame([new_task])], ignore_index=True)
                        save_csv(group_tasks, GROUP_TASKS_FILE)
                        st.success("Task added ✅")
                    except Exception as e:
                        st.error(f"Couldn't save task: {e}")

        # --- Group Chat (form) ---
        with st.form(key=f"chat_form_{safe}", clear_on_submit=True):
            msg_text = st.text_input("Message", placeholder="Type a message...")
            send_submitted = st.form_submit_button("Send Message")
            if send_submitted:
                m = msg_text.strip()
                if m:
                    new_msg = {
                        "GroupName": selected_group,
                        "Username": username,
                        "Message": m,
                        "Time": datetime.now().strftime("%H:%M:%S"),
                    }
                    try:
                        group_chat = pd.concat([group_chat, pd.DataFrame([new_msg])], ignore_index=True)
                        save_csv(group_chat, GROUP_CHAT_FILE)
                        st.success("Message sent 💬")
                    except Exception as e:
                        st.error(f"Couldn't save message: {e}")

        # display chat
        chat_sel = group_chat[group_chat["GroupName"] == selected_group]
        if not chat_sel.empty:
            for _, row in chat_sel.iterrows():
                st.write(f"[{row['Time']}] **{row['Username']}**: {row['Message']}")

    # ---------- Create / Add Group (toggle + form) ----------
    if st.button("➕ Create / Add Group"):
        st.session_state.show_create_group = not st.session_state.show_create_group

    if st.session_state.show_create_group:
        with st.form(key="create_group_form", clear_on_submit=True):
            new_group_name = st.text_input("Group Name", placeholder="My Team")
            new_member = st.text_input("Add Member by username (comma separated ok)", placeholder="friend1,friend2")
            create = st.form_submit_button("Create / Add")
            if create:
                gn = new_group_name.strip()
                if not gn:
                    st.error("Group name can't be empty")
                else:
                    # create group if not exists
                    if not (groups_df["GroupName"] == gn).any():
                        try:
                            groups_df = pd.concat([groups_df, pd.DataFrame([{"GroupName": gn, "Members": username}])], ignore_index=True)
                            save_csv(groups_df, GROUPS_FILE)
                            st.success(f"Group '{gn}' created ✅")
                        except Exception as e:
                            st.error(f"Couldn't create group: {e}")
                    # add extra members if provided
                    if new_member.strip():
                        members_to_add = [m.strip() for m in new_member.split(",") if m.strip() and m.strip() != username]
                        if members_to_add:
                            idx = groups_df[groups_df["GroupName"] == gn].index[0]
                            current = str(groups_df.at[idx, "Members"])
                            cur_list = [m for m in current.split(",") if m.strip()]
                            changed = False
                            for m in members_to_add:
                                if m not in cur_list:
                                    cur_list.append(m)
                                    changed = True
                            if changed:
                                groups_df.at[idx, "Members"] = ",".join(cur_list)
                                try:
                                    save_csv(groups_df, GROUPS_FILE)
                                    st.success(f"Added members to '{gn}' ✅")
                                except Exception as e:
                                    st.error(f"Couldn't add members: {e}")











