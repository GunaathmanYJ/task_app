import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time

st.set_page_config(page_title="TaskUni", layout="wide")
st.title("📌 TaskUni — Your personal Task tracker")

# ---------------- Files for persistent storage ----------------
TASKS_FILE = "tasks_data.csv"
TIMER_FILE = "timer_data.csv"

# Ensure files exist
if not os.path.exists(TASKS_FILE):
    pd.DataFrame(columns=["User","Task","Status","Date"]).to_csv(TASKS_FILE,index=False)
if not os.path.exists(TIMER_FILE):
    pd.DataFrame(columns=["User","Task","Target_HMS","Focused_HMS","Date"]).to_csv(TIMER_FILE,index=False)

# Load CSV
if "tasks" not in st.session_state:
    st.session_state.tasks = pd.read_csv(TASKS_FILE)
if "timer_data" not in st.session_state:
    st.session_state.timer_data = pd.read_csv(TIMER_FILE)
if "countdown_running" not in st.session_state:
    st.session_state.countdown_running = False
if "current_countdown_task" not in st.session_state:
    st.session_state.current_countdown_task = ""

today_date = datetime.now().strftime("%d-%m-%Y")

# ---------------- Sidebar: Username ----------------
st.sidebar.subheader("👤 Enter your name")
username = st.sidebar.text_input("Your name:", value="")
if username.strip() == "":
    st.info("Please enter your name to continue.")
    st.stop()  # stop until user enters name

# ---------------- Filter data for user ----------------
user_tasks = st.session_state.tasks[st.session_state.tasks['User']==username]
user_timer_data = st.session_state.timer_data[st.session_state.timer_data['User']==username]

# ---------------- Button functions ----------------
def mark_done(idx):
    st.session_state.tasks.at[idx,"Status"]="Done"
    st.session_state.tasks.to_csv(TASKS_FILE,index=False)

def mark_notdone(idx):
    st.session_state.tasks.at[idx,"Status"]="Not Done"
    st.session_state.tasks.to_csv(TASKS_FILE,index=False)

def delete_task(idx):
    st.session_state.tasks = st.session_state.tasks.drop(idx).reset_index(drop=True)
    st.session_state.tasks.to_csv(TASKS_FILE,index=False)

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer"])

# ---------------- Task Tracker ----------------
with tab1:
    st.subheader(f"Hello {username}, add or view your tasks")
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input.strip():
        new_task = {"User": username, "Task": task_name_input.strip(),"Status":"Pending","Date":today_date}
        st.session_state.tasks = pd.concat([st.session_state.tasks,pd.DataFrame([new_task])],ignore_index=True)
        st.session_state.tasks.to_csv(TASKS_FILE,index=False)
        st.experimental_rerun()

    st.sidebar.subheader("📅 View Tasks by Date")
    all_dates = sorted(user_tasks['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("Select a date", all_dates if all_dates else [today_date])

    tasks_for_day = user_tasks[user_tasks['Date']==selected_date]

    def highlight_status(s):
        if s=="Done": return 'background-color:#00C853;color:white'
        elif s=="Not Done": return 'background-color:#D50000;color:white'
        else: return 'background-color:#FFA500;color:white'

    if tasks_for_day.empty:
        st.write("No tasks recorded for this day.")
    else:
        df_display = tasks_for_day[["Task","Status"]].copy()
        df_display.index += 1
        st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]), use_container_width=True)

        st.markdown("### Update Tasks")
        for i,row in tasks_for_day.iterrows():
            col1, col2, col3, col4 = st.columns([3,1,1,1])
            col1.markdown(f"**{row['Task']} :**")
            col2.button("Done", key=f"done_{i}", on_click=mark_done, args=(i,))
            col3.button("Not Done", key=f"notdone_{i}", on_click=mark_notdone, args=(i,))
            col4.button("Delete", key=f"delete_{i}", on_click=delete_task, args=(i,))

# ---------------- PDF generation ----------------
class PDF(FPDF):
    def header(self):
        self.set_font("Arial","B",16)
        self.cell(0,10,"Task Report Card",ln=True,align="C")
        self.ln(10)

