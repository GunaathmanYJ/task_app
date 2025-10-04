import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
from io import BytesIO
from fpdf import FPDF

# ----------------- Setup -----------------
st.set_page_config(page_title="TaskUni Premium", layout="wide")

# ----------------- Auto-create users.csv -----------------
if not os.path.exists("users.csv"):
    df_users = pd.DataFrame(columns=["username","password"])
    df_users.to_csv("users.csv", index=False)

# ----------------- Load users -----------------
users = pd.read_csv("users.csv")

# ----------------- Login/Register -----------------
st.sidebar.image("taskuni.png", width=100)
auth_option = st.sidebar.radio("Choose option", ["Login", "Register"])

if auth_option == "Register":
    st.sidebar.subheader("Register a new account")
    new_user = st.sidebar.text_input("Username", key="reg_user")
    new_pass = st.sidebar.text_input("Password", type="password", key="reg_pass")
    if st.sidebar.button("Register"):
        if new_user in users["username"].values:
            st.sidebar.error("Username already exists")
        elif new_user.strip() == "" or new_pass.strip() == "":
            st.sidebar.warning("Fill both username and password")
        else:
            users = pd.concat([users, pd.DataFrame([{"username":new_user, "password":new_pass}])], ignore_index=True)
            users.to_csv("users.csv", index=False)
            st.sidebar.success("Account created! Now login.")

elif auth_option == "Login":
    st.sidebar.subheader("Login to TaskUni")
    login_user = st.sidebar.text_input("Username", key="login_user")
    login_pass = st.sidebar.text_input("Password", type="password", key="login_pass")
    if st.sidebar.button("Login"):
        if login_user not in users["username"].values:
            st.sidebar.error("Username not found")
            st.stop()
        correct_pass = users.loc[users["username"]==login_user, "password"].values[0]
        if login_pass != correct_pass:
            st.sidebar.error("Incorrect password")
            st.stop()
        else:
            st.session_state["user"] = login_user
            st.sidebar.success(f"Welcome {login_user}!")

# ----------------- Ensure user is logged in -----------------
if "user" not in st.session_state:
    st.warning("Please login or register to use TaskUni")
    st.stop()

username = st.session_state["user"]

# ----------------- Files per user -----------------
TASKS_FILE = f"tasks_{username}.csv"
TIMER_FILE = f"timer_{username}.csv"
POMODORO_FILE = f"pomodoro_{username}.csv"
GROUP_FILE = "group_study.csv"

if not os.path.exists(TASKS_FILE):
    pd.DataFrame(columns=["Task","Status","Date"]).to_csv(TASKS_FILE, index=False)

if not os.path.exists(TIMER_FILE):
    pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS","Date"]).to_csv(TIMER_FILE, index=False)

if not os.path.exists(POMODORO_FILE):
    pd.DataFrame(columns=["Session","Work_HMS","Short_Break_HMS","Long_Break_HMS","Date"]).to_csv(POMODORO_FILE, index=False)

if not os.path.exists(GROUP_FILE):
    pd.DataFrame(columns=["Username","Message","Note","Time"]).to_csv(GROUP_FILE, index=False)

# ----------------- Load user data -----------------
tasks = pd.read_csv(TASKS_FILE)
timers = pd.read_csv(TIMER_FILE)
pomodoros = pd.read_csv(POMODORO_FILE)
group_study = pd.read_csv(GROUP_FILE)

today_date = datetime.now().strftime("%Y-%m-%d")

# ----------------- Main Tabs -----------------
tab1, tab2, tab3, tab4 = st.tabs(["📝 Tasks", "⏱ Timer", "🍅 Pomodoro", "👥 Group Study"])
# ----------------- Tab 1: Tasks -----------------
with tab1:
    st.subheader(f"Tasks for {today_date}")
    
    # Add Task
    task_input = st.text_input("Enter new task")
    if st.button("Add Task"):
        if task_input.strip():
            new_task = {"Task": task_input.strip(), "Status": "Pending", "Date": today_date}
            tasks = pd.concat([tasks, pd.DataFrame([new_task])], ignore_index=True)
            tasks.to_csv(TASKS_FILE, index=False)
            st.success("Task added!")

    # Display today's tasks
    today_tasks = tasks[tasks["Date"]==today_date]
    if today_tasks.empty:
        st.write("No tasks for today.")
    else:
        def highlight_status(s):
            if s=="Done": return 'background-color:#00C853;color:white'
            elif s=="Not Done": return 'background-color:#D50000;color:white'
            else: return 'background-color:#FFA500;color:white'
        
        df_display = today_tasks[["Task","Status"]].copy()
        df_display.index += 1
        st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]), use_container_width=True)
        
        st.markdown("### Update Tasks")
        for i, row in today_tasks.iterrows():
            cols = st.columns([3,1,1,1])
            cols[0].write(f"{row['Task']}:")
            if cols[1].button("Done", key=f"done_{i}"):
                tasks.at[i,"Status"]="Done"
                tasks.to_csv(TASKS_FILE,index=False)
                st.experimental_rerun()
            if cols[2].button("Not Done", key=f"notdone_{i}"):
                tasks.at[i,"Status"]="Not Done"
                tasks.to_csv(TASKS_FILE,index=False)
                st.experimental_rerun()
            if cols[3].button("Delete", key=f"delete_{i}"):
                tasks = tasks.drop(i).reset_index(drop=True)
                tasks.to_csv(TASKS_FILE,index=False)
                st.experimental_rerun()
    
    # ---------------- PDF Export ----------------
    if st.button("Download Tasks PDF"):
        class TaskPDF(FPDF):
            def header(self):
                self.set_font("Arial","B",16)
                self.cell(0,10,"Tasks Report",ln=True,align="C")
                self.ln(10)
        pdf = TaskPDF()
        pdf.add_page()
        pdf.set_font("Arial","",12)
        pdf.set_fill_color(200,200,200)
        pdf.cell(10,10,"#",border=1,fill=True)
        pdf.cell(100,10,"Task",border=1,fill=True)
        pdf.cell(30,10,"Status",border=1,fill=True)
        pdf.cell(40,10,"Date",border=1,fill=True)
        pdf.ln()
        for idx,row in tasks.iterrows():
            pdf.cell(10,10,str(idx+1),border=1)
            pdf.cell(100,10,row["Task"],border=1)
            pdf.cell(30,10,row["Status"],border=1)
            pdf.cell(40,10,row["Date"],border=1)
            pdf.ln()
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        st.download_button("⬇️ Download PDF", pdf_bytes, file_name="tasks_report.pdf", mime="application/pdf")

