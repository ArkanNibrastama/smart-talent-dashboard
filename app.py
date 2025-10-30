import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.graph_objects as go
from openai import OpenAI
import re
import traceback

# --- 1. PENGATURAN KONEKSI & FUNGSI INTI ---

# Ganti dengan URL koneksi database Postgres Anda
# Format: "postgresql://user:password@host:port/database"
DB_PASS = st.secrets["DB_PASS"]
DB_URL_CONN = f"postgresql://postgres.bwhzmldclqcuzocvlngc:{DB_PASS}@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

# Salin fungsi koneksi database Anda
@st.cache_resource
def create_db_engine(conn_string):
    try:
        engine = create_engine(conn_string)
        with engine.connect() as connection:
            print("Koneksi database SQLAlchemy berhasil!")
        return engine
    except Exception as e:
        st.error(f"Error koneksi database: {e}")
        return None

db_engine = create_db_engine(DB_URL_CONN)

# Fungsi untuk memuat daftar karyawan (untuk pilihan benchmark)
@st.cache_data
def load_employee_list(_engine):
    if _engine is None:
        return pd.DataFrame({'employee_id': [], 'fullname': []})
    try:
        query = "SELECT employee_id, fullname FROM employees ORDER BY fullname;"
        with _engine.connect() as conn:
            df_employees = pd.read_sql_query(text(query), conn)
        return df_employees
    except Exception as e:
        st.error(f"Gagal memuat daftar karyawan: {e}")
        return pd.DataFrame({'employee_id': [], 'fullname': []})

# Fungsi untuk memanggil AI (Ganti dengan API LLM Anda)
# @st.cache_data
def get_ai_profile(role_name, job_level, role_purpose):
    # 2. Tambahkan print di awal
    print("\n--- DEBUG: Memulai get_ai_profile ---")
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=st.secrets["OPENROUTER_API_KEY"]
        )

        prompt = f"""
        Anda adalah asisten HR yang membantu manajer membuat profil pekerjaan.
        Buat profil pekerjaan untuk lowongan baru di perusahaan kami.
        Nama Peran: {role_name}
        Level Pekerjaan: {job_level}
        Tujuan Peran: {role_purpose}

        Format output dalam 3 bagian (GUNAKAN MARKDOWN):
        ### Deskripsi Pekerjaan
        [Buat deskripsi singkat 2-3 kalimat]

        ### Persyaratan Kunci
        [Buat 5-7 bullet points persyaratan]

        ### Kompetensi Kunci
        [Buat 5-7 bullet points kompetensi]
        """

        print("--- DEBUG: Mengirim prompt ke OpenRouter... ---")
        response = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            messages=[{"role": "user", "content": prompt}],
            extra_headers={"HTTP-Referer": "http://localhost:8501"}
        )
        print("--- DEBUG: Menerima respons dari OpenRouter. ---")
        
        # 4. Cek apakah responsnya valid sebelum diakses
        if response and response.choices and len(response.choices) > 0:
            raw_response_text = response.choices[0].message.content
            
            print("\n" + "="*30)
            print("--- DEBUGGING: AI RAW RESPONSE (DARI DALAM FUNGSI) ---")
            print(f"Tipe data: {type(raw_response_text)}")
            print(f"Panjang: {len(raw_response_text)}")
            print("--- ISI DI BAWAH INI ---")
            print(raw_response_text) # Ini adalah print utama
            print("="*30 + "\n")
            
            if not raw_response_text:
                print("--- DEBUG: AI mengembalikan string KOSONG. ---")
                return "### AI mengembalikan respons kosong."
            
            return raw_response_text
        else:
            print(f"--- DEBUG: Respons AI tidak valid. Respons mentah: {response} ---")
            return "### Gagal mendapatkan 'choices' dari respons AI."

    except Exception as e:
        # 3. TAMBAHKAN PRINT() DI DALAM BLOK EXCEPT
        print("\n" + "!"*30)
        print("--- DEBUG: TERJADI ERROR DI FUNGSI AI ---")
        print(f"Tipe Error: {type(e)}")
        print(f"Error: {e}")
        print("Traceback:")
        # Cetak traceback lengkap ke terminal
        print(traceback.format_exc()) 
        print("!"*30 + "\n")
        
        st.error(f"Gagal menghubungi API AI: {e}")
        return f"### Gagal Menghasilkan Profil AI\nError: {e}"
    
