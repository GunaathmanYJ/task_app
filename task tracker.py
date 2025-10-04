import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, date
from fpdf import FPDF
import matplotlib.pyplot as plt

# ----------------- Constants -----------------
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Files (per-user files will be prefixed dynamically)
GLOBAL_FILES = {
    "groups": os.path.join(DATA_DIR, "groups.csv"),
    "group_tasks": os.path.join(DATA_DIR, "group_tasks.csv"),
    "group_chat": os.path.join(DATA_DIR, "group_chat.csv"),
    "invites": os.path.join(DATA_DIR, "group_invites.csv"),
    "notifs": os.path.join(DATA_DIR, "group_notifications.csv"),
}

# ----------------- Utilities -----------------
@st.cache_data
def load_or_create_csv(file, columns):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            # Ensure columns exist
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
            return df
        except Exception:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)


def save_df(df, file):
    # Create backup on first save
    try:
        df.to_csv(file, index=False)
    except Exception as e:
        st.error(f"Failed to save {file}: {e}")


# Simple helper to parse dates safely
def parse_date(s):
    try:
        return pd.to_datetime(s).date()
    except Exception:
        return None


# ----------------- Session state defaults -----------------
if "timer" not in st.session_state:
    st.session_state.timer = {"running": False}
if "pomo" not in st.session_state:
    st.session_state.pomo = {"running": False}

# ----------------- Sidebar: User -----------------
st.sidebar.title("Taskuni — Optimized 🚀")
st.sidebar.subheader("👤 Enter your username")
username = st.sidebar.text_input("Username", key="username_input")

if not username:
    st.sidebar.info("Please enter a username to continue — this app stores simple CSVs under ./data/")
    st.stop()

# User-specific file paths
TASKS_FILE = os.path.join(DATA_DIR, f"tasks_{username}.csv")
TIMER_FILE = os.path.join(DATA_DIR, f"timer_{username}.csv")
PROFILE_FILE = os.path.join(DATA_DIR, f"profile_{username}.csv")

today_date = date.today().isoformat()

# ----------------- Load data (cached) -----------------
TASK_COLUMNS = ["ID", "Task", "Status", "DateAdded", "Deadline", "Priority", "Notes"]
tasks_df = load_or_create_csv(TASKS_FILE, TASK_COLUMNS)

TIMER_COLUMNS = ["Task", "Duration(min)", "Date", "Start", "End"]
timer_df = load_or_create_csv(TIMER_FILE, TIMER_COLUMNS)

groups_df = load_or_create_csv(GLOBAL_FILES["groups"], ["GroupName", "Admin", "Members"])
group_tasks_df = load_or_create_csv(GLOBAL_FILES["group_tasks"], ["GroupName", "Task", "Status", "AddedBy", "Date", "AssignedTo"])
group_chat_df = load_or_create_csv(GLOBAL_FILES["group_chat"], ["GroupName", "Username", "Message", "Time"])
invites_df = load_or_create_csv(GLOBAL_FILES["invites"], ["ToUser", "FromUser", "GroupName", "Status"])
notifs_df = load_or_create_csv(GLOBAL_FILES["notifs"], ["User", "Message", "Time"])

# ----------------- Helper functions to render & mutate tasks -----------------

def _next_id(df):
    if df.empty:
        return 1
    try:
        return int(df["ID"].max()) + 1
    except Exception:
        return len(df) + 1


def add_task(task_text, priority="Medium", deadline=None, notes=""):
    global tasks_df
    new = {
        "ID": _next_id(tasks_df),
        "Task": task_text,
        "Status": "Pending",
        "DateAdded": today_date,
        "Deadline": deadline if deadline else "",
        "Priority": priority,
        "Notes": notes,
    }
    tasks_df = pd.concat([tasks_df, pd.DataFrame([new])], ignore_index=True)
    save_df(tasks_df, TASKS_FILE)


def update_task_status(task_id, status):
    global tasks_df
    tasks_df.loc[tasks_df["ID"] == task_id, "Status"] = status
    save_df(tasks_df, TASKS_FILE)


def delete_task(task_id):
    global tasks_df
    tasks_df = tasks_df[tasks_df["ID"] != task_id].reset_index(drop=True)
    save_df(tasks_df, TASKS_FILE)


