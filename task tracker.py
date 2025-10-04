import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, date
from fpdf import FPDF
import matplotlib.pyplot as plt

# ---------------- Utility: Load or create CSV with columns ----------------
def load_or_create_csv(file, columns):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)

# ---------------- Sidebar: Username ----------------
st.sidebar.subheader("👤 Enter your username")
username = st.sidebar.text_input("Username", key="username_input")

if not username:
    st.warning("Please enter a username to continue.")
    st.stop()

today_date = str(date.today())

# ---------------- Tabs ----------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Tasks", "⏳ Timer", "🍅 Pomodoro", "👥 Group Workspace", "📊 Analytics"])

# ---------------- Tab 1: Personal Tasks ----------------
with tab1:
    st.subheader(f"📋 {username}'s Task Tracker")

    TASKS_FILE = f"tasks_{username}.csv"
    tasks = load_or_create_csv(TASKS_FILE, ["Task", "Status", "Date", "Priority", "Deadline"])

    task_input = st.text_input("Add a new task", key="task_input")
    priority = st.selectbox("Priority", ["Low", "Medium", "High"], key="priority_input")
    deadline = st.date_input("Deadline", value=date.today(), key="deadline_input")

    if st.button("➕ Add Task"):
        if task_input.strip():
            new_task = {
                "Task": task_input.strip(),
                "Status": "Pending",
                "Date": today_date,
                "Priority": priority,
                "Deadline": deadline
            }
            tasks = pd.concat([tasks, pd.DataFrame([new_task])], ignore_index=True)
            tasks.to_csv(TASKS_FILE, index=False)
            st.success("Task added!")
            st.rerun()

    if not tasks.empty:
        st.markdown("### 🔎 Your Tasks")
        for i, row in tasks.iterrows():
            cols = st.columns([3, 1, 1, 1, 1])
            cols[0].write(f"**{row['Task']}** ({row['Status']}) | Priority: {row['Priority']} | Deadline: {row['Deadline']}")
            if cols[1].button("Done", key=f"done_{i}"):
                tasks.at[i, "Status"] = "Done"
                tasks.to_csv(TASKS_FILE, index=False)
                st.rerun()
            if cols[2].button("Not Done", key=f"notdone_{i}"):
                tasks.at[i, "Status"] = "Not Done"
                tasks.to_csv(TASKS_FILE, index=False)
                st.rerun()
            if cols[3].button("Delete", key=f"delete_{i}"):
                tasks = tasks.drop(i).reset_index(drop=True)
                tasks.to_csv(TASKS_FILE, index=False)
                st.rerun()

# ---------------- Tab 2: Timer ----------------
with tab2:
    st.subheader("⏳ Focus Timer")

    TIMER_FILE = f"timer_{username}.csv"
    timer_data = load_or_create_csv(TIMER_FILE, ["Task", "Duration(min)", "Date", "Start", "End"])

    timer_task = st.text_input("Task name", key="timer_task")
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=180, value=25)

    if st.button("▶ Start Timer"):
        st.session_state.timer_running = True
        st.session_state.start_time = time.time()
        st.session_state.duration = duration * 60
        st.session_state.timer_task = timer_task

    if st.session_state.get("timer_running", False):
        elapsed = time.time() - st.session_state.start_time
        remaining = max(0, int(st.session_state.duration - elapsed))
        mins, secs = divmod(remaining, 60)
        st.metric("Time Remaining", f"{mins:02d}:{secs:02d}")
        if remaining == 0:
            st.session_state.timer_running = False
            st.success("⏰ Time’s up!")
            new_entry = {
                "Task": st.session_state.timer_task,
                "Duration(min)": st.session_state.duration // 60,
                "Date": today_date,
                "Start": datetime.fromtimestamp(st.session_state.start_time).strftime("%H:%M:%S"),
                "End": datetime.now().strftime("%H:%M:%S"),
            }
            timer_data = pd.concat([timer_data, pd.DataFrame([new_entry])], ignore_index=True)
            timer_data.to_csv(TIMER_FILE, index=False)
            st.balloons()

    st.markdown("### Logged Sessions")
    st.dataframe(timer_data, use_container_width=True)

    if st.button("📄 Export Log as PDF"):
        class TimerPDF(FPDF):
            def header(self):
                self.set_font("Arial", "B", 16)
                self.cell(0, 10, "Focused Timer Report", ln=True, align="C")
                self.ln(10)

        pdf = TimerPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for _, row in timer_data.iterrows():
            pdf.cell(0, 10, f"{row['Date']} | {row['Task']} | {row['Duration(min)']} min", ln=True)
        pdf_file = f"{username}_timer_log.pdf"
        pdf.output(pdf_file)
        with open(pdf_file, "rb") as f:
            st.download_button("⬇ Download PDF", f, file_name=pdf_file)

# ---------------- Tab 3: Pomodoro ----------------
with tab3:
    st.subheader("🍅 Pomodoro Timer")

    pomo_task = st.text_input("Pomodoro Task", key="pomo_task")
    pomo_duration = st.number_input("Focus Duration (minutes)", 1, 120, 25)
    break_duration = st.number_input("Break Duration (minutes)", 1, 60, 5)

    if st.button("▶ Start Pomodoro"):
        st.session_state.pomo_running = True
        st.session_state.pomo_start = time.time()
        st.session_state.pomo_duration = pomo_duration * 60
        st.session_state.pomo_task = pomo_task

    if st.session_state.get("pomo_running", False):
        elapsed = time.time() - st.session_state.pomo_start
        remaining = max(0, int(st.session_state.pomo_duration - elapsed))
        mins, secs = divmod(remaining, 60)
        st.metric("Pomodoro Remaining", f"{mins:02d}:{secs:02d}")
        if remaining == 0:
            st.session_state.pomo_running = False
            st.success("🍅 Pomodoro finished! Take a break.")

# ---------------- Tab 4: Group Workspace ----------------
with tab4:
    st.subheader("👥 Group Workspace")
    st.info("Group features code unchanged for brevity — keep same as your current version, just replace any st.experimental_rerun() with st.rerun().")

# ---------------- Tab 5: Analytics ----------------
with tab5:
    st.subheader("📊 Productivity Analytics")

    if not timer_data.empty:
        st.markdown("### Focus Duration Over Time")
        timer_data["Date"] = pd.to_datetime(timer_data["Date"])
        daily_sum = timer_data.groupby("Date")["Duration(min)"].sum()
        fig, ax = plt.subplots()
        daily_sum.plot(kind="bar", ax=ax, color="skyblue")
        ax.set_ylabel("Minutes")
        ax.set_title("Daily Focus Time")
        st.pyplot(fig)
    else:
        st.info("No timer data yet. Start a focus session to see analytics.")