# Fungsi untuk menjalankan query SQL dinamis dari Task 2
def fetch_talent_data(_engine, benchmark_ids):
    if _engine is None or not benchmark_ids:
        return pd.DataFrame()
        
    # 1. Format ID benchmark untuk klausa 'IN'
    # Hasil: ('EMP100312', 'EMP100335')
    formatted_ids = tuple(benchmark_ids)
    
    # Jika hanya 1 ID, tuple perlu format khusus: ('EMP100312',)
    if len(formatted_ids) == 1:
        formatted_ids = f"('{formatted_ids[0]}')"

    # 2. Ambil query lengkap dari Task 2
    # Ganti CTE 1 dengan versi dinamis
    
    sql_task_3_query_string = f"""
    WITH
    -- 1. Tentukan Benchmark (DINAMIS DARI INPUT)
    benchmark_selection AS (
        SELECT employee_id FROM employees WHERE employee_id IN {formatted_ids}
    ),
    
    -- 2. Dapatkan Rating Performance Terbaru...
    latest_performance AS (
        SELECT DISTINCT ON (employee_id)
            employee_id, rating,
            CASE WHEN rating = 5.0 THEN 1 ELSE 0 END AS is_high_performer
        FROM performance_yearly
        WHERE rating BETWEEN 1 AND 5
        ORDER BY employee_id, year DESC
    ),
    
    -- 3. Dapatkan Skor Kompetensi Terbaru...
    latest_competencies AS (
        SELECT DISTINCT ON (employee_id, pillar_code)
            employee_id, pillar_code, score
        FROM competencies_yearly
        WHERE score IS NOT NULL AND score != ''
        ORDER BY employee_id, pillar_code, year DESC
    ),
    
    -- 4. Pivot Skor Kompetensi...
    pivot_competencies AS (
        SELECT
            employee_id,
            MAX(CASE WHEN pillar_code = 'LIE' THEN CAST(score AS NUMERIC) ELSE NULL END) AS "LIE",
            MAX(CASE WHEN pillar_code = 'SEA' THEN CAST(score AS NUMERIC) ELSE NULL END) AS "SEA",
            MAX(CASE WHEN pillar_code = 'STO' THEN CAST(score AS NUMERIC) ELSE NULL END) AS "STO",
            MAX(CASE WHEN pillar_code = 'GDR' THEN CAST(score AS NUMERIC) ELSE NULL END) AS "GDR"
        FROM latest_competencies
        GROUP BY employee_id
    ),
    
    -- 5. Pivot Skor PAPI...
    pivot_papi AS (
        SELECT
            employee_id,
            MAX(CASE WHEN scale_code = 'Papi_L' THEN score ELSE NULL END) AS "Papi_L",
            MAX(CASE WHEN scale_code = 'Papi_A' THEN score ELSE NULL END) AS "Papi_A",
            MAX(CASE WHEN scale_code = 'Papi_B' THEN score ELSE NULL END) AS "Papi_B",
            MAX(CASE WHEN scale_code = 'Papi_C' THEN score ELSE NULL END) AS "Papi_C"
        FROM papi_scores
        WHERE score IS NOT NULL
        GROUP BY employee_id
    ),
    
    -- 6. Dapatkan Top 5 Strengths...
    top_5_strengths AS (
        SELECT employee_id, theme
        FROM strengths
        WHERE rank <= 5 AND theme IS NOT NULL
    ),
    
    -- 7. Rule Engine: Terapkan 10 ATURAN TV...
    tv_scores_wide AS (
        SELECT
            e.employee_id,
            CASE WHEN pc."LIE" >= 2.0 AND pc."SEA" >= 1.8 THEN 1 ELSE 0 END AS "tv_lie_skill",
            CASE WHEN pp."Papi_L" > 5 AND pp."Papi_A" > 4 THEN 1 ELSE 0 END AS "tv_leadership_drive",
            CASE WHEN EXISTS (SELECT 1 FROM top_5_strengths s WHERE s.employee_id = e.employee_id AND s.theme = 'Command') THEN 1 ELSE 0 END AS "tv_command_talent",
            CASE WHEN pc."STO" >= 1.8 THEN 1 ELSE 0 END AS "tv_sto_skill",
            CASE WHEN pp."Papi_B" < 5 AND pp."Papi_C" < 6 THEN 1 ELSE 0 END AS "tv_agility_profile",
            CASE WHEN EXISTS (SELECT 1 FROM top_5_strengths s WHERE s.employee_id = e.employee_id AND s.theme = 'Strategic') THEN 1 ELSE 0 END AS "tv_strategic_talent",
            CASE WHEN EXISTS (SELECT 1 FROM top_5_strengths s WHERE s.employee_id = e.employee_id AND s.theme = 'Achiever') THEN 1 ELSE 0 END AS "tv_achiever_talent",
            CASE WHEN pc."GDR" > 1.0 THEN 1 ELSE 0 END AS "tv_gdr_skill",
            CASE WHEN g.name IN ('IV', 'V') AND e.years_of_service_months > 49 THEN 1 ELSE 0 END AS "tv_context_filter",
            CASE WHEN ps.iq > 101 THEN 1 ELSE 0 END AS "tv_cognitive_filter"
        FROM employees e
        LEFT JOIN latest_performance lp ON e.employee_id = lp.employee_id
        LEFT JOIN pivot_competencies pc ON e.employee_id = pc.employee_id
        LEFT JOIN pivot_papi pp ON e.employee_id = pp.employee_id
        LEFT JOIN profiles_psych ps ON e.employee_id = ps.employee_id
        LEFT JOIN dim_grades g ON e.grade_id = g.grade_id
        WHERE lp.rating IS NOT NULL
    ),
    
    -- 8. Unpivot TV Scores...
    unpivoted_tv_scores AS (
        SELECT employee_id, 'Leadership' AS tgv_name, 'LIE_Skill' AS tv_name, "tv_lie_skill" AS user_score FROM tv_scores_wide
        UNION ALL SELECT employee_id, 'Leadership', 'Leadership_Drive', "tv_leadership_drive" FROM tv_scores_wide
        UNION ALL SELECT employee_id, 'Leadership', 'Command_Talent', "tv_command_talent" FROM tv_scores_wide
        UNION ALL SELECT employee_id, 'Strategic', 'STO_Skill', "tv_sto_skill" FROM tv_scores_wide
        UNION ALL SELECT employee_id, 'Strategic', 'Agility_Profile', "tv_agility_profile" FROM tv_scores_wide
        UNION ALL SELECT employee_id, 'Strategic', 'Strategic_Talent', "tv_strategic_talent" FROM tv_scores_wide
        UNION ALL SELECT employee_id, 'Drive', 'Achiever_Talent', "tv_achiever_talent" FROM tv_scores_wide
        UNION ALL SELECT employee_id, 'Drive', 'GDR_Skill', "tv_gdr_skill" FROM tv_scores_wide
        UNION ALL SELECT employee_id, 'Foundation', 'Context_Filter', "tv_context_filter" FROM tv_scores_wide
        UNION ALL SELECT employee_id, 'Foundation', 'Cognitive_Filter', "tv_cognitive_filter" FROM tv_scores_wide
    ),
    
    -- 9. Hitung Baseline (MEDIAN) dari Benchmark
    baseline_scores AS (
        SELECT
            tv_name,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY user_score) AS baseline_score
        FROM unpivoted_tv_scores
        WHERE employee_id IN (SELECT employee_id FROM benchmark_selection)
        GROUP BY tv_name
    ),
    
    -- 10. Hitung TV Match Rate...
    tv_match_rates AS (
        SELECT
            u.employee_id, u.tgv_name, u.tv_name,
            b.baseline_score, u.user_score,
            CASE WHEN u.user_score = b.baseline_score THEN 100.0 ELSE 0.0 END AS tv_match_rate
        FROM unpivoted_tv_scores u
        JOIN baseline_scores b ON u.tv_name = b.tv_name
    ),
    
    -- 11. Hitung TGV Match Rate...
    tgv_match_rates AS (
        SELECT employee_id, tgv_name, AVG(tv_match_rate) AS tgv_match_rate
        FROM tv_match_rates
        GROUP BY employee_id, tgv_name
    ),
    
    -- 12. Hitung Final Match Rate...
    final_match_rate AS (
        SELECT
            employee_id,
            SUM(
                tgv_match_rate * CASE
                    WHEN tgv_name = 'Leadership' THEN 0.35
                    WHEN tgv_name = 'Strategic' THEN 0.35
                    WHEN tgv_name = 'Drive' THEN 0.15
                    WHEN tgv_name = 'Foundation' THEN 0.15
                END
            ) AS final_match_rate
        FROM tgv_match_rates
        GROUP BY employee_id
    ),
    
    -- 13. Dapatkan Detail Karyawan...
    employee_details AS (
        SELECT
            e.employee_id, e.fullname,
            dir.name AS directorate,
            pos.name AS role,
            g.name AS grade
        FROM employees e
        LEFT JOIN dim_directorates dir ON e.directorate_id = dir.directorate_id
        LEFT JOIN dim_positions pos ON e.position_id = pos.position_id
        LEFT JOIN dim_grades g ON e.grade_id = g.grade_id
    )
    
    -- 14. FINAL SELECT
    SELECT
        t.employee_id, d.fullname,
        d.directorate, d.role, d.grade,
        t.tgv_name, t.tv_name,
        t.baseline_score, t.user_score,
        t.tv_match_rate,
        g.tgv_match_rate,
        f.final_match_rate
    FROM tv_match_rates AS t
    JOIN tgv_match_rates AS g ON t.employee_id = g.employee_id AND t.tgv_name = g.tgv_name
    JOIN final_match_rate AS f ON t.employee_id = f.employee_id
    JOIN employee_details AS d ON t.employee_id = d.employee_id
    ORDER BY
        f.final_match_rate DESC,
        t.employee_id,
        CASE
            WHEN t.tgv_name = 'Leadership' THEN 1
            WHEN t.tgv_name = 'Strategic' THEN 2
            WHEN t.tgv_name = 'Drive' THEN 3
            WHEN t.tgv_name = 'Foundation' THEN 4
        END,
        t.tv_name;
    """
    
    # Eksekusi query
    try:
        with _engine.connect() as conn:
            df_results = pd.read_sql_query(text(sql_task_3_query_string), conn)
        return df_results
    except Exception as e:
        st.error(f"Error saat eksekusi query dinamis: {e}")
        return pd.DataFrame()