# ----------------- Layout: Tabs -----------------

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Tasks", "⏳ Timer", "🍅 Pomodoro", "👥 Group Workspace", "📊 Analytics"])

# ----------------- Tab 1: Tasks -----------------
with tab1:
    st.header(f"{username}'s Tasks")
    with st.expander("➕ Add a Task", expanded=True):
        task_text = st.text_input("Task description", key="new_task_text")
        prio = st.selectbox("Priority", ["High", "Medium", "Low"], index=1, key="new_task_prio")
        deadline = st.date_input("Deadline (optional)", key="new_task_deadline")
        notes = st.text_area("Notes (optional)", key="new_task_notes")
        if st.button("Add Task", key="add_task_btn"):
            deadline_str = deadline.isoformat() if isinstance(deadline, date) else ""
            add_task(task_text.strip(), priority=prio, deadline=deadline_str, notes=notes.strip())
            st.success("Task added ✅")
            st.experimental_rerun()

    # Filters & sorting
    st.markdown("**Filters**")
    col1, col2, col3 = st.columns(3)
    show_status = col1.selectbox("Status", ["All", "Pending", "Done", "Not Done"], index=0)
    sort_by = col2.selectbox("Sort by", ["DateAdded", "Deadline", "Priority"], index=0)
    search_q = col3.text_input("Search tasks")

    display_df = tasks_df.copy()
    if show_status != "All":
        display_df = display_df[display_df["Status"] == show_status]
    if search_q:
        display_df = display_df[display_df["Task"].str.contains(search_q, case=False, na=False)]

    # Convert deadline to date for sorting where possible
    display_df["_Deadline_parsed"] = display_df["Deadline"].apply(lambda x: parse_date(x))
    if sort_by == "Deadline":
        display_df = display_df.sort_values(by=["_Deadline_parsed"], na_position="last")
    elif sort_by == "Priority":
        # custom priority order
        priority_order = {"High": 0, "Medium": 1, "Low": 2, "": 3}
        display_df["_porder"] = display_df["Priority"].map(priority_order).fillna(3)
        display_df = display_df.sort_values(by=["_porder"]) 
    else:
        display_df = display_df.sort_values(by=["DateAdded"], ascending=False)

    display_df = display_df.drop(columns=["_Deadline_parsed"], errors="ignore")

    if display_df.empty:
        st.info("No tasks yet — add one above!")
    else:
        for _, row in display_df.iterrows():
            cols = st.columns([4, 1, 1, 1, 1])
            task_label = f"{row['Task']}"
            if row.get("Deadline"):
                task_label += f" — due {row['Deadline']}"
            task_label += f"  \nPriority: {row.get('Priority','Medium')} | Status: {row.get('Status','Pending')}"
            cols[0].markdown(task_label)
            if cols[1].button("Done", key=f"done_{row['ID']}"):
                update_task_status(row['ID'], "Done")
                st.experimental_rerun()
            if cols[2].button("Not Done", key=f"notdone_{row['ID']}"):
                update_task_status(row['ID'], "Not Done")
                st.experimental_rerun()
            if cols[3].button("Edit", key=f"edit_{row['ID']}"):
                # Simple inline edit modal using st.session_state
                st.session_state.editing = row['ID']
                st.experimental_rerun()
            if cols[4].button("Delete", key=f"del_{row['ID']}"):
                delete_task(row['ID'])
                st.experimental_rerun()

    # Inline edit area
    if st.session_state.get("editing"):
        edit_id = st.session_state.get("editing")
        r = tasks_df[tasks_df["ID"] == edit_id].iloc[0]
        st.markdown("---")
        st.subheader("Edit Task")
        new_text = st.text_input("Task", value=r["Task"], key="edit_text")
        new_prio = st.selectbox("Priority", ["High", "Medium", "Low"], index=["High","Medium","Low"].index(r.get("Priority","Medium")), key="edit_prio")
        new_deadline = st.date_input("Deadline (leave empty to clear)", key="edit_deadline")
        new_notes = st.text_area("Notes", value=r.get("Notes",""), key="edit_notes")
        if st.button("Save Changes", key="save_edit"):
            tasks_df.loc[tasks_df["ID"] == edit_id, "Task"] = new_text.strip()
            tasks_df.loc[tasks_df["ID"] == edit_id, "Priority"] = new_prio
            tasks_df.loc[tasks_df["ID"] == edit_id, "Deadline"] = new_deadline.isoformat() if isinstance(new_deadline, date) else ""
            tasks_df.loc[tasks_df["ID"] == edit_id, "Notes"] = new_notes.strip()
            save_df(tasks_df, TASKS_FILE)
            del st.session_state["editing"]
            st.success("Saved ✅")
            st.experimental_rerun()

