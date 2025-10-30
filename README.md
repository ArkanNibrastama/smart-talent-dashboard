# 🚀 Talent Match Intelligence System

## 🎯 Deskripsi Proyek

Tujuan proyek ini adalah untuk membangun sistem "Talent Match Intelligence" yang interaktif. Sistem ini membantu para pemimpin bisnis untuk:
1.  **Menemukan Pola Sukses:** Mengidentifikasi "DNA" atau karakteristik kunci dari karyawan berkinerja terbaik (High Performer).
2.  **Mencari Kandidat Serupa:** Menemukan talenta internal lain yang memiliki profil serupa untuk kebutuhan suksesi atau promosi.

Aplikasi ini mengubah analisis data mentah (Task 1) dan logika SQL yang kompleks (Task 2) menjadi sebuah *dashboard* yang fungsional, dinamis, dan dapat ditindaklanjuti (Task 3).

## ✨ Fitur Utama

* **AI-Generated Job Profiles:** Secara dinamis menghasilkan deskripsi pekerjaan, persyaratan, dan kompetensi kunci menggunakan AI (LLM via OpenRouter) berdasarkan input peran dari manajer.
* **Dynamic Talent Matching:** Menjalankan query SQL *real-time* (lebih dari 300 baris) yang membandingkan semua karyawan dengan 1-3 karyawan *benchmark* yang dipilih.
* **Interactive Dashboard :**
    * **Ranked Talent List:** Menampilkan daftar karyawan yang paling cocok, diurutkan berdasarkan `final_match_rate`.
    * **Match-Rate Distribution:** Histogram yang menunjukkan distribusi skor kecocokan di seluruh perusahaan.
    * **Benchmark vs. Candidate:** Radar chart untuk membandingkan skor TGV (Talent Group Variable) antara kandidat terpilih dan *benchmark*.
    * **Strengths & Gaps:** Bar chart yang merinci skor per TV (Talent Variable), menyoroti kekuatan dan kesenjangan kandidat.

## 🛠️ Teknologi yang Digunakan

* **Bahasa:** Python
* **Framework Aplikasi:** Streamlit
* **Database:** PostgreSQL (Dis hosting di Supabase, berdasarkan kode)
* **Manajemen Database:** SQLAlchemy & Psycopg2
* **Analisis Data:** Pandas
* **Visualisasi:** Plotly
* **AI / LLM:** OpenRouter (menggunakan library `openai`)

## ⚙️ Pengaturan & Instalasi

Untuk menjalankan proyek ini secara lokal, ikuti langkah-langkah berikut:

### 1. Prasyarat
* Python 3.9+
* Akses ke database PostgreSQL (misalnya, akun Supabase gratis).

### 2. Kloning Repositori
```bash
git clone [URL_GIT_ANDA_DI_SINI]
cd [NAMA_FOLDER_ANDA]
```

### 3. Populasikan Database Anda
Ini adalah langkah paling penting. Kode ini tidak akan berjalan tanpa database yang berfungsi.

1. Masuk ke layanan database Postgres Anda (misal: Supabase).

2. Buat 17 tabel secara manual sesuai dengan ERD dan kamus data di Case Study Brief - Data Analyst 2025 rev 1.1.pdf.

3. Impor 17 file CSV yang sesuai ke dalam 17 tabel yang baru Anda buat.

### 4. Siapkan Virtual Environment & Dependensi
Sangat disarankan untuk menggunakan virtual environment.

```bash
# Buat virtual environment
python -m venv venv

# Aktifkan (Windows)
.\venv\Scripts\activate
# Aktifkan (Mac/Linux)
source venv/bin/activate
```
install dependencies:

```bash
pip install -r requirements.txt
```

### 5. Atur Secrets (Kunci API & DB)
Aplikasi ini menggunakan st.secrets untuk mengelola kunci API dengan aman.

1. Buat folder baru di root proyek Anda: .streamlit

2. Di dalam folder .streamlit, buat file baru: secrets.toml

3. Isi file secrets.toml dengan kredensial Anda:

```bash
# .streamlit/secrets.toml

# Ganti 'PASSWORD_DB_ANDA' dengan password Postgres/Supabase Anda
DB_PASS = "PASSWORD_DB_ANDA"

# Ganti 'sk-or-...' dengan API key OpenRouter Anda
OPENROUTER_API_KEY = "sk-or-xxxxxxxxxxxxxxxxxxxxxx"
```

## Cara Menjalankan

Setelah database terisi dan file secrets.toml diatur, Anda siap menjalankan aplikasi:

```bash
streamlit run app.py
```

Aplikasi akan terbuka secara otomatis di browser Anda di http://localhost:8501.