@st.cache_data
def parse_ai_profile(ai_text_response):
    """
    Mem-parsing teks markdown dari AI menjadi format tabel
    [cite_start]sesuai permintaan PDF [cite: 123-125].
    """
    
    # (DEBUGGING: Anda bisa hilangkan tanda # di bawah ini untuk melihat
    #  output mentah dari AI di terminal/log Anda jika masih gagal)
    # print("--- AI RAW RESPONSE ---")
    # print(ai_text_response)
    # print("-------------------------")

    data_for_table = []
    
    # Pola regex yang lebih fleksibel (menggunakan \s+ bukan \s*\n)
    pattern = r'###\s*(.*?)\s+(.*?)(?=\n###|\Z)'
    
    # re.DOTALL membuat '.' cocok dengan newline, penting untuk konten multi-baris
    matches = re.findall(pattern, ai_text_response, re.DOTALL | re.IGNORECASE)
    
    if matches:
        for match in matches:
            category = match[0].strip()
            description = match[1].strip()
            
            # Ubah nama kategori agar sesuai dengan PDF
            if "deskripsi" in category.lower():
                pdf_category = "Job description"
            elif "persyaratan" in category.lower():
                pdf_category = "Job requirements"
            elif "kompetensi" in category.lower():
                pdf_category = "key competencies"
            else:
                pdf_category = category

            data_for_table.append({
                "Column": pdf_category,
                "Desc": description
            })
            
    if not data_for_table:
        # Fallback HANYA JIKA parsing gagal total
        st.warning("Gagal mem-parsing respons AI. Menampilkan sebagai teks mentah.")
        return pd.DataFrame([{"Column": "AI Response (Raw)", "Desc": ai_text_response}])
        
    return pd.DataFrame(data_for_table)


