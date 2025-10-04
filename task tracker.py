import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time
from io import BytesIO
from streamlit_autorefresh import st_autorefresh

# ---------------- Page config ----------------
st.set_page_config(page_title="TaskUni Premium", layout="wide")

# ---------------- Sidebar Logo ----------------
st.sidebar.image("taskuni.png", width=100)  # small logo only in sidebar

# ---------------- Files for storing users ----------------
USERS_FILE = "users.csv"
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["username","password"]).to_csv(USERS_FILE, index=False)

# ---------------- Login/Register ----------------
st.title("👤 Welcome to TaskUni Premium")

login_col, register_col = st.columns(2)

with register_col:
    st.subheader("Register")
    reg_username = st.text_input("New Username", key="reg_user")
    reg_password = st.text_input("New Password", type="password", key="reg_pass")
    if st.button("Register", key="reg_btn"):
        users = pd.read_csv(USERS_FILE)
        if reg_username in users["username"].values:
            st.warning("Username already exists!")
        elif reg_username.strip() == "" or reg_password.strip() == "":
            st.warning("Enter valid username and password")
        else:
            users = pd.concat([users, pd.DataFrame([{"username":reg_username,"password":reg_password}])], ignore_index=True)
            users.to_csv(USERS_FILE, index=False)
            st.success("Registered! You can now login.")

with login_col:
    st.subheader("Login")
    login_username = st.text_input("Username", key="login_user")
    login_password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login", key="login_btn"):
        users = pd.read_csv(USERS_FILE)
        if login_username in users["username"].values:
            correct_pass = users.loc[users["username"]==login_username, "password"].values[0]
            if login_password == correct_pass:
                st.success("Login successful!")
                st.session_state.username = login_username
            else:
                st.error("Incorrect password")
        else:
            st.error("Username not found")

if "username" not in st.session_state:
    st.stop()

username = st.session_state.username
today_date = datetime.now().strftime("%d-%m-%Y")

# ---------------- Files for persistent storage per user ----------------
TASKS_FILE = f"tasks_{username}.csv"
TIMER_FILE = f"timer_{username}.csv"

# ---------------- Load persistent data ----------------
if "tasks" not in st.session_state:
    if os.path.exists(TASKS_FILE):
        st.session_state.tasks = pd.read_csv(TASKS_FILE)
    else:
        st.session_state.tasks = pd.DataFrame(columns=["Task", "Status", "Date"])

if "timer_data" not in st.session_state:
    if os.path.exists(TIMER_FILE):
        st.session_state.timer_data = pd.read_csv(TIMER_FILE)
    else:
        st.session_state.timer_data = pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS","Date"])

if "countdown_running" not in st.session_state:
    st.session_state.countdown_running = False
if "countdown_paused" not in st.session_state:
    st.session_state.countdown_paused = False
if "countdown_remaining_seconds" not in st.session_state:
    st.session_state.countdown_remaining_seconds = 0

# ---------------- Tabs ----------------
tab1, tab2, tab3 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer", "🍅 Pomodoro & Group Study (coming)"])

# ---------------- Task Tracker Tab ----------------
with tab1:
    st.subheader(f"Tasks for {today_date}")
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input.strip():
        new_task = {"Task": task_name_input.strip(), "Status": "Pending", "Date": today_date}
        st.session_state.tasks = pd.concat([st.session_state.tasks, pd.DataFrame([new_task])], ignore_index=True)
        st.session_state.tasks.to_csv(TASKS_FILE, index=False)

    tasks_today = st.session_state.tasks[st.session_state.tasks['Date']==today_date]
    if tasks_today.empty:
        st.write("No tasks recorded for today.")
    else:
        def highlight_status(s):
            if s=="Done":
                return 'background-color:#00C853;color:white'
            elif s=="Not Done":
                return 'background-color:#D50000;color:white'
            else:
                return 'background-color:#FFA500;color:white'
        df_display = tasks_today[["Task","Status"]].copy()
        df_display.index += 1
        st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]), use_container_width=True)

        st.markdown("### Update Tasks")
        for i, row in tasks_today.iterrows():
            cols = st.columns([3,1,1,1])
            cols[0].write(f"{row['Task']}:")
            if cols[1].button("Done", key=f"done_{i}"):
                st.session_state.tasks.at[i,"Status"]="Done"
                st.session_state.tasks.to_csv(TASKS_FILE,index=False)
            if cols[2].button("Not Done", key=f"notdone_{i}"):
                st.session_state.tasks.at[i,"Status"]="Not Done"
                st.session_state.tasks.to_csv(TASKS_FILE,index=False)
            if cols[3].button("Delete", key=f"delete_{i}"):
                st.session_state.tasks = st.session_state.tasks.drop(i).reset_index(drop=True)
                st.session_state.tasks.to_csv(TASKS_FILE,index=False)