def generate_task_pdf(tasks_df, filename="task_report.pdf"):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial","",12)
    pdf.set_fill_color(200,200,200)
    pdf.cell(10,10,"#",border=1,fill=True)
    pdf.cell(100,10,"Task",border=1,fill=True)
    pdf.cell(40,10,"Status",border=1,fill=True)
    pdf.ln()
    for i,row in tasks_df.iterrows():
        pdf.cell(10,10,str(i+1),border=1)
        pdf.multi_cell(100,10,row["Task"],border=1)
        if row["Status"]=="Done": pdf.set_text_color(0,200,0)
        elif row["Status"]=="Not Done": pdf.set_text_color(255,0,0)
        else: pdf.set_text_color(255,165,0)
        pdf.cell(40,10,row["Status"],border=1)
        pdf.set_text_color(0,0,0)
        pdf.ln()
    pdf.output(filename)
    return filename

st.sidebar.subheader("💾 Download Task Report")
if st.sidebar.button("Download Task PDF"):
    user_tasks_pdf = st.session_state.tasks[st.session_state.tasks['User']==username]
    if not user_tasks_pdf.empty:
        pdf_file = generate_task_pdf(user_tasks_pdf)
        with open(pdf_file,"rb") as f:
            st.sidebar.download_button("⬇️ Download Task PDF",f,file_name=pdf_file,mime="application/pdf")
    else:
        st.sidebar.warning("No tasks to generate PDF!")

# ---------------- Countdown Timer ----------------
with tab2:
    st.subheader(f"{username}'s Countdown Timer")
    col_h, col_m, col_s = st.columns(3)
    with col_h: init_hours = st.number_input("Hours",0,23,0,1,key="input_hours")
    with col_m: init_minutes = st.number_input("Minutes",0,59,0,1,key="input_minutes")
    with col_s: init_seconds = st.number_input("Seconds",0,59,0,1,key="input_seconds")

    task_for_timer = st.text_input("Task name for this countdown (optional)", key="countdown_task")
    start_col, stop_col = st.columns([1,1])
    start_btn = start_col.button("Start Countdown")
    stop_btn = stop_col.button("Stop Countdown")
    display_box = st.empty()

    if start_btn:
        total_seconds = init_hours*3600 + init_minutes*60 + init_seconds
        if total_seconds>0:
            st.session_state.countdown_running=True
            st.session_state.countdown_h=init_hours
            st.session_state.countdown_m=init_minutes
            st.session_state.countdown_s=init_seconds
            st.session_state.current_countdown_task = task_for_timer if task_for_timer else "Unnamed"
            st.success(f"Countdown started for {st.session_state.current_countdown_task}")
        else: st.warning("Set a time greater than 0.")

    if stop_btn and st.session_state.countdown_running:
        focused_h = init_hours - st.session_state.countdown_h
        focused_m = init_minutes - st.session_state.countdown_m
        focused_s = init_seconds - st.session_state.countdown_s
        focused_hms=f"{focused_h}h {focused_m}m {focused_s}s"
        new_timer_row = {
            "User": username,
            "Task": st.session_state.get("current_countdown_task","Unnamed"),
            "Target_HMS": f"{init_hours}h {init_minutes}m {init_seconds}s",
            "Focused_HMS": focused_hms,
            "Date": today_date
        }
        st.session_state.timer_data=pd.concat([st.session_state.timer_data,pd.DataFrame([new_timer_row])],ignore_index=True)
        st.session_state.timer_data.to_csv(TIMER_FILE,index=False)
        st.session_state.countdown_running=False
        st.success(f"Countdown stopped. Focused: {focused_hms}")

# ---------------- Timer Log ----------------
st.sidebar.subheader("⏳ Your Focused Sessions")
user_timer_data = st.session_state.timer_data[st.session_state.timer_data['User']==username]
if not user_timer_data.empty:
    st.sidebar.dataframe(user_timer_data, use_container_width=True)
else:
    st.sidebar.write("No focused sessions logged yet.")


