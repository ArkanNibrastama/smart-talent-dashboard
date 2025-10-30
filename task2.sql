WITH
-- 1. Tentukan Benchmark (Input dari Manager)
benchmark_selection AS (
    SELECT 'EMP100312' AS employee_id
    UNION ALL
    SELECT 'EMP100335' AS employee_id
    UNION ALL
    SELECT 'EMP100175' AS employee_id
),

-- 2. Dapatkan Rating Performance Terbaru (Valid 1-5)
latest_performance AS (
    SELECT DISTINCT ON (employee_id)
        employee_id,
        rating,
        CASE WHEN rating = 5.0 THEN 1 ELSE 0 END AS is_high_performer
    FROM performance_yearly
    WHERE rating BETWEEN 1 AND 5
    ORDER BY employee_id, year DESC
),

-- 3. Dapatkan Skor Kompetensi Terbaru
latest_competencies AS (
    SELECT DISTINCT ON (employee_id, pillar_code)
        employee_id,
        pillar_code,
        score -- ini masih TEXT
    FROM competencies_yearly
    -- === PERBAIKAN 1 DI SINI ===
    -- Filter NULL DAN string kosong
    WHERE score IS NOT NULL AND score != ''
    ORDER BY employee_id, pillar_code, year DESC
),

-- 4. Pivot Skor Kompetensi
pivot_competencies AS (
    SELECT
        employee_id,
        -- === PERBAIKAN 2 DI SINI ===
        -- CAST score dari TEXT ke NUMERIC sebelum di-MAX
        MAX(CASE WHEN pillar_code = 'LIE' THEN CAST(score AS NUMERIC) ELSE NULL END) AS "LIE",
        MAX(CASE WHEN pillar_code = 'SEA' THEN CAST(score AS NUMERIC) ELSE NULL END) AS "SEA",
        MAX(CASE WHEN pillar_code = 'STO' THEN CAST(score AS NUMERIC) ELSE NULL END) AS "STO",
        MAX(CASE WHEN pillar_code = 'GDR' THEN CAST(score AS NUMERIC) ELSE NULL END) AS "GDR"
    FROM latest_competencies
    GROUP BY employee_id
),

-- 5. Pivot Skor PAPI (Asumsi ini sudah numerik, jika error, perbaiki dgn pola yg sama)
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

-- 6. Dapatkan Top 5 Strengths (Tabel Lookup)
top_5_strengths AS (
    SELECT
        employee_id,
        theme
    FROM strengths
    WHERE rank <= 5 AND theme IS NOT NULL
),

-- 7. Rule Engine: Terapkan 9 ATURAN TV ke SEMUA Karyawan (Hasilnya "Wide")
tv_scores_wide AS (
    SELECT
        e.employee_id,
        
        -- TV 1: Leadership - LIE_Skill
        -- Perbandingan ini sekarang aman (NUMERIC >= NUMERIC)
        CASE
            WHEN pc."LIE" >= 2.0 AND pc."SEA" >= 1.8 THEN 1
            ELSE 0
        END AS "tv_lie_skill",
        
        -- TV 2: Leadership - Leadership_Drive
        CASE
            WHEN pp."Papi_L" > 5 AND pp."Papi_A" > 4 THEN 1
            ELSE 0
        END AS "tv_leadership_drive",
        
        -- TV 3: Leadership - Command_Talent
        CASE
            WHEN EXISTS (SELECT 1 FROM top_5_strengths s WHERE s.employee_id = e.employee_id AND s.theme = 'Command') THEN 1
            ELSE 0
        END AS "tv_command_talent",
        
        -- TV 4: Strategic - STO_Skill
        CASE
            WHEN pc."STO" >= 1.8 THEN 1
            ELSE 0
        END AS "tv_sto_skill",
        
        -- TV 5: Strategic - Agility_Profile
        CASE
            WHEN pp."Papi_B" < 5 AND pp."Papi_C" < 6 THEN 1
            ELSE 0
        END AS "tv_agility_profile",
        
        -- TV 6: Strategic - Strategic_Talent
        CASE
            WHEN EXISTS (SELECT 1 FROM top_5_strengths s WHERE s.employee_id = e.employee_id AND s.theme = 'Strategic') THEN 1
            ELSE 0
        END AS "tv_strategic_talent",

        -- TV 7: Drive - Achiever_Talent
        CASE
            WHEN EXISTS (SELECT 1 FROM top_5_strengths s WHERE s.employee_id = e.employee_id AND s.theme = 'Achiever') THEN 1
            ELSE 0
        END AS "tv_achiever_talent",
        
        -- TV 8: Drive - GDR_Skill
        CASE
            WHEN pc."GDR" > 1.0 THEN 1
            ELSE 0
        END AS "tv_gdr_skill",
        
        -- TV 9: Foundation - Context_Filter
        CASE
            WHEN g.name IN ('IV', 'V') AND e.years_of_service_months > 49 THEN 1
            ELSE 0
        END AS "tv_context_filter",

        -- TV 10: Foundation - Cognitive_Filter
        CASE
            WHEN ps.iq > 101 THEN 1
            ELSE 0
        END AS "tv_cognitive_filter"

    FROM employees e
    LEFT JOIN latest_performance lp ON e.employee_id = lp.employee_id
    LEFT JOIN pivot_competencies pc ON e.employee_id = pc.employee_id
    LEFT JOIN pivot_papi pp ON e.employee_id = pp.employee_id
    LEFT JOIN profiles_psych ps ON e.employee_id = ps.employee_id
    LEFT JOIN dim_grades g ON e.grade_id = g.grade_id
    WHERE lp.rating IS NOT NULL
),

