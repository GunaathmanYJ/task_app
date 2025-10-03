import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import threading
import time

# --- App Config ---
st.set_page_config(page_title="Taskuni", layout="wide")
st.title("📌 Taskuni — Tracker + Focus Timer")

# --- Initialize session state ---
if "tasks" not in st.session_state:
    st.session_state.tasks = pd.DataFrame(columns=["Task", "Status"])
if "timer_data" not in st.session_state:
    st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_Hours", "Focused_Hours"])
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

# --- Alarm selection with your custom MP3 names ---
alarm_choice = st.selectbox("Choose Alarm Sound", ["Beep 1", "Beep 2", "Beep 3", "Beep 4", "Beep 5"])
alarm_files = {
    "Beep 1": "bedside-clock-alarm-95792.mp3",
    "Beep 2": "clock-alarm-8761.mp3",
    "Beep 3": "notification-2-371511.mp3",
    "Beep 4": "notification-3-371510.mp3",
    "Beep 5": "notification-6-371507.mp3"
}
selected_alarm = alarm_files[alarm_choice]

# --- White Noise toggle ---
play_white_noise = st.checkbox("🎵 Play White Noise")

# --- Tabs ---
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Focus Timer"])

# ----------------- TASK TRACKER -----------------
with tab1:
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input:
        st.session_state.tasks = pd.concat(
            [st.session_state.tasks, pd.DataFrame([[task_name_input, "Pending"]], columns=["Task", "Status"])],
            ignore_index=True
        )
        st.rerun()  

    # Display tasks
    st.subheader("Tasks")
    for i, row in st.session_state.tasks.iterrows():
        color = "#FFA500" 
        if row['Status'] == "Done":
            color = "#00C853" 
        elif row['Status'] == "Not Done":
            color = "#D50000" 

        col1, col2, col3 = st.columns([5,1,1])
        col1.markdown(
            f"<div style='padding:10px; border-radius:8px; background-color:{color}; color:white'>{i+1}. {row['Task']} - {row['Status']}</div>",
            unsafe_allow_html=True
        )
        
        if col2.button("✅ Done", key=f"done_{i}"):
            st.session_state.tasks.at[i, "Status"] = "Done"
            st.rerun()
            st.success(f"✅ {row['Task']} Complete! 🎉")

        if col3.button("❌ Not Done", key=f"notdone_{i}"):
            st.session_state.tasks.at[i, "Status"] = "Not Done"
            st.rerun()
            
    # Report Card
    st.subheader("📊 Task Report Card")
    if not st.session_state.tasks.empty:
        def highlight_status(status):
            if status == "Done":
                return 'background-color: #00C853; color: white'
            elif status == "Not Done":
                return 'background-color: #D50000; color: white'
            else:
                return 'background-color: #FFA500; color: white'

        df_display = st.session_state.tasks.copy()
        df_display.index += 1
        st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]), use_container_width=True)

        done_count = len(df_display[df_display["Status"]=="Done"])
        not_done_count = len(df_display[df_display["Status"]=="Not Done"])
        pending_count = len(df_display[df_display["Status"]=="Pending"])
        st.markdown(f"✅ **Done:** {done_count} | ❌ **Not Done:** {not_done_count} | ⏳ **Pending:** {pending_count}")

    # PDF generation
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 16)
            self.cell(0, 10, "Task Report Card", ln=True, align="C")
            self.ln(10)

    def generate_pdf(tasks_df, filename="task_report.pdf"):
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", "", 12)

        pdf.set_fill_color(200, 200, 200)
        pdf.cell(10, 10, "#", border=1, fill=True)
        pdf.cell(100, 10, "Task", border=1, fill=True)
        pdf.cell(40, 10, "Status", border=1, fill=True)
        pdf.ln()
        
        for i, row in tasks_df.iterrows():
            pdf.cell(10, 10, str(i+1), border=1)
            pdf.cell(100, 10, row["Task"], border=1)
            if row["Status"] == "Done":
                pdf.set_text_color(0, 200, 0)
            elif row["Status"] == "Not Done":
                pdf.set_text_color(255, 0, 0)
            else:  
                pdf.set_text_color(255, 165, 0)
            pdf.cell(40, 10, row["Status"], border=1)
            pdf.set_text_color(0,0,0)
            pdf.ln()

        pdf.output(filename)
        return filename

    if st.button("💾 Generate PDF Report"):
        if not st.session_state.tasks.empty:
            pdf_file = generate_pdf(st.session_state.tasks)
            st.success(f"✅ PDF generated: {pdf_file}")
            with open(pdf_file, "rb") as f:
                st.download_button(
                    label="⬇️ Download PDF",
                    data=f,
                    file_name=pdf_file,
                    mime="application/pdf"
                )
        else:
            st.warning("⚠️ No tasks to generate PDF!")

