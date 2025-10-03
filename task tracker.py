import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import time

st.set_page_config(page_title="Taskuni", layout="wide")
st.title("📌 Taskuni — Tracker + Focus Timer")

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
if "alarm_playing" not in st.session_state:
    st.session_state.alarm_playing = False
if "white_noise_playing" not in st.session_state:
    st.session_state.white_noise_playing = False

# ---------------- ALARM & WHITE NOISE ----------------
alarm_choice = st.selectbox("Choose Alarm Sound", ["Beep 1","Beep 2","Beep 3","Beep 4","Beep 5"])
alarm_files = {
    "Beep 1":"bedside-clock-alarm-95792.mp3",
    "Beep 2":"clock-alarm-8761.mp3",
    "Beep 3":"notification-2-371511.mp3",
    "Beep 4":"notification-3-371510.mp3",
    "Beep 5":"notification-6-371507.mp3"
}
selected_alarm = alarm_files[alarm_choice]

play_white_noise = st.checkbox("🎵 Play White Noise")

# ---------------- TABS ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker","⏱️ Focus Timer"])

# ---------------- TASK TRACKER ----------------
with tab1:
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input:
        st.session_state.tasks = pd.concat([st.session_state.tasks,pd.DataFrame([[task_name_input,"Pending"]],columns=["Task","Status"])],ignore_index=True)
        st.rerun()

    st.subheader("Tasks")
    for i,row in st.session_state.tasks.iterrows():
        color = "#FFA500"
        if row["Status"]=="Done": color="#00C853"
        elif row["Status"]=="Not Done": color="#D50000"
        col1,col2,col3 = st.columns([5,1,1])
        col1.markdown(f"<div style='padding:10px;border-radius:8px;background-color:{color};color:white'>{i+1}. {row['Task']} - {row['Status']}</div>",unsafe_allow_html=True)
        if col2.button("✅ Done",key=f"done_{i}"):
            st.session_state.tasks.at[i,"Status"]="Done"
            st.rerun()
        if col3.button("❌ Not Done",key=f"notdone_{i}"):
            st.session_state.tasks.at[i,"Status"]="Not Done"
            st.rerun()

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
    task_name_timer = st.text_input("Task Name for Timer")
    target_time = st.number_input("Target Hours", min_value=0.0, step=0.01)
    timer_box = st.empty() # Placeholder for real-time timer
    report_box = st.empty() # Placeholder for timer report table

    col1,col2 = st.columns(2)
    with col1:
        if st.button("Start Timer"):
            if not task_name_timer:
                st.warning("Enter a task name first!")
            elif st.session_state.timer_start:
                st.warning("⏳ Timer already running!")
            else:
                st.session_state.current_task = task_name_timer
                st.session_state.current_target = target_time
                st.session_state.timer_start = datetime.now()
                st.success(f"Timer started for {task_name_timer}!")

    with col2:
        if st.button("Stop Timer"):
            if st.session_state.timer_start:
                elapsed = datetime.now()-st.session_state.timer_start
                total_seconds = int(elapsed.total_seconds())
                hours,remainder=divmod(total_seconds,3600)
                minutes,seconds=divmod(remainder,60)
                focused_str = f"{hours}h {minutes}m {seconds}s"
                st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([{
                    "Task":st.session_state.current_task,
                    "Target_Hours":st.session_state.current_target,
                    "Focused_Hours":focused_str
                }])],ignore_index=True)
            st.session_state.timer_start = None
            timer_box.info("⏹️ Timer stopped manually.")
            # Stop audio
            st.session_state.alarm_playing=False
            st.session_state.white_noise_playing=False
            st.markdown("""<script>var audio=document.getElementById('alarm');if(audio){audio.pause();} var wn=document.getElementById('white_noise');if(wn){wn.pause();}</script>""",unsafe_allow_html=True)

    # --- Real-time timer loop ---
    if st.session_state.timer_start:
        start_time = st.session_state.timer_start
        while st.session_state.timer_start:
            elapsed = datetime.now()-start_time
            total_seconds = int(elapsed.total_seconds())
            hours,remainder=divmod(total_seconds,3600)
            minutes,seconds=divmod(remainder,60)
            timer_box.info(f"⏱️ {st.session_state.current_task} - {hours}h {minutes}m {seconds}s")

            # Play white noise
            if play_white_noise and not st.session_state.white_noise_playing:
                st.session_state.white_noise_playing=True
                st.markdown(f"""
                    <audio autoplay loop id="white_noise">
                        <source src="white_noise.mp3" type="audio/mp3">
                    </audio>
                """,unsafe_allow_html=True)

            # Check target
            if total_seconds >= int(st.session_state.current_target*3600):
                st.session_state.timer_start = None
                st.session_state.alarm_playing=True
                timer_box.success(f"🎯 Target reached for {st.session_state.current_task}!")
                # Alarm sound
                st.markdown(f"""
                    <audio autoplay loop id="alarm">
                        <source src="{selected_alarm}" type="audio/mp3">
                    </audio>
                """,unsafe_allow_html=True)
                # Stop white noise
                st.session_state.white_noise_playing=False
                st.markdown("""<script>var wn=document.getElementById('white_noise');if(wn){wn.pause();}</script>""",unsafe_allow_html=True)
                # Log focused time
                focused_str=f"{hours}h {minutes}m {seconds}s"
                st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([{
                    "Task":st.session_state.current_task,
                    "Target_Hours":st.session_state.current_target,
                    "Focused_Hours":focused_str
                }])],ignore_index=True)
                st.session_state.current_task=""
                st.session_state.current_target=0.0
                break
            time.sleep(1)
            st.experimental_rerun()

    # Timer report table
    st.subheader("⏳ Focus Timer Report")
    if not st.session_state.timer_data.empty:
        report_box.dataframe(st.session_state.timer_data,use_container_width=True)
