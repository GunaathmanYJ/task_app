import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="Taskuni", layout="wide")
st.title("📌 Taskuni — Task Tracker + Focus Timer")

# ---------------- SESSION STATE ----------------
if "tasks" not in st.session_state:
    st.session_state.tasks = pd.DataFrame(columns=["Task","Status"])
if "timer_data" not in st.session_state:
    st.session_state.timer_data = pd.DataFrame(columns=["Task","Target_Hours","Focused_Hours"])
if "timer_start" not in st.session_state:
    st.session_state.timer_start = None
if "current_task" not in st.session_state:
    st.session_state.current_task = ""
if "current_target" not in st.session_state:
    st.session_state.current_target = 0.0
if "timer_active" not in st.session_state:
    st.session_state.timer_active = False
if "alarm_played" not in st.session_state:
    st.session_state.alarm_played = False
if "elapsed_time" not in st.session_state:
    st.session_state.elapsed_time = timedelta()

# ---------------- AUDIO FILES ----------------
alarm_files = {
    "Beep 1":"bedside-clock-alarm-95792.mp3",
    "Beep 2":"clock-alarm-8761.mp3",
    "Beep 3":"notification-2-371511.mp3",
    "Beep 4":"notification-3-371510.mp3",
    "Beep 5":"notification-6-371507.mp3"
}

# ---------------- TABS ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker","⏱️ Focus Timer"])

# ---------------- TASK TRACKER ----------------
with tab1:
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input:
        st.session_state.tasks = pd.concat(
            [st.session_state.tasks,pd.DataFrame([[task_name_input,"Pending"]],columns=["Task","Status"])],
            ignore_index=True
        )
        st.experimental_rerun()

    st.subheader("Tasks")
    for i,row in st.session_state.tasks.iterrows():
        color = "#FFA500"
        if row["Status"]=="Done": color="#00C853"
        elif row["Status"]=="Not Done": color="#D50000"
        col1,col2,col3 = st.columns([5,1,1])
        col1.markdown(f"<div style='padding:10px;border-radius:8px;background-color:{color};color:white'>{i+1}. {row['Task']} - {row['Status']}</div>",unsafe_allow_html=True)
        if col2.button("✅ Done",key=f"done_{i}"):
            st.session_state.tasks.at[i,"Status"]="Done"
            st.experimental_rerun()
        if col3.button("❌ Not Done",key=f"notdone_{i}"):
            st.session_state.tasks.at[i,"Status"]="Not Done"
            st.experimental_rerun()

    st.subheader("📊 Task Report Card")
    if not st.session_state.tasks.empty:
        def highlight_status(s):
            if s=="Done": return 'background-color:#00C853;color:white'
            elif s=="Not Done": return 'background-color:#D50000;color:white'
            else: return 'background-color:#FFA500;color:white'
        df_display = st.session_state.tasks.copy()
        df_display.index+=1
        st.dataframe(df_display.style.applymap(highlight_status,subset=["Status"]),use_container_width=True)
        done_count = len(df_display[df_display["Status"]=="Done"])
        not_done_count = len(df_display[df_display["Status"]=="Not Done"])
        pending_count = len(df_display[df_display["Status"]=="Pending"])
        st.markdown(f"✅ Done: {done_count} | ❌ Not Done: {not_done_count} | ⏳ Pending: {pending_count}")

    class PDF(FPDF):
        def header(self):
            self.set_font("Arial","B",16)
            self.cell(0,10,"Task Report Card",ln=True,align="C")
            self.ln(10)
    def generate_pdf(tasks_df,filename="task_report.pdf"):
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
            pdf.cell(100,10,row["Task"],border=1)
            if row["Status"]=="Done": pdf.set_text_color(0,200,0)
            elif row["Status"]=="Not Done": pdf.set_text_color(255,0,0)
            else: pdf.set_text_color(255,165,0)
            pdf.cell(40,10,row["Status"],border=1)
            pdf.set_text_color(0,0,0)
            pdf.ln()
        pdf.output(filename)
        return filename
    if st.button("💾 Generate PDF Report"):
        if not st.session_state.tasks.empty:
            pdf_file = generate_pdf(st.session_state.tasks)
            st.success(f"✅ PDF generated: {pdf_file}")
            with open(pdf_file,"rb") as f:
                st.download_button("⬇️ Download PDF",f,file_name=pdf_file,mime="application/pdf")
        else:
            st.warning("⚠️ No tasks to generate PDF!")

