import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="Taskuni", layout="wide")
st.title("⏱️ Focus Timer — Real Time + Sounds")

# ---------------- SESSION STATE ----------------
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

# ---------------- AUDIO FILES ----------------
alarm_files = {
    "Beep 1":"bedside-clock-alarm-95792.mp3",
    "Beep 2":"clock-alarm-8761.mp3",
    "Beep 3":"notification-2-371511.mp3",
    "Beep 4":"notification-3-371510.mp3",
    "Beep 5":"notification-6-371507.mp3"
}
alarm_choice = st.selectbox("Choose Alarm Sound", list(alarm_files.keys()))
selected_alarm = alarm_files[alarm_choice]

play_white_noise = st.checkbox("🎵 Play White Noise")

# ---------------- TIMER INPUTS ----------------
task_name = st.text_input("Task Name")
target_hours = st.number_input("Target Hours", min_value=0.0, step=0.01)

timer_box = st.empty()
report_box = st.empty()

col1,col2 = st.columns(2)
with col1:
    if st.button("Start Timer"):
        if not task_name:
            st.warning("Enter a task name first!")
        elif st.session_state.timer_active:
            st.warning("Timer already running!")
        else:
            st.session_state.current_task = task_name
            st.session_state.current_target = target_hours
            st.session_state.timer_start = datetime.now()
            st.session_state.timer_active = True
            st.success(f"Timer started for {task_name}!")

with col2:
    if st.button("Stop Timer"):
        if st.session_state.timer_active:
            elapsed = datetime.now()-st.session_state.timer_start
            total_seconds = int(elapsed.total_seconds())
            hours,remainder = divmod(total_seconds,3600)
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

# ---------------- REAL-TIME TIMER LOOP ----------------
if st.session_state.timer_active:
    start_time = st.session_state.timer_start
    while st.session_state.timer_active:
        elapsed = datetime.now() - start_time
        total_seconds = int(elapsed.total_seconds())
        hours,remainder = divmod(total_seconds,3600)
        minutes,seconds = divmod(remainder,60)
        timer_box.info(f"⏱️ {st.session_state.current_task} - {hours}h {minutes}m {seconds}s")

        # Play white noise
        if play_white_noise:
            timer_box.markdown(f"""
                <audio autoplay loop id="white_noise">
                    <source src="white_noise.mp3" type="audio/mp3">
                </audio>
            """, unsafe_allow_html=True)

        # Check if target reached
        if total_seconds >= int(st.session_state.current_target*3600):
            st.success(f"🎯 Target reached for {st.session_state.current_task}!")
            st.markdown(f"""
                <audio autoplay loop id="alarm">
                    <source src="{selected_alarm}" type="audio/mp3">
                </audio>
            """, unsafe_allow_html=True)

            # Log focused time
            focused_str = f"{hours}h {minutes}m {seconds}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data,pd.DataFrame([{
                "Task":st.session_state.current_task,
                "Target_Hours":st.session_state.current_target,
                "Focused_Hours":focused_str
            }])], ignore_index=True)

            st.session_state.timer_active = False
            st.session_state.current_task = ""
            st.session_state.current_target = 0.0
            break

        time.sleep(1)

# ---------------- TIMER REPORT ----------------
st.subheader("⏳ Focus Timer Report")
if not st.session_state.timer_data.empty:
    report_box.dataframe(st.session_state.timer_data,use_container_width=True)
