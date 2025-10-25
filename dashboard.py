import streamlit as st
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

st.title("OmniPredatorV4 Dashboard © 2025 Slickofficials HQ by Amson Multi Global LTD")
st.write("Resale rights included. Contact: slickofficials@amsonmultiglobal.com")

try:
    creds_str = os.getenv('CREDENTIALS_JSON')
    if not creds_str:
        st.error("CREDENTIALS_JSON not set in Variables.")
    else:
        # Clean the string: strip whitespace and ensure it's JSON
        creds_str = creds_str.strip().strip('"').strip("'")  # Remove outer quotes if added
        creds_dict = json.loads(creds_str)
        creds = Credentials.from_service_account_info(creds_dict)
        sheets_service = build('sheets', 'v4', credentials=creds)
        sheet_id = os.getenv('SHEET_ID')
        if not sheet_id:
            st.error("SHEET_ID not set in Variables.")
        else:
            sheet = sheets_service.spreadsheets().values().get(spreadsheetId=sheet_id, range="A:A").execute()
            data = sheet.get('values', [])
            if data:
                st.write("### Recent Logs")
                for row in data[-10:]:
                    st.write(row[0])
            else:
                st.write("No data yet.")
except json.JSONDecodeError as e:
    st.error(f"JSON error: {e}. Paste escaped JSON into CREDENTIALS_JSON (single line, no breaks).")
except Exception as e:
    st.error(f"Dashboard error: {e}. Check CREDENTIALS_JSON and SHEET_ID.")

if st.button("Refresh"):
    st.experimental_rerun()
