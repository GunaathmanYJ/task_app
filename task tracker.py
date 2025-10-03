import streamlit as st
from fpdf import FPDF
from datetime import datetime
import time

st.set_page_config(page_title="TaskUni", layout="wide")
st.title("📌 TaskUni — Your personal Task tracker (Session Only)")

# ---------------- Session State ----------------
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "timer_data" not in st.session_state:
    st.session_state.timer_data = []
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

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer"])

# ---------------- Task Tracker ----------------
with tab1:
    st.subheader(f"Hello {username}, add or view your tasks")
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input.strip():
        new_task = {"Task": task_name_input.strip(), "Status": "Pending", "Date": today_date}
        st.session_state.tasks.append(new_task)
        st.experimental_rerun()

    st.sidebar.subheader("📅 View Tasks by Date")
    all_dates = sorted({t["Date"] for t in st.session_state.tasks}, reverse=True)
    selected_date = st.sidebar.selectbox("Select a date", all_dates if all_dates else [today_date])

    tasks_for_day = [t for t in st.session_state.tasks if t["Date"] == selected_date]

    def highlight_status(s):
        if s=="Done": return 'background-color:#00C853;color:white'
        elif s=="Not Done": return 'background-color:#D50000;color:white'
        else: return 'background-color:#FFA500;color:white'

    if not tasks_for_day:
        st.write("No tasks recorded for this day.")
    else:
        for idx, task in enumerate(tasks_for_day):
            col1, col2, col3, col4 = st.columns([3,1,1,1])
            col1.markdown(f"**{task['Task']} :**")
            if col2.button("Done", key=f"done_{idx}"):
                task['Status'] = "Done"
                st.experimental_rerun()
            if col3.button("Not Done", key=f"notdone_{idx}"):
                task['Status'] = "Not Done"
                st.experimental_rerun()
            if col4.button("Delete", key=f"delete_{idx}"):
                st.session_state.tasks.remove(task)
                st.experimental_rerun()

# ---------------- PDF generation ----------------
class PDF(FPDF):
    def header(self):
        self.set_font("Arial","B",16)
        self.cell(0,10,"Task Report Card",ln=True,align="C")
        self.ln(10)

def generate_task_pdf(tasks_list, filename="task_report.pdf"):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial","",12)
    pdf.set_fill_color(200,200,200)
    pdf.cell(10,10,"#",border=1,fill=True)
    pdf.cell(100,10,"Task",border=1,fill=True)
    pdf.cell(40,10,"Status",border=1,fill=True)
    pdf.ln()
    for i, task in enumerate(tasks_list):
        pdf.cell(10,10,str(i+1),border=1)
        pdf.multi_cell(100,10,task["Task"],border=1)
        if task["Status"]=="Done": pdf.set_text_color(0,200,0)
        elif task["Status"]=="Not Done": pdf.set_text_color(255,0,0)
        else: pdf.set_text_color(255,165,0)
        pdf.cell(40,10,task["Status"],border=1)
        pdf.set_text_color(0,0,0)
        pdf.ln()
    pdf.output(filename)
    return filename

st.sidebar.subheader("💾 Download Task Report")
if st.sidebar.button("Download Task PDF"):
    if st.session_state.tasks:
        pdf_file = generate_task_pdf(st.session_state.tasks)
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
        st.session_state.timer_data.append({
            "Task": st.session_state.current_countdown_task,
            "Target_HMS": f"{init_hours}h {init_minutes}m {init_seconds}s",
            "Focused_HMS": focused_hms,
            "Date": today_date
        })
        st.session_state.countdown_running=False
        st.success(f"Countdown stopped. Focused: {focused_hms}")

# ---------------- Timer Log ----------------
st.sidebar.subheader("⏳ Your Focused Sessions")
if st.session_state.timer_data:
    st.sidebar.dataframe(st.session_state.timer_data)
else:
    st.sidebar.write("No focused sessions logged yet.")