-- 8. Unpivot TV Scores (Ubah dari "Wide" ke "Long")
unpivoted_tv_scores AS (
    SELECT employee_id, 'Leadership' AS tgv_name, 'LIE_Skill' AS tv_name, "tv_lie_skill" AS user_score FROM tv_scores_wide
    UNION ALL
    SELECT employee_id, 'Leadership' AS tgv_name, 'Leadership_Drive' AS tv_name, "tv_leadership_drive" FROM tv_scores_wide
    UNION ALL
    SELECT employee_id, 'Leadership' AS tgv_name, 'Command_Talent' AS tv_name, "tv_command_talent" FROM tv_scores_wide
    UNION ALL
    SELECT employee_id, 'Strategic' AS tgv_name, 'STO_Skill' AS tv_name, "tv_sto_skill" FROM tv_scores_wide
    UNION ALL
    SELECT employee_id, 'Strategic' AS tgv_name, 'Agility_Profile' AS tv_name, "tv_agility_profile" FROM tv_scores_wide
    UNION ALL
    SELECT employee_id, 'Strategic' AS tgv_name, 'Strategic_Talent' AS tv_name, "tv_strategic_talent" FROM tv_scores_wide
    UNION ALL
    SELECT employee_id, 'Drive' AS tgv_name, 'Achiever_Talent' AS tv_name, "tv_achiever_talent" FROM tv_scores_wide
    UNION ALL
    SELECT employee_id, 'Drive' AS tgv_name, 'GDR_Skill' AS tv_name, "tv_gdr_skill" FROM tv_scores_wide
    UNION ALL
    SELECT employee_id, 'Foundation' AS tgv_name, 'Context_Filter' AS tv_name, "tv_context_filter" FROM tv_scores_wide
    UNION ALL
    SELECT employee_id, 'Foundation' AS tgv_name, 'Cognitive_Filter' AS tv_name, "tv_cognitive_filter" FROM tv_scores_wide
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

-- 10. Hitung TV Match Rate (Bandingkan semua user dgn baseline)
tv_match_rates AS (
    SELECT
        u.employee_id,
        u.tgv_name,
        u.tv_name,
        b.baseline_score,
        u.user_score,
        CASE
            WHEN u.user_score = b.baseline_score THEN 100.0
            ELSE 0.0
        END AS tv_match_rate
    FROM unpivoted_tv_scores u
    JOIN baseline_scores b ON u.tv_name = b.tv_name
),

-- 11. Hitung TGV Match Rate (Rata-rata TV dalam TGV)
tgv_match_rates AS (
    SELECT
        employee_id,
        tgv_name,
        AVG(tv_match_rate) AS tgv_match_rate
    FROM tv_match_rates
    GROUP BY employee_id, tgv_name
),

-- 12. Hitung Final Match Rate (Rata-rata TGV terbobot)
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

-- 13. Dapatkan Detail Karyawan (untuk output akhir)
employee_details AS (
    SELECT
        e.employee_id,
        dir.name AS directorate,
        pos.name AS role,
        g.name AS grade
    FROM employees e
    LEFT JOIN dim_directorates dir ON e.directorate_id = dir.directorate_id
    LEFT JOIN dim_positions pos ON e.position_id = pos.position_id
    LEFT JOIN dim_grades g ON e.grade_id = g.grade_id
)

-- 14. FINAL SELECT: Gabungkan semua dan format output
SELECT
    t.employee_id,
    d.directorate,
    d.role,
    d.grade,
    t.tgv_name,
    t.tv_name,
    t.baseline_score,
    t.user_score,
    t.tv_match_rate,
    g.tgv_match_rate,
    f.final_match_rate
FROM tv_match_rates AS t
JOIN tgv_match_rates AS g ON t.employee_id = g.employee_id AND t.tgv_name = g.tgv_name
JOIN final_match_rate AS f ON t.employee_id = f.employee_id
JOIN employee_details AS d ON t.employee_id = d.employee_id
-- Urutkan berdasarkan skor akhir tertinggi
ORDER BY
    f.final_match_rate DESC,
    t.employee_id,
    -- Lalu urutkan TGV berdasarkan bobot
    CASE
        WHEN t.tgv_name = 'Leadership' THEN 1
        WHEN t.tgv_name = 'Strategic' THEN 2
        WHEN t.tgv_name = 'Drive' THEN 3
        WHEN t.tgv_name = 'Foundation' THEN 4
    END,
    t.tv_name;