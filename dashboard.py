import streamlit as st
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

st.title("OmniPredatorV4 Dashboard © 2025 Slickofficials HQ by Amson Multi Global LTD")
st.write("Resale rights included. Contact: slickofficials@amsonmultiglobal.com")

try:
    creds_dict = json.loads(os.getenv('CREDENTIALS_JSON'))
    creds = Credentials.from_service_account_info(creds_dict)
    sheets_service = build('sheets', 'v4', credentials=creds)
    sheet_id = os.getenv('SHEET_ID')

    sheet = sheets_service.spreadsheets().values().get(spreadsheetId=sheet_id, range="A:A").execute()
    data = sheet.get('values', [])

    if data:
        st.write("### Recent Logs")
        for row in data[-10:]:
            st.write(row[0])
    else:
        st.write("No data yet.")
except Exception as e:
    st.error(f"Dashboard error: {e} - Check CREDENTIALS_JSON in Variables.")

if st.button("Refresh"):
    st.experimental_rerun()
