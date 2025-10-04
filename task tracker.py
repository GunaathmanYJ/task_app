import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# ---------------- Utility ----------------
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

def save_csv(df, file):
    df.to_csv(file, index=False)

def color_status(val):
    if val == "Done":
        return "background-color: lightgreen"
    elif val == "Pending":
        return "background-color: yellow"
    else:
        return "background-color: lightcoral"

today_date = str(date.today())

# ---------------- LOGIN/REGISTER ----------------
users_file = "users.csv"
users = load_or_create_csv(users_file, ["Username","Password"])

st.title("🔐 TaskUni Login/Register")
auth_mode = st.radio("Choose:", ["Login", "Register"])

if "username_input" not in st.session_state:
    st.session_state.username_input = ""
if "password_input" not in st.session_state:
    st.session_state.password_input = ""

st.session_state.username_input = st.text_input("Username", st.session_state.username_input)
st.session_state.password_input = st.text_input("Password", st.session_state.password_input, type="password")

if auth_mode == "Register" and st.button("Register"):
    if st.session_state.username_input.strip() and st.session_state.password_input.strip():
        if st.session_state.username_input in users["Username"].values:
            st.error("Username already exists")
        else:
            users = pd.concat([users,pd.DataFrame([{"Username":st.session_state.username_input.strip(),"Password":st.session_state.password_input.strip()}])], ignore_index=True)
            save_csv(users, users_file)
            st.success("Registered successfully! Please login.")
elif auth_mode == "Login" and st.button("Login"):
    if st.session_state.username_input.strip() and st.session_state.password_input.strip():
        if st.session_state.username_input in users["Username"].values:
            pw = users.loc[users["Username"]==st.session_state.username_input,"Password"].values[0]
            if pw == st.session_state.password_input:
                st.session_state.username = st.session_state.username_input
            else:
                st.error("Wrong password")
        else:
            st.error("Username not found")

if "username" not in st.session_state:
    st.stop()

username = st.session_state.username

# ---------------- TABS ----------------
tab1, tab2, tab3, tab4 = st.tabs(["📋 Tasks", "⏳ Timer", "🍅 Pomodoro", "👥 Group"])

# ---------------- TAB 1: TASKS ----------------
with tab1:
    st.subheader(f"{username}'s Tasks")
    tasks_file = f"tasks_{username}.csv"
    tasks = load_or_create_csv(tasks_file, ["Task","Status","Date"])

    if "task_input" not in st.session_state:
        st.session_state.task_input = ""
    st.session_state.task_input = st.text_input("Add Task", st.session_state.task_input)

    def update_task_status(file, i, status):
        df = pd.read_csv(file)
        df.at[i, "Status"] = status
        df.to_csv(file, index=False)
        st.experimental_rerun()

    def delete_task(file, i):
        df = pd.read_csv(file)
        df = df.drop(i).reset_index(drop=True)
        df.to_csv(file, index=False)
        st.experimental_rerun()

    if st.button("Add Task") and st.session_state.task_input.strip():
        new_task = {"Task":st.session_state.task_input.strip(),"Status":"Pending","Date":today_date}
        tasks = pd.concat([tasks,pd.DataFrame([new_task])], ignore_index=True)
        save_csv(tasks, tasks_file)
        st.session_state.task_input=""
        st.experimental_rerun()

    if not tasks.empty:
        for i, row in tasks.iterrows():
            col1, col2, col3 = st.columns([1,1,1])
            col1.button("Done", key=f"done_{i}", on_click=update_task_status, args=(tasks_file, i, "Done"))
            col2.button("Not Done", key=f"notdone_{i}", on_click=update_task_status, args=(tasks_file, i, "Not Done"))
            col3.button("Delete", key=f"delete_{i}", on_click=delete_task, args=(tasks_file, i))
        st.dataframe(tasks.style.applymap(color_status, subset=["Status"]), use_container_width=True)

