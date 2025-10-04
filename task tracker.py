import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import time
from io import BytesIO
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="TaskUni Premium", layout="wide")

# ---------------- Auto-create users.csv ----------------
USERS_FILE = "users.csv"
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["username","password"]).to_csv(USERS_FILE,index=False)

users = pd.read_csv(USERS_FILE)

# ---------------- Login/Register Tabs ----------------
tab_login, tab_register = st.tabs(["Login","Register"])

logged_in_user = None

with tab_login:
    st.subheader("Login")
    login_user = st.text_input("Username", key="login_user")
    login_pass = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        if login_user not in users["username"].values:
            st.error("User not found! Please register first.")
        else:
            correct_pass = users.loc[users["username"]==login_user,"password"].values[0]
            if login_pass == correct_pass:
                st.success(f"Logged in as {login_user}")
                logged_in_user = login_user
            else:
                st.error("Incorrect password!")

with tab_register:
    st.subheader("Register")
    reg_user = st.text_input("Choose Username", key="reg_user")
    reg_pass = st.text_input("Choose Password", type="password", key="reg_pass")
    if st.button("Register"):
        if reg_user in users["username"].values:
            st.error("Username already taken")
        elif reg_user.strip() == "" or reg_pass.strip() == "":
            st.warning("Enter valid username & password")
        else:
            new_user = pd.DataFrame({"username":[reg_user],"password":[reg_pass]})
            new_user.to_csv(USERS_FILE, mode="a", header=False, index=False)
            st.success(f"Account created! You can now log in as {reg_user}")
