import streamlit as st
import pandas as pd
import mysql.connector
from twilio.rest import Client
import plotly.express as px
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
from datetime import datetime
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# Hardcoded username and password for demonstration purposes
correct_username = "TAA123"
correct_password = "TAA123"

# Fungsi untuk autentikasi user
def authenticate_user(username, password):
    return username == correct_username and password == correct_password

# Fungsi proses login
def login():
    st.markdown(
    """
    <style>
        .title {
            font-size: 36px;
            color: lightblue;  /* Ubah warna sesuai keinginan Anda */
            text-align: center;
            margin-bottom: 20px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Menampilkan judul dengan gaya yang telah ditentukan
    st.markdown('<p class="title">Login Dashboard Monitoring BA Dismantle</p>', unsafe_allow_html=True)
    st.sidebar.image("tbg.png")
    with st.form("login_form"):
        username = st.text_input("Username:")
        password = st.text_input("Password:", type="password")

        submitted = st.form_submit_button("Login")

        if submitted:
            if authenticate_user(username, password):
                st.session_state.login_form_hidden = True
                st.success("Login successful! Welcome to the main menu.")
            else:
                st.error("Invalid username or password. Please try again.")

# Fungsi untuk mendapatkan koneksi ke database MySQL
def create_connection():
    connection = mysql.connector.connect(
        host='localhost',  # Ganti dengan host Anda
        user='root',    # Ganti dengan username Anda
        password='',  # Ganti dengan password Anda
        database='dashboard'  # Ganti dengan nama database Anda
    )
    return connection

# Fungsi untuk menjalankan query dan mendapatkan hasil sebagai dataframe
def run_query(query, fetch=True):
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute(query)
    
    if fetch:
        result = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        connection.close()
        return pd.DataFrame(result, columns=columns)

    connection.commit()
    connection.close()


def get_drive_files():
    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

    # Ganti path ke file kredensial JSON yang telah Anda unduh dari Google Cloud Console
    SERVICE_ACCOUNT_FILE = 'credential.json'

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )

    drive_service = build('drive', 'v3', credentials=creds)

    # Mendapatkan daftar file dari Google Drive
    results = drive_service.files().list(pageSize=10, fields="nextPageToken, files(id, name)").execute()
    files = results.get('files', [])

    return files

# Fungsi untuk membuat tata letak sidebar
def create_sidebar(data, drive_files):
    st.sidebar.title("Filter Data")

    # Filter nilai unik hanya untuk kolom yang diinginkan pada sidebar
    columns_to_filter = ['regional_name', 'Operator_id', 'Group Product', 'Actual Status Perangkat', 'Feedback Regional', 'Additional Remark Perangkat']

    for column in columns_to_filter:
        unique_values = [None] + list(data[column].unique())  # Menambahkan nilai default None
        selected_value = st.sidebar.selectbox(f'Pilih {column}', unique_values)

        # Filter data berdasarkan nilai yang dipilih
        if selected_value is not None:
            data = data[data[column] == selected_value]

    jumlah_baris = len(data)
    st.sidebar.write(f"Jumlah Baris: {jumlah_baris}")

    # Tombol "Kirim Pesan ke WhatsApp"
    if st.sidebar.button("Reminder!"):

        check_and_send_email(data)

    # Tombol untuk mengunduh data
    csv_data = data.to_csv(index=False, encoding='utf-8')
    b64 = base64.b64encode(csv_data.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="filtered_data.csv">Unduh Data (CSV)</a>'
    st.sidebar.markdown(href, unsafe_allow_html=True)

    # Tombol untuk melakukan pemrosesan file yang ada di Google Drive
    if st.sidebar.button("Update Data"):
        process_matching_files(data, drive_files)

    return data

# Fungsi untuk melakukan pemrosesan file yang ada di Google Drive
def process_matching_files(data, drive_files):
    matching_sites = data['Site Name'].tolist()
    
    site_counts = {}
    
    # Iterate through Google Drive files
    for file in drive_files:
        name_without_extension, _ = os.path.splitext(file['name'])
        
        # Check if the file name matches any site name in the DataFrame
        if name_without_extension in matching_sites:
            
            site_counts[name_without_extension] = site_counts.get(name_without_extension, 0) + 1
            # Perform processing here, for example, print the matching file name
            query = f"UPDATE dashboard SET `Additional Remark Perangkat` = 'BA Dismantle Done Upload' WHERE `Site Name` = '{name_without_extension}'"
            run_query(query, fetch=False)
            st.success(f"Database updated for site: {name_without_extension}")

    for site, count in site_counts.items():
        if count > 1:
            st.warning(f"Multiple files found for site: {site}. Updated {count} times.")

def authenticate_gsheets(creds_file):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
    client = gspread.authorize(creds)
    return client

def get_google_sheets_data(sheet_key, sheet_name):
    client = authenticate_gsheets('credential.json')
    sheet = client.open_by_key(sheet_key)
    worksheet = sheet.worksheet(sheet_name)
    data = worksheet.get_all_values()
    return pd.DataFrame(data[1:], columns=data[0])

# Fungsi untuk membuat tata letak utama untuk Dashboard
def create_dashboard_layout(data):
    
    st.title('Dashboard')
    
    
    # Menampilkan data yang difilter menggunakan Pandas DataFrame
    #st.dataframe(data)
    
    # Menampilkan Circular Progress untuk 'Additional Remark Perangkat'
    additional_remark_status = data['Additional Remark Perangkat'].value_counts(normalize=True) * 100
    ba_dismantle_percentage = additional_remark_status.get('BA Dismantle Done Upload', 0)
    ba_dismantle_count = data['Additional Remark Perangkat'].value_counts().get('BA Dismantle Done Upload', 0)
    
    # Menampilkan Circular Progress Bar
    st.progress(ba_dismantle_percentage / 100)
    st.markdown('<p style="font-size: 20px; font-weight: bold;">BA Dismantle Done Upload: {:.2f}%</p>'.format(ba_dismantle_percentage), unsafe_allow_html=True)

    
    jumlah_baris = len(data)
    jumlah_tiapregional = len(data['regional_name'])
    # Enter your Google Sheets credentials JSON file path
    credentials_path = 'credential.json'
    # Enter your Google Sheets key and sheet name
    sheet_key = '16RORO0C0Zwp1eBh-qUn6JQSryPb_1iqtJSHd5YAFIRA'
    sheet_name = 'Site Information'
    
    try:
        df = get_google_sheets_data(sheet_key, sheet_name)         
        # Display number of rows and columns
        num_rows, num_columns = df.shape
         
    except Exception as e:
            st.error(f"Error: {e}")
    
    doneupload = num_rows + ba_dismantle_count
    nyupload = jumlah_baris - doneupload
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div style="background-color: #e6e6ff; padding: 10px; border-radius: 10px;">'
                '<p style="font-size: 18px; text-align: center; color: #33a0ff; margin: 0; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">Total SOW</p>'
                '<p style="font-size: 14px; text-align: center; color: black; margin: 0; ">Jumlah: {:.0f}</p>'
                '</div>'.format(jumlah_baris), unsafe_allow_html=True)

    with col2:
        st.markdown('<div style="background-color: #e6ffe6; padding: 10px; border-radius: 10px;">'
                '<p style="font-size: 16px; text-align: center; color: #0b6149; margin: 0; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">BA Dismantle Done Upload</p>'
                '<p style="font-size: 14px; text-align: center; color: black;margin: 0; ">Jumlah: {:.0f}</p>'
                '</div>'.format(doneupload), unsafe_allow_html=True)

    with col3:
        st.markdown('<div style="background-color: #ffe6e6; padding: 10px; border-radius: 10px;">'
                '<p style="font-size: 18px; text-align: center; color: #ff5733; margin: 0; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">BA Dismantle NY Upload</p>'
                '<p style="font-size: 14px; text-align: center; color: black ;margin: 0; ">Jumlah: {:.0f}</p>'
                '</div>'.format(nyupload), unsafe_allow_html=True)

    

    # Visualisasi hanya untuk kolom tertentus
    selected_columns1 = ['regional_name']
    for column in selected_columns1:
            # Hanya visualisasikan kolom dengan lebih dari satu nilai unik
            fig = px.histogram(data, x=column, title=f'Distribusi {column}', color=column, height=500, width=700)
            fig.update_traces(texttemplate='%{y}', textposition='outside',)
            st.plotly_chart(fig)
        
        

    # Filter rows where Additional Remark Perangkat is either 'BA Done Upload' or 'BA NY Upload'
    filtered_data = data[data['Additional Remark Perangkat'].isin(['BA Dismantle Done Upload', 'BA Dismantle NY Upload'])]
    
    # Create a stacked bar chart
    fig = px.histogram(
    filtered_data,
    x='regional_name',
    color='Additional Remark Perangkat',
    title='Distribusi BA Done Upload dan BA NY Upload berdasarkan Regional',
    height=500,
    width=700
)
    # Sort regional_name alphabetically
    sorted_regional_names = sorted(filtered_data['regional_name'].unique(), key=lambda x: str(x).lower())
    fig.update_xaxes(categoryorder='array', categoryarray=sorted_regional_names)

    fig.update_traces(texttemplate='%{y}', textposition='outside')
    st.plotly_chart(fig)
## Display BA Dismantle percentage as a line chart
    ba_dismantle_percentage_data = data.groupby(['regional_name', 'Additional Remark Perangkat'])['Additional Remark Perangkat'].count().unstack().fillna(0)

# Calculate the percentage for 'BA Dismantle Done Upload'
    ba_dismantle_percentage_data['BA Dismantle percentage'] = (ba_dismantle_percentage_data['BA Dismantle Done Upload'] / ba_dismantle_percentage_data.sum(axis=1)) * 100

# Sort regional_name alphabetically
    sorted_regional_names = sorted(data['regional_name'].unique(), key=lambda x: str(x).lower())

# Create a line chart with plotly.graph_objects
    ba_dismantle_percentage_fig = go.Figure()

# Add trace for BA Dismantle percentage as a line
    ba_dismantle_percentage_fig.add_trace(
    go.Scatter(
        x=sorted_regional_names,
        y=ba_dismantle_percentage_data['BA Dismantle percentage'],
        mode='lines+markers',
        name='BA Dismantle Percentage',
        text=ba_dismantle_percentage_data['BA Dismantle percentage'].round(2).astype(str) + '%',  # Add labels to each point
        textposition='top center',  # Adjust text position as needed
        line=dict(color='blue'), 
        textfont=dict(color='white') # Adjust line color as needed
    )
)

# Set layout properties
    ba_dismantle_percentage_fig.update_layout(
    title='Persentase BA Dismantle berdasarkan Regional',
    xaxis=dict(title='Regional Name'),
    yaxis=dict(title='BA Dismantle Percentage'),
    height=500,
    width=700,
)

# Display the chart
    st.plotly_chart(ba_dismantle_percentage_fig)
    
    
    
# Fungsi untuk membuat tata letak utama untuk Database
def create_database_layout(data, drive_files):
    st.title('Database')
    
    # Menampilkan data yang difilter menggunakan Pandas DataFrame
    st.dataframe(data)

    # Menampilkan informasi file dari Google Drive
    if drive_files:
        st.write("Daftar File BA Uploaded by Regional:")
        file_data = []
        for file in drive_files:
            name_without_extension, _ = os.path.splitext(file['name'])
            file_data.append({"Name": name_without_extension})

        # Membuat DataFrame dari data file
        df = pd.DataFrame(file_data)

        # Menampilkan tabel menggunakan Streamlit
        st.table(df)
    else:
        st.write("Tidak ada file yang ditemukan di Google Drive.")

# Fungsi untuk mengirim email
def send_email(site_names_table, spv_ome):
    sender_email = "taatbg01@gmail.com"  # Ganti dengan alamat email pengirim
    password = "ialo cnll uubi kfne"  # Ganti dengan kata sandi email pengirim

    # Daftar penerima email sesuai dengan logika yang diberikan
    if spv_ome == "Sudaryono":
        receiver_email = "revfath.syafaat@tower-bersama.com"
    elif spv_ome == "Asep Iip Saripudin":
        receiver_email = "rrevfathrs@gmail.com"
    else:
        receiver_email = "revfath.syafaat@tower-bersama.com"

    subject = f"List Site Names - BA Dismantle NY Upload"

    # Membuat email
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Menambahkan HTML dengan tabel site names
    body = f"""<html>
                <body>
                    <p>Dear {spv_ome},</p>
                    <p>Berikut adalah daftar Site Names yang memiliki Additional Remark Perangkat BA Dismantle NY Upload :</p>
                    {site_names_table}
                    <p>Terima Kasih,</p>
                    <p>Best Regards</p>
                    <p><b>Asset Assesment Department</b></p>
                    <p><b>Asset Productivity Division</b></p>
                </body>
                </html>
            """

    # Menambahkan teks email
    message.attach(MIMEText(body, "html"))

    # Mengirim email
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

# Fungsi untuk mengecek dan mengirim email berdasarkan logika yang diberikan
def check_and_send_email(data):
    # Membuat dictionary untuk menyimpan site names berdasarkan SPV OME
    site_names_by_spv_ome = {}

    for index, row in data.iterrows():
        additional_remark_perangkat = row["Additional Remark Perangkat"]
        spv_ome = row["SPV Ome"]

        if additional_remark_perangkat == "BA Dismantle NY Upload":
            site_id = row["SiteID Trim"]
            site_name = row["Site Name"]
            spv = row["SPV Ome"]
            sonumb = row["Sonumb Trim"]
            operator = row["Operator_id"]

            # Menyimpan site names berdasarkan SPV OME
            if spv_ome not in site_names_by_spv_ome:
                site_names_by_spv_ome[spv_ome] = []

            site_names_by_spv_ome[spv_ome].append({"So Numb":sonumb,"Site ID": site_id, "Site Name": site_name, "Operator": operator, "SPV OME": spv })

    for spv_ome, site_names in site_names_by_spv_ome.items():
        if site_names:
            # Membuat DataFrame dari site names
            site_names_df = pd.DataFrame(site_names)

            # Membuat tabel HTML dari DataFrame
            site_names_table = site_names_df.to_html(index=False)

            send_email(site_names_table, spv_ome)

    st.success("Email berhasil dikirim ke masing-masing SPV Ome")

# Fungsi untuk menyimpan database
def save_to_mysql(df, table_name, db_connection, replace_existing_table=False):
    cursor = db_connection.cursor()

    # Membuat tabel jika belum ada atau mengganti tabel yang sudah ada
    if replace_existing_table:
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")

    # Cek apakah tabel sudah ada
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    table_exists = cursor.fetchone()

    if not table_exists:
        # Jika tabel belum ada, buat tabel baru dengan Remark
        create_table_query = f"CREATE TABLE `{table_name}` ({', '.join([f'`{col}` VARCHAR(255)' for col in df.columns] + ['`Remark` VARCHAR(255)'])})"
        cursor.execute(create_table_query)
    else:
        # Jika tabel sudah ada, tambahkan kolom Remark jika belum ada
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE 'Remark'")
        remark_column_exists = cursor.fetchone()

        if not remark_column_exists:
            cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `Remark` VARCHAR(255)")

    # Menangani nilai nan
    df.fillna('', inplace=True)

    # Memeriksa apakah kolom 'Remark' sudah ada dalam dataframe atau tidak
    if 'Remark' not in df.columns:
        # Jika tidak ada, tambahkan kolom 'Remark' dengan nilai default kosong
        df['Remark'] = ''

    # Menyimpan data ke dalam tabel
    for _, row in df.iterrows():
        insert_query = f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in df.columns])}) VALUES ({', '.join(['%s']*len(df.columns))})"
        values = tuple(row)
        cursor.execute(insert_query, values)

    # Commit perubahan ke database
    db_connection.commit()

# Fungsi untuk membuat tata letak update remark
def create_sidebar_remark(data):
    st.sidebar.title("Update Remark")

    # Filter nilai unik hanya untuk kolom yang diinginkan pada sidebar
    columns_to_filter = ['Site Name']

    for column in columns_to_filter:
        unique_values = [None] + list(data[column].unique())  # Menambahkan nilai default None
        selected_value = st.sidebar.selectbox(f'Pilih {column}', unique_values)

        # Filter data berdasarkan nilai yang dipilih
        if selected_value is not None:
            data = data[data[column] == selected_value]

            # Tampilkan textfield dan tombol untuk memperbarui kolom 'Remark'
            remark_value = st.text_area("Isi Kolom Remark:", value="")
            update_button = st.button("Update Remark")

            if update_button and remark_value:
                # Update database
                update_query = f"UPDATE dashboard SET Remark = '{remark_value}' WHERE `Site Name` = '{selected_value}'"
                connection = create_connection()
                cursor = connection.cursor()
                cursor.execute(update_query)
                connection.commit()
                connection.close()

                # Tampilkan pesan sukses
                st.success(f"Kolom Remark untuk '{selected_value}' telah diperbarui!")

    jumlah_baris = len(data)
    st.sidebar.write(f"Jumlah Baris: {jumlah_baris}")

    # Tombol untuk mengunduh data
    csv_data = data.to_csv(index=False, encoding='utf-8')
    b64 = base64.b64encode(csv_data.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="filtered_data.csv">Unduh Data (CSV)</a>'
    st.sidebar.markdown(href, unsafe_allow_html=True)

    return data


# Fungsi untuk membuat tata letak utama
def create_main_layout_remark(data):
    st.title('Database')

    # Menampilkan data yang difilter menggunakan Pandas DataFrame
    st.dataframe(data)



# Main Streamlit app
def main():
    st.set_page_config(page_title="Login App", page_icon=":lock:")

    # Check if the login form should be displayed
    if not hasattr(st.session_state, 'login_form_hidden') or not st.session_state.login_form_hidden:
        login()
    else:
                st.sidebar.image("tbg.png")
                # Mendapatkan daftar file dari Google Drive
                files = get_drive_files()

                # Menampilkan main menu
                main_menu = st.sidebar.radio("Main Menu", ["Upload", "Database","Dashboard","Update Remark"])

                # Query SQL untuk mendapatkan data dari tabel tertentu
                query = "SELECT * FROM dashboard"  # Ganti dengan nama tabel Anda

                # Menampilkan data menggunakan Pandas DataFrame
                data = run_query(query)

                # Menampilkan tata letak berdasarkan pilihan menu
                if main_menu == "Dashboard":
                    # Membuat tata letak sidebar
                    data = create_sidebar(data, files)
                    create_dashboard_layout(data)
                    
                    
                    
                    
                elif main_menu == "Database":
                    # Menampilkan tata letak utama untuk Database
                    create_database_layout(data, files)
                elif main_menu == "Upload" :
                    st.title("Upload File")

                # Upload file menggunakan Streamlit
                    uploaded_file = st.file_uploader("Pilih file untuk diupload", type=["csv"])

                    if uploaded_file is not None:
                    # Membaca file menjadi dataframe
                        df = pd.read_csv(uploaded_file, encoding='cp1252', sep=';')  # Ubah menjadi pd.read_excel() jika file adalah format Excel
                    # Menampilkan informasi file
                        st.write("Informasi File:")
                        st.write(f"Jumlah Baris: {len(df)}")
                        st.write(f"Jumlah Kolom: {len(df.columns)}")
                        st.write("Isi Dataframe:")
                        st.write(df)

                    # Simpan dataframe ke dalam database MySQL
                        db_connection = mysql.connector.connect(
                        host='localhost',
                        user='root',
                        password='',
                        database='dashboard'
                    )

                        table_name = 'dashboard'  # Ganti dengan nama tabel yang diinginkan
                        replace_existing_table = True  # Ganti dengan nilai True jika ingin mengganti tabel yang sudah ada
                        save_to_mysql(df, table_name, db_connection, replace_existing_table)
                        st.success(f"Data berhasil disimpan ke dalam tabel {table_name} di database.")

                elif main_menu == "Update Remark" :
                    # Query SQL untuk mendapatkan data dari tabel tertentu
                    query = "SELECT * FROM dashboard"  # Ganti dengan nama tabel Anda

                    # Menampilkan data menggunakan Pandas DataFrame
                    data = run_query(query)

                    # Membuat tata letak sidebar
                    data = create_sidebar_remark(data)

                    # Membuat tata letak utama
                    create_main_layout_remark(data)

    
    
if __name__ == '__main__':
    main()
