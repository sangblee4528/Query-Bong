SELECT 
    R.route_nm AS '노선명', 
    S.station_nm AS '정류장명', 
    COUNT(T.trip_id) AS '이용건수'
FROM Trip_Log T
INNER JOIN Route_Master R ON T.route_id = R.route_id
INNER JOIN Station_Master S ON T.geton_station_id = S.station_id
WHERE T.base_date = '20251219'
  AND R.route_nm = '140'
GROUP BY R.route_nm, S.station_nm