# --- 2. STREAMLIT UI ---

st.set_page_config(layout="wide")
st.title("🚀 Talent Match Intelligence System")

# Inisialisasi Session State
if 'profile_generated' not in st.session_state:
    st.session_state.profile_generated = False
    st.session_state.df_results = pd.DataFrame()
    st.session_state.ai_profile = ""
    st.session_state.role_name = "Data Analyst"
    st.session_state.job_level = "Middle"
    st.session_state.role_purpose = "Menganalisis data untuk menemukan wawasan bisnis."

# --- Input Sidebar ---
# ... (Sidebar UI Anda tetap sama) ...
st.sidebar.header("1. Buat Profil Pekerjaan Baru")
role_name_input = st.sidebar.text_input("Nama Peran (Role Name)", st.session_state.role_name, key="role_name")
job_level_input = st.sidebar.selectbox("Level Pekerjaan (Job Level)", ["Entry", "Middle", "Senior", "Lead"], key="job_level")
role_purpose_input = st.sidebar.text_area("Tujuan Peran (Role Purpose)", st.session_state.role_purpose, key="role_purpose")

st.sidebar.header("2. Pilih Karyawan Benchmark")
df_employees_list = load_employee_list(db_engine)
benchmark_input = st.sidebar.multiselect(
    "Pilih 1-3 Karyawan Benchmark:",
    options=df_employees_list['employee_id'],
    format_func=lambda x: f"{df_employees_list[df_employees_list['employee_id'] == x]['fullname'].values[0]} ({x})",
    max_selections=3
)
submit_button = st.sidebar.button("📊 Generate Profile & Find Talent")

