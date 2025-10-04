import streamlit as st
import pandas as pd
import os
import hashlib
import time
from datetime import datetime, date

# ---------------- Utility Functions ----------------
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

today_date = str(date.today())

# ---------------- Session State ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None

# ---------------- Login / Register ----------------
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
                st.experimental_rerun()
            else:
                st.error("Wrong password!")
        else:
            st.error("Username not found!")

# ---------------- Main App ----------------
if st.session_state.logged_in:
    st.title(f"TaskUni - {st.session_state.username}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Tasks", "⏳ Timer", "🍅 Pomodoro", "👥 Group Workspace"])
    
    # ---------------- Tab 1: Tasks ----------------
    with tab1:
        st.subheader("Your Tasks")
        TASKS_FILE = f"tasks_{st.session_state.username}.csv"
        tasks = load_or_create_csv(TASKS_FILE, ["Task","Status","Date"])
        if "tasks_data" not in st.session_state:
            st.session_state.tasks_data = tasks

        task_input = st.text_input("Add a new task")
        if st.button("➕ Add Task"):
            if task_input.strip():
                new_task = {"Task":task_input.strip(), "Status":"Pending", "Date":today_date}
                st.session_state.tasks_data = pd.concat([st.session_state.tasks_data, pd.DataFrame([new_task])], ignore_index=True)
                save_csv(st.session_state.tasks_data, TASKS_FILE)
                st.success("Task added!")

        if not st.session_state.tasks_data.empty:
            for i, row in st.session_state.tasks_data.iterrows():
                cols = st.columns([4,1,1,1])
                status_color = "yellow" if row["Status"]=="Pending" else ("green" if row["Status"]=="Done" else "red")
                cols[0].markdown(f"<span style='color:{status_color}'>{row['Task']} ({row['Status']})</span>", unsafe_allow_html=True)
                if cols[1].button("Done", key=f"done_{i}"):
                    st.session_state.tasks_data.at[i,"Status"]="Done"; save_csv(st.session_state.tasks_data,TASKS_FILE)
                if cols[2].button("Not Done", key=f"notdone_{i}"):
                    st.session_state.tasks_data.at[i,"Status"]="Not Done"; save_csv(st.session_state.tasks_data,TASKS_FILE)
                if cols[3].button("Delete", key=f"delete_{i}"):
                    st.session_state.tasks_data = st.session_state.tasks_data.drop(i).reset_index(drop=True)
                    save_csv(st.session_state.tasks_data,TASKS_FILE)
    
    # ---------------- Tab 2: Timer ----------------
    with tab2:
        st.subheader("Focus Timer")
        TIMER_FILE = f"timer_{st.session_state.username}.csv"
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
    
    # ---------------- Tab 3: Pomodoro ----------------
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
    
    # ---------------- Tab 4: Group Workspace ----------------
    with tab4:
        st.subheader("Group Workspace")
        GROUPS_FILE = "groups.csv"
        GROUP_TASKS_FILE = "group_tasks.csv"
        GROUP_CHAT_FILE = "group_chat.csv"
        INVITES_FILE = "group_invites.csv"
        
        groups_df = load_or_create_csv(GROUPS_FILE, ["GroupName","Admin","Members"])
        group_tasks = load_or_create_csv(GROUP_TASKS_FILE, ["GroupName","Task","Status","AddedBy","Date"])
        group_chat = load_or_create_csv(GROUP_CHAT_FILE, ["GroupName","Username","Message","Time"])
        invites_df = load_or_create_csv(INVITES_FILE, ["ToUser","FromUser","GroupName","Status"])
        
        if st.button("➕ Create Group"):
            group_name = st.text_input("Group Name")
            friends_input = st.text_input("Add Friends (comma-separated usernames)")
            if group_name and friends_input:
                members = [st.session_state.username] + [f.strip() for f in friends_input.split(",")]
                new_group = {"GroupName":group_name,"Admin":st.session_state.username,"Members":",".join(members)}
                groups_df = pd.concat([groups_df,pd.DataFrame([new_group])], ignore_index=True)
                save_csv(groups_df,GROUPS_FILE)
                st.success("Group created! Members added automatically.")