# ---------------- Countdown Timer Tab ----------------
with tab2:
    st.subheader("Countdown Timer")
    col_h, col_m, col_s = st.columns(3)
    with col_h:
        hours = st.number_input("Hours", 0, 23, 0, key="hours_input")
    with col_m:
        minutes = st.number_input("Minutes", 0, 59, 0, key="minutes_input")
    with col_s:
        seconds = st.number_input("Seconds", 0, 59, 0, key="seconds_input")

    countdown_task_name = st.text_input("Task name (optional)", key="countdown_task_input")
    start_col, pause_col, stop_col = st.columns([1,1,1])
    start_btn = start_col.button("Start Countdown")
    pause_btn = pause_col.button("Pause/Resume")
    stop_btn = stop_col.button("Stop Countdown")
    display_box = st.empty()

    # Start
    if start_btn:
        total_seconds = hours*3600 + minutes*60 + seconds
        if total_seconds <=0:
            st.warning("Set a time greater than 0")
        else:
            st.session_state.countdown_running = True
            st.session_state.countdown_paused = False
            st.session_state.countdown_total_seconds = total_seconds
            st.session_state.countdown_start_time = time.time()
            st.session_state.countdown_task_name = countdown_task_name if countdown_task_name else "Unnamed"

    # Pause/Resume toggle
    if pause_btn and st.session_state.countdown_running:
        st.session_state.countdown_paused = not st.session_state.countdown_paused
        if not st.session_state.countdown_paused:
            st.session_state.countdown_start_time = time.time() - st.session_state.countdown_remaining_seconds

    # Stop
    if stop_btn and st.session_state.countdown_running:
        elapsed = int(time.time() - st.session_state.countdown_start_time) if not st.session_state.countdown_paused else st.session_state.countdown_remaining_seconds
        focused = min(elapsed, st.session_state.countdown_total_seconds)
        h = focused//3600
        m = (focused%3600)//60
        s = focused%60
        st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
            "Task": st.session_state.countdown_task_name,
            "Target_HMS": f"{hours}h {minutes}m {seconds}s",
            "Focused_HMS": f"{h}h {m}m {s}s",
            "Date": today_date
        }])], ignore_index=True)
        st.session_state.timer_data.to_csv(TIMER_FILE,index=False)
        st.session_state.countdown_running = False
        st.session_state.countdown_paused = False
        st.success(f"Countdown stopped. Focused: {h}h {m}m {s}s")

    # Display countdown
    if st.session_state.countdown_running and not st.session_state.countdown_paused:
        st_autorefresh(interval=1000, key="timer_refresh")
        elapsed = int(time.time() - st.session_state.countdown_start_time)
        remaining = max(st.session_state.countdown_total_seconds - elapsed,0)
        st.session_state.countdown_remaining_seconds = remaining
        h = remaining//3600
        m = (remaining%3600)//60
        s = remaining%60
        display_box.markdown(f"<h1 style='text-align:center;font-size:160px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1>"
                             f"<h3 style='text-align:center;font-size:48px;'>Task: {st.session_state.countdown_task_name}</h3>",
                             unsafe_allow_html=True)
        if remaining==0:
            st.session_state.countdown_running=False
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.countdown_task_name,
                "Target_HMS": f"{hours}h {minutes}m {seconds}s",
                "Focused_HMS": f"{hours}h {minutes}m {seconds}s",
                "Date": today_date
            }])], ignore_index=True)
            st.session_state.timer_data.to_csv(TIMER_FILE,index=False)
            display_box.success("🎯 Countdown Finished!")

    # Total focused today
    today_timer_data = st.session_state.timer_data[st.session_state.timer_data["Date"]==today_date]
    if not today_timer_data.empty:
        def hms_to_seconds(hms_str):
            h=m=s=0
            try:
                parts = hms_str.split()
                for part in parts:
                    if 'h' in part: h=int(part.replace('h',''))
                    elif 'm' in part: m=int(part.replace('m',''))
                    elif 's' in part: s=int(part.replace('s',''))
            except: pass
            return h*3600 + m*60 + s
        total_seconds = sum([hms_to_seconds(t) for t in today_timer_data['Focused_HMS']])
        total_h = total_seconds//3600
        total_m = (total_seconds%3600)//60
        total_s = total_seconds%60
        st.markdown(f"### 🎯 Total Focused Time Today: {total_h}h {total_m}m {total_s}s")
