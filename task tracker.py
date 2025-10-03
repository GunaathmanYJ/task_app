import streamlit as st
import pandas as pd
from fpdf import FPDF
import time

st.set_page_config(page_title="Taskuni", layout="wide")
st.title("📌 Taskuni — Task Scheduler + Manual Countdown Timer")

# ---------------- Session state initialization ----------------
if "tasks" not in st.session_state:
    st.session_state.tasks = pd.DataFrame(columns=["Task", "Status"])
if "timer_data" not in st.session_state:
    st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_HMS", "Focused_HMS"])
if "countdown_running" not in st.session_state:
    st.session_state.countdown_running = False
if "alarm_playing" not in st.session_state:
    st.session_state.alarm_playing = False
if "white_noise_on" not in st.session_state:
    st.session_state.white_noise_on = False
if "stop_alarm_trigger" not in st.session_state:
    st.session_state.stop_alarm_trigger = False

# ---------------- Audio files mapping (your custom names) ----------------
alarm_files = {
    "Beep 1": "bedside-clock-alarm-95792.mp3",
    "Beep 2": "clock-alarm-8761.mp3",
    "Beep 3": "notification-2-371511.mp3",
    "Beep 4": "notification-3-371510.mp3",
    "Beep 5": "notification-6-371507.mp3"
}

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Manual Countdown Timer"])

# ---------------- Task Tracker (unchanged) ----------------
with tab1:
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input:
        st.session_state.tasks = pd.concat(
            [st.session_state.tasks, pd.DataFrame([[task_name_input, "Pending"]], columns=["Task", "Status"])],
            ignore_index=True
        )
        st.experimental_rerun()

    st.subheader("Tasks")
    for i, row in st.session_state.tasks.iterrows():
        color = "#FFA500"
        if row["Status"] == "Done":
            color = "#00C853"
        elif row["Status"] == "Not Done":
            color = "#D50000"

        col1, col2, col3 = st.columns([5, 1, 1])
        col1.markdown(
            f"<div style='padding:10px;border-radius:8px;background-color:{color};color:white'>{i+1}. {row['Task']} - {row['Status']}</div>",
            unsafe_allow_html=True
        )
        if col2.button("✅ Done", key=f"done_{i}"):
            st.session_state.tasks.at[i, "Status"] = "Done"
            st.experimental_rerun()
        if col3.button("❌ Not Done", key=f"notdone_{i}"):
            st.session_state.tasks.at[i, "Status"] = "Not Done"
            st.experimental_rerun()

    st.subheader("📊 Task Report Card")
    if not st.session_state.tasks.empty:
        def highlight_status(s):
            if s == "Done":
                return 'background-color:#00C853;color:white'
            elif s == "Not Done":
                return 'background-color:#D50000;color:white'
            else:
                return 'background-color:#FFA500;color:white'

        df_display = st.session_state.tasks.copy()
        df_display.index += 1
        st.dataframe(df_display.style.applymap(highlight_status, subset=["Status"]), use_container_width=True)

        done_count = len(df_display[df_display["Status"] == "Done"])
        not_done_count = len(df_display[df_display["Status"] == "Not Done"])
        pending_count = len(df_display[df_display["Status"] == "Pending"])
        st.markdown(f"✅ Done: {done_count} | ❌ Not Done: {not_done_count} | ⏳ Pending: {pending_count}")

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
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
        pdf.output(filename)
        return filename

    if st.button("💾 Generate PDF Report"):
        if not st.session_state.tasks.empty:
            pdf_file = generate_pdf(st.session_state.tasks)
            st.success(f"✅ PDF generated: {pdf_file}")
            with open(pdf_file, "rb") as f:
                st.download_button("⬇️ Download PDF", f, file_name=pdf_file, mime="application/pdf")
        else:
            st.warning("⚠️ No tasks to generate PDF!")

