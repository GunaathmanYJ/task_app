import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, date
from fpdf import FPDF

# ---------------- Utility: Load or create CSV with columns ----------------
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

# ---------------- Sidebar: Username ----------------
st.sidebar.subheader("👤 Enter your username")
username = st.sidebar.text_input("Username", key="username_input")

if not username:
    st.warning("Please enter a username to continue.")
    st.stop()

today_date = str(date.today())

# ---------------- Tabs ----------------
tab1, tab2, tab3, tab4 = st.tabs(["📋 Tasks", "⏳ Timer", "🍅 Pomodoro", "👥 Group Workspace"])

# ---------------- Tab 1: Personal Tasks ----------------
with tab1:
    st.subheader(f"📋 {username}'s Task Tracker")

    TASKS_FILE = f"tasks_{username}.csv"
    tasks = load_or_create_csv(TASKS_FILE, ["Task", "Status", "Date"])

    task_input = st.text_input("Add a new task", key="task_input")
    if st.button("➕ Add Task"):
        if task_input.strip():
            new_task = {"Task": task_input.strip(), "Status": "Pending", "Date": today_date}
            tasks = pd.concat([tasks, pd.DataFrame([new_task])], ignore_index=True)
            tasks.to_csv(TASKS_FILE, index=False)

    if not tasks.empty:
        for i, row in tasks.iterrows():
            cols = st.columns([3, 1, 1, 1])
            cols[0].write(f"{row['Task']} ({row['Status']})")
            if cols[1].button("Done", key=f"done_{i}"):
                tasks.at[i, "Status"] = "Done"; tasks.to_csv(TASKS_FILE, index=False)
            if cols[2].button("Not Done", key=f"notdone_{i}"):
                tasks.at[i, "Status"] = "Not Done"; tasks.to_csv(TASKS_FILE, index=False)
            if cols[3].button("Delete", key=f"delete_{i}"):
                tasks = tasks.drop(i).reset_index(drop=True); tasks.to_csv(TASKS_FILE, index=False)

# ---------------- Tab 2: Timer ----------------
with tab2:
    st.subheader("⏳ Focus Timer")

    TIMER_FILE = f"timer_{username}.csv"
    timer_data = load_or_create_csv(TIMER_FILE, ["Task", "Duration(min)", "Date", "Start", "End"])

    timer_task = st.text_input("Task name", key="timer_task")
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=180, value=25)

    if st.button("▶ Start Timer"):
        st.session_state.timer_running = True
        st.session_state.start_time = time.time()
        st.session_state.duration = duration * 60
        st.session_state.timer_task = timer_task

    if st.session_state.get("timer_running", False):
        elapsed = time.time() - st.session_state.start_time
        remaining = max(0, int(st.session_state.duration - elapsed))
        mins, secs = divmod(remaining, 60)
        st.metric("Time Remaining", f"{mins:02d}:{secs:02d}")
        if remaining == 0:
            st.session_state.timer_running = False
            st.success("⏰ Time’s up!")
            new_entry = {
                "Task": st.session_state.timer_task,
                "Duration(min)": st.session_state.duration // 60,
                "Date": today_date,
                "Start": datetime.fromtimestamp(st.session_state.start_time).strftime("%H:%M:%S"),
                "End": datetime.now().strftime("%H:%M:%S"),
            }
            timer_data = pd.concat([timer_data, pd.DataFrame([new_entry])], ignore_index=True)
            timer_data.to_csv(TIMER_FILE, index=False)

    st.markdown("### Logged Sessions")
    st.dataframe(timer_data, use_container_width=True)

    # Export as PDF
    if st.button("📄 Export Log as PDF"):
        class TimerPDF(FPDF):
            def header(self):
                self.set_font("Arial", "B", 16)
                self.cell(0, 10, "Focused Timer Report", ln=True, align="C")
                self.ln(10)

        pdf = TimerPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for _, row in timer_data.iterrows():
            pdf.cell(0, 10, f"{row['Date']} | {row['Task']} | {row['Duration(min)']} min", ln=True)
        pdf_file = f"{username}_timer_log.pdf"
        pdf.output(pdf_file)
        with open(pdf_file, "rb") as f:
            st.download_button("⬇ Download PDF", f, file_name=pdf_file)

# ---------------- Tab 3: Pomodoro ----------------
with tab3:
    st.subheader("🍅 Pomodoro Timer")

    pomo_task = st.text_input("Pomodoro Task", key="pomo_task")
    pomo_duration = st.number_input("Focus Duration (minutes)", 1, 120, 25)
    break_duration = st.number_input("Break Duration (minutes)", 1, 60, 5)

    if st.button("▶ Start Pomodoro"):
        st.session_state.pomo_running = True
        st.session_state.pomo_start = time.time()
        st.session_state.pomo_duration = pomo_duration * 60
        st.session_state.pomo_task = pomo_task

    if st.session_state.get("pomo_running", False):
        elapsed = time.time() - st.session_state.pomo_start
        remaining = max(0, int(st.session_state.pomo_duration - elapsed))
        mins, secs = divmod(remaining, 60)
        st.metric("Pomodoro Remaining", f"{mins:02d}:{secs:02d}")
        if remaining == 0:
            st.session_state.pomo_running = False
            st.success("🍅 Pomodoro finished! Take a break.")

# ---------------- Tab 4: Group Workspace ----------------
with tab4:
    st.subheader("👥 Group Workspace")

    GROUPS_FILE = "groups.csv"
    GROUP_TASKS_FILE = "group_tasks.csv"
    GROUP_CHAT_FILE = "group_chat.csv"
    INVITES_FILE = "group_invites.csv"
    NOTIFS_FILE = "group_notifications.csv"

    groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Admin","Members"])
    group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
    group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])
    invites_df = load_or_create_csv(INVITES_FILE, ["ToUser","FromUser","GroupName","Status"])
    notifs_df = load_or_create_csv(NOTIFS_FILE, ["User","Message","Time"])

    # Create group
    st.markdown("### ➕ Create Group")
    grp_name_input = st.text_input("Group Name", key="create_group_input")
    if st.button("Create Group"):
        if grp_name_input.strip() and not (groups_df["GroupName"]==grp_name_input.strip()).any():
            new_group = {"GroupName":grp_name_input.strip(),"Admin":username,"Members":username}
            groups_df = pd.concat([groups_df,pd.DataFrame([new_group])],ignore_index=True)
            groups_df.to_csv(GROUPS_FILE,index=False)
            st.success(f"✅ Group '{grp_name_input.strip()}' created!")

    # My groups
    st.markdown("### 🔹 Your Groups")
    my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]
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
            groups_df.loc[groups_df["GroupName"]==row["GroupName"],"Members"] = groups_df.loc[groups_df["GroupName"]==row["GroupName"],"Members"].apply(lambda x: x+","+username if username not in x else x)
            groups_df.to_csv(GROUPS_FILE,index=False)
            invites_df.at[i,"Status"]="Accepted"
            invites_df.to_csv(INVITES_FILE,index=False)
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
            cols[0].write(f"{row['Task']} ({row['AddedBy']}) - {row['Status']}")
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
