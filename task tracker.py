import streamlit as st
import pandas as pd
import os
import hashlib
import time
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
import re  # moved inside login-checked block

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
        if username_input.strip()=="" or password_input.strip()=="":
            st.warning("Fill both fields")
        elif username_input in users["Username"].values:
            st.error("Username exists!")
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
                st.rerun()   # instantly rerun so login screen disappears
            else:
                st.error("Wrong password!")
        else:
            st.error("Username not found!")

# ------------------ MAIN APP ------------------
if st.session_state.logged_in:
    username = st.session_state.username
    st.title(f"TaskUni - {username}")

    # Display logo in sidebar
    if os.path.exists("taskuni.png"):
        st.sidebar.image("taskuni.png", use_container_width=True)

    # safe key helper for group workspace
    def _safe_key(s: str) -> str:
        return re.sub(r"\W+", "_", str(s)).strip("_") or "grp"

    # ------------------ TABS ------------------
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

    # ------------------ TAB 4: GROUP WORKSPACE (UPGRADED) ------------------
with tab4:
    st.subheader("👥 Group Workspace")
    GROUPS_FILE = "groups.csv"
    GROUP_TASKS_FILE = "group_tasks.csv"
    GROUP_CHAT_FILE = "group_chat.csv"

    groups_df = load_or_create_csv(GROUPS_FILE, ["GroupID","GroupName","Members","JoinCode","Admin"])
    group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupID","Task","Status","AddedBy","Date"])
    group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupID","Username","Message","Time"])

    if "selected_group" not in st.session_state:
        st.session_state.selected_group = None
    if "show_create_group" not in st.session_state:
        st.session_state.show_create_group = False

    # ---------------- CREATE GROUP BUTTON AT TOP ----------------
    if st.button("➕ Create / Add Group", key="top_create_btn"):
        st.session_state.show_create_group = not st.session_state.show_create_group

    if st.session_state.show_create_group:
        with st.expander("Create / Add Group", expanded=True):
            new_group_name = st.text_input("Group Name", placeholder="My Team")
            join_code_input = st.text_input("Join Code (optional)", placeholder="Leave empty for random")
            new_members = st.text_input("Add Members (comma separated)", placeholder="friend1,friend2")
            create = st.button("Create Group", key="create_btn")
            if create:
                gn = new_group_name.strip()
                jc = join_code_input.strip() or os.urandom(3).hex()
                if not gn:
                    st.error("Group name can't be empty")
                else:
                    grp_id = str(int(time.time()*1000))
                    groups_df = pd.concat([groups_df, pd.DataFrame([{
                        "GroupID": grp_id,
                        "GroupName": gn,
                        "Members": st.session_state.username,
                        "JoinCode": jc,
                        "Admin": st.session_state.username
                    }])], ignore_index=True)
                    # Add additional members
                    if new_members.strip():
                        members_to_add = [m.strip() for m in new_members.split(",") if m.strip() and m.strip()!=st.session_state.username]
                        idx = groups_df[groups_df["GroupID"]==grp_id].index[0]
                        current = str(groups_df.at[idx, "Members"])
                        cur_list = [m for m in current.split(",") if m.strip()]
                        for m in members_to_add:
                            if m not in cur_list: cur_list.append(m)
                        groups_df.at[idx,"Members"] = ",".join(cur_list)
                    save_csv(groups_df, GROUPS_FILE)
                    st.success(f"Group '{gn}' created ✅ (Join code: {jc})")

    # ---------------- JOIN GROUP BY CODE ----------------
    st.markdown("---")
    st.markdown("### 🔑 Join Group by Code")
    code_input = st.text_input("Enter Group Join Code", placeholder="Enter code here")
    join_btn = st.button("Join Group", key="join_btn")
    if join_btn and code_input.strip():
        code_input = code_input.strip()
        match = groups_df[groups_df["JoinCode"]==code_input]
        if match.empty:
            st.error("Invalid code!")
        else:
            grp_row = match.iloc[0]
            members = str(grp_row["Members"]).split(",")
            if st.session_state.username in members:
                st.info("You are already a member of this group.")
            else:
                members.append(st.session_state.username)
                idx = match.index[0]
                groups_df.at[idx,"Members"] = ",".join(members)
                save_csv(groups_df, GROUPS_FILE)
                st.success(f"You joined '{grp_row['GroupName']}' successfully!")

    # ---------------- DISPLAY USER GROUPS ----------------
    st.markdown("---")
    st.markdown("### Your Groups")
    groups_df["Members"] = groups_df["Members"].astype(str)
    my_groups = groups_df[groups_df["Members"].str.contains(st.session_state.username, na=False)]

    if my_groups.empty:
        st.info("You are not part of any group yet.")
    else:
        for _, row in my_groups.iterrows():
            grp_name = row["GroupName"]
            grp_id = row["GroupID"]
            safe = _safe_key(grp_id)
            if st.button(f"📂 {grp_name}", key=f"group_btn_{safe}"):
                st.session_state.selected_group = grp_id

    # ---------------- SELECTED GROUP ----------------
    selected_group = st.session_state.selected_group
    if selected_group:
        grp_row = groups_df[groups_df["GroupID"]==selected_group].iloc[0]
        st.markdown(f"### **{grp_row['GroupName']}** — Tasks & Chat")
        safe = _safe_key(selected_group)

        # show join code inside group
        st.info(f"🔑 Group Join Code: {grp_row['JoinCode']}")

        # show members and count
        members_list = [m.strip() for m in str(grp_row["Members"]).split(",") if m.strip()]
        st.markdown(f"**Members ({len(members_list)}):** {', '.join(members_list)}")

        # ---------------- Add Member (Admin only) ----------------
        if grp_row["Admin"] == st.session_state.username:
            with st.form(key=f"add_member_form_{safe}", clear_on_submit=True):
                new_member = st.text_input("Add Member to this group", placeholder="Enter username")
                add_submitted = st.form_submit_button("➕ Add Member")
                if add_submitted:
                    nm = new_member.strip()
                    if nm and nm not in members_list:
                        members_list.append(nm)
                        idx = groups_df[groups_df["GroupID"]==selected_group].index[0]
                        groups_df.at[idx,"Members"] = ",".join(members_list)
                        save_csv(groups_df, GROUPS_FILE)
                        st.success(f"{nm} added to the group ✅")
                    elif nm in members_list:
                        st.warning(f"{nm} is already a member")

        # ---------------- Add Task ----------------
        with st.form(key=f"add_task_form_{safe}", clear_on_submit=True):
            task_text = st.text_input("Add Task", placeholder="Enter new task...")
            add_submitted = st.form_submit_button("➕ Add Task")
            if add_submitted:
                t = task_text.strip()
                if t:
                    new_task = {
                        "GroupID": selected_group,
                        "Task": t,
                        "Status": "Pending",
                        "AddedBy": st.session_state.username,
                        "Date": today_date,
                    }
                    group_tasks = pd.concat([group_tasks, pd.DataFrame([new_task])], ignore_index=True)
                    group_tasks.to_csv(GROUP_TASKS_FILE, index=False)
                    st.success("✅ Task added")

        # ---------------- Display Tasks ----------------
        group_specific_tasks = group_tasks[group_tasks["GroupID"]==selected_group]
        st.markdown("#### 📋 Current Tasks")
        if not group_specific_tasks.empty:
            st.dataframe(group_specific_tasks[["Task","Status","AddedBy","Date"]].reset_index(drop=True))
        else:
            st.info("No tasks yet. Add one above ☝️")

        # ---------------- Chat ----------------
        with st.form(key=f"chat_form_{safe}", clear_on_submit=True):
            msg_text = st.text_input("Message", placeholder="Type a message...")
            send_submitted = st.form_submit_button("Send Message")
            if send_submitted:
                m = msg_text.strip()
                if m:
                    new_msg = {
                        "GroupID": selected_group,
                        "Username": st.session_state.username,
                        "Message": m,
                        "Time": datetime.now().strftime("%H:%M:%S"),
                    }
                    group_chat = pd.concat([group_chat, pd.DataFrame([new_msg])], ignore_index=True)
                    group_chat.to_csv(GROUP_CHAT_FILE, index=False)
                    st.success("💬 Message sent")

        chat_sel = group_chat[group_chat["GroupID"]==selected_group]
        if not chat_sel.empty:
            st.markdown("#### 💭 Group Chat")
            for _, row in chat_sel.iterrows():
                st.write(f"[{row['Time']}] **{row['Username']}**: {row['Message']}")


