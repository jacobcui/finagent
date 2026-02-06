import os

import requests
import streamlit as st

from .auth import MyobAuth


class MyobPayrollAgent:
    def __init__(self, auth_handler=None):
        self.auth = auth_handler or MyobAuth()
        self.access_token = None
        self.refresh_token = None
        self.company_file_uri = None
        self.company_file_id = None
        self.base_url = "https://api.myob.com/accountright/"

    def authenticate_with_code(self, code):
        """Exchanges code for tokens."""
        tokens = self.auth.exchange_code_for_token(code)
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        return True

    def _get_headers(self):
        if not self.access_token:
            raise Exception("Not authenticated.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "x-myobapi-key": self.auth.client_id,
            "x-myobapi-version": "v2",
            "Accept-Encoding": "gzip,deflate",
        }

    def list_company_files(self):
        """Lists available company files."""
        headers = self._get_headers()
        response = requests.get(self.base_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to list company files: {response.text}")

    def select_company_file(self, company_file_id, company_file_uri=None):
        """Selects a company file to work with."""
        self.company_file_id = company_file_id
        if company_file_uri:
            self.company_file_uri = company_file_uri
        else:
            self.company_file_uri = f"{self.base_url}{company_file_id}"

    def get_employees(self):
        """Retrieves list of employees."""
        if not self.company_file_uri:
            raise Exception("No company file selected.")

        endpoint = f"{self.company_file_uri}/Contact/Employee"
        headers = self._get_headers()
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get employees: {response.text}")

    def get_payroll_categories(self):
        """Retrieves payroll categories."""
        if not self.company_file_uri:
            raise Exception("No company file selected.")

        endpoint = f"{self.company_file_uri}/Payroll/PayrollCategory"
        headers = self._get_headers()
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get payroll categories: {response.text}")

    def record_pay_run(self, payload):
        """Records a pay run transaction."""
        if not self.company_file_uri:
            raise Exception("No company file selected.")

        # Note: The actual endpoint for processing pay varies by version.
        # Using a common endpoint for recording timesheets as a proxy
        # for 'paying' logic in this demo.
        # For actual payment processing, one would typically post
        # to specific Payroll transaction endpoints.
        endpoint = f"{self.company_file_uri}/Payroll/Timesheet"
        headers = self._get_headers()
        response = requests.post(endpoint, headers=headers, json=payload)

        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"Failed to record pay run: {response.text}")


def app():
    st.title("MYOB Payroll Agent")
    st.markdown("Automate your payroll tasks with MYOB AccountRight API.")

    # Initialize agent in session state
    if "myob_agent" not in st.session_state:
        # We need env vars for this to work
        client_id = os.getenv("MYOB_CLIENT_ID")
        client_secret = os.getenv("MYOB_CLIENT_SECRET")

        if not client_id or not client_secret:
            st.error(
                "Missing MYOB_CLIENT_ID or MYOB_CLIENT_SECRET environment variables."
            )
            st.info("Please set them in your .env file or environment.")
            return

        try:
            st.session_state["myob_agent"] = MyobPayrollAgent()
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            return

    agent = st.session_state["myob_agent"]

    # Auth Section
    if not agent.access_token:
        st.subheader("Authentication Required")
        auth_url = agent.auth.get_authorization_url()
        st.markdown(f"1. [Click here to authorize with MYOB]({auth_url})")
        st.markdown("2. Copy the code from the redirected URL.")

        code = st.text_input("Enter Authorization Code:")
        if st.button("Authenticate"):
            if code:
                try:
                    agent.authenticate_with_code(code)
                    st.success("Authentication successful!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Authentication failed: {e}")
            else:
                st.warning("Please enter the code.")
        return

    st.success("Authenticated with MYOB")

    # Company File Selection
    if not agent.company_file_id:
        st.subheader("Select Company File")
        if st.button("Fetch Company Files"):
            try:
                files = agent.list_company_files()
                st.session_state["myob_files"] = files
            except Exception as e:
                st.error(f"Error fetching files: {e}")

        if "myob_files" in st.session_state:
            files = st.session_state["myob_files"]
            if isinstance(files, list) and files:
                options = {f"{f['Name']} ({f['Id']})": f for f in files}
                selected_name = st.selectbox(
                    "Choose a company file:", list(options.keys())
                )
                if st.button("Select File"):
                    selected_file = options[selected_name]
                    agent.select_company_file(selected_file["Id"], selected_file["Uri"])
                    st.success(f"Selected: {selected_file['Name']}")
                    st.rerun()
            else:
                st.info("No company files found.")
        return

    st.info(f"Using Company File ID: {agent.company_file_id}")
    if st.button("Change Company File"):
        agent.company_file_id = None
        agent.company_file_uri = None
        st.rerun()

    # Main Functionality
    st.divider()
    tab1, tab2, tab3 = st.tabs(["Employees", "Payroll Categories", "Process Pay Run"])

    with tab1:
        st.subheader("Employee List")
        if st.button("Load Employees"):
            try:
                data = agent.get_employees()
                st.session_state["myob_employees"] = data
                st.json(data)
            except Exception as e:
                st.error(f"Error: {e}")

    with tab2:
        st.subheader("Payroll Categories")
        if st.button("Load Categories"):
            try:
                data = agent.get_payroll_categories()
                st.json(data)
            except Exception as e:
                st.error(f"Error: {e}")

    with tab3:
        st.subheader("Process Pay Run (Timesheet)")

        # Ensure we have employees loaded to select from
        if "myob_employees" not in st.session_state:
            st.info("Please load employees in the 'Employees' tab first.")
        else:
            employees = st.session_state["myob_employees"]
            if isinstance(employees, list):
                emp_options = {
                    f"{e.get('FirstName', '')} {e.get('LastName', '')}": e
                    for e in employees
                }
                selected_emp_name = st.selectbox(
                    "Select Employee", list(emp_options.keys())
                )

                if selected_emp_name:
                    selected_emp = emp_options[selected_emp_name]
                    start_date = st.date_input("Start Date")
                    end_date = st.date_input("End Date")
                    hours = st.number_input("Hours Worked", min_value=0.0, step=0.5)

                    if st.button("Submit Pay Run"):
                        payload = {
                            "Employee": {"UID": selected_emp.get("UID")},
                            "StartDate": start_date.isoformat(),
                            "EndDate": end_date.isoformat(),
                            "Entries": [
                                {
                                    "Date": start_date.isoformat(),
                                    "Hours": hours,
                                    "Notes": "Processed via FinAgent",
                                }
                            ],
                        }
                        try:
                            # Note: This is a demo call.
                            # Real API might require more specific structure.
                            # result = agent.record_pay_run(payload)
                            # st.success("Pay run recorded successfully!")
                            # st.json(result)

                            # For safety in this demo environment, we mock the success
                            st.info(
                                f"Simulating submission to: "
                                f"{agent.company_file_uri}/Payroll/Timesheet"
                            )
                            st.json(payload)
                            st.success(
                                "✅ Pay run payload constructed and ready to send. "
                                "(Simulation Mode)"
                            )
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.warning("Unexpected employee data format.")