# --- Logika Tombol Submit ---
if submit_button:
    if not benchmark_input:
        st.error("Harap pilih setidaknya 1 karyawan benchmark.")
    elif db_engine is None:
        st.error("Koneksi database gagal.")
    else:
        with st.spinner("Menganalisis... Memanggil AI dan menjalankan query SQL..."):
            st.session_state.ai_profile = get_ai_profile(role_name_input, job_level_input, role_purpose_input)
            st.session_state.df_results = fetch_talent_data(db_engine, benchmark_input)
            st.session_state.profile_generated = True

# --- 3. AREA OUTPUT UTAMA (VERSI MODIFIKASI) ---

if st.session_state.profile_generated:
    if not st.session_state.df_results.empty:
        
        df_results = st.session_state.df_results
        df_ranked_list = df_results.drop_duplicates(subset=['employee_id']).sort_values(by='final_match_rate', ascending=False)
        
        # --- Output 1 (AI Profile) ---
        st.header(f"1. AI-Generated Job Profile: {st.session_state.role_name}")
        with st.container(border=True):
            # Gunakan fungsi parsing yang sudah diperbaiki
            df_ai_profile = parse_ai_profile(st.session_state.ai_profile)
            st.dataframe(df_ai_profile, use_container_width=True, hide_index=True)

        # --- Output 2 (Ranked List) ---
        st.header("2. Ranked Talent List")
        df_ranked_display = df_ranked_list.copy()
        df_ranked_display['final_match_rate'] = df_ranked_display['final_match_rate'].map('{:,.1f}%'.format)
        st.dataframe(
            df_ranked_display[['employee_id', 'fullname', 'role', 'final_match_rate']],
            use_container_width=True,
            hide_index=True
        )

        # --- Output 3 (Dashboard Visualization) ---
        st.header("3. Dashboard Visualization")
        
        st.subheader("Distribusi Skor Kecocokan (Match-Rate Distribution)")
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=df_ranked_list['final_match_rate'],
            marker_color='#FFB81C',
            xbins=dict(start=0, end=100, size=5)
        ))
        fig_hist.update_layout(
            title_text='Distribusi Final Match Rate (Semua Kandidat)',
            xaxis_title_text='Skor Kecocokan Final (%)',
            yaxis_title_text='Jumlah Karyawan'
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        st.divider()

        st.subheader("Analisis Detail: Benchmark vs. Kandidat")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            top_5_candidates = df_ranked_list.head(20)['employee_id'].tolist()
            selected_candidate_id = st.selectbox(
                "Pilih kandidat untuk perbandingan detail:",
                options=top_5_candidates,
                format_func=lambda x: f"{df_ranked_list[df_ranked_list['employee_id'] == x]['fullname'].values[0]} ({x})"
            )
        
        if selected_candidate_id:
            with col2:
                # --- Visual 2: Benchmark vs Candidate (Radar Chart) ---
                df_candidate = df_results[df_results['employee_id'] == selected_candidate_id]
                df_candidate_tgv = df_candidate.drop_duplicates(subset=['tgv_name'])[['tgv_name', 'tgv_match_rate']]
                
                df_benchmark = df_results[df_results['employee_id'].isin(benchmark_input)]
                df_benchmark_tgv = df_benchmark.groupby('tgv_name')['tgv_match_rate'].mean().reset_index()
                
                df_plot = df_candidate_tgv.merge(df_benchmark_tgv, on='tgv_name', suffixes=('_candidate', '_benchmark'))
                
                fig_radar = go.Figure()
                categories = df_plot['tgv_name']
                
                # === PERBAIKAN 2: Ganti 'tv_' menjadi 'tgv_' ===
                fig_radar.add_trace(go.Scatterpolar(
                    r=df_plot['tgv_match_rate_benchmark'], # <-- PERBAIKAN
                    theta=categories, fill='toself', name='Benchmark (Median)'
                ))
                fig_radar.add_trace(go.Scatterpolar(
                    r=df_plot['tgv_match_rate_candidate'], # <-- PERBAIKAN
                    theta=categories, fill='toself',
                    name=f"Kandidat: {df_ranked_list[df_ranked_list['employee_id'] == selected_candidate_id]['fullname'].values[0]}"
                ))
                # === BATAS PERBAIKAN 2 ===
                
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    title="Perbandingan TGV: Kandidat vs. Benchmark"
                )
                st.plotly_chart(fig_radar, use_container_width=True)

                # --- Visual 3: Top Strengths and Gaps (TV Level) ---
                st.markdown("---")
                st.subheader(f"Kekuatan & Kesenjangan (Strengths & Gaps) vs. Benchmark")
                
                df_candidate_tv = df_candidate.drop_duplicates(subset=['tv_name'])
                df_candidate_tv = df_candidate_tv.sort_values(by='tv_match_rate', ascending=True)

                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    x=df_candidate_tv['tv_match_rate'],
                    y=df_candidate_tv['tv_name'],
                    orientation='h',
                    marker_color=df_candidate_tv['tv_match_rate'].apply(lambda x: '#00875A' if x > 0 else '#D63D2E')
                ))
                fig_bar.update_layout(
                    title_text=f"Analisis TV: {df_ranked_list[df_ranked_list['employee_id'] == selected_candidate_id]['fullname'].values[0]}",
                    xaxis_title_text='Match Rate (100 = Sesuai Benchmark, 0 = Tidak Sesuai)',
                    yaxis_title_text='Talent Variable (TV)',
                    height=400
                )
                st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.error("Query SQL tidak mengembalikan hasil. Periksa benchmark atau koneksi database.")
else:
    st.info("Harap isi input di sidebar kiri dan klik 'Generate Profile' untuk memulai.")