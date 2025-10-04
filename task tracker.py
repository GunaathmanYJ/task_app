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

# ---------------- Main App ----------------
if "logged_in_user" in st.session_state:
    username = st.session_state.logged_in_user

    # ---------------- Initialize session_state ----------------
    if "last_username" not in st.session_state:
        st.session_state.last_username = ""
    if "tasks" not in st.session_state:
        st.session_state.tasks = pd.DataFrame(columns=["Task", "Status", "Date"])
    if "timer_data" not in st.session_state:
        st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_HMS", "Focused_HMS"])
    if "countdown_running" not in st.session_state:
        st.session_state.countdown_running = False
    if "pomo_running" not in st.session_state:
        st.session_state.pomo_running = False
    if "group_update" not in st.session_state:
        st.session_state.group_update = 0

    # ---------------- Reset session if user changed ----------------
    if st.session_state.last_username != username:
        st.session_state.tasks = pd.DataFrame(columns=["Task", "Status", "Date"])
        st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_HMS", "Focused_HMS"])
        st.session_state.countdown_running = False
        st.session_state.pomo_running = False
        st.session_state.group_update = 0
        st.session_state.last_username = username

    # ---------------- Files ----------------
    TASKS_FILE = f"tasks_{username}.csv"
    TIMER_FILE = f"timer_{username}.csv"

    # Load personal data
    if os.path.exists(TASKS_FILE):
        st.session_state.tasks = pd.read_csv(TASKS_FILE)
    if os.path.exists(TIMER_FILE):
        st.session_state.timer_data = pd.read_csv(TIMER_FILE)

    # ---------------- Page ----------------
    st.set_page_config(page_title="TaskUni Premium", layout="wide")
    st.title("📌 TaskUni — Task & Group Workspace")
    today_date = datetime.now().strftime("%d-%m-%Y")

    # ---------------- Tabs ----------------
    tab1, tab2, tab3, group_tab = st.tabs(["📝 Personal Tasks", "⏱️ Countdown Timer", "🍅 Pomodoro Timer", "👥 Group Workspace"])

    # ---------------- Helper: HMS to seconds ----------------
    def hms_to_seconds(hms_str):
        try:
            h, m, s = 0, 0, 0
            parts = hms_str.split()
            for part in parts:
                if "h" in part: h=int(part.replace("h",""))
                elif "m" in part: m=int(part.replace("m",""))
                elif "s" in part: s=int(part.replace("s",""))
            return h*3600 + m*60 + s
        except: return 0

    # ---------------- Personal Task Helpers ----------------
    def mark_done(idx):
        st.session_state.tasks.at[idx, "Status"]="Done"
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)
    def mark_notdone(idx):
        st.session_state.tasks.at[idx, "Status"]="Not Done"
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)
    def delete_task(idx):
        st.session_state.tasks = st.session_state.tasks.drop(idx).reset_index(drop=True)
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

    # ---------------- Tab 1: Personal Tasks ----------------
    with tab1:
        st.subheader("📝 Your Tasks")
        task_input = st.text_input("Enter Task")
        if st.button("Add Task") and task_input.strip():
            new_task = {"Task": task_input.strip(), "Status":"Pending", "Date":today_date}
            st.session_state.tasks = pd.concat([st.session_state.tasks,pd.DataFrame([new_task])],ignore_index=True)
            st.session_state.tasks.to_csv(TASKS_FILE,index=False)

        tasks_today = st.session_state.tasks[st.session_state.tasks["Date"]==today_date]
        if not tasks_today.empty:
            def highlight_status(s):
                if s=="Done": return "background-color:#00C853;color:white"
                elif s=="Not Done": return "background-color:#D50000;color:white"
                else: return "background-color:#FFA500;color:white"
            df_disp = tasks_today[["Task","Status"]].copy()
            df_disp.index+=1
            st.dataframe(df_disp.style.applymap(highlight_status,subset=["Status"]),use_container_width=True)
            st.markdown("### Update Tasks")
            for i,row in tasks_today.iterrows():
                cols = st.columns([3,1,1,1])
                cols[0].write(f"{row['Task']}:")
                cols[1].button("Done",key=f"done_{i}",on_click=mark_done,args=(i,))
                cols[2].button("Not Done",key=f"notdone_{i}",on_click=mark_notdone,args=(i,))
                cols[3].button("Delete",key=f"delete_{i}",on_click=delete_task,args=(i,))
        else:
            st.write("No tasks for today.")

    # ---------------- Tab 2: Countdown Timer ----------------
    with tab2:
        st.subheader("⏱️ Countdown Timer")
        h_col,m_col,s_col = st.columns(3)
        with h_col: hours = st.number_input("Hours",0,23,0)
        with m_col: minutes = st.number_input("Minutes",0,59,0)
        with s_col: seconds = st.number_input("Seconds",0,59,0)
        cd_task = st.text_input("Task name (optional)")
        start_btn = st.button("Start Countdown")
        stop_btn = st.button("Stop Countdown")
        display_box = st.empty()

        if start_btn:
            total_sec = hours*3600+minutes*60+seconds
            if total_sec>0:
                st.session_state.countdown_running=True
                st.session_state.countdown_total_seconds=total_sec
                st.session_state.countdown_start_time=time.time()
                st.session_state.countdown_task_name=cd_task if cd_task else "Unnamed"
            else: st.warning("Set time>0")

        if stop_btn and st.session_state.countdown_running:
            elapsed = int(time.time()-st.session_state.countdown_start_time)
            focused = min(elapsed,st.session_state.countdown_total_seconds)
            h = focused//3600; m=(focused%3600)//60; s=focused%60
            st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([{
                "Task":st.session_state.countdown_task_name,
                "Target_HMS":f"{hours}h {minutes}m {seconds}s",
                "Focused_HMS":f"{h}h {m}m {s}s"
            }])],ignore_index=True)
            st.session_state.timer_data.to_csv(TIMER_FILE,index=False)
            st.session_state.countdown_running=False
            st.success(f"Countdown stopped. Focused: {h}h {m}m {s}s")

        if st.session_state.get("countdown_running",False):
            st_autorefresh(interval=1000,key="cd_refresh")
            elapsed = int(time.time()-st.session_state.countdown_start_time)
            remaining = max(st.session_state.countdown_total_seconds-elapsed,0)
            h = remaining//3600; m=(remaining%3600)//60; s=remaining%60
            display_box.markdown(f"<h1 style='text-align:center;font-size:120px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1><h3 style='text-align:center;'>Task: {st.session_state.countdown_task_name}</h3>",unsafe_allow_html=True)
            if remaining==0:
                st.session_state.countdown_running=False
                st.success("🎯 Countdown Finished!")

    # ---------------- Tab 3: Pomodoro ----------------
    with tab3:
        st.subheader("🍅 Pomodoro Timer")
        pomo_dur = st.number_input("Pomodoro Duration (minutes)",1,180,25)
        break_dur = st.number_input("Break Duration (minutes)",1,60,5)
        pomo_start_btn = st.button("Start Pomodoro")
        pomo_stop_btn = st.button("Stop Pomodoro")
        pomo_disp = st.empty()
        if pomo_start_btn:
            st.session_state.pomo_running=True
            st.session_state.pomo_start_time=time.time()
            st.session_state.pomo_total_seconds=pomo_dur*60
        if st.session_state.get("pomo_running",False):
            st_autorefresh(interval=1000,key="pomo_refresh")
            elapsed = int(time.time()-st.session_state.pomo_start_time)
            remaining = max(st.session_state.pomo_total_seconds-elapsed,0)
            m = remaining//60; s=remaining%60
            pomo_disp.markdown(f"<h1 style='text-align:center;font-size:100px;'>🍅 {m:02d}:{s:02d}</h1>",unsafe_allow_html=True)
            if remaining==0:
                st.session_state.pomo_running=False
                st.success("Pomodoro finished! Take a break.")

    # ---------------- Tab 4: Group Workspace ----------------
    with group_tab:
        st.subheader("👥 Group Workspace")
        GROUPS_FILE = "groups.csv"
        GROUP_TASKS_FILE = "group_tasks.csv"
        GROUP_CHAT_FILE = "group_chat.csv"
        INVITES_FILE = "group_invites.csv"
        NOTIFS_FILE = "group_notifications.csv"

        # Load / init
        groups_df = pd.read_csv(GROUPS_FILE) if os.path.exists(GROUPS_FILE) else pd.DataFrame(columns=["GroupName","Admin","Members"])
        group_tasks = pd.read_csv(GROUP_TASKS_FILE) if os.path.exists(GROUP_TASKS_FILE) else pd.DataFrame(columns=["GroupName","Task","Status","AddedBy","Date"])
        group_chat = pd.read_csv(GROUP_CHAT_FILE) if os.path.exists(GROUP_CHAT_FILE) else pd.DataFrame(columns=["GroupName","Username","Message","Time"])
        invites_df = pd.read_csv(INVITES_FILE) if os.path.exists(INVITES_FILE) else pd.DataFrame(columns=["ToUser","FromUser","GroupName","Status"])
        notifs_df = pd.read_csv(NOTIFS_FILE) if os.path.exists(NOTIFS_FILE) else pd.DataFrame(columns=["User","Message","Time"])

        # Create group
        st.markdown("### ➕ Create Group")
        grp_name_input = st.text_input("Group Name", key="create_group_input")
        if st.button("Create Group"):
            if grp_name_input.strip() and not (groups_df["GroupName"]==grp_name_input.strip()).any():
                new_group = {"GroupName":grp_name_input.strip(),"Admin":username,"Members":username}
                groups_df = pd.concat([groups_df,pd.DataFrame([new_group])],ignore_index=True)
                groups_df.to_csv(GROUPS_FILE,index=False)
                st.success(f"✅ Group '{grp_name_input.strip()}' created!")

        # Show my groups
        st.markdown("### 🔹 Your Groups")
        my_groups = groups_df[groups_df["Members"].str.contains(username)]
        for _,grp in my_groups.iterrows():
            st.write(f"**{grp['GroupName']}** | Admin: {grp['Admin']} | Members: {grp['Members']}")

        # Invite members
        st.markdown("### ➕ Invite Member")
        selected_group = st.selectbox("Select group", my_groups["GroupName"] if not my_groups.empty else [])
        new_member = st.text_input("Enter username to invite", key="invite_user_input2")
        if st.button("Send Invite", key="invite_btn"):
            if selected_group and new_member.strip() and new_member!=username:
                invites_df = pd.concat([invites_df,pd.DataFrame([{
                    "ToUser":new_member.strip(),
                    "FromUser":username,
                    "GroupName":selected_group,
                    "Status":"Pending"
                }])],ignore_index=True)
                invites_df.to_csv(INVITES_FILE,index=False)
                st.success(f"✅ Invite sent to {new_member.strip()}!")

        # Pending invites
        st.markdown("### 🔔 Pending Invites")
        my_pending = invites_df[(invites_df["ToUser"]==username)&(invites_df["Status"]=="Pending")]
        for i,row in my_pending.iterrows():
            st.write(f"{row['FromUser']} invited you to join group '{row['GroupName']}'")
            if st.button(f"Accept_{i}"):
                # Add user to group
                groups_df.loc[groups_df["GroupName"]==row["GroupName"],"Members"] = groups_df.loc[groups_df["GroupName"]==row["GroupName"],"Members"].apply(lambda x: username if pd.isna(x) else x+","+username)
                groups_df.to_csv(GROUPS_FILE,index=False)
                invites_df.at[i,"Status"]="Accepted"
                invites_df.to_csv(INVITES_FILE,index=False)
                # Notification
                notifs_df = pd.concat([notifs_df,pd.DataFrame([{
                    "User":username,
                    "Message":f"You joined group '{row['GroupName']}' invited by {row['FromUser']}",
                    "Time":datetime.now().strftime("%H:%M:%S")
                }])],ignore_index=True)
                notifs_df.to_csv(NOTIFS_FILE,index=False)
                st.success("✅ Invite accepted!")
            if st.button(f"Reject_{i}"):
                invites_df.at[i,"Status"]="Rejected"
                invites_df.to_csv(INVITES_FILE,index=False)
                st.info("Invite rejected.")

        # Notifications
        st.markdown("### 🔔 Notifications")
        my_notifs = notifs_df[notifs_df["User"]==username]
        for _,notif in my_notifs.iterrows():
            st.info(f"[{notif['Time']}] {notif['Message']}")

        # Group tasks & chat
        st.markdown("### 📝 Group Tasks & Chat")
        if not my_groups.empty:
            sel_group_task = st.selectbox("Select group to view tasks/chat", my_groups["GroupName"])
            # Tasks
            st.markdown("#### Tasks")
            group_tasks_sel = group_tasks[group_tasks["GroupName"]==sel_group_task]
            task_input_grp = st.text_input("Add Task", key="grp_task_input")
            if st.button("Add Task", key="grp_add_task_btn") and task_input_grp.strip():
                new_task = {"GroupName":sel_group_task,"Task":task_input_grp.strip(),"Status":"Pending","AddedBy":username,"Date":today_date}
                group_tasks = pd.concat([group_tasks,pd.DataFrame([new_task])],ignore_index=True)
                group_tasks.to_csv(GROUP_TASKS_FILE,index=False)
            for i,row in group_tasks_sel.iterrows():
                cols = st.columns([3,1,1,1])
                cols[0].write(f"{row['Task']} ({row['AddedBy']})")
                if cols[1].button("Done",key=f"g_done_{i}"): group_tasks.loc[i,"Status"]="Done"; group_tasks.to_csv(GROUP_TASKS_FILE,index=False)
                if cols[2].button("Not Done",key=f"g_notdone_{i}"): group_tasks.loc[i,"Status"]="Not Done"; group_tasks.to_csv(GROUP_TASKS_FILE,index=False)
                if cols[3].button("Delete",key=f"g_del_{i}"): group_tasks = group_tasks.drop(i).reset_index(drop=True); group_tasks.to_csv(GROUP_TASKS_FILE,index=False)
            # Chat
            st.markdown("#### Chat")
            chat_input = st.text_input("Enter message", key="grp_chat_input")
            if st.button("Send", key="grp_chat_send"):
                if chat_input.strip():
                    group_chat = pd.concat([group_chat,pd.DataFrame([{
                        "GroupName":sel_group_task,
                        "Username":username,
                        "Message":chat_input.strip(),
                        "Time":datetime.now().strftime("%H:%M:%S")
                    }])],ignore_index=True)
                    group_chat.to_csv(GROUP_CHAT_FILE,index=False)
            group_chat_sel = group_chat[group_chat["GroupName"]==sel_group_task]
            for _,row in group_chat_sel.iterrows():
                st.write(f"[{row['Time']}] **{row['Username']}**: {row['Message']}")