if logged_in_user:  # Only show main app if user logged in

    # ---------------- Sidebar Logo ----------------
    st.sidebar.image("taskuni.png", width=100)

    # ---------------- Load user data ----------------
    today_date = datetime.now().strftime("%d-%m-%Y")
    TASKS_FILE = f"tasks_{logged_in_user}.csv"
    TIMER_FILE = f"timer_{logged_in_user}.csv"
    POMODORO_FILE = f"pomodoro_{logged_in_user}.csv"

    # Load or initialize
    if os.path.exists(TASKS_FILE):
        tasks_df = pd.read_csv(TASKS_FILE)
    else:
        tasks_df = pd.DataFrame(columns=["Task","Status","Date"])

    if os.path.exists(TIMER_FILE):
        timer_df = pd.read_csv(TIMER_FILE)
    else:
        timer_df = pd.DataFrame(columns=["Task","Target_HMS","Focused_HMS","Date"])

    if os.path.exists(POMODORO_FILE):
        pomo_df = pd.read_csv(POMODORO_FILE)
    else:
        pomo_df = pd.DataFrame(columns=["Task","Duration_min","Focused_min","Date"])

    # ---------------- Main Tabs ----------------
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Task Tracker","⏱️ Timer","🍅 Pomodoro","👥 Group Study"])

    # ---------------- Task Tracker ----------------
    with tab1:
        st.subheader(f"Tasks for {today_date}")
        task_input = st.text_input("Enter Task", key="task_input")
        if st.button("Add Task"):
            if task_input.strip():
                new_task = {"Task":task_input.strip(),"Status":"Pending","Date":today_date}
                tasks_df = pd.concat([tasks_df,pd.DataFrame([new_task])],ignore_index=True)
                tasks_df.to_csv(TASKS_FILE,index=False)
                st.success("Task added!")

        # Show today's tasks
        today_tasks = tasks_df[tasks_df['Date']==today_date]
        if not today_tasks.empty:
            def highlight_status(s):
                if s=="Done":
                    return 'background-color:#00C853;color:white'
                elif s=="Not Done":
                    return 'background-color:#D50000;color:white'
                else:
                    return 'background-color:#FFA500;color:white'
            df_display = today_tasks[["Task","Status"]].copy()
            df_display.index += 1
            st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]),use_container_width=True)

            st.markdown("### Update Tasks")
            for i,row in today_tasks.iterrows():
                cols = st.columns([3,1,1,1])
                cols[0].write(f"{row['Task']}:")
                cols[1].button("Done", key=f"done_{i}", on_click=lambda idx=i: update_task_status(idx,"Done"))
                cols[2].button("Not Done", key=f"notdone_{i}", on_click=lambda idx=i: update_task_status(idx,"Not Done"))
                cols[3].button("Delete", key=f"delete_{i}", on_click=lambda idx=i: delete_task(idx))

    # ---------------- Countdown Timer ----------------
    with tab2:
        st.subheader("Countdown Timer")
        col_h,col_m,col_s = st.columns(3)
        hours = col_h.number_input("Hours",0,23,0,key="hours_input")
        minutes = col_m.number_input("Minutes",0,59,0,key="minutes_input")
        seconds = col_s.number_input("Seconds",0,59,0,key="seconds_input")
        timer_task_name = st.text_input("Task name (optional)", key="timer_task_input")
        start_timer = st.button("Start Timer")
        stop_timer = st.button("Stop Timer")
        pause_timer = st.button("Pause/Resume Timer")

        if "timer_running" not in st.session_state:
            st.session_state.timer_running=False
            st.session_state.timer_start_time=None
            st.session_state.timer_total_seconds=0
            st.session_state.timer_paused=False
            st.session_state.timer_elapsed=0

        if start_timer:
            total_seconds = hours*3600 + minutes*60 + seconds
            if total_seconds>0:
                st.session_state.timer_running=True
                st.session_state.timer_start_time=time.time()
                st.session_state.timer_total_seconds=total_seconds
                st.session_state.timer_task_name = timer_task_name if timer_task_name else "Unnamed"
                st.session_state.timer_paused=False
                st.session_state.timer_elapsed=0

        if pause_timer and st.session_state.timer_running:
            st.session_state.timer_paused = not st.session_state.timer_paused
            if st.session_state.timer_paused:
                st.warning("Timer paused")
            else:
                st.success("Timer resumed")
                st.session_state.timer_start_time = time.time()

        if stop_timer and st.session_state.timer_running:
            elapsed = st.session_state.timer_elapsed
            h=m=s=0
            total_seconds = st.session_state.timer_total_seconds
            if st.session_state.timer_paused:
                elapsed = st.session_state.timer_elapsed
            else:
                elapsed += int(time.time()-st.session_state.timer_start_time)
            elapsed = min(elapsed,total_seconds)
            h = elapsed//3600
            m = (elapsed%3600)//60
            s = elapsed%60
            new_timer = {"Task":st.session_state.timer_task_name,
                         "Target_HMS":f"{hours}h {minutes}m {seconds}s",
                         "Focused_HMS":f"{h}h {m}m {s}s",
                         "Date":today_date}
            timer_df = pd.concat([timer_df,pd.DataFrame([new_timer])],ignore_index=True)
            timer_df.to_csv(TIMER_FILE,index=False)
            st.success(f"Timer stopped. Focused: {h}h {m}m {s}s")
            st.session_state.timer_running=False

        # Display timer
        if st.session_state.timer_running and not st.session_state.timer_paused:
            st_autorefresh(interval=1000,key="timer_refresh")
            elapsed = int(time.time()-st.session_state.timer_start_time) + st.session_state.timer_elapsed
            remaining = max(st.session_state.timer_total_seconds - elapsed,0)
            h = remaining//3600
            m = (remaining%3600)//60
            s = remaining%60
            st.markdown(f"<h1 style='text-align:center;font-size:120px;'>⏱️ {h:02d}:{m:02d}:{s:02d}</h1>"
                        f"<h3 style='text-align:center;font-size:36px;'>Task: {st.session_state.timer_task_name}</h3>",
                        unsafe_allow_html=True)
            if remaining==0:
                new_timer = {"Task":st.session_state.timer_task_name,
                             "Target_HMS":f"{hours}h {minutes}m {seconds}s",
                             "Focused_HMS":f"{hours}h {minutes}m {seconds}s",
                             "Date":today_date}
                timer_df = pd.concat([timer_df,pd.DataFrame([new_timer])],ignore_index=True)
                timer_df.to_csv(TIMER_FILE,index=False)
                st.session_state.timer_running=False
                st.success("🎯 Countdown Finished!")

    # ---------------- Pomodoro Tab ----------------
    with tab3:
        st.subheader("Pomodoro Timer")
        if "pomo_running" not in st.session_state:
            st.session_state.pomo_running=False
            st.session_state.pomo_start_time=None
            st.session_state.pomo_total_seconds=0
            st.session_state.pomo_elapsed=0
            st.session_state.pomo_paused=False
            st.session_state.pomo_pause_count=0
            st.session_state.daily_focus_target_min=0
            st.session_state.daily_focus_done_min=0

        st.session_state.daily_focus_target_min = st.number_input(
            "How many hours you want to focus today?", 0.5, 12.0, step=0.5, key="daily_focus_target")*60

        pomo_work = st.number_input("Work minutes", 5, 180, value=25, key="pomo_work_min")
        short_break = st.number_input("Short break minutes", 1, 60, value=5, key="pomo_short_break")
        long_break = st.number_input("Long break minutes", 1, 60, value=15, key="pomo_long_break")
        pomo_rounds = st.number_input("How many pomodoros?", 1, 20, value=4, key="pomo_rounds")

        start_pomo = st.button("Start Pomodoro")
        pause_pomo = st.button("Pause/Resume Pomodoro")
        cancel_pomo = st.button("Cancel Pomodoro")

        if start_pomo:
            st.session_state.pomo_running=True
            st.session_state.pomo_start_time=time.time()
            st.session_state.pomo_total_seconds=int(pomo_work*60)
            st.session_state.pomo_paused=False

        if pause_pomo and st.session_state.pomo_running:
            st.session_state.pomo_paused = not st.session_state.pomo_paused
            st.session_state.pomo_pause_count +=1 if st.session_state.pomo_paused else 0
            if st.session_state.pomo_pause_count>2:
                st.warning("Pausing more than 2 times cancels Pomodoro")
                st.session_state.pomo_running=False
            else:
                msg = "Pomodoro paused" if st.session_state.pomo_paused else "Pomodoro resumed"
                st.info(msg)
                if not st.session_state.pomo_paused:
                    st.session_state.pomo_start_time=time.time()

        if cancel_pomo and st.session_state.pomo_running:
            st.session_state.pomo_running=False
            st.warning("Pomodoro cancelled")

        # Pomodoro countdown
        if st.session_state.pomo_running and not st.session_state.pomo_paused:
            st_autorefresh(interval=1000,key="pomo_refresh")
            elapsed=int(time.time()-st.session_state.pomo_start_time)+st.session_state.pomo_elapsed
            remaining=max(st.session_state.pomo_total_seconds - elapsed,0)
            m,s= divmod(remaining,60)
            st.markdown(f"<h1 style='text-align:center;font-size:80px;'>🍅 {m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
            if remaining==0:
                st.success("Pomodoro Finished!")
                st.session_state.daily_focus_done_min += pomo_work
                new_pomo = {"Task":"Pomodoro","Duration_min":pomo_work,"Focused_min":pomo_work,"Date":today_date}
                pomo_df = pd.concat([pomo_df,pd.DataFrame([new_pomo])],ignore_index=True)
                pomo_df.to_csv(POMODORO_FILE,index=False)
                st.session_state.pomo_running=False

        # Check daily target
        if st.session_state.daily_focus_done_min >= st.session_state.daily_focus_target_min:
            st.balloons()
            st.success("🎉 You reached your daily focus target! Take a break now.")

    # ---------------- Group Study Tab ----------------
    with tab4:
        st.subheader("Group Study")
        GROUP_FILE = "group_study.csv"
        if not os.path.exists(GROUP_FILE):
            pd.DataFrame(columns=["Username","Message","Notes","DateTime"]).to_csv(GROUP_FILE,index=False)
        group_df = pd.read_csv(GROUP_FILE)

        username_input = logged_in_user
        msg_input = st.text_input("Message")
        note_input = st.text_area("Shared Note")
        if st.button("Send Message"):
            if msg_input.strip():
                new_msg = {"Username":username_input,"Message":msg_input,"Notes":"","DateTime":datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
                group_df = pd.concat([group_df,pd.DataFrame([new_msg])],ignore_index=True)
            if note_input.strip():
                new_note = {"Username":username_input,"Message":"","Notes":note_input,"DateTime":datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
                group_df = pd.concat([group_df,pd.DataFrame([new_note])],ignore_index=True)
            group_df.to_csv(GROUP_FILE,index=False)
            st.success("Updated!")

        if not group_df.empty:
            st.dataframe(group_df.sort_values("DateTime"),use_container_width=True)

    # ---------------- PDF Exports ----------------
    st.sidebar.subheader("Export Reports")
    if not tasks_df.empty:
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
            pdf.cell(10,10,"#",border=1,fill=True)
            pdf.cell(100,10,"Task",border=1,fill=True)
            pdf.cell(30,10,"Status",border=1,fill=True)
            pdf.cell(40,10,"Date",border=1,fill=True)
            pdf.ln()
            for i,row in tasks_df.iterrows():
                pdf.cell(10,10,str(i+1),border=1)
                pdf.cell(100,10,row["Task"],border=1)
                pdf.cell(30,10,row["Status"],border=1)
                pdf.cell(40,10,row["Date"],border=1)
                pdf.ln()
            return BytesIO(pdf.output(dest='S').encode('latin-1'))
        if st.sidebar.button("💾 Download Tasks PDF"):
            pdf_bytes = generate_task_pdf(tasks_df)
            st.sidebar.download_button("⬇️ Download Tasks PDF",pdf_bytes,file_name="tasks_report.pdf",mime="application/pdf")

    if not timer_df.empty:
        class TimerPDF(FPDF):
            def header(self):
                self.set_font("Arial","B",16)
                self.cell(0,10,"Timers Report",ln=True,align="C")
                self.ln(10)
        def generate_timer_pdf(timer_df):
            pdf = TimerPDF()
            pdf.add_page()
            pdf.set_font("Arial","",12)
            pdf.set_fill_color(200,200,200)
            pdf.cell(10,10,"#",border=1,fill=True)
            pdf.cell(80,10,"Task",border=1,fill=True)
            pdf.cell(50,10,"Target Time",border=1,fill=True)
            pdf.cell(50,10,"Focused Time",border=1,fill=True)
            pdf.ln()
            for i,row in timer_df.iterrows():
                pdf.cell(10,10,str(i+1),border=1)
                pdf.cell(80,10,row["Task"],border=1)
                pdf.cell(50,10,row["Target_HMS"],border=1)
                pdf.cell(50,10,row["Focused_HMS"],border=1)
                pdf.ln()
            return BytesIO(pdf.output(dest='S').encode('latin-1'))
        if st.sidebar.button("💾 Download Timer PDF"):
            pdf_bytes = generate_timer_pdf(timer_df)
            st.sidebar.download_button("⬇️ Download Timer PDF",pdf_bytes,file_name="timer_report.pdf",mime="application/pdf")

    if not pomo_df.empty:
        class PomoPDF(FPDF):
            def header(self):
                self.set_font("Arial","B",16)
                self.cell(0,10,"Pomodoro Report",ln=True,align="C")
                self.ln(10)
        def generate_pomo_pdf(pomo_df):
            pdf = PomoPDF()
            pdf.add_page()
            pdf.set_font("Arial","",12)
            pdf.set_fill_color(200,200,200)
            pdf.cell(10,10,"#",border=1,fill=True)
            pdf.cell(80,10,"Task",border=1,fill=True)
            pdf.cell(50,10,"Duration (min)",border=1,fill=True)
            pdf.cell(50,10,"Focused (min)",border=1,fill=True)
            pdf.cell(30,10,"Date",border=1,fill=True)
            pdf.ln()
            for i,row in pomo_df.iterrows():
                pdf.cell(10,10,str(i+1),border=1)
                pdf.cell(80,10,row["Task"],border=1)
                pdf.cell(50,10,str(row["Duration_min"]),border=1)
                pdf.cell(50,10,str(row["Focused_min"]),border=1)
                pdf.cell(30,10,row["Date"],border=1)
                pdf.ln()
            return BytesIO(pdf.output(dest='S').encode('latin-1'))
        if st.sidebar.button("💾 Download Pomodoro PDF"):
            pdf_bytes = generate_pomo_pdf(pomo_df)
            st.sidebar.download_button("⬇️ Download Pomodoro PDF",pdf_bytes,file_name="pomodoro_report.pdf",mime="application/pdf")