# ---------------- Manual Countdown Timer Tab ----------------
with tab2:
    st.write("Set countdown time (hours : minutes : seconds)")
    col_h, col_m, col_s = st.columns(3)
    with col_h:
        init_hours = st.number_input("Hours", min_value=0, max_value=23, value=0, step=1, key="input_hours")
    with col_m:
        init_minutes = st.number_input("Minutes", min_value=0, max_value=59, value=0, step=1, key="input_minutes")
    with col_s:
        init_seconds = st.number_input("Seconds", min_value=0, max_value=59, value=0, step=1, key="input_seconds")

    task_for_timer = st.text_input("Task name for this countdown (optional)", key="countdown_task")

    alarm_choice = st.selectbox("Choose Alarm Sound", list(alarm_files.keys()), key="alarm_choice_ui")
    selected_alarm_file = alarm_files[alarm_choice]

    white_noise_choice = st.checkbox("🎵 Turn on white noise during countdown (requires white_noise.mp3)", key="white_noise_checkbox")

    start_col, stop_col, stop_alarm_col = st.columns([1,1,1])
    start_btn = start_col.button("Start Countdown")
    stop_btn = stop_col.button("Stop Countdown")
    stop_alarm_btn = stop_alarm_col.button("Stop Alarm (if playing)")

    # Placeholders
    display_box = st.empty()
    controls_box = st.empty()  # for audio fallback buttons if autoplay blocked

    # Convert initial HMS into total seconds when starting
    if start_btn:
        total_seconds = init_hours * 3600 + init_minutes * 60 + init_seconds
        if total_seconds <= 0:
            st.warning("Set a time greater than 0.")
        else:
            # Store countdown state as HH,MM,SS integers for manual decrement logic
            st.session_state.countdown_h = init_hours
            st.session_state.countdown_m = init_minutes
            st.session_state.countdown_s = init_seconds
            st.session_state.countdown_running = True
            st.session_state.alarm_playing = False
            st.session_state.white_noise_on = white_noise_choice
            # store which task (optional)
            st.session_state.current_countdown_task = task_for_timer if task_for_timer else "Unnamed"
            st.success(f"Countdown started for {st.session_state.current_countdown_task}")

    # Stop countdown button
    if stop_btn:
        if st.session_state.countdown_running:
            # compute elapsed by comparing initial set - remaining
            rem_seconds = st.session_state.countdown_h * 3600 + st.session_state.countdown_m * 60 + st.session_state.countdown_s
            initial_total = init_hours * 3600 + init_minutes * 60 + init_seconds
            elapsed_seconds = initial_total - rem_seconds
            # format focused HMS
            eh = elapsed_seconds // 3600
            em = (elapsed_seconds % 3600) // 60
            es = elapsed_seconds % 60
            focused_hms = f"{eh}h {em}m {es}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.get("current_countdown_task", "Unnamed"),
                "Target_HMS": f"{init_hours}h {init_minutes}m {init_seconds}s",
                "Focused_HMS": focused_hms
            }])], ignore_index=True)
            st.session_state.countdown_running = False
            st.session_state.white_noise_on = False
            st.success(f"Countdown stopped. Focus logged: {focused_hms}")
        else:
            st.info("No countdown running.")

    # Stop alarm button (pauses any HTML audio element by id)
    if stop_alarm_btn:
        st.session_state.alarm_playing = False
        st.session_state.stop_alarm_trigger = True
        # inject JS to pause any playing audio elements with ids we used
        st.markdown(
            """
            <script>
            var alarm = document.getElementById('countdown_alarm');
            if(alarm){ alarm.pause(); }
            var wn = document.getElementById('countdown_white_noise');
            if(wn){ wn.pause(); }
            </script>
            """,
            unsafe_allow_html=True,
        )

    # Countdown loop (manual HMS decrement)
    if st.session_state.countdown_running:
        # Ensure our HMS values exist (when session restarted mid-run)
        h = st.session_state.get("countdown_h", 0)
        m = st.session_state.get("countdown_m", 0)
        s = st.session_state.get("countdown_s", 0)

        # Display current timer and run decrement loop
        while st.session_state.countdown_running:
            # Show the timer prominently
            display_box.markdown(f"### ⏱️ Countdown — {h:02d}:{m:02d}:{s:02d}  \n**Task:** {st.session_state.get('current_countdown_task','Unnamed')}")
            # If white noise requested, render looping white noise (browser may require a prior interaction)
            if st.session_state.white_noise_on:
                display_box.markdown(
                    """
                    <audio autoplay loop id="countdown_white_noise">
                        <source src="white_noise.mp3" type="audio/mp3">
                    </audio>
                    """,
                    unsafe_allow_html=True,
                )

            # sleep one second
            time.sleep(1)

            # decrement logic
            if s > 0:
                s -= 1
            else:
                # s == 0
                if m > 0:
                    m -= 1
                    s = 59
                else:
                    # m == 0
                    if h > 0:
                        h -= 1
                        m = 59
                        s = 59
                    else:
                        # reached 0:0:0
                        h, m, s = 0, 0, 0
                        st.session_state.countdown_running = False
                        break

            # save back to session state so stop button computes elapsed correctly if pressed
            st.session_state.countdown_h = h
            st.session_state.countdown_m = m
            st.session_state.countdown_s = s

        # countdown finished naturally (hit 00:00:00)
        if not st.session_state.countdown_running and not st.session_state.alarm_playing:
            # stop white noise if on
            if st.session_state.white_noise_on:
                # pause via JS element id if possible
                st.markdown(
                    """
                    <script>
                    var wn = document.getElementById('countdown_white_noise');
                    if(wn){ wn.pause(); }
                    </script>
                    """,
                    unsafe_allow_html=True,
                )
                st.session_state.white_noise_on = False

            # Play alarm via HTML autoplay (browser might block; fallback below)
            st.session_state.alarm_playing = True
            display_box.success("🎯 Time's up!")

            # HTML autoplay attempt (may be blocked by browser)
            display_box.markdown(
                f"""
                <audio autoplay id="countdown_alarm">
                    <source src="{selected_alarm_file}" type="audio/mp3">
                </audio>
                """,
                unsafe_allow_html=True,
            )

            # Also provide a fallback player/button (guaranteed to be clickable)
            controls_box.markdown("**If you don't hear the alarm automatically, press Play below:**")
            controls_box.audio(selected_alarm_file, format="audio/mp3", start_time=0)

            # Log full focused time (initial - 0)
            initial_total = init_hours * 3600 + init_minutes * 60 + init_seconds
            elapsed_seconds = initial_total  # whole duration completed
            eh = elapsed_seconds // 3600
            em = (elapsed_seconds % 3600) // 60
            es = elapsed_seconds % 60
            focused_hms = f"{eh}h {em}m {es}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.get("current_countdown_task", "Unnamed"),
                "Target_HMS": f"{init_hours}h {init_minutes}m {init_seconds}s",
                "Focused_HMS": focused_hms
            }])], ignore_index=True)

            # set stop_alarm_trigger false until user presses stop
            st.session_state.stop_alarm_trigger = False

# ---------------- Timer report (shared) ----------------
st.sidebar.subheader("⏳ Focused Sessions Log")
if not st.session_state.timer_data.empty:
    st.sidebar.dataframe(st.session_state.timer_data, use_container_width=True)
else:
    st.sidebar.write("No focused sessions logged yet.")
