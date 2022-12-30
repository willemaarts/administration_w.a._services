from datetime import datetime, date
import calendar
import traceback
import streamlit as st
import pandas as pd
import numpy as np
import locale
import gspread as gs
from PIL import Image

st.set_page_config(page_title="Financial statement - W.A. Services", layout="wide", initial_sidebar_state="collapsed")

hide_default_format = """
       <style>
       footer {visibility: hidden;}
       footer {visibility: hidden;}
       </style>
       """
st.markdown(hide_default_format, unsafe_allow_html=True)

def run_credentials():
    credentials = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"],
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
        }
    return(credentials)


def retreive_data():

    # https://docs.gspread.org/en/latest/user-guide.html

    try: 
        credentials = run_credentials()

        gc = gs.service_account_from_dict(credentials)

        sh = gc.open(st.secrets["private_gsheets_url"])

        list_of_lists = sh.sheet1.get_all_values()
        
        return(list_of_lists)

    except Exception:
        traceback.print_exc()

def contruct_data(data):

    calc_data = {}
    
    revenue_incl = data.query("balancesheet_item == 'Omzet'")['amount_inc_vat'].sum()
    costs = data.query("balancesheet_item == 'Kosten'")['amount_inc_vat'].sum()
    private = data.query("balancesheet_item == 'Prive'")['amount_inc_vat'].sum()
    equity = data.query("balancesheet_item == 'Omzet'")['amount_ex_vat'].sum()

    EBIT = revenue_incl - abs(costs)

    # No debiteuren
    VAT_to_be_paid = data.query("balancesheet_item == 'Omzet'")['amount_vat'].sum()
    VAT_paid = data.query("balancesheet_item == 'Betaald BTW'")['amount_inc_vat'].sum()
    zvw_paid = data.query("balancesheet_item == 'Betaald winstbelasting'")['amount_inc_vat'].sum()

    current_vat_to_be_paid = VAT_to_be_paid + VAT_paid

    zvw_to_be_paid = ((EBIT - abs(VAT_paid - current_vat_to_be_paid)) * 0.055) - abs(zvw_paid)
    
    net_profit = EBIT - abs(VAT_paid - current_vat_to_be_paid) - zvw_to_be_paid

    laptop = 0
    debiteuren = 0
    vat_to_receive = 0
    
    bank = abs(revenue_incl) - abs(VAT_paid) - abs(zvw_paid) - abs(costs) - abs(private)
    
    t_assets = laptop + debiteuren + vat_to_receive + bank
    
    eq = equity - abs(private) - abs(costs) - zvw_to_be_paid
    
    crediteuren = 0
    t_liabilities = eq + current_vat_to_be_paid + zvw_to_be_paid

    calc_data = {
        'revenue': revenue_incl,
        'costs': costs,
        'private': private,
        'equity': equity,
        'EBIT': EBIT,
        'VAT_to_be_paid': VAT_to_be_paid,
        'VAT_paid': VAT_paid,
        'zvw_paid': zvw_paid,
        'current_vat_to_be_paid': current_vat_to_be_paid,
        'zvw_to_be_paid': zvw_to_be_paid,
        'net_profit': net_profit,
        'laptop': laptop,
        'costs': costs,
        'debiteuren': debiteuren,
        'vat_to_receive': vat_to_receive,
        'bank': bank,
        'eq': eq,
        'crediteuren': crediteuren,
        't_liabilities': t_liabilities,
        't_assets': t_assets,
    }

    return calc_data

# Header of the page
with st.container():

    # --- Initialising SessionSate ---
    if "dict" not in st.session_state:
        st.session_state.dict = {}

    if "run" not in st.session_state:
        st.session_state.run = False

    placeholder = st.empty()

    with placeholder.form("login"):
        st.markdown("#### Login")
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", placeholder="Enter password", type="password")
        login_button = st.form_submit_button("Login")

    l_column, m_column, r_column = st.columns([0.5,6,0.5])

    with m_column:
        st.markdown("<h1 style='text-align: center; color: white;'>Administration - W.A. Services</h1>", unsafe_allow_html=True)
    with r_column:
        st.image(Image.open('images/Logo Blue(1) Vector.png'))
    
    st.write("---")