# ---------------- FOCUS TIMER ----------------
with tab2:
    task_name_timer = st.text_input("Task Name for Timer",key="timer_task")
    target_time = st.number_input("Target Hours", min_value=0.0, step=0.01,key="timer_target")
    alarm_choice = st.selectbox("Choose Alarm Sound", list(alarm_files.keys()))
    selected_alarm = alarm_files[alarm_choice]
    play_white_noise = st.checkbox("🎵 Play White Noise")

    timer_placeholder = st.empty()
    report_placeholder = st.empty()

    col1,col2 = st.columns(2)
    with col1:
        if st.button("Start Timer") and task_name_timer:
            if st.session_state.timer_active:
                st.warning("Timer already running!")
            else:
                st.session_state.current_task = task_name_timer
                st.session_state.current_target = target_time
                st.session_state.timer_start = datetime.now()
                st.session_state.timer_active = True
                st.session_state.alarm_played = False
                st.session_state.elapsed_time = timedelta()
                st.success(f"Timer started for {task_name_timer}!")

    with col2:
        if st.button("Stop Timer"):
            if st.session_state.timer_active:
                elapsed = datetime.now()-st.session_state.timer_start
                st.session_state.elapsed_time += elapsed
                hours,remainder = divmod(int(st.session_state.elapsed_time.total_seconds()),3600)
                minutes,seconds = divmod(remainder,60)
                focused_str = f"{hours}h {minutes}m {seconds}s"
                st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([{
                    "Task":st.session_state.current_task,
                    "Target_Hours":st.session_state.current_target,
                    "Focused_Hours":focused_str
                }])],ignore_index=True)
                st.success(f"⏹️ Timer stopped manually for {st.session_state.current_task}")
            st.session_state.timer_active = False
            st.session_state.timer_start = None
            st.session_state.alarm_played = False

    # ---------------- REAL-TIME TIMER DISPLAY ----------------
    if st.session_state.timer_active:
        elapsed = datetime.now()-st.session_state.timer_start
        st.session_state.elapsed_time += elapsed
        st.session_state.timer_start = datetime.now()  # reset start
        hours,remainder = divmod(int(st.session_state.elapsed_time.total_seconds()),3600)
        minutes,seconds = divmod(remainder,60)
        timer_placeholder.info(f"⏱️ {st.session_state.current_task} - {hours}h {minutes}m {seconds}s")

        if play_white_noise:
            timer_placeholder.markdown("""
                <audio autoplay loop>
                    <source src="white_noise.mp3" type="audio/mp3">
                </audio>
            """,unsafe_allow_html=True)

        # ---------------- AUTO ALARM AT TARGET ----------------
        if int(st.session_state.elapsed_time.total_seconds()) >= int(st.session_state.current_target*3600) and not st.session_state.alarm_played:
            st.session_state.alarm_played = True
            timer_placeholder.success(f"🎯 Target reached for {st.session_state.current_task}!")

            # Autoplay alarm sound
            timer_placeholder.markdown(f"""
                <audio autoplay>
                    <source src="{selected_alarm}" type="audio/mp3">
                </audio>
            """, unsafe_allow_html=True)

            focused_str = f"{hours}h {minutes}m {seconds}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([{
                "Task":st.session_state.current_task,
                "Target_Hours":st.session_state.current_target,
                "Focused_Hours":focused_str
            }])], ignore_index=True)

            st.session_state.timer_active = False
            st.session_state.current_task = ""
            st.session_state.current_target = 0.0

    # ---------------- FOCUS TIMER REPORT ----------------
    st.subheader("⏳ Focus Timer Report")
    if not st.session_state.timer_data.empty:
        report_placeholder.dataframe(st.session_state.timer_data,use_container_width=True)
