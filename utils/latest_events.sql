SELECT 
POEv.publicID AS 'ID',
DATE_FORMAT(Origin.time_value, '%Y/%m/%d %H:%i:%S') AS 'orig_time', 
Origin.latitude_value AS lat,
Origin.longitude_value AS lon,
ROUND(Origin.depth_value)  AS z,
ROUND(Magnitude.magnitude_value, 1) AS mag,
Origin.creationInfo_author as 'author',
Origin.quality_usedStationCount as 'stationcount',
Origin.quality_usedPhaseCount as 'phasecount',
Origin.latitude_uncertainty as 'lat_e',
Origin.longitude_uncertainty as 'lon_e',
Origin.depth_uncertainty as 'z_e',
Origin.time_uncertainty as 't_e',
Origin.quality_minimumDistance as 'min_dis',
convert(cast(convert(EventDescription.text using latin1) as binary) using utf8) AS 'region'
FROM  
Event AS EvMF left join PublicObject AS POEv ON EvMF._oid = POEv._oid
left join PublicObject as POOri ON EvMF.preferredOriginID=POOri.publicID 
left join Origin ON POOri._oid=Origin._oid
left join PublicObject as POMag on EvMF.preferredMagnitudeID=POMag.publicID  
left join Magnitude ON Magnitude._oid = POMag._oid 
left join EventDescription ON EvMF._oid=EventDescription._parent_oid  
WHERE  
Origin.time_value BETWEEN "{ti}" AND "{tf}"
#AND Origin.latitude_value BETWEEN -5.5 AND 16.5 AND Origin.longitude_value BETWEEN -86.5 AND -66.7
AND EvMF.type like 'earthquake'
# =====================================================
# localizables (descomentar/comentar la siguiente línea para solo localizables/no localizables
# =====================================================
#AND (EvMF.type like 'earthquake' or EvMF.type is null or EvMF.type like 'volcanic eruption'or AreaOfInfluence.area is not null) AND Magnitude.magnitude_value IS NOT null AND Origin.latitude_uncertainty IS NOT NULL AND Origin.longitude_uncertainty IS NOT NULL AND Origin.quality_azimuthalGap IS NOT NULL
# =====================================================
# no localizables
# =====================================================
#and (EvMF.type like 'not locatable' or EvMF.type like 'explosion' or EvMF.type like 'earthquake' or EvMF.type is null or EvMF.type like 'volcanic eruption' or AreaOfInfluence.area is not null) 

ORDER BY Origin.time_value