# ---------------- TAB 2: TIMER ----------------
with tab2:
    st.subheader("⏳ Focus Timer")
    timer_file = f"timer_{username}.csv"
    timer_data = load_or_create_csv(timer_file, ["Task","Duration(min)","Date","Start","End"])

    if "timer_running" not in st.session_state:
        st.session_state.timer_running = False
        st.session_state.timer_paused = False
        st.session_state.timer_elapsed = 0
        st.session_state.timer_task_name = ""
        st.session_state.timer_start_time = None

    col1, col2, col3 = st.columns(3)
    timer_task = st.text_input("Timer Task", st.session_state.get("timer_task_name",""))
    timer_duration = st.number_input("Duration (minutes)",1,180,25)

    if col1.button("▶ Start Timer"):
        st.session_state.timer_running = True
        st.session_state.timer_paused = False
        st.session_state.timer_start_time = time.time()
        st.session_state.timer_elapsed = 0
        st.session_state.timer_task_name = timer_task

    if col2.button("⏸ Pause/▶ Resume"):
        if st.session_state.timer_running:
            if st.session_state.timer_paused:
                st.session_state.timer_paused = False
                st.session_state.timer_start_time = time.time()
            else:
                st.session_state.timer_paused = True
                st.session_state.timer_elapsed += time.time() - st.session_state.timer_start_time

    if col3.button("⏹ Stop Timer") and st.session_state.timer_running:
        st.session_state.timer_running = False
        elapsed = st.session_state.timer_elapsed + (time.time() - st.session_state.timer_start_time if st.session_state.timer_start_time else 0)
        new_entry = {
            "Task": st.session_state.timer_task_name,
            "Duration(min)": round(elapsed/60,1),
            "Date": today_date,
            "Start": datetime.fromtimestamp(st.session_state.timer_start_time).strftime("%H:%M:%S") if st.session_state.timer_start_time else "",
            "End": datetime.now().strftime("%H:%M:%S")
        }
        timer_data = pd.concat([timer_data, pd.DataFrame([new_entry])], ignore_index=True)
        save_csv(timer_data, timer_file)
        st.session_state.timer_elapsed = 0
        st.session_state.timer_start_time = None
        st.experimental_rerun()

    if st.session_state.timer_running:
        elapsed = (time.time() - st.session_state.timer_start_time if not st.session_state.timer_paused else 0) + st.session_state.timer_elapsed
        remaining = max(0, timer_duration*60 - elapsed)
        mins, secs = divmod(int(remaining),60)
        st.metric("Remaining", f"{mins:02d}:{secs:02d}")

    st.markdown("### Today's Timer History")
    today_timer = timer_data[timer_data["Date"]==today_date]
    if not today_timer.empty:
        st.dataframe(today_timer,use_container_width=True)

# ---------------- TAB 3: POMODORO ----------------
with tab3:
    st.subheader("🍅 Pomodoro")
    pomo_file = f"pomo_{username}.csv"
    pomo_data = load_or_create_csv(pomo_file, ["Task","Duration(min)","Date","Start","End"])

    if "pomo_running" not in st.session_state:
        st.session_state.pomo_running = False
        st.session_state.pomo_paused = False
        st.session_state.pomo_elapsed = 0
        st.session_state.pomo_task_name = ""
        st.session_state.pomo_start_time = None

    col1, col2, col3 = st.columns(3)
    pomo_task = st.text_input("Pomodoro Task", st.session_state.get("pomo_task_name",""))
    pomo_duration = st.number_input("Focus Duration (minutes)",1,120,25)

    if col1.button("▶ Start Pomodoro"):
        st.session_state.pomo_running = True
        st.session_state.pomo_paused = False
        st.session_state.pomo_start_time = time.time()
        st.session_state.pomo_elapsed = 0
        st.session_state.pomo_task_name = pomo_task

    if col2.button("⏸ Pause/▶ Resume Pomodoro"):
        if st.session_state.pomo_running:
            if st.session_state.pomo_paused:
                st.session_state.pomo_paused = False
                st.session_state.pomo_start_time = time.time()
            else:
                st.session_state.pomo_paused = True
                st.session_state.pomo_elapsed += time.time() - st.session_state.pomo_start_time

    if col3.button("⏹ Stop Pomodoro") and st.session_state.pomo_running:
        st.session_state.pomo_running = False
        elapsed = st.session_state.pomo_elapsed + (time.time() - st.session_state.pomo_start_time if st.session_state.pomo_start_time else 0)
        new_entry = {
            "Task": st.session_state.pomo_task_name,
            "Duration(min)": round(elapsed/60,1),
            "Date": today_date,
            "Start": datetime.fromtimestamp(st.session_state.pomo_start_time).strftime("%H:%M:%S") if st.session_state.pomo_start_time else "",
            "End": datetime.now().strftime("%H:%M:%S")
        }
        pomo_data = pd.concat([pomo_data, pd.DataFrame([new_entry])], ignore_index=True)
        save_csv(pomo_data, pomo_file)
        st.session_state.pomo_elapsed = 0
        st.session_state.pomo_start_time = None
        st.experimental_rerun()

    if st.session_state.pomo_running:
        elapsed = (time.time() - st.session_state.pomo_start_time if not st.session_state.pomo_paused else 0) + st.session_state.pomo_elapsed
        remaining = max(0, pomo_duration*60 - elapsed)
        mins, secs = divmod(int(remaining),60)
        st.metric("Pomodoro Remaining", f"{mins:02d}:{secs:02d}")

    st.markdown("### Today's Pomodoro History")
    today_pomo = pomo_data[pomo_data["Date"]==today_date]
    if not today_pomo.empty:
        st.dataframe(today_pomo,use_container_width=True)

