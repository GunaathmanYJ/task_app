import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

st.set_page_config(page_title="Task App", layout="wide")
st.title("📋 Task Tracker")

# Initialize tasks
if "tasks" not in st.session_state:
    st.session_state.tasks = pd.DataFrame(columns=["Task", "Status"])

# Add task input
task_name = st.text_input("Enter your task")
if st.button("Add Task") and task_name:
    st.session_state.tasks = pd.concat(
        [st.session_state.tasks, pd.DataFrame([[task_name, "Pending"]], columns=["Task", "Status"])],
        ignore_index=True
    )
    st.rerun()  

# Display tasks
st.subheader("📝 Tasks")
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
        st.success(f"✅ {row['Task']} Complete!\nKeep it up 🎉")

    if col3.button("❌ Not Done", key=f"notdone_{i}"):
        st.session_state.tasks.at[i, "Status"] = "Not Done"
        st.rerun()

# Task report card
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

# PDF class
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Task Report Card", ln=True, align="C")
        self.ln(10)

# PDF generation function
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

# Generate PDF button
if st.button("💾 Generate PDF Report"):
    if not st.session_state.tasks.empty:
        pdf_file = generate_pdf(st.session_state.tasks)
        st.success(f"✅ PDF generated: {pdf_file}")
        # Download button
        with open(pdf_file, "rb") as f:
            st.download_button(
                label="⬇️ Download PDF",
                data=f,
                file_name=pdf_file,
                mime="application/pdf"
            )
    else:
        st.warning("⚠️ No tasks to generate PDF!")
