import streamlit as st
import requests
import pandas as pd
import qrcode
from io import BytesIO

# Google Apps Script Web App URL yahan paste karein
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxlkofcLzxs5QE1RHdKDdsdwrSue03c6Gdfh9fAmXymbcw9n-4ur8vB0TJABSTw2ZkQ/exec"

st.set_page_config(page_title="Multi-Zone Task Dashboard", layout="wide")

st.title("🚀 Multi-Zone Task & Time Tracking Portal")

# Check URL Query Parameters for QR Code Auto-Login (e.g., ?mobile=9876543210)
query_params = st.query_params
scanned_mobile = query_params.get("mobile", None)

# --- SECTION 1: 500+ USERS QR CODE / DAILY TIME LOGGING ---
if scanned_mobile:
    st.info(f"📱 Quick Mode Active for Mobile: {scanned_mobile}")
    
    # Fetch member details from backend using mobile
    res = requests.get(f"{WEB_APP_URL}?action=getMember&mobile={scanned_mobile}").json()
    
    if res.get("found"):
        name = res["name"]
        zone = res["zone"]
        st.success(f"Welcome back, **{name}**! (Zone: **{zone}**) 👋")
        
        # Fetch active tasks for this zone
        all_data = requests.get(f"{WEB_APP_URL}?action=getData").json()
        tasks = all_data.get("tasks", [])
        
        task_options = {}
        for r in tasks[1:]:
            if r[0] and (r[1] == zone or r[1] == "All"):
                task_options[f"{r[2]} ({r[1]})"] = r[0]
                
        with st.form("quick_time_form"):
            selected_task_label = st.selectbox("Select Task / Activity", options=list(task_options.keys()) if task_options else ["No Tasks Available"])
            hours = st.number_input("Hours Spent Today", min_value=0.5, max_value=24.0, step=0.5)
            submit_btn = st.form_submit_button("Submit Daily Hours")
            
            if submit_btn:
                if selected_task_label != "No Tasks Available":
                    payload = {
                        "action": "submitTime",
                        "name": name,
                        "zone": zone,
                        "taskId": task_options[selected_task_label],
                        "hours": hours,
                        "mobile": scanned_mobile
                    }
                    requests.post(WEB_APP_URL, json=payload)
                    st.success("✅ Hours logged successfully! You can close this page.")
                else:
                    st.error("Please select a valid task.")
    else:
        st.error("❌ Mobile number not found. Please register first.")
        
else:
    # --- SECTION 2: MAIN DASHBOARD & SIGNUP PORTAL ---
    tab1, tab2 = st.tabs(["📊 Dashboard & Admin", "📝 User Signup & QR Generation"])
    
    with tab2:
        st.subheader("New Member Signup (Get Your Permanent QR Code)")
        with st.form("signup_form"):
            s_name = st.text_input("Full Name")
            s_mobile = st.text_input("Mobile Number (Unique ID)")
            s_zone = st.selectbox("Select Your Zone", [f"Zone {i}" for i in range(1, 16)])
            s_submit = st.form_submit_button("Register & Generate QR")
            
            if s_submit:
                if s_name and s_mobile:
                    payload = {"action": "registerMember", "name": s_name, "mobile": s_mobile, "zone": s_zone}
                    requests.post(WEB_APP_URL, json=payload)
                    st.success("Registration Successful! Save your QR Code below:")
                    
                    # Generate QR Code pointing to this Streamlit app with mobile query param
                    current_app_url = st.query_params.get("origin", "https://task-dashboard-9glpaczfpjbruvt3c6v7k6.streamlit.app/") # Apna app URL yahan dal sakte ho
                    qr_link = f"https://task-dashboard-9glpaczfpjbruvt3c6v7k6.streamlit.app/{s_mobile}" # Replace with your deployed streamlit URL
                    
                    img = qrcode.make(qr_link)
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    st.image(buf.getvalue(), caption=f"QR Code for {s_name} ({s_zone})")
                    st.write(f"Direct Quick Link: `{qr_link}`")
                else:
                    st.warning("Please fill in all fields.")

    with tab1:
        st.subheader("Admin & Zone Head Portal Login")
        admin_email = st.text_input("Enter your authorized Gmail")
        
        if st.button("Access Dashboard"):
            res = requests.get(f"{WEB_APP_URL}?action=checkUser&email={admin_email}").json()
            if res.get("found"):
                st.session_state["user"] = res
                st.success(f"Access Granted! Role: {res['role']} | Zone: {res['zone']}")
            else:
                st.error("Access Denied: Email not registered.")
                
        if "user" in st.session_state:
            user = st.session_state["user"]
            st.markdown(f"### Welcome, {user['role']} ({user['zone']})")
            
            # Fetch data
            data = requests.get(f"{WEB_APP_URL}?action=getData").json()
            tasks_df = pd.DataFrame(data["tasks"][1:], columns=data["tasks"][0]) if len(data["tasks"]) > 1 else pd.DataFrame()
            logs_df = pd.DataFrame(data["logs"][1:], columns=data["logs"][0]) if len(data["logs"]) > 1 else pd.DataFrame()
            
            # Task Creation Panel
            if user["role"] in ["SuperAdmin", "ZoneHead"]:
                with st.expander("➕ Assign New Task"):
                    with st.form("task_form"):
                        t_title = st.text_input("Task Title / Description")
                        t_assign = st.text_input("Assign To (Member Name)")
                        t_zone = user["zone"] if user["role"] == "ZoneHead" else st.selectbox("Target Zone", [f"Zone {i}" for i in range(1, 16)])
                        t_sub = st.form_submit_button("Publish Task")
                        
                        if t_sub:
                            import random
                            task_payload = {"action": "addTask", "taskId": f"T-{random.randint(1000,9999)}", "zone": t_zone, "title": t_title, "assignedTo": t_assign}
                            requests.post(WEB_APP_URL, json=task_payload)
                            st.success("Task Published Successfully!")
                            st.rerun()
                            
            # Analytics & Leaderboard
            st.markdown("---")
            st.subheader("🏆 Zone Leaderboard (Total Hours Ranking)")
            if not logs_df.empty and len(logs_df.columns) >= 6:
                logs_df["HoursSpent"] = pd.to_numeric(logs_df.iloc[:, 5], errors="coerce").fillna(0)
                leaderboard = logs_df.groupby(logs_df.columns[3])["HoursSpent"].sum().reset_index()
                leaderboard.columns = ["Zone Name", "Total Hours"]
                leaderboard = leaderboard.sort_values(by="Total Hours", ascending=False).reset_index(drop=True)
                leaderboard.index += 1
                
                col1, col2 = st.columns(2)
                with col1:
                    st.dataframe(leaderboard, use_container_width=True)
                with col2:
                    st.bar_chart(leaderboard.set_index("Zone Name")["Total Hours"])
            else:
                st.info("No time logs submitted yet.")
                
            # Task Table View
            st.markdown("### 📋 Active Tasks")
            if not tasks_df.empty:
                if user["role"] == "ZoneHead":
                    filtered_tasks = tasks_df[tasks_df.iloc[:, 1] == user["zone"]]
                else:
                    filtered_tasks = tasks_df
                st.dataframe(filtered_tasks, use_container_width=True)