SELECT 
    pick.time_value AS pick_time,
    a.phase_code AS phase_type,
    pick.waveformID_networkCode AS network,
    pick.waveformID_stationCode AS station,
    pick.waveformID_locationCode AS location,
    pick.waveformID_channelCode AS channel
FROM 
    Event e
JOIN 
    PublicObject poe ON e._oid = poe._oid
JOIN 
    PublicObject po_origin ON e.preferredOriginID = po_origin.publicID
JOIN 
    Origin o ON po_origin._oid = o._oid
JOIN 
    Arrival a ON a._parent_oid = o._oid
JOIN 
    PublicObject po_pick ON a.pickID = po_pick.publicID
JOIN 
    Pick pick ON po_pick._oid = pick._oid
WHERE 
    poe.publicID = '{eventID}'
group by pick.waveformID_stationCode
order by pick.time_value asc

