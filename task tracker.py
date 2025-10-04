import streamlit as st
import pandas as pd
import os
import hashlib
import time
from datetime import datetime, date

# ------------------ UTILITY FUNCTIONS ------------------
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
    if val == "Done":
        return 'background-color: lightgreen'
    elif val == "Pending":
        return 'background-color: yellow'
    elif val == "Not Done":
        return 'background-color: red'

today_date = str(date.today())

# ------------------ SESSION STATE ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None

# ------------------ LOGIN / REGISTER ------------------
if not st.session_state.logged_in:
    st.title("🔐 TaskUni Login / Register")
    users_file = "users.csv"
    users = load_or_create_csv(users_file, ["Username","Password"])
    
    choice = st.radio("Login or Register", ["Login","Register"])
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    
    if choice=="Register" and st.button("Register"):
        if username_input.strip() == "" or password_input.strip() == "":
            st.warning("Please fill both fields.")
        elif username_input in users["Username"].values:
            st.error("Username already exists!")
        else:
            users = pd.concat([users, pd.DataFrame([{
                "Username":username_input.strip(),
                "Password":hash_password(password_input.strip())
            }])], ignore_index=True)
            save_csv(users, users_file)
            st.success("Registered! Now login.")
            
    if choice=="Login" and st.button("Login"):
        if username_input.strip() in users["Username"].values:
            stored_pass = users.loc[users["Username"]==username_input.strip(), "Password"].values[0]
            if stored_pass == hash_password(password_input.strip()):
                st.session_state.logged_in = True
                st.session_state.username = username_input.strip()
                st.success(f"Welcome {st.session_state.username}!")
            else:
                st.error("Wrong password!")
        else:
            st.error("Username not found!")