# ----------------- Tab 2: Countdown Timer -----------------
with tab2:
    st.subheader("Countdown Timer")
    col_h,col_m,col_s = st.columns(3)
    with col_h:
        hours = st.number_input("Hours", 0,23,0)
    with col_m:
        minutes = st.number_input("Minutes",0,59,0)
    with col_s:
        seconds = st.number_input("Seconds",0,59,0)
    
    countdown_task = st.text_input("Task name (optional)")
    start_col, stop_col = st.columns([1,1])
    
    if "countdown_running" not in st.session_state:
        st.session_state.countdown_running=False
    display_box = st.empty()
    
    # Start countdown
    if start_col.button("Start Countdown") and not st.session_state.countdown_running:
        total_seconds = hours*3600 + minutes*60 + seconds
        if total_seconds>0:
            st.session_state.countdown_running=True
            st.session_state.countdown_start=time.time()
            st.session_state.countdown_total=total_seconds
            st.session_state.countdown_task = countdown_task if countdown_task else "Unnamed"
        else:
            st.warning("Set a time greater than 0")
    
    # Stop countdown
    if stop_col.button("Stop Countdown") and st.session_state.countdown_running:
        elapsed=int(time.time()-st.session_state.countdown_start)
        focused=min(elapsed,st.session_state.countdown_total)
        h=focused//3600
        m=(focused%3600)//60
        s=focused%60
        timers = pd.concat([timers, pd.DataFrame([{
            "Task":st.session_state.countdown_task,
            "Target_HMS":f"{hours}h {minutes}m {seconds}s",
            "Focused_HMS":f"{h}h {m}m {s}s",
            "Date":today_date
        }])],ignore_index=True)
        timers.to_csv(TIMER_FILE,index=False)
        st.success(f"Stopped! Focused: {h}h {m}m {s}s")
        st.session_state.countdown_running=False
    
    # Display running countdown
    if st.session_state.countdown_running:
        elapsed = int(time.time()-st.session_state.countdown_start)
        remaining = max(st.session_state.countdown_total - elapsed,0)
        h=remaining//3600
        m=(remaining%3600)//60
        s=remaining%60
        display_box.markdown(f"<h1 style='text-align:center;font-size:120px;'>⏱ {h:02d}:{m:02d}:{s:02d}</h1>"
                             f"<h3 style='text-align:center;'>Task: {st.session_state.countdown_task}</h3>", unsafe_allow_html=True)
        if remaining==0:
            timers = pd.concat([timers, pd.DataFrame([{
                "Task":st.session_state.countdown_task,
                "Target_HMS":f"{hours}h {minutes}m {seconds}s",
                "Focused_HMS":f"{hours}h {minutes}m {seconds}s",
                "Date":today_date
            }])],ignore_index=True)
            timers.to_csv(TIMER_FILE,index=False)
            display_box.success("🎯 Countdown Finished!")
            st.session_state.countdown_running=False
    
    # Total focused today
    today_timer_data = timers[timers["Date"]==today_date]
    if not today_timer_data.empty:
        total_seconds=0
        for t in today_timer_data['Focused_HMS']:
            parts=t.split()
            total_seconds += int(parts[0].replace('h',''))*3600 + int(parts[1].replace('m',''))*60 + int(parts[2].replace('s',''))
        th=total_seconds//3600
        tm=(total_seconds%3600)//60
        ts=total_seconds%60
        st.markdown(f"### 🎯 Total Focused Time Today: {th}h {tm}m {ts}s")