# ---------------- TAB 4: GROUP ----------------
with tab4:
    st.subheader("Group Workspace")

    GROUPS_FILE="groups.csv"
    GROUP_TASKS_FILE="group_tasks.csv"
    GROUP_CHAT_FILE="group_chat.csv"

    groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Members"])
    group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
    group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])

    st_autorefresh(interval=5000)  # Refresh every 5 seconds for live chat

    if "creating_group" not in st.session_state:
        st.session_state.creating_group = False
        st.session_state.new_group_name = ""

    if st.button("➕ Create New Group"):
        st.session_state.creating_group=True
        st.session_state.new_group_name=""

    if st.session_state.creating_group:
        group_name = st.text_input("Enter Group Name", value=st.session_state.new_group_name, key="group_name_input")
        if st.button("OK", key="group_name_ok") and group_name.strip():
            if (groups_df["GroupName"]==group_name.strip()).any():
                st.error("Group exists!")
            else:
                groups_df=pd.concat([groups_df,pd.DataFrame([{"GroupName":group_name.strip(),"Members":username}])],ignore_index=True)
                save_csv(groups_df,GROUPS_FILE)
                st.success(f"Group '{group_name.strip()}' created!")
                st.session_state.new_group_name=group_name.strip()

        if st.session_state.new_group_name:
            member_input = st.text_input("Add Member by Username", key="add_member_input")
            if st.button("Add Member", key="add_member_btn") and member_input.strip():
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

    my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]
    for _, grp in my_groups.iterrows():
        group_key = grp['GroupName'].replace(" ","_")
        st.markdown(f"## {grp['GroupName']}")

        # Tasks
        st.markdown("### Tasks")
        grp_tasks_sel = group_tasks[group_tasks["GroupName"]==grp['GroupName']]

        if "task_input_"+group_key not in st.session_state:
            st.session_state["task_input_"+group_key]=""
        st.session_state["task_input_"+group_key] = st.text_input("Add Task", st.session_state["task_input_"+group_key], key=f"task_input_{group_key}")

        if st.button("Add Task", key=f"add_task_btn_{group_key}") and st.session_state["task_input_"+group_key].strip():
            new_task = {"GroupName":grp['GroupName'],"Task":st.session_state["task_input_"+group_key].strip(),
                        "Status":"Pending","AddedBy":username,"Date":today_date}
            group_tasks = pd.concat([group_tasks,pd.DataFrame([new_task])],ignore_index=True)
            save_csv(group_tasks,GROUP_TASKS_FILE)
            st.session_state["task_input_"+group_key]=""
            st.experimental_rerun()

        if not grp_tasks_sel.empty:
            st.dataframe(grp_tasks_sel.style.applymap(color_status, subset=["Status"]), use_container_width=True)

        # Chat
        st.markdown("### Chat")
        if "chat_input_"+group_key not in st.session_state:
            st.session_state["chat_input_"+group_key]=""
        st.session_state["chat_input_"+group_key] = st.text_input("Message", st.session_state["chat_input_"+group_key], key=f"chat_input_{group_key}")

        if st.button("Send", key=f"send_btn_{group_key}") and st.session_state["chat_input_"+group_key].strip():
            new_msg = {"GroupName":grp['GroupName'],"Username":username,
                       "Message":st.session_state["chat_input_"+group_key].strip(),"Time":datetime.now().strftime("%H:%M:%S")}
            group_chat = pd.concat([group_chat,pd.DataFrame([new_msg])],ignore_index=True)
            save_csv(group_chat,GROUP_CHAT_FILE)
            st.session_state["chat_input_"+group_key]=""
            st.experimental_rerun()

        chat_sel = group_chat[group_chat["GroupName"]==grp['GroupName']]
        for _, row in chat_sel.iterrows():
            st.write(f"[{row['Time']}] **{row['Username']}**: {row['Message']}")