def main():

    if st.secrets['credentials']['name'] == username and st.secrets['credentials']['password'] == password:
        placeholder.empty()
    else:
        return
        
    with st.container():

        locale.setlocale(locale.LC_ALL, '') # Use '' for auto, or force e.g. to 'nl_NL.UTF-8' 

        disabled = 1
        current_month = (int(datetime.now().strftime('%m')))

        # If session stage = False, retreive data
        if st.session_state.run == False:
            st.session_state.dict = retreive_data()
            st.session_state.run = True

        # --- Constructing dataframe ---
        df = pd.DataFrame(st.session_state.dict, columns=st.session_state.dict[0]) 
        df = df.iloc[1:]

        cols = ['amount_ex_vat', 'vat_percentage','amount_inc_vat', 'amount_vat']
        df[cols] = df[cols].apply(pd.to_numeric, errors='coerce', axis=1)

        df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True)

        # --- Initializing query selections in sidebar ---
        month_select = st.sidebar.multiselect(
            'Select months:',
            options=df['month'].unique(),
            default=str(current_month)
        )

        balance_Select = st.sidebar.multiselect(
            'Select the balancesheet item:',
            options=df['balancesheet_item'].unique(),
            default=df['balancesheet_item'].unique()
        )

        df_selection = df.query(
            f"month == @month_select & balancesheet_item == @balance_Select" 
        )

        st.markdown(f"<h1 style='text-align: center; color: white;'>Total figure of {calendar.month_name[int(month_select[0])]}</h1>", unsafe_allow_html=True)
        
        # --- Displaying KPI's of selected month --- 
        l1_c, l_c, m1_c, m2_c, m3_c,r_c, r1_c = st.columns([1,1,1,1,1,1,1])

        with l_c:
            revenue = df.query("balancesheet_item == 'Omzet' & month == @month_select")['amount_inc_vat'].sum()
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>Revenue</p>", unsafe_allow_html=True)
            st.markdown(f"<h6 style='text-align: center; color: white; font-size:45px;'>€ {revenue:n}</h6>", unsafe_allow_html=True)
        with m1_c:
            costs = df.query("balancesheet_item == 'Kosten' & month == @month_select")['amount_inc_vat'].sum()
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>Costs</p>", unsafe_allow_html=True)
            st.markdown(f"<h6 style='text-align: center; color: white; font-size:45px;'>€ {costs:n}</h6>", unsafe_allow_html=True)
        with m2_c:
            EBITDA = (revenue + costs)
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>EBITDA</p>", unsafe_allow_html=True)
            st.markdown(f"<h6 style='text-align: center; color: white; font-size:45px;'>€ {EBITDA:n}</h6>", unsafe_allow_html=True)
        with m3_c:
            ITDA = df.query("balancesheet_item == 'Betaald BTW' & month == @month_select")['amount_inc_vat'].sum()
            ITDA1 = df.query("balancesheet_item == 'Betaald Zvw' & month == @month_select")['amount_inc_vat'].sum()
            profit = (EBITDA + ITDA + ITDA1)
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>Profit</p>", unsafe_allow_html=True)
            st.markdown(f"<h6 style='text-align: center; color: white; font-size:45px;'>€ {profit:n}</h6>", unsafe_allow_html=True)
        with r_c:
            private = df.query("balancesheet_item == 'Prive' & month == @month_select")['amount_inc_vat'].sum()
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>Private</p>", unsafe_allow_html=True)
            st.markdown(f"<h6 style='text-align: center; color: white; font-size:45px;'>€ {private:n}</h6>", unsafe_allow_html=True) 
                
        # --- Display queried df ---
        l, m, r = st.columns([1,6,1])
        with m:
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.dataframe(df_selection.iloc[::-1])

        st.write('---')

        # If session stage = False, calculate the data
        calc_data = contruct_data(df)

        # --- Display balance sheet ---
        t1, t2 = st.columns([10,5])
        with t1:
            st.markdown(f"<h1 style='text-align: center; color: white;'>Balance sheet</h1>", unsafe_allow_html=True)
        
        with t2:
            st.markdown(f"<h1 style='text-align: center; color: white;'>P&L</h1>", unsafe_allow_html=True)

        m1, m2, m3, m4, m5, m6, m7, m8, r1, r2 = st.columns([2,1,1,1,1.5,1,1,1,3,2])
        
        # --- Balance sheet ---
        with m1:
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Vaste activa</p>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)

            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Vlottende activa</p>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)

            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Total:</p>", unsafe_allow_html=True)

        with m2:
            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Laptop</p>", unsafe_allow_html=True)

            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Debiteuren</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>T.V. BTW</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Bank</p>", unsafe_allow_html=True)
        
        with m3:
            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['laptop'],2)}</p>", unsafe_allow_html=True)

            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['debiteuren'],2)}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['vat_to_receive'],2)}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['bank'],2)}</p>", unsafe_allow_html=True)

        with m4:
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['t_assets'],2)}</p>", unsafe_allow_html=True)

        with m5:
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Eigen vermogen</p>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)

            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Vreemd vermogen kort</p>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)

            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Total:</p>", unsafe_allow_html=True)

        with m6:
            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>EQ</p>", unsafe_allow_html=True)

            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Crediteuren</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>T.B. BTW</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>T.B. Zvw</p>", unsafe_allow_html=True)
        
        with m7:
            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['eq'],2)}</p>", unsafe_allow_html=True)

            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['crediteuren'],2)}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['current_vat_to_be_paid'],2)}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['zvw_to_be_paid'],2)}</p>", unsafe_allow_html=True)

        with m8:
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<br><br>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>€ {round(calc_data['t_liabilities'],2)}</p>", unsafe_allow_html=True)

        # --- P&L ---
        with r1:

            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Revenue</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Costs</p>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)
            
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>EBIT</p>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)

            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>VAT Paid</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Zvw Paid</p>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)

            st.markdown(f"<p style='text-align: right; color: white; font-size:20px;'>Profit</p>", unsafe_allow_html=True)

        with r2:

            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>€ {round(calc_data['revenue'],2)}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>€ {round(calc_data['costs'],2)}</p>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)
            
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>€ {round(calc_data['EBIT'],2)}</p>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)

            p_vat = df.query("balancesheet_item == 'Betaald BTW'")['amount_inc_vat'].sum()
            p_zvw = df.query("balancesheet_item == 'Betaald Zvw'")['amount_inc_vat'].sum()
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>€ {round(p_vat,2)}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>€ {round(p_zvw,2)}</p>", unsafe_allow_html=True)
            st.markdown(f"<br>", unsafe_allow_html=True)

            p_prt = calc_data['EBIT'] + p_vat + p_zvw
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>€ {round(p_prt,2)}</p>", unsafe_allow_html=True)


        if round(calc_data['t_assets'],2) - round(calc_data['t_liabilities'],2) != 0:
            st.warning('Balance sheet is not equal', icon='❌')

        # --- Enter new data ---
        with st.sidebar:
            st.write("---")
            st.markdown("# Add data:")

            i_index = int(df['index'].iloc[-1]) + 1

            i_date = st.text_input(
                'Add details',
                value=f"{int(datetime.now().strftime('%d'))}/{int(datetime.now().strftime('%m'))}/{int(datetime.now().strftime('%Y'))}"
            )

            i_invoice = st.text_input('Add invoice number:')

            i_relation = st.sidebar.multiselect(
                'Select relation:',
                options=df['relation'].unique(),
                max_selections=1
            )

            i_details = st.text_input('Add details')
            
            i_amount = st.number_input('Add amount excl VAT')

            i_vat = st.sidebar.multiselect(
                'Select VAT:',
                options=df['vat_percentage'].unique()
            )

            i_balance = st.sidebar.multiselect(
                'Select balance sheet item:',
                options=df['balancesheet_item'].unique(),
                max_selections=1
            )

            if st.button('submit'):
                with st.spinner('Storing data...'):
                    if i_vat[0] == 0.0: i_vat_amount = 0
                    else: i_vat_amount = (i_amount * i_vat[0])

                    i_amount_incl_vat = i_amount + i_vat_amount

                    i_year = int(datetime.now().strftime('%Y'))
                    i_month = int(datetime.now().strftime('%m'))
                    i_day = int(datetime.now().strftime('%d'))

                    try: 
                        credentials = run_credentials()

                        gc = gs.service_account_from_dict(credentials)

                        sh = gc.open(st.secrets["private_gsheets_url"])

                        a=len(sh.sheet1.col_values(1))

                        data = [i_index,i_date,i_invoice,i_relation[0],i_details,i_amount,i_vat[0],i_vat_amount,
                            i_amount_incl_vat,i_balance[0],i_year,i_month,i_day]

                        start_letter = "A"
                        end_letter = "M"
                        range1 = "%s%d:%s%d" % (start_letter, a+1, end_letter, a+1)
                        cell_list = sh.sheet1.range(range1)

                        for x in range(len(data)):
                            cell_list[x].value = str(data[x])

                        sh.sheet1.update_cells(cell_list)  

                    except Exception:
                        traceback.print_exc()
                        st.error('error')
                    
                st.success('done')

                st.session_state.run = False
                st.experimental_rerun()

        # --- Check if amount is correct ---

        st.write('---')
        
        st.markdown(f"<h2 style='text-align: center; color: white;'>Check if balance amount is correct</h2>", unsafe_allow_html=True)

        # --- Initialising SessionSate ---
        if "bank" not in st.session_state:
            st.session_state.bank = 0

        if "saving" not in st.session_state:
            st.session_state.saving = 0

        m1,m2,m3,m4 = st.columns([1,2,2,1])

        with m2:
            st.session_state.bank = st.number_input(
                'Current bank account'
            )
            difference_bank = round(calc_data['eq'],2) - st.session_state.bank

            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>Difference bank account</p>", unsafe_allow_html=True)
            st.markdown(f"<h6 style='text-align: center; color: white; font-size:45px;'>€ {round(difference_bank,2)}</h6>", unsafe_allow_html=True)
        
        with m3:
            st.session_state.saving = st.number_input(
                'Current savings account'
            )
            difference_saving = (round(calc_data['current_vat_to_be_paid'],2) +  round(calc_data['zvw_to_be_paid'],2)) - st.session_state.saving
            
            st.markdown(f"<p style='text-align: center; color: white; font-size:20px;'>Difference savings account</p>", unsafe_allow_html=True)
            st.markdown(f"<h6 style='text-align: center; color: white; font-size:45px;'>€ {round(difference_saving,2)}</h6>", unsafe_allow_html=True)

if __name__ == '__main__':  

    main()