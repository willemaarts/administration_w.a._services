from datetime import datetime, date
import calendar
import traceback
import streamlit as st
import pandas as pd
import numpy as np
import locale
import gspread as gs

st.set_page_config(page_title="Financial statement - W.A. Services", layout="wide", initial_sidebar_state="collapsed")

@st.experimental_singleton
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

@st.experimental_memo(show_spinner=True)
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
    
    # Calculate VA
    laptop = 0

    # Calculate VLA
    debiteuren = 0
    vat_to_receive = 0
    bank = abs(revenue_incl) - abs(VAT_paid) - abs(zvw_paid) - abs(costs) - abs(private)
    
    # Total assest
    t_assets = laptop + debiteuren + vat_to_receive + bank

    # Calculate EQ
    eq = equity - abs(private) - abs(costs) - zvw_to_be_paid

    # Calculate VVK
    crediteuren = 0
    #current_vat_to_be_paid
    
    # Calculate zvw to be paid
    #zvw_to_be_paid

    # Total liabilities
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

def main():

    st.markdown("<h1 style='text-align: center; color: grey;'>Administration W.A. Services</h1>", unsafe_allow_html=True)

    placeholder = st.empty()

    with placeholder.form("login"):
        st.markdown("#### Login")
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", placeholder="Enter password", type="password")
        login_button = st.form_submit_button("Login")

    if st.secrets['credentials']['name'] == username and st.secrets['credentials']['password'] == password:
        placeholder.empty()
    else:
        return

    current_month = (int(datetime.now().strftime('%m')))

    g_data = retreive_data() 

    df = pd.DataFrame(g_data, columns=g_data[0]) 
    df = df.iloc[1:]

    cols = ['amount_ex_vat', 'vat_percentage','amount_inc_vat', 'amount_vat']
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce', axis=1)

    df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True)

    month_select = st.sidebar.multiselect(
        'Select the month:',
        options=df['month'].unique(),
        default=str(current_month)
    )

    balance_Select = st.sidebar.multiselect(
        'Select the balance:',
        options=df['balancesheet_item'].unique(),
        default=df['balancesheet_item'].unique()
    )

    df_selection = df.query(
        f"month == @month_select & balancesheet_item == @balance_Select" 
    )

    st.header(f'Total figure of the month: {calendar.month_name[int(month_select[0])]}')

    l_c, m1_c, m2_c, r_c = st.columns([1,1,1,1])

    with l_c:
        revenue = df.query("balancesheet_item == 'Omzet' & month == @month_select")['amount_inc_vat'].sum()
        st.metric("Revenue:",f'€ {revenue:n}')
    with m1_c:
        costs = df.query("balancesheet_item == 'Kosten' & month == @month_select")['amount_inc_vat'].sum()
        st.metric("Costs:",f'€ {costs:n}')
    with m2_c:
        private = df.query("balancesheet_item == 'Prive' & month == @month_select")['amount_inc_vat'].sum()
        st.metric("Private:",f'€ {private:n}')     
    with r_c:
        profit = (revenue + costs + private)
        st.metric("EBITDA:",f'€ {profit:n}')


    st.json(g_data, expanded=False)
    st.dataframe(df_selection)

    st.write('---')

    calc_data = contruct_data(df)

    m1, m2, m3, m4, m5, m6 = st.columns([1,1,1,1,1,1])

    with m1:
        st.subheader('Vaste activa:')
        st.metric('Laptop', calc_data['laptop'])

        st.subheader('Vlottende activa:')
        st.metric('debiteuren', calc_data['debiteuren'])
        st.metric('vat_to_receive', calc_data['vat_to_receive'])
        st.metric('bank', round(calc_data['bank'],2))

        st.subheader('Total')
        st.metric('totaal assets', round(calc_data['t_assets'],2))

    with m2:
        pass

    with m3:    
        st.subheader('Eigen vermogen:')
        st.metric('eq', round(calc_data['eq'],2))

        st.subheader('VVK:')
        st.metric('Crediteuren', calc_data['crediteuren'])
        st.metric('current_vat_to_be_paid', round(calc_data['current_vat_to_be_paid'],2))
        st.metric('zvw_to_be_paid', round(calc_data['zvw_to_be_paid'],2))

        st.subheader('Total')
        st.metric('totaal assets', round(calc_data['t_assets'],2))

    with m4:
        pass

    with m5:
        pass

    with m6:
        curr_bank = st.number_input(
            'Current bank account'
        )
        difference_bank = round(calc_data['eq'],2) - curr_bank
        st.metric('Difference bank account:',
        value=round(difference_bank,2))

        curr_saving = st.number_input(
            'Current savings account'
        )
        difference_saving = (round(calc_data['current_vat_to_be_paid'],2) +  round(calc_data['zvw_to_be_paid'],2)) - curr_saving
        st.metric('Difference saving account:',
        value=round(difference_saving,2))

    with st.sidebar:
        st.write("---")
        st.markdown("# Add data:")

        i_index = int(df['index'].iloc[-1]) + 1

        i_date = st.text_input(
            'Add details',
            value=f"{int(datetime.now().strftime('%d'))}/{int(datetime.now().strftime('%m'))}/{int(datetime.now().strftime('%Y'))}"
        )

        i_invoice = st.text_input(
            'Add invoice number:'
        )

        i_relation = st.sidebar.multiselect(
            'Select relation:',
            options=df['relation'].unique(),
            max_selections=1
        )

        i_details = st.text_input(
            'Add details'
        )
        
        i_amount = st.number_input(
            'Add amount excl VAT'
        )

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

            st.experimental_memo.clear()
            st.experimental_rerun()


if __name__ == '__main__':  

    main()