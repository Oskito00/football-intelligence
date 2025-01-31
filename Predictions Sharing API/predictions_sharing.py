from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from typing import List, Dict, Any
import os
import uvicorn

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/matches")
async def get_matches():
    try:
        # Get the absolute path to the CSV file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, 'match_predictions.csv')
        
        df = pd.read_csv(csv_path)
        matches = df.to_dict('records')
        return {
            "status": "success",
            "data": matches
        }
    except Exception as e:
        print(f"Error: {str(e)}")  # For debugging
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    LOCAL_IP = "192.168.0.33"  # Your private IP
    PORT = 8080  # Changed to 8080
    
    print(f"Starting server on {LOCAL_IP}:{PORT}")
    print(f"API will be available at: http://{LOCAL_IP}:{PORT}/api/matches")
    uvicorn.run(app, host=LOCAL_IP, port=PORT)