# ---------------- Pomodoro & Group Study Tab ----------------
with tab3:
    pomo_tab, group_tab = st.tabs(["🍅 Pomodoro Timer", "👥 Group Study"])

    # ---------------- Pomodoro Timer ----------------
    with pomo_tab:
        st.subheader("Pomodoro Timer")
        if "pomo_running" not in st.session_state:
            st.session_state.pomo_running = False
        if "pomo_paused" not in st.session_state:
            st.session_state.pomo_paused = False
        if "pomo_remaining_seconds" not in st.session_state:
            st.session_state.pomo_remaining_seconds = 0
        if "pomo_pause_count" not in st.session_state:
            st.session_state.pomo_pause_count = 0
        if "pomo_total_cycles" not in st.session_state:
            st.session_state.pomo_total_cycles = 0
        if "pomo_current_cycle" not in st.session_state:
            st.session_state.pomo_current_cycle = 0
        if "daily_focus_target" not in st.session_state:
            st.session_state.daily_focus_target = 60*60  # default 1h
        if "daily_focus_accumulated" not in st.session_state:
            st.session_state.daily_focus_accumulated = 0

        # Pomodoro setup
        st.markdown("### Setup Pomodoro")
        st.session_state.pomo_work_min = st.number_input("Work minutes", 5, 180, value=25)
        st.session_state.pomo_short_break_min = st.number_input("Short break minutes", 1, 30, value=5)
        st.session_state.pomo_long_break_min = st.number_input("Long break minutes", 5, 60, value=15)
        st.session_state.pomo_cycles = st.number_input("Number of cycles", 1, 20, value=4)
        st.session_state.daily_focus_target = st.number_input("Daily focus target (minutes)", 10, 1440, value=int(st.session_state.daily_focus_target/60))

        start_pomo, pause_pomo, cancel_pomo = st.columns(3)
        if start_pomo.button("Start Pomodoro"):
            st.session_state.pomo_running = True
            st.session_state.pomo_paused = False
            st.session_state.pomo_pause_count = 0
            st.session_state.pomo_current_cycle = 1
            st.session_state.pomo_remaining_seconds = st.session_state.pomo_work_min*60
            st.session_state.pomo_phase = "Work"
            st.success(f"Pomodoro started: Cycle 1/{st.session_state.pomo_cycles}")

        if pause_pomo.button("Pause/Resume Pomodoro") and st.session_state.pomo_running:
            if not st.session_state.pomo_paused:
                st.session_state.pomo_paused = True
                st.session_state.pomo_pause_count +=1
                if st.session_state.pomo_pause_count>2:
                    st.warning("Pausing more than 2 times cancels Pomodoro")
                    st.session_state.pomo_running=False
            else:
                st.session_state.pomo_paused = False
                st.session_state.pomo_start_time = time.time() - st.session_state.pomo_remaining_seconds

        if cancel_pomo.button("Cancel Pomodoro"):
            st.session_state.pomo_running = False
            st.info("Pomodoro cancelled.")

        # Pomodoro logic
        if st.session_state.pomo_running and not st.session_state.pomo_paused:
            st_autorefresh(interval=1000, key="pomo_refresh")
            if "pomo_start_time" not in st.session_state:
                st.session_state.pomo_start_time = time.time()
            elapsed = int(time.time() - st.session_state.pomo_start_time)
            st.session_state.pomo_remaining_seconds = max(st.session_state.pomo_remaining_seconds - elapsed, 0)
            st.session_state.pomo_start_time = time.time()

            # Display timer
            h = st.session_state.pomo_remaining_seconds//3600
            m = (st.session_state.pomo_remaining_seconds%3600)//60
            s = st.session_state.pomo_remaining_seconds%60
            st.markdown(f"<h1 style='text-align:center;font-size:120px;'>{h:02d}:{m:02d}:{s:02d} ({st.session_state.pomo_phase})</h1>", unsafe_allow_html=True)

            # End of phase
            if st.session_state.pomo_remaining_seconds<=0:
                if st.session_state.pomo_phase=="Work":
                    st.session_state.daily_focus_accumulated += st.session_state.pomo_work_min*60
                    if st.session_state.daily_focus_accumulated >= st.session_state.daily_focus_target*60:
                        st.success("🎉 You reached your daily focus target! Time to take a break.")
                    st.session_state.pomo_phase = "Short Break" if st.session_state.pomo_current_cycle < st.session_state.pomo_cycles else "Long Break"
                    st.session_state.pomo_remaining_seconds = st.session_state.pomo_short_break_min*60 if st.session_state.pomo_phase=="Short Break" else st.session_state.pomo_long_break_min*60
                    st.session_state.pomo_start_time = time.time()
                else:  # Break phase
                    st.session_state.pomo_current_cycle +=1
                    if st.session_state.pomo_current_cycle>st.session_state.pomo_cycles:
                        st.session_state.pomo_running=False
                        st.success("Pomodoro session complete!")
                    else:
                        st.session_state.pomo_phase="Work"
                        st.session_state.pomo_remaining_seconds = st.session_state.pomo_work_min*60
                        st.session_state.pomo_start_time = time.time()

        # Log Pomodoro data
        if "pomodoro_log" not in st.session_state:
            st.session_state.pomodoro_log = pd.DataFrame(columns=["Date","Cycle","Phase","Duration_HMS"])
        if st.session_state.pomo_running==False and st.session_state.pomo_current_cycle>0:
            # Add last finished cycle to log
            phase_duration = st.session_state.pomo_work_min*60 if st.session_state.pomo_phase=="Work" else st.session_state.pomo_short_break_min*60
            h = phase_duration//3600
            m = (phase_duration%3600)//60
            s = phase_duration%60
            new_entry = {"Date":today_date, "Cycle":st.session_state.pomo_current_cycle, "Phase":st.session_state.pomo_phase, "Duration_HMS":f"{h}h {m}m {s}s"}
            if new_entry not in st.session_state.pomodoro_log.to_dict("records"):
                st.session_state.pomodoro_log = pd.concat([st.session_state.pomodoro_log,pd.DataFrame([new_entry])], ignore_index=True)

        st.markdown("### Pomodoro Log")
        if not st.session_state.pomodoro_log.empty:
            st.dataframe(st.session_state.pomodoro_log, use_container_width=True)

    # ---------------- Group Study Tab ----------------
    with group_tab:
        st.subheader("Group Study Room")
        GROUP_USERS_FILE = "group_users.csv"
        GROUP_MESSAGES_FILE = "group_messages.csv"
        GROUP_NOTES_FILE = "group_notes.txt"

        # Ensure files exist
        for f, default in [(GROUP_USERS_FILE,pd.DataFrame(columns=["username"])),
                           (GROUP_MESSAGES_FILE,pd.DataFrame(columns=["username","message","timestamp"]))]:
            if not os.path.exists(f):
                default.to_csv(f,index=False)
        if not os.path.exists(GROUP_NOTES_FILE):
            open(GROUP_NOTES_FILE,"w").write("")

        group_users = pd.read_csv(GROUP_USERS_FILE)
        if username not in group_users["username"].values:
            if st.button("Join Group Study"):
                group_users = pd.concat([group_users,pd.DataFrame([{"username":username}])], ignore_index=True)
                group_users.to_csv(GROUP_USERS_FILE,index=False)
                st.success("You joined the group!")

        st.write("Current users in group:")
        st.write(pd.read_csv(GROUP_USERS_FILE)["username"].tolist())

        # Messages
        st.markdown("### 🗨️ Messages")
        msg_input = st.text_input("Enter message")
        if st.button("Send Message"):
            msgs = pd.read_csv(GROUP_MESSAGES_FILE)
            msgs = pd.concat([msgs,pd.DataFrame([{"username":username,"message":msg_input,"timestamp":datetime.now()}])], ignore_index=True)
            msgs.to_csv(GROUP_MESSAGES_FILE,index=False)
        st.write(pd.read_csv(GROUP_MESSAGES_FILE)[["username","message","timestamp"]])

        # Notes
        st.markdown("### 📝 Shared Notes")
        with open(GROUP_NOTES_FILE,"r") as f:
            notes_content = f.read()
        edited_notes = st.text_area("Edit notes", value=notes_content, height=200)
        if st.button("Save Notes"):
            with open(GROUP_NOTES_FILE,"w") as f:
                f.write(edited_notes)
            st.success("Notes saved!")

