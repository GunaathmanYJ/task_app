import streamlit as st
import pandas as pd
from fpdf import FPDF
import time

st.set_page_config(page_title="Taskuni Stable", layout="wide")
st.title("📌 Taskuni — Your personal Task tracker")

# ---------------- Session state ----------------
if "tasks" not in st.session_state:
    st.session_state.tasks = pd.DataFrame(columns=["Task", "Status"])
if "timer_data" not in st.session_state:
    st.session_state.timer_data = pd.DataFrame(columns=["Task", "Target_HMS", "Focused_HMS"])
if "countdown_running" not in st.session_state:
    st.session_state.countdown_running = False

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["📝 Task Tracker", "⏱️ Countdown Timer"])

# ---------------- Task Tracker ----------------
with tab1:
    task_name_input = st.text_input("Enter your task")
    if st.button("Add Task") and task_name_input:
        st.session_state.tasks = pd.concat(
            [st.session_state.tasks, pd.DataFrame([[task_name_input, "Pending"]], columns=["Task", "Status"])],
            ignore_index=True
        )

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
        if col3.button("❌ Not Done", key=f"notdone_{i}"):
            st.session_state.tasks.at[i, "Status"] = "Not Done"

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

    # Generate PDF for Tasks
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 16)
            self.cell(0, 10, "Task Report Card", ln=True, align="C")
            self.ln(10)

    def generate_task_pdf(tasks_df, filename="task_report.pdf"):
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

    if st.button("💾 Download Task PDF"):
        if not st.session_state.tasks.empty:
            pdf_file = generate_task_pdf(st.session_state.tasks)
            with open(pdf_file, "rb") as f:
                st.download_button("⬇️ Download Task PDF", f, file_name=pdf_file, mime="application/pdf")
        else:
            st.warning("⚠️ No tasks to generate PDF!")

# ---------------- Manual Countdown Timer ----------------
with tab2:
    st.write("Set countdown time")
    col_h, col_m, col_s = st.columns(3)
    with col_h:
        init_hours = st.number_input("Hours", min_value=0, max_value=23, value=0, step=1, key="input_hours")
    with col_m:
        init_minutes = st.number_input("Minutes", min_value=0, max_value=59, value=0, step=1, key="input_minutes")
    with col_s:
        init_seconds = st.number_input("Seconds", min_value=0, max_value=59, value=0, step=1, key="input_seconds")

    task_for_timer = st.text_input("Task name for this countdown (optional)", key="countdown_task")

    start_col, stop_col = st.columns([1,1])
    start_btn = start_col.button("Start Countdown")
    stop_btn = stop_col.button("Stop Countdown")

    display_box = st.empty()

    # Start countdown
    if start_btn:
        total_seconds = init_hours*3600 + init_minutes*60 + init_seconds
        if total_seconds <= 0:
            st.warning("Set a time greater than 0.")
        else:
            st.session_state.countdown_running = True
            st.session_state.countdown_h = init_hours
            st.session_state.countdown_m = init_minutes
            st.session_state.countdown_s = init_seconds
            st.session_state.current_countdown_task = task_for_timer if task_for_timer else "Unnamed"
            st.success(f"Countdown started for {st.session_state.current_countdown_task}")

    # Stop countdown
    if stop_btn:
        if st.session_state.countdown_running:
            elapsed_seconds = (init_hours*3600 + init_minutes*60 + init_seconds) - (st.session_state.countdown_h*3600 + st.session_state.countdown_m*60 + st.session_state.countdown_s)
            eh = elapsed_seconds // 3600
            em = (elapsed_seconds % 3600) // 60
            es = elapsed_seconds % 60
            focused_hms = f"{eh}h {em}m {es}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.get("current_countdown_task","Unnamed"),
                "Target_HMS": f"{init_hours}h {init_minutes}m {init_seconds}s",
                "Focused_HMS": focused_hms
            }])], ignore_index=True)
            st.session_state.countdown_running = False
            st.success(f"Countdown stopped. Focused logged: {focused_hms}")
        else:
            st.info("No countdown running.")

    # Countdown logic
    if st.session_state.countdown_running:
        h = st.session_state.countdown_h
        m = st.session_state.countdown_m
        s = st.session_state.countdown_s
        while st.session_state.countdown_running and (h>0 or m>0 or s>0):
            display_box.markdown(f"### ⏱️ {h:02d}:{m:02d}:{s:02d}  \n**Task:** {st.session_state.current_countdown_task}")
            time.sleep(1)
            if s>0:
                s -=1
            else:
                s=59
                if m>0:
                    m-=1
                else:
                    m=59
                    if h>0:
                        h-=1
                    else:
                        m=0
                        s=0
            st.session_state.countdown_h = h
            st.session_state.countdown_m = m
            st.session_state.countdown_s = s

        # Countdown finished naturally
        if st.session_state.countdown_running:
            st.session_state.countdown_running = False
            focused_hms = f"{init_hours}h {init_minutes}m {init_seconds}s"
            st.session_state.timer_data = pd.concat([st.session_state.timer_data, pd.DataFrame([{
                "Task": st.session_state.get("current_countdown_task","Unnamed"),
                "Target_HMS": focused_hms,
                "Focused_HMS": focused_hms
            }])], ignore_index=True)
            display_box.success("🎯 Countdown Finished!")

# ---------------- Timer Report PDF ----------------
st.sidebar.subheader("⏳ Focused Sessions Log")
if not st.session_state.timer_data.empty:
    st.sidebar.dataframe(st.session_state.timer_data, use_container_width=True)
    
    # PDF generation
    class TimerPDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 16)
            self.cell(0, 10, "Focused Timer Report", ln=True, align="C")
            self.ln(10)

    def generate_timer_pdf(timer_df, filename="timer_report.pdf"):
        pdf = TimerPDF()
        pdf.add_page()
        pdf.set_font("Arial", "", 12)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(10, 10, "#", border=1, fill=True)
        pdf.cell(80, 10, "Task", border=1, fill=True)
        pdf.cell(50, 10, "Target Time", border=1, fill=True)
        pdf.cell(50, 10, "Focused Time", border=1, fill=True)
        pdf.ln()
        for i, row in timer_df.iterrows():
            pdf.cell(10, 10, str(i+1), border=1)
            pdf.cell(80, 10, row["Task"], border=1)
            pdf.cell(50, 10, row["Target_HMS"], border=1)
            pdf.cell(50, 10, row["Focused_HMS"], border=1)
            pdf.ln()
        pdf.output(filename)
        return filename

    if st.sidebar.button("💾 Download Timer PDF"):
        pdf_file = generate_timer_pdf(st.session_state.timer_data)
        with open(pdf_file, "rb") as f:
            st.sidebar.download_button("⬇️ Download Timer PDF", f, file_name=pdf_file, mime="application/pdf")
else:
    st.sidebar.write("No focused sessions logged yet.")


