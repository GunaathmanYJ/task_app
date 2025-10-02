import streamlit as st
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Task App", layout="wide")
st.title("📋 Task Tracker")

# Initialize tasks
if "tasks" not in st.session_state:
    st.session_state.tasks = pd.DataFrame(columns=["Task", "Status"])

# Initialize input state
if "task_input" not in st.session_state:
    st.session_state.task_input = ""

# Add task input
task_name = st.text_input("Enter your task", key="task_input", value=st.session_state.task_input)

if st.button("Add Task") and task_name:
    st.session_state.tasks = pd.concat(
        [st.session_state.tasks, pd.DataFrame([[task_name, "Pending"]], columns=["Task", "Status"])],
        ignore_index=True
    )
    st.session_state.task_input = ""  # clear input automatically after adding

# Display tasks
st.subheader("📝 Tasks")
for i, row in st.session_state.tasks.iterrows():
    color = "#FFA500"  # Pending
    if row['Status'] == "Done":
        color = "#00C853"
    elif row['Status'] == "Not Done":
        color = "#D50000"

    col1, col2, col3 = st.columns([5, 1, 1])
    col1.markdown(
        f"<div style='padding:10px; border-radius:8px; background-color:{color}; color:white'>{i+1}. {row['Task']} - {row['Status']}</div>",
        unsafe_allow_html=True
    )

    if col2.button("Done", key=f"done_{i}"):
        st.session_state.tasks.at[i, "Status"] = "Done"

    if col3.button("Not Done", key=f"notdone_{i}"):
        st.session_state.tasks.at[i, "Status"] = "Not Done"

# Task report card
st.subheader("📊 Task Report Card")
if not st.session_state.tasks.empty:
    def highlight_status(status):
        if status == "Done":
            return 'background-color: #00C853; color: white'
        elif status == "Not Done":
            return 'background-color: #D50000; color: white'