# ---------------- Sidebar PDF Export ----------------
st.sidebar.subheader("📄 Reports")

# Timer PDF
if not st.session_state.timer_data.empty:
    class TimerPDF(FPDF):
        def header(self):
            self.set_font("Arial","B",16)
            self.cell(0,10,"Focused Timer Report",ln=True,align="C")
            self.ln(10)
    def generate_timer_pdf(timer_df):
        pdf = TimerPDF()
        pdf.add_page()
        pdf.set_font("Arial","",12)
        pdf.set_fill_color(200,200,200)
        pdf.cell(10,10,"#",1,0,fill=True)
        pdf.cell(80,10,"Task",1,0,fill=True)
        pdf.cell(50,10,"Target Time",1,0,fill=True)
        pdf.cell(50,10,"Focused Time",1,1,fill=True)
        for i,row in timer_df.iterrows():
            pdf.cell(10,10,str(i+1),1)
            pdf.cell(80,10,row["Task"],1)
            pdf.cell(50,10,row["Target_HMS"],1)
            pdf.cell(50,10,row["Focused_HMS"],1)
            pdf.ln()
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        return BytesIO(pdf_bytes)
    if st.sidebar.button("💾 Download Timer PDF"):
        pdf_bytes = generate_timer_pdf(st.session_state.timer_data)
        st.sidebar.download_button("⬇️ Download Timer PDF", pdf_bytes, file_name="timer_report.pdf", mime="application/pdf")