# ------------------ MAIN APP ------------------
if st.session_state.logged_in:
    username = st.session_state.username
    st.title(f"TaskUni - {username}")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Tasks", "⏳ Timer", "🍅 Pomodoro", "👥 Group Workspace"])
    
    # ------------------ TAB 1: TASKS ------------------
    with tab1:
        st.subheader("Your Tasks")
        TASKS_FILE = f"tasks_{username}.csv"
        tasks = load_or_create_csv(TASKS_FILE, ["Task","Status","Date"])
        
        task_input = st.text_input("Add a new task")
        if st.button("➕ Add Task"):
            if task_input.strip():
                tasks = pd.concat([tasks, pd.DataFrame([{"Task":task_input.strip(), "Status":"Pending", "Date":today_date}])], ignore_index=True)
                save_csv(tasks, TASKS_FILE)
                st.success("Task added!")

        if not tasks.empty:
            # Display as styled dataframe (report sheet)
            st.dataframe(tasks.style.applymap(color_status, subset=["Status"]), use_container_width=True)
            
            # Buttons below dataframe for single-click update
            st.markdown("### Update Task Status")
            for i, row in tasks.iterrows():
                cols = st.columns([4,1,1,1])
                cols[0].write(f"{row['Task']}")
                if cols[1].button("Done", key=f"done_{i}"):
                    tasks.at[i,"Status"]="Done"; save_csv(tasks,TASKS_FILE)
                    st.experimental_rerun()
                if cols[2].button("Not Done", key=f"notdone_{i}"):
                    tasks.at[i,"Status"]="Not Done"; save_csv(tasks,TASKS_FILE)
                    st.experimental_rerun()
                if cols[3].button("Delete", key=f"delete_{i}"):
                    tasks = tasks.drop(i).reset_index(drop=True); save_csv(tasks,TASKS_FILE)
                    st.experimental_rerun()
    
    # ------------------ TAB 2: TIMER ------------------
    with tab2:
        st.subheader("Focus Timer")
        TIMER_FILE = f"timer_{username}.csv"
        timer_data = load_or_create_csv(TIMER_FILE, ["Task","Duration(min)","Date","Start","End"])

        timer_task = st.text_input("Task name for timer")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=180, value=25)
        if st.button("▶ Start Timer"):
            start_time = time.time()
            st.success("Timer started...")
            time.sleep(duration*60)
            st.success("⏰ Time’s up!")
            end_time = time.time()
            new_entry = {"Task":timer_task,"Duration(min)":duration,"Date":today_date,
                         "Start":datetime.fromtimestamp(start_time).strftime("%H:%M:%S"),
                         "End":datetime.fromtimestamp(end_time).strftime("%H:%M:%S")}
            timer_data = pd.concat([timer_data, pd.DataFrame([new_entry])], ignore_index=True)
            save_csv(timer_data,TIMER_FILE)

        st.markdown("### Logged Sessions")
        st.dataframe(timer_data, use_container_width=True)

    # ------------------ TAB 3: POMODORO ------------------
    with tab3:
        st.subheader("Pomodoro Timer")
        pomo_task = st.text_input("Pomodoro Task", key="pomo_task")
        pomo_duration = st.number_input("Focus Duration (minutes)", 1, 120, 25)
        break_duration = st.number_input("Break Duration (minutes)", 1, 60, 5)
        if st.button("▶ Start Pomodoro"):
            st.success(f"Pomodoro started for {pomo_duration} min! Focus!")
            time.sleep(pomo_duration*60)
            st.info(f"Take a break for {break_duration} min!")
            time.sleep(break_duration*60)
            st.success("Pomodoro cycle completed!")

    # ------------------ TAB 4: GROUP WORKSPACE ------------------
    with tab4:
        st.subheader("Premium Group Workspace")
        GROUPS_FILE = "groups.csv"
        GROUP_TASKS_FILE = "group_tasks.csv"
        GROUP_CHAT_FILE = "group_chat.csv"
        
        groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Admin","Members"])
        group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
        group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])
        
        # Create group
        if st.button("➕ Create Group"):
            group_name = st.text_input("Group Name")
            friends_input = st.text_input("Add Friends (comma-separated usernames)")
            if group_name and friends_input:
                members = [username] + [f.strip() for f in friends_input.split(",")]
                new_group = {"GroupName":group_name,"Admin":username,"Members":",".join(members)}
                groups_df = pd.concat([groups_df,pd.DataFrame([new_group])], ignore_index=True)
                save_csv(groups_df,GROUPS_FILE)
                st.success("Group created! Members added automatically.")

        # Show groups user belongs to
        my_groups = groups_df[groups_df["Members"].str.contains(username, na=False)]
        if not my_groups.empty:
            st.markdown("### Your Groups")
            for _,grp in my_groups.iterrows():
                st.write(f"**{grp['GroupName']}** | Admin: {grp['Admin']} | Members: {grp['Members']}")

            selected_group = st.selectbox("Select Group", my_groups["GroupName"])
            
            # Group Tasks
            st.markdown("#### Group Tasks")
            group_tasks_sel = group_tasks[group_tasks["GroupName"]==selected_group]
            new_task = st.text_input("Add Group Task")
            if st.button("Add Task to Group"):
                if new_task.strip():
                    group_tasks = pd.concat([group_tasks,pd.DataFrame([{
                        "GroupName":selected_group,
                        "Task":new_task.strip(),
                        "Status":"Pending",
                        "AddedBy":username,
                        "Date":today_date
                    }])], ignore_index=True)
                    save_csv(group_tasks,GROUP_TASKS_FILE)
                    st.success("Task added to group!")
            if not group_tasks_sel.empty:
                st.dataframe(group_tasks_sel.style.applymap(color_status, subset=["Status"]), use_container_width=True)

            # Group Chat
            st.markdown("#### Group Chat")
            chat_msg = st.text_input("Enter message", key="chat_input")
            if st.button("Send Message"):
                if chat_msg.strip():
                    group_chat = pd.concat([group_chat,pd.DataFrame([{
                        "GroupName":selected_group,
                        "Username":username,
                        "Message":chat_msg.strip(),
                        "Time":datetime.now().strftime("%H:%M:%S")
                    }])], ignore_index=True)
                    save_csv(group_chat,GROUP_CHAT_FILE)
                    st.success("Message sent!")
            chat_sel = group_chat[group_chat["GroupName"]==selected_group]
            for _,row in chat_sel.iterrows():
                st.write(f"[{row['Time']}] **{row['Username']}**: {row['Message']}")
