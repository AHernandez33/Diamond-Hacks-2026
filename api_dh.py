# this code is for the api
# all files will be merged with this file as we create the api

# from fastapi import FastAPI, HTTPException, UploadFile, File, Form
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import HTMLResponse
# from pydantic import BaseModel
# from typing import List
# from google import genai
# from main_steps import predict_reaction, image_to_smiles
# import tempfile
# import os 

# app = FastAPI(
#     title = "Anti O-Reaper AI - Specialized AI Tutor for Organic Chemistry",
#     description = "An AI model that will predict and guide you on organic reactions",
#     version = "1.0.0",
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # write the classes 

# class MechanismStepResponse(BaseModel):
#     label: str
#     smiles: str
#     explanation: str

# class PredictRequest(BaseModel):
#     substrates: str
#     reactants: str
#     solvents: str = ""

# class PredictResponse(BaseModel):
#     product_smiles: str
#     reaction_name: str
#     mech_summary: str
#     assumptions: List[str]
#     steps: List[str]
#     confidence: float
#     mechanism_mode_steps: List[MechanismStepResponse]

# @app.get("/health")
# def health():
#     return {"status": "ok", "message": "API is running"}

# @app.get("/", response_class=HTMLResponse)
# def root():
#     return """
# <!DOCTYPE html>
# <html lang="en">
# <head>
# <meta charset="UTF-8"/>
# <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
# <title>Anti O-Reaper AI</title>
# <link href="https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
# <style>
#   *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

#   :root {
#     --bg:       #0a0e14;
#     --surface:  #111720;
#     --border:   #1e2d40;
#     --accent:   #3b9eff;
#     --accent2:  #00e5c0;
#     --text:     #e2eaf4;
#     --muted:    #5a7393;
#     --danger:   #ff5f6d;
#     --success:  #00e5c0;
#   }

#   body {
#     background: var(--bg);
#     color: var(--text);
#     font-family: 'DM Sans', sans-serif;
#     font-weight: 300;
#     min-height: 100vh;
#     display: flex;
#     flex-direction: column;
#     align-items: center;
#     padding: 48px 24px 80px;
#   }

#   body::before {
#     content: '';
#     position: fixed;
#     inset: 0;
#     background-image:
#       linear-gradient(var(--border) 1px, transparent 1px),
#       linear-gradient(90deg, var(--border) 1px, transparent 1px);
#     background-size: 48px 48px;
#     opacity: 0.35;
#     pointer-events: none;
#     z-index: 0;
#   }

#   .wrap {
#     position: relative;
#     z-index: 1;
#     width: 100%;
#     max-width: 980px;
#   }

#   header {
#     margin-bottom: 52px;
#     text-align: center;
#   }

#   .eyebrow {
#     font-family: 'DM Mono', monospace;
#     font-size: 11px;
#     letter-spacing: 0.2em;
#     text-transform: uppercase;
#     color: var(--accent);
#     margin-bottom: 14px;
#   }

#   h1 {
#     font-size: clamp(28px, 5vw, 42px);
#     font-weight: 300;
#     letter-spacing: -0.02em;
#     line-height: 1.15;
#     color: var(--text);
#   }

#   h1 span {
#     color: var(--accent2);
#     font-style: italic;
#   }

#   .subtitle {
#     margin-top: 12px;
#     color: var(--muted);
#     font-size: 14px;
#     letter-spacing: 0.01em;
#   }

#   .card {
#     background: var(--surface);
#     border: 1px solid var(--border);
#     border-radius: 12px;
#     padding: 32px;
#     margin-bottom: 24px;
#   }

#   .card-label {
#     font-family: 'DM Mono', monospace;
#     font-size: 10px;
#     letter-spacing: 0.18em;
#     text-transform: uppercase;
#     color: var(--muted);
#     margin-bottom: 12px;
#   }

#   .input-row {
#     display: flex;
#     gap: 10px;
#     flex-wrap: wrap;
#   }

#   input[type=text] {
#     flex: 1;
#     min-width: 220px;
#     background: var(--bg);
#     border: 1px solid var(--border);
#     border-radius: 8px;
#     padding: 12px 16px;
#     font-family: 'DM Mono', monospace;
#     font-size: 14px;
#     color: var(--text);
#     outline: none;
#     transition: border-color 0.2s;
#   }

#   input[type=text]:focus {
#     border-color: var(--accent);
#   }

#   input[type=text]::placeholder { color: var(--muted); }

#   button {
#     background: var(--accent);
#     color: #fff;
#     border: none;
#     border-radius: 8px;
#     padding: 12px 24px;
#     font-family: 'DM Sans', sans-serif;
#     font-size: 14px;
#     font-weight: 500;
#     cursor: pointer;
#     transition: opacity 0.15s, transform 0.1s;
#     white-space: nowrap;
#   }

#   button:hover { opacity: 0.88; }
#   button:active { transform: scale(0.97); }
#   button:disabled { opacity: 0.4; cursor: not-allowed; }

#   #status {
#     font-family: 'DM Mono', monospace;
#     font-size: 12px;
#     min-height: 20px;
#     color: var(--muted);
#     margin-top: 14px;
#     display: flex;
#     align-items: center;
#     gap: 8px;
#   }

#   .dot {
#     width: 6px; height: 6px;
#     border-radius: 50%;
#     background: var(--accent);
#     animation: pulse 1s ease-in-out infinite;
#   }

#   @keyframes pulse {
#     0%, 100% { opacity: 1; }
#     50% { opacity: 0.2; }
#   }

#   #result {
#     display: none;
#   }

