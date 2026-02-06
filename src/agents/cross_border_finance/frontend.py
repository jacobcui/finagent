import os
import sys

import requests
import streamlit as st

# Add the project root to the python path to ensure imports work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import src.agents.cross_border_finance.blockchain_log as blockchain_log  # noqa: E402
from src.agents.cross_border_finance import compliance  # noqa: E402
from src.agents.cross_border_finance import lock_engine  # noqa: E402
from src.agents.cross_border_finance import tax_report
from src.agents.myob_payroll import agent as myob_payroll  # noqa: E402

# Configure the page - this must be the first Streamlit command
st.set_page_config(
    page_title="Cross Border Finance Agent",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.environ.get("API_URL", "http://127.0.0.1:5000")


def login_page():
    st.title("Welcome to Cross Border Finance Agent")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/2830/2830284.png", width=200)

    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            st.subheader("Login")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", type="primary"):
                try:
                    resp = requests.post(
                        f"{API_URL}/api/login",
                        json={"email": email, "password": password},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state["logged_in"] = True
                        st.session_state["user"] = data["user"]
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(resp.json().get("error", "Login failed"))
                except Exception as e:
                    st.error(f"Connection error: {e}")
                    st.info("Ensure the Flask backend is running on port 5000.")

        with tab2:
            st.subheader("Register")
            new_email = st.text_input("New Email", key="reg_email")
            new_password = st.text_input(
                "New Password", type="password", key="reg_password"
            )
            if st.button("Register"):
                try:
                    resp = requests.post(
                        f"{API_URL}/api/register",
                        json={"email": new_email, "password": new_password},
                    )
                    if resp.status_code == 201:
                        data = resp.json()
                        st.success(data.get("message"))
                        if "mock_verify_link" in data:
                            st.info(
                                "Mock Verification Link (Click to verify): "
                                f"[Link]({data['mock_verify_link']})"
                            )
                            st.caption(
                                "In a real app, this would be sent to your email."
                            )
                    else:
                        st.error(resp.json().get("error", "Registration failed"))
                except Exception as e:
                    st.error(f"Connection error: {e}")


def home():
    st.title("Cross Border Finance Agent Platform")
    if "user" in st.session_state:
        st.success(f"Welcome back, {st.session_state['user']['email']}!")

    st.markdown("""
    ### Welcome to the Unified Cross Border Finance Platform

    This platform integrates multiple specialized intelligent agents to assist with
    your cross-border financial operations.

    Please select a tool from the sidebar to get started:

    *   **💱 Exchange Rate Lock Engine**: Real-time exchange rate calculation and
        locking strategies.
    *   **🛡️ Compliance Check (ASIC)**: Automated self-assessment for ASIC regulatory
        compliance.
    *   **🧾 Tax Report Generator (ATO)**: Generate compliant tax reports
        for cross-border trade.
    *   **🔗 Blockchain Log Evidence**: Verify and view immutable transaction
        logs on the blockchain.
    *   **💰 MYOB Payroll**: Automate payroll tasks and manage employees
        via MYOB AccountRight API.
    """)

    st.info("Select a module from the sidebar navigation.")


def app():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_page()
        return

    st.sidebar.title("Navigation")
    if "user" in st.session_state:
        st.sidebar.caption(f"User: {st.session_state['user']['email']}")

    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["user"] = None
        st.rerun()

    st.sidebar.markdown("---")

    # Define available apps
    apps = {
        "Home": home,
        "Exchange Rate Lock": lock_engine.app,
        "Compliance Check": compliance.app,
        "Tax Report": tax_report.app,
        "Blockchain Log": blockchain_log.app,
        "MYOB Payroll": myob_payroll.app,
    }

    selection = st.sidebar.radio("Go to", list(apps.keys()))

    # Display the selected app
    st.sidebar.markdown("---")
    st.sidebar.caption("v1.0.0 | FinAgent")

    app_func = apps[selection]
    app_func()


if __name__ == "__main__":
    app()
