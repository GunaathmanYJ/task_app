import streamlit as st
from fpdf import FPDF
from datetime import datetime
import time
import pandas as pd

st.set_page_config(page_title="TaskUni", layout="wide")
st.title("📌 TaskUni — Your personal Task tracker")

# ---------------- Session State ----------------
if "tasks" not in st.session_state:
    st.session_state.tasks = pd.DataFrame(columns=["Task", "Status", "Date"])
if "timer_data" not in st.session_state:
    st.session_state.timer_data = pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS","Date"])
if "countdown_running" not in st.session_state:
    st.session_state.countdown_running = False
if "current_countdown_task" not in st.session_state:
    st.session_state.current_countdown_task = ""
if "remaining_seconds" not in st.session_state:
    st.session_state.remaining_seconds = 0

today_date = datetime.now().strftime("%d-%m-%Y")

# ---------------- Button functions ----------------
def mark_done(idx):
    st.session_state.tasks.at[idx,"Status"]="Done"

def mark_notdone(idx):
    st.session_state.tasks.at[idx,"Status"]="Not Done"

def delete_task(idx):
    st.session_state.tasks = st.session_state.tasks.drop(idx).reset_index(drop=True)

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer"])

# ---------------- Task Tracker ----------------
with tab1:
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input.strip():
        new_task = {"Task": task_name_input.strip(),"Status":"Pending","Date":today_date}
        st.session_state.tasks = pd.concat([st.session_state.tasks,pd.DataFrame([new_task])],ignore_index=True)

# ---------------- Sidebar: Select Date ----------------
st.sidebar.subheader("📅 View Tasks by Date")
all_dates = sorted(st.session_state.tasks['Date'].unique(), reverse=True)
selected_date = st.sidebar.selectbox("Select a date", all_dates if all_dates else [today_date])

# ---------------- Main panel: Tasks for selected date ----------------
st.subheader(f"Tasks on {selected_date}")
tasks_for_day = st.session_state.tasks[st.session_state.tasks['Date']==selected_date]

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

# ---------------- Generate Task PDF ----------------
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
    if not st.session_state.tasks.empty:
        pdf_file = generate_task_pdf(st.session_state.tasks)
        with open(pdf_file,"rb") as f:
            st.sidebar.download_button("⬇️ Download Task PDF",f,file_name=pdf_file,mime="application/pdf")
    else:
        st.sidebar.warning("No tasks to generate PDF!")

# ---------------- Countdown Timer ----------------
with tab2:
    st.write("Set countdown time")
    col_h, col_m, col_s = st.columns(3)
    with col_h: init_hours = st.number_input("Hours",min_value=0,max_value=23,value=0,step=1,key="input_hours")
    with col_m: init_minutes = st.number_input("Minutes",min_value=0,max_value=59,value=0,step=1,key="input_minutes")
    with col_s: init_seconds = st.number_input("Seconds",min_value=0,max_value=59,value=0,step=1,key="input_seconds")

    task_for_timer = st.text_input("Task name for this countdown (optional)", key="countdown_task")
    start_col, stop_col = st.columns([1,1])
    start_btn = start_col.button("Start Countdown")
    stop_btn = stop_col.button("Stop Countdown")
    display_box = st.empty()

    # Start Countdown
    if start_btn:
        total_seconds = init_hours*3600 + init_minutes*60 + init_seconds
        if total_seconds>0:
            st.session_state.countdown_running=True
            st.session_state.remaining_seconds = total_seconds
            st.session_state.current_countdown_task = task_for_timer if task_for_timer else "Unnamed"
            st.success(f"Countdown started for {st.session_state.current_countdown_task}")
        else:
            st.warning("Set a time greater than 0.")

    # Stop Countdown
    if stop_btn and st.session_state.countdown_running:
        remaining = st.session_state.remaining_seconds
        elapsed = (init_hours*3600 + init_minutes*60 + init_seconds) - remaining
        eh = elapsed//3600
        em = (elapsed%3600)//60
        es = elapsed%60
        focused_hms = f"{eh}h {em}m {es}s"
        new_timer_row = {"Task": st.session_state.current_countdown_task,
                         "Target_HMS": f"{init_hours}h {init_minutes}m {init_seconds}s",
                         "Focused_HMS": focused_hms,
                         "Date": today_date}
        st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([new_timer_row])],ignore_index=True)
        st.session_state.countdown_running=False
        st.success(f"Countdown stopped. Focused: {focused_hms}")

    # Auto-update Timer Display (without experimental rerun)
    if st.session_state.countdown_running:
        total_sec = st.session_state.remaining_seconds
        if total_sec > 0:
            h = total_sec//3600
            m = (total_sec%3600)//60
            s = total_sec%60
            display_box.markdown(f"<h1 style='font-size:80px;text-align:center'>{h:02d}:{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
            time.sleep(1)
            st.session_state.remaining_seconds -= 1
        else:
            st.session_state.countdown_running = False
            st.success(f"⏰ Timer finished for {st.session_state.current_countdown_task}")
            # Log automatically
            focused_hms = f"{init_hours}h {init_minutes}m {init_seconds}s"
            new_timer_row = {"Task": st.session_state.current_countdown_task,
                             "Target_HMS": focused_hms,
                             "Focused_HMS": focused_hms,
                             "Date": today_date}
            st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([new_timer_row])],ignore_index=True)

# ---------------- Timer Report Sidebar ----------------
st.sidebar.subheader("⏳ Focused Sessions Log")
if not st.session_state.timer_data.empty:
    st.sidebar.dataframe(st.session_state.timer_data, use_container_width=True)
else:
    st.sidebar.write("No focused sessions logged yet.")
