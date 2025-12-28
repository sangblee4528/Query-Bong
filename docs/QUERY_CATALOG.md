# 📊 SQL Query RAG Catalog

시스템에 등록된 SQL 템플릿 목록입니다. (업데이트: 2025-12-25 20:13:51)

## 📈 Summary
- **unitA**: 2개
- **unitC**: 2개

---

### 🔹 노선의 정류장별 승차 건수 (`q_001`)
- **설명**: 특정 버스 노선의 각 정류장별 이용 건수를 집계
- **분류**: unitA (단순 테이블)
- **엔티티**: 없음
- **복잡도**: low
- **수정 가능 파라미터**: `base_date` (partition_key), `route_nm` (filter)

#### [SQL Template]
```sql
SELECT 
        Route_Master.route_nm AS '노선명', 
        Station_Master.station_nm AS '정류장명', 
        COUNT(Trip_Log.trip_id) AS '이용건수'
    FROM Trip_Log
    INNER JOIN Route_Master ON Trip_Log.route_id = Route_Master.route_id
    INNER JOIN Station_Master ON Trip_Log.geton_station_id = Station_Master.station_id
    WHERE Trip_Log.base_date = '20251219'
      AND Route_Master.route_nm = '140'
    GROUP BY Route_Master.route_nm, Station_Master.station_nm
```

---

### 🔹 노선의 승차 로그 (LEFT JOIN 테스트) (`v_unit_test`)
- **설명**: 설명 없음
- **분류**: unitA (단순 테이블)
- **엔티티**: T, R
- **복잡도**: low
- **수정 가능 파라미터**: `base_date` (partition_key)

#### [SQL Template]
```sql
SELECT 
        Trip_Log.trip_id,
        Trip_Log.base_date,
        Route_Master.route_nm
    FROM Trip_Log
    LEFT JOIN Route_Master ON Trip_Log.route_id = Route_Master.route_id
    WHERE Trip_Log.base_date = '20251219'
```

---

### 🔹 example query (`example`)
- **설명**: example_query.sql 파일에서 로드됨
- **분류**: unitC (복합 정보 (R + S + T))
- **엔티티**: R, S, T
- **복잡도**: high
- **수정 가능 파라미터**: `base_date` (partition_key), `route_nm` (filter)

#### [SQL Template]
```sql
SELECT 
    Route_Master.route_nm AS '노선명', 
    Station_Master.station_nm AS '정류장명', 
    COUNT(Trip_Log.trip_id) AS '이용건수'
FROM Trip_Log
INNER JOIN Route_Master ON Trip_Log.route_id = Route_Master.route_id
INNER JOIN Station_Master ON Trip_Log.geton_station_id = Station_Master.station_id
WHERE Trip_Log.base_date = '20251219'
  AND Route_Master.route_nm = '140'
GROUP BY Route_Master.route_nm, Station_Master.station_nm
```

---

### 🔹 노선의 정류장별 승차 건수 (`v_q_001`)
- **설명**: 설명 없음
- **분류**: unitC (복합 정보 (R + S + T))
- **엔티티**: R, S, T
- **복잡도**: high
- **수정 가능 파라미터**: `base_date` (partition_key), `route_nm` (filter)

#### [SQL Template]
```sql
SELECT 
        Route_Master.route_nm AS '노선명', 
        Station_Master.station_nm AS '정류장명', 
        COUNT(Trip_Log.trip_id) AS '이용건수'
    FROM Trip_Log
    INNER JOIN Route_Master ON Trip_Log.route_id = Route_Master.route_id
    INNER JOIN Station_Master ON Trip_Log.geton_station_id = Station_Master.station_id
    WHERE Trip_Log.base_date = '20251219'
      AND Route_Master.route_nm = '140'
    GROUP BY Route_Master.route_nm, Station_Master.station_nm
```

---

