#!/bin/bash
BASE_URL="http://localhost:5000/api"

curl -X POST $BASE_URL/devices -H "Content-Type: application/json" -d '{"device_id":"phone_001","name":"Phone","owner":"John","device_type":"mobile"}'
curl -X POST $BASE_URL/track -H "Content-Type: application/json" -d '{"device_id":"phone_001","latitude":41.9028,"longitude":12.4964,"accuracy":10.5}'
curl $BASE_URL/devices
