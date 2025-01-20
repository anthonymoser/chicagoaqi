CREATE OR REPLACE TABLE 
  chicago_aqi.suggested_locations(
    id STRING,
    session_id STRING,
    lat FLOAT64,
    long FLOAT64, 
    label STRING,
    reason STRING,
    time_submitted TIMESTAMP
  );

CREATE OR REPLACE TABLE 
    chicago_aqi.email_list(
        session_id STRING,
        suggestion_id STRING,
        email STRING, 
        time_submitted TIMESTAMP 
    );