# ----------------- Tab 2: Focus Timer -----------------
with tab2:
    st.header("⏳ Focus Timer (single task)")
    timer_task = st.text_input("Task name (optional)", key="timer_task_input")
    duration_min = st.number_input("Duration (minutes)", min_value=1, max_value=180, value=25, key="timer_duration")

    if not st.session_state.timer.get("running"):
        if st.button("▶ Start Timer", key="start_timer_btn"):
            st.session_state.timer = {
                "running": True,
                "start_time": time.time(),
                "duration": int(duration_min * 60),
                "task": timer_task or "Unnamed Task"
            }
            st.experimental_rerun()
    else:
        elapsed = time.time() - st.session_state.timer["start_time"]
        remaining = max(0, int(st.session_state.timer["duration"] - elapsed))
        mins, secs = divmod(remaining, 60)
        st.metric("Time Remaining", f"{mins:02d}:{secs:02d}")
        if remaining == 0:
            st.session_state.timer["running"] = False
            st.success("⏰ Time’s up!")
            new_entry = {
                "Task": st.session_state.timer["task"],
                "Duration(min)": st.session_state.timer["duration"] // 60,
                "Date": today_date,
                "Start": datetime.fromtimestamp(st.session_state.timer["start_time"]).strftime("%H:%M:%S"),
                "End": datetime.now().strftime("%H:%M:%S"),
            }
            timer_df = pd.concat([timer_df, pd.DataFrame([new_entry])], ignore_index=True)
            save_df(timer_df, TIMER_FILE)
            # small visual cue
            st.balloons()

    st.markdown("### Logged Sessions")
    timer_df_local = load_or_create_csv(TIMER_FILE, TIMER_COLUMNS)
    st.dataframe(timer_df_local, use_container_width=True)

    # Export PDF
    if st.button("📄 Export Timer Log as PDF"):
        class TimerPDF(FPDF):
            def header(self):
                self.set_font("Arial", "B", 16)
                self.cell(0, 10, "Focused Timer Report", ln=True, align="C")
                self.ln(10)

        pdf = TimerPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for _, row in timer_df_local.iterrows():
            pdf.cell(0, 10, f"{row['Date']} | {row['Task']} | {row['Duration(min)']} min", ln=True)
        pdf_file = os.path.join(DATA_DIR, f"{username}_timer_log.pdf")
        pdf.output(pdf_file)
        with open(pdf_file, "rb") as f:
            st.download_button("⬇ Download PDF", f, file_name=os.path.basename(pdf_file))

# ----------------- Tab 3: Pomodoro -----------------
with tab3:
    st.header("🍅 Pomodoro")
    pomo_task = st.text_input("Pomodoro Task", key="pomo_task_input")
    pomo_focus = st.number_input("Focus (min)", min_value=1, max_value=120, value=25, key="pomo_focus")
    pomo_break = st.number_input("Break (min)", min_value=1, max_value=60, value=5, key="pomo_break")

    if not st.session_state.pomo.get("running"):
        if st.button("▶ Start Pomodoro", key="start_pomo_btn"):
            st.session_state.pomo = {
                "running": True,
                "start_time": time.time(),
                "duration": int(pomo_focus * 60),
                "task": pomo_task or "Pomodoro Task",
                "phase": "focus"
            }
            st.experimental_rerun()
    else:
        elapsed = time.time() - st.session_state.pomo["start_time"]
        remaining = max(0, int(st.session_state.pomo["duration"] - elapsed))
        mins, secs = divmod(remaining, 60)
        st.metric("Pomodoro Remaining", f"{mins:02d}:{secs:02d}")
        if remaining == 0:
            st.session_state.pomo["running"] = False
            st.success("🍅 Pomodoro finished! Take a break.")
            # Log into timer_df as a completed session
            new_entry = {
                "Task": st.session_state.pomo["task"],
                "Duration(min)": st.session_state.pomo["duration"] // 60,
                "Date": today_date,
                "Start": datetime.fromtimestamp(st.session_state.pomo["start_time"]).strftime("%H:%M:%S"),
                "End": datetime.now().strftime("%H:%M:%S"),
            }
            timer_df = pd.concat([timer_df, pd.DataFrame([new_entry])], ignore_index=True)
            save_df(timer_df, TIMER_FILE)