# Task PDF
if not st.session_state.tasks.empty:
    class TaskPDF(FPDF):
        def header(self):
            self.set_font("Arial","B",16)
            self.cell(0,10,"Tasks Report",ln=True,align="C")
            self.ln(10)
    def generate_task_pdf(tasks_df):
        pdf = TaskPDF()
        pdf.add_page()
        pdf.set_font("Arial","",12)
        pdf.set_fill_color(200,200,200)
        pdf.cell(10,10,"#",1,0,fill=True)
        pdf.cell(100,10,"Task",1,0,fill=True)
        pdf.cell(30,10,"Status",1,0,fill=True)
        pdf.cell(40,10,"Date",1,1,fill=True)
        for i,row in tasks_df.iterrows():
            pdf.cell(10,10,str(i+1),1)
            pdf.cell(100,10,row["Task"],1)
            pdf.cell(30,10,row["Status"],1)
            pdf.cell(40,10,row["Date"],1)
            pdf.ln()
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        return BytesIO(pdf_bytes)
    if st.sidebar.button("💾 Download Tasks PDF"):
        pdf_bytes = generate_task_pdf(st.session_state.tasks)
        st.sidebar.download_button("⬇️ Download Tasks PDF", pdf_bytes, file_name="tasks_report.pdf", mime="application/pdf")
