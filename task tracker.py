import streamlit as st
import pandas as pd
import datetime
import time
import hashlib
from streamlit_authenticator import Authenticate

# Initialize session state variables
if 'tasks' not in st.session_state:
    st.session_state.tasks = []
if 'notes' not in st.session_state:
    st.session_state.notes = []
if 'timer' not in st.session_state:
    st.session_state.timer = 0
if 'pomodoro' not in st.session_state:
    st.session_state.pomodoro = 0
if 'authentication_status' not in st.session_state:
    st.session_state.authentication_status = False
if 'username' not in st.session_state:
    st.session_state.username = None

# User authentication
def authenticate_user():
    credentials = {
        "usernames": {
            "admin": {
                "email": "admin@example.com",
                "name": "Admin User",
                "password": hashlib.sha256("admin123".encode()).hexdigest()
            }
        }
    }
    authenticator = Authenticate(credentials, "my_cookie", "my_key", cookie_expiry_days=30)
    name, authentication_status, username = authenticator.login("Login", "main")
    if authentication_status:
        st.session_state.authentication_status = True
        st.session_state.username = username
        authenticator.logout("Logout", "main")
    return authentication_status

# Main application logic
def app():
    if not st.session_state.authentication_status:
        if authenticate_user():
            st.success(f"Welcome {st.session_state.username}")
        else:
            st.error("Please enter a valid username and password")
            return

    st.title("Task Tracker App")

    # Task Management
    with st.expander("Manage Tasks"):
        task = st.text_input("Add a new task")
        if st.button("Add Task"):
            if task:
                st.session_state.tasks.append({"task": task, "status": "Pending"})
                st.success("Task added!")
            else:
                st.warning("Please enter a task.")

        for idx, task in enumerate(st.session_state.tasks):
            col1, col2 = st.columns([3, 1])
            col1.write(f"{task['task']} ({task['status']})")
            if col2.button("Done", key=f"done_{idx}"):
                st.session_state.tasks[idx]['status'] = "Done"
            if col2.button("Delete", key=f"delete_{idx}"):
                st.session_state.tasks.pop(idx)
                st.session_state.tasks = st.session_state.tasks  # Refresh list

    # Timer
    with st.expander("Timer"):
        if st.button("Start Timer"):
            st.session_state.timer = 0
        if st.button("Reset Timer"):
            st.session_state.timer = 0
        st.write(f"Timer: {st.session_state.timer} seconds")
        time.sleep(1)
        st.session_state.timer += 1

    # Pomodoro Timer
    with st.expander("Pomodoro Timer"):
        if st.button("Start Pomodoro"):
            st.session_state.pomodoro = 25 * 60  # 25 minutes
        if st.button("Reset Pomodoro"):
            st.session_state.pomodoro = 0
        st.write(f"Pomodoro Timer: {st.session_state.pomodoro // 60} minutes {st.session_state.pomodoro % 60} seconds")
        if st.session_state.pomodoro > 0:
            time.sleep(1)
            st.session_state.pomodoro -= 1

    # Group Workspace
    with st.expander("Group Workspace"):
        note = st.text_area("Add a note")
        if st.button("Add Note"):
            if note:
                st.session_state.notes.append(note)
                st.success("Note added!")
            else:
                st.warning("Please enter a note.")

        st.write("Notes:")
        for note in st.session_state.notes:
            st.write(f"- {note}")

if __name__ == "__main__":
    app()