# ----------------- Tab 4: Group Workspace -----------------
with tab4:
    st.header("👥 Group Workspace")
    # Create group
    st.subheader("Create Group")
    grp_name = st.text_input("Group name", key="grp_name")
    if st.button("Create Group", key="create_group_btn"):
        if grp_name.strip() and not (groups_df["GroupName"] == grp_name.strip()).any():
            new = {"GroupName": grp_name.strip(), "Admin": username, "Members": username}
            groups_df = pd.concat([groups_df, pd.DataFrame([new])], ignore_index=True)
            save_df(groups_df, GLOBAL_FILES["groups"])
            st.success("Group created ✅")
            st.experimental_rerun()

    # My groups
    st.subheader("Your Groups")
    my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]
    if my_groups.empty:
        st.info("You are not a member of any groups yet.")
    else:
        for _, g in my_groups.iterrows():
            st.markdown(f"**{g['GroupName']}** | Admin: {g['Admin']} | Members: {g['Members']}")

    # Invite members
    st.subheader("Invite")
    if not my_groups.empty:
        sel_group = st.selectbox("Select group to invite to", my_groups["GroupName"], key="invite_select")
        invite_user = st.text_input("Username to invite", key="invite_username")
        if st.button("Send Invite", key="send_inv_btn"):
            if invite_user.strip() and invite_user.strip() != username:
                invites_df = pd.concat([invites_df, pd.DataFrame([{"ToUser": invite_user.strip(), "FromUser": username, "GroupName": sel_group, "Status": "Pending"}])], ignore_index=True)
                save_df(invites_df, GLOBAL_FILES["invites"])
                st.success("Invite sent ✅")

    # Accept / Reject invites
    st.subheader("Pending Invites")
    my_pending = invites_df[(invites_df["ToUser"] == username) & (invites_df["Status"] == "Pending")]
    for i, row in my_pending.iterrows():
        st.write(f"{row['FromUser']} invited you to join {row['GroupName']}")
        if st.button(f"Accept_{i}"):
            groups_df.loc[groups_df["GroupName"] == row['GroupName'], "Members"] = groups_df.loc[groups_df["GroupName"] == row['GroupName'], "Members"].apply(lambda x: x + "," + username if username not in x else x)
            save_df(groups_df, GLOBAL_FILES["groups"])
            invites_df.at[i, "Status"] = "Accepted"
            save_df(invites_df, GLOBAL_FILES["invites"])
            notifs_df = pd.concat([notifs_df, pd.DataFrame([{"User": username, "Message": f"You joined group '{row['GroupName']}'", "Time": datetime.now().strftime("%H:%M:%S") }])], ignore_index=True)
            save_df(notifs_df, GLOBAL_FILES["notifs"])
            st.success("Joined group ✅")
            st.experimental_rerun()
        if st.button(f"Reject_{i}"):
            invites_df.at[i, "Status"] = "Rejected"
            save_df(invites_df, GLOBAL_FILES["invites"])
            st.info("Invite rejected")

    # Notifications
    st.subheader("Notifications")
    my_notifs = notifs_df[notifs_df["User"] == username]
    for _, n in my_notifs.iterrows():
        st.info(f"[{n['Time']}] {n['Message']}")

    # Group tasks & chat
    st.subheader("Group Tasks & Chat")
    if not my_groups.empty:
        sel_group2 = st.selectbox("Select group to view", my_groups["GroupName"], key="group_view_select")
        # Group tasks
        st.markdown("**Tasks in group**")
        grp_tasks_local = group_tasks_df[group_tasks_df["GroupName"] == sel_group2]
        new_grp_task = st.text_input("New group task", key="new_grp_task")
        assignee = st.text_input("Assign to (optional)", key="new_grp_assignee")
        if st.button("Add group task", key="add_grp_task_btn"):
            if new_grp_task.strip():
                newt = {"GroupName": sel_group2, "Task": new_grp_task.strip(), "Status": "Pending", "AddedBy": username, "Date": today_date, "AssignedTo": assignee.strip()}
                group_tasks_df = pd.concat([group_tasks_df, pd.DataFrame([newt])], ignore_index=True)
                save_df(group_tasks_df, GLOBAL_FILES["group_tasks"])
                st.success("Group task added ✅")
                st.experimental_rerun()
        for i, r in grp_tasks_local.iterrows():
            cols = st.columns([4, 1, 1, 1])
            cols[0].markdown(f"{r['Task']} — added by {r['AddedBy']} | assigned: {r.get('AssignedTo','-')} | status: {r['Status']}")
            if cols[1].button("Mark Done", key=f"gdone_{i}"):
                group_tasks_df.loc[i, "Status"] = "Done"
                save_df(group_tasks_df, GLOBAL_FILES["group_tasks"])
                st.experimental_rerun()
            if cols[2].button("Delete", key=f"gdel_{i}"):
                group_tasks_df = group_tasks_df.drop(i).reset_index(drop=True)
                save_df(group_tasks_df, GLOBAL_FILES["group_tasks"])
                st.experimental_rerun()
            if cols[3].button("Comment", key=f"gcomm_{i}"):
                st.session_state["commenting_on"] = i
                st.experimental_rerun()

        # Chat UI
        st.markdown("**Chat**")
        chat_message = st.text_input("Message", key="grp_chat_msg")
        if st.button("Send message", key="grp_chat_send_btn"):
            if chat_message.strip():
                group_chat_df = pd.concat([group_chat_df, pd.DataFrame([{"GroupName": sel_group2, "Username": username, "Message": chat_message.strip(), "Time": datetime.now().strftime("%H:%M:%S")}])], ignore_index=True)
                save_df(group_chat_df, GLOBAL_FILES["group_chat"])
                st.experimental_rerun()

        chat_local = group_chat_df[group_chat_df["GroupName"] == sel_group2]
        for _, m in chat_local.iterrows():
            st.write(f"[{m['Time']}] **{m['Username']}**: {m['Message']}")