#   .error {
#     color: var(--danger);
#     font-family: 'DM Mono', monospace;
#     font-size: 12px;
#     padding: 12px 16px;
#     border: 1px solid var(--danger);
#     border-radius: 8px;
#     background: rgba(255,95,109,0.06);
#     margin-top: 14px;
#   }

#   pre {
#     white-space: pre-wrap;
#     word-wrap: break-word;
#     background: #0d131c;
#     border: 1px solid var(--border);
#     border-radius: 8px;
#     padding: 16px;
#     margin-top: 12px;
#     color: var(--text);
#     font-family: 'DM Mono', monospace;
#     font-size: 12px;
#   }

#   footer {
#     margin-top: 48px;
#     text-align: center;
#     font-family: 'DM Mono', monospace;
#     font-size: 11px;
#     color: var(--muted);
#     letter-spacing: 0.08em;
#   }
# </style>
# </head>
# <body>
# <div class="wrap">

#   <header>
#     <p class="eyebrow">Organic Chemistry · API UI</p>
#     <h1>Anti O-Reaper AI<br><span>Reaction Predictor</span></h1>
#     <p class="subtitle">Predict products, mechanism steps, and explanations from substrate, reactants, and solvent</p>
#   </header>

#   <div class="card">
#     <p class="card-label">Reaction Input</p>
#     <div class="input-row">
#       <input type="text" id="substrates-input" placeholder="Substrate"/>
#       <input type="text" id="reactants-input" placeholder="Reactants"/>
#       <input type="text" id="solvents-input" placeholder="Solvents"/>
#       <button id="predict-btn" onclick="predictReaction()">Predict</button>
#     </div>
#     <div id="status"></div>
#     <div id="error-box"></div>
#   </div>

#   <div class="card" id="result">
#     <p class="card-label">Prediction Result</p>
#     <pre id="result-json"></pre>
#   </div>

#   <footer>Anti O-Reaper AI · FastAPI frontend</footer>
# </div>

# <script>
#   const statusBox = document.getElementById('status');
#   const resultBox = document.getElementById('result');
#   const resultJson = document.getElementById('result-json');
#   const errorBox = document.getElementById('error-box');
#   const predictBtn = document.getElementById('predict-btn');

#   async function predictReaction() {
#     const substrates = document.getElementById('substrates-input').value.trim();
#     const reactants = document.getElementById('reactants-input').value.trim();
#     const solvents = document.getElementById('solvents-input').value.trim();

#     errorBox.innerHTML = '';
#     resultBox.style.display = 'none';
#     predictBtn.disabled = true;
#     statusBox.innerHTML = '<div class="dot"></div> Predicting reaction...';

#     try {
#       const res = await fetch('/predict', {
#         method: 'POST',
#         headers: { 'Content-Type': 'application/json' },
#         body: JSON.stringify({ substrates, reactants, solvents })
#       });

#       const data = await res.json();

#       if (!res.ok) {
#         errorBox.innerHTML = '<div class="error">Error: ' + (data.detail || 'Unknown error') + '</div>';
#         statusBox.innerHTML = '';
#         predictBtn.disabled = false;
#         return;
#       }

#       resultJson.textContent = JSON.stringify(data, null, 2);
#       resultBox.style.display = 'block';
#       statusBox.innerHTML = '<span style="color: var(--success)">Done</span>';
#     } catch (e) {
#       errorBox.innerHTML = '<div class="error">Network error or backend not running.</div>';
#       statusBox.innerHTML = '';
#     } finally {
#       predictBtn.disabled = false;
#     }
#   }
# </script>
# </body>
# </html>
# """

# @app.post("/predict", response_model = PredictResponse)
# def predict(req: PredictRequest):
#     try:
#         result = predict_reaction(req.substrates, req.reactants, req.solvents)
#         return PredictResponse(
#             product_smiles = result.product_smiles,
#             reaction_name = result.reaction_name,
#             mech_summary = result.mech_summary,
#             assumptions = result.assumptions,
#             steps = result.steps,
#             confidence = result.confindence,
#             mechanism_mode_steps = [
#                 MechanismStepResponse(
#                     label = step.label,
#                     smiles = step.smiles,
#                     explanation = step.explanation,
#                 )
#                 for step in result.mechanism_mode_steps
#             ],
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/predict from image")
# async def predict_from_image(
#     image: UploadFile = File(...),
#     reactants: str = Form(...),
#     solvents: str = Form("")
# ):
#     api_key = os.getenv("GEMINI_API_KEY")
#     if not api_key:
#         raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set")

#     client = genai.Client(api_key=api_key)
#     temp_path = None 
#     try:
#         suffix = os.path.splitext(image.filename)[1] or ".png"
#         with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
#             contents = await image.read()
#             tmp.write(contents)
#             temp_path = tmp.name
        
#         substrates, notes = image_to_smiles(client, temp_path)
#         result = predict_reaction(substrates, reactants, solvents)

#         return {
#             "detected_substrate_smiles": substrates,
#             "image_notes": notes, 
#             "product_smiles_string": result.product_smiles,
#             "reaction_name": result.reaction_name,
#             "mech_summary": result.mech_summary,
#             "assumptions": result.assumptions,
#             "steps": result.steps,
#             "confidence": result.confindence,
#             "mechanism_mode_steps": [
#                 {
#                     "label": step.label,
#                     "smiles_string": step.smiles,
#                     "explanation": step.explanation, 
#                 }
#                 for step in result.mechanism_mode_steps
#             ]
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         if temp_path and os.path.exists(temp_path):
#             os.remove(temp_path)


# will still stick with streamlit - this is extra at this point 

