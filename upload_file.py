import streamlit as st
import pandas as pd
import mysql.connector

# Fungsi untuk menyimpan informasi file ke dalam database MySQL
def save_to_mysql(df, table_name, db_connection, replace_existing_table=False):
    cursor = db_connection.cursor()

    # Mengecek apakah tabel sudah ada
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    table_exists = cursor.fetchone()

    if table_exists:
        if replace_existing_table:
            # Menghapus tabel yang sudah ada
            cursor.execute(f"DROP TABLE `{table_name}`")
        else:
            # Tampilkan peringatan dan batalkan penyimpanan
            st.warning(f"Tabel dengan nama {table_name} sudah ada di database. Gunakan opsi replace_existing_table=True untuk menggantinya.")
            return

    # Membuat tabel baru
    create_table_query = f"CREATE TABLE `{table_name}` ({', '.join([f'`{col}` VARCHAR(255)' for col in df.columns])})"
    cursor.execute(create_table_query)

    # Menangani nilai nan
    df.fillna('', inplace=True)

    # Menyimpan data ke dalam tabel
    for _, row in df.iterrows():
        insert_query = f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in df.columns])}) VALUES ({', '.join(['%s']*len(df.columns))})"
        values = tuple(row)
        cursor.execute(insert_query, values)

    # Commit perubahan ke database
    db_connection.commit()

# Fungsi utama aplikasi Streamlit
def main():
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

if __name__ == "__main__":
    main()