# ----------------- Tab 5: Analytics -----------------
with tab5:
    st.header("📊 Analytics & Productivity")
    st.markdown("Insights based on your tasks and timer logs")

    # Basic task stats
    total = len(tasks_df)
    done = len(tasks_df[tasks_df["Status"] == "Done"]) if total > 0 else 0
    pending = len(tasks_df[tasks_df["Status"] == "Pending"]) if total > 0 else 0
    st.metric("Total tasks", total)
    st.metric("Completed tasks", done)
    st.metric("Pending tasks", pending)

    # Priority distribution
    prio_counts = tasks_df["Priority"].value_counts().reindex(["High","Medium","Low"]).fillna(0)
    fig, ax = plt.subplots()
    ax.bar(prio_counts.index.astype(str), prio_counts.values)
    ax.set_title("Tasks by Priority")
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    st.pyplot(fig)

    # Timer summary (weekly)
    timer_local = load_or_create_csv(TIMER_FILE, TIMER_COLUMNS)
    if not timer_local.empty:
        timer_local['Date_parsed'] = pd.to_datetime(timer_local['Date'], errors='coerce')
        last7 = (pd.Timestamp.today() - pd.Timedelta(days=7)).normalize()
        weekly = timer_local[timer_local['Date_parsed'] >= last7]
        if not weekly.empty:
            weekly_summary = weekly.groupby('Date')['Duration(min)'].sum()
            fig2, ax2 = plt.subplots()
            ax2.plot(weekly_summary.index, weekly_summary.values)
            ax2.set_title('Last 7 days: Focus minutes')
            ax2.set_xlabel('Date')
            ax2.set_ylabel('Minutes')
            st.pyplot(fig2)
        else:
            st.info("No timer activity in the last 7 days")
    else:
        st.info("No timer logs yet — start some sessions to see analytics")

    # Quick tips box
    st.markdown("---")
    st.subheader("Mentor tip")
    st.write("Small, consistent focus beats sporadic marathon sessions. Aim for daily 2–4 Pomodoros and review your priorities weekly. You've got this — keep stacking wins!")

# --------------- End of app ---------------

# Note for developer: This code keeps CSV-based storage for simplicity. For production or multi-user real-time sync, migrate to SQLite or a small backend.