# ----------------- FOCUS TIMER -----------------
with tab2:
    task_name_timer = st.text_input("Task Name for Timer")
    target_time = st.number_input("Target Hours", min_value=0.0, step=0.01)  # small for testing
    timer_placeholder = st.empty()

    def run_timer(task, target_hours, alarm_file, white_noise_file=None):
        st.session_state.current_task = task
        st.session_state.current_target = target_hours
        st.session_state.timer_start = datetime.now()
        target_seconds = int(target_hours * 3600)
        elapsed_seconds = 0

        # Start white noise if enabled
        if white_noise_file and play_white_noise:
            st.session_state.white_noise_playing = True
            st.markdown(f"""
                <audio autoplay loop id="white_noise">
                    <source src="{white_noise_file}" type="audio/mp3">
                </audio>
            """, unsafe_allow_html=True)

        while elapsed_seconds < target_seconds:
            if st.session_state.timer_start is None:
                break  # Timer stopped
            elapsed = datetime.now() - st.session_state.timer_start
            elapsed_seconds = int(elapsed.total_seconds())
            hours, remainder = divmod(elapsed_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            timer_placeholder.info(f"Timer running: {hours}h {minutes}m {seconds}s")
            time.sleep(1)

        # Stop white noise
        if st.session_state.white_noise_playing:
            st.session_state.white_noise_playing = False
            st.markdown("""
                <script>
                var audio = document.getElementById('white_noise');
                if(audio){ audio.pause(); }
                </script>
            """, unsafe_allow_html=True)

        # When target reached
        if st.session_state.timer_start is not None:
            timer_placeholder.success(f"🎯 Target time reached for {task}!")
            st.session_state.alarm_playing = True
            st.markdown(f"""
                <audio autoplay loop id="alarm">
                    <source src="{alarm_file}" type="audio/mp3">
                </audio>
            """, unsafe_allow_html=True)

            focused_str = f"{hours}h {minutes}m {seconds}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": task,
                "Target_Hours": target_hours,
                "Focused_Hours": focused_str
            }])], ignore_index=True)

            st.session_state.timer_start = None
            st.session_state.current_task = ""
            st.session_state.current_target = 0.0

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Timer"):
            if task_name_timer:
                white_noise_file = "white_noise.mp3" if play_white_noise else None
                threading.Thread(target=run_timer, args=(task_name_timer, target_time, selected_alarm, white_noise_file), daemon=True).start()
            else:
                st.warning("Enter a task name first!")

    with col2:
        if st.button("Stop Timer"):
            st.session_state.timer_start = None
            timer_placeholder.info("⏹️ Timer stopped manually.")
            if st.session_state.alarm_playing:
                st.session_state.alarm_playing = False
                st.markdown("""
                    <script>
                    var audio = document.getElementById('alarm');
                    if(audio){ audio.pause(); }
                    </script>
                """, unsafe_allow_html=True)
            if st.session_state.white_noise_playing:
                st.session_state.white_noise_playing = False
                st.markdown("""
                    <script>
                    var audio = document.getElementById('white_noise');
                    if(audio){ audio.pause(); }
                    </script>
                """, unsafe_allow_html=True)

    if st.button("Generate Timer Report"):
        if not st.session_state.timer_data.empty:
            st.subheader("⏱️ Timer Task Report")
            st.dataframe(st.session_state.timer_data)
        else:
            st.info("No timed tasks logged yet.")
