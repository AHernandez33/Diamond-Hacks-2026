# Now using streamlit for front-end development 
# this enables the user to access to an interactive visualization of molecular 3D reactions based on what was input in terms of organic chemical reactions 

import streamlit as st
import streamlit.components.v1 as components
import py3Dmol
from rdkit import Chem 
from rdkit.Chem import AllChem
from main_steps import predict_reaction


# set the titles - also apply to the API (flask and current streamlit right now)
st.set_page_config(page_title="Anti O-Reaper AI - Specialized AI Tutor for Organic Chemistry", layout="wide")
st.title("Anti O-Reaper AI - Specialized AI Tutor for Organic Chemistry")
st.write("This AI will help you teach reactions and the reasoning behind it, as well as molecular visualization")

def smiles_to_3d(smiles_string, name="molecule"):
    mol = Chem.MolFromSmiles(smiles_string)
    if mol is None:
        raise ValueError(f"INVALID: {smiles_string}")

    mol = Chem.AddHs(mol)
    status = AllChem.EmbedMolecule(mol, randomSeed=42)
    if status != 0:
        raise RuntimeError(f"Embedding failed for {smiles_string}")
    
    if AllChem.UFFHasAllMoleculeParams(mol):
        AllChem.UFFOptimizeMolecule(mol)
    
    mol.SetProp("_Name", name)
    return mol 

# now define rendering the molecule 
def render_molecule_3d(smiles_string, label="Molecule", height=450):
    mol = smiles_to_3d(smiles_string, label)
    mol_block = Chem.MolToMolBlock(mol)

    viewer = py3Dmol.view(width=750, height=height)
    viewer.addModel(mol_block, "mol")
    viewer.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
    viewer.setBackgroundColor("black")
    viewer.zoomTo()

    components.html(viewer._make_html(), height=height, scrolling=False)


# photo upload (binds in with the 1/2 option in the main_steps.py file)
# upload = st.file_uploader("Upload a molecule image", type = ["png", "jpg", "pdf", "jpeg"])

# more import 
from main_steps import predict_reaction, image_to_smiles
from google import genai
import tempfile
import os

def tutor_chat(messages, substrates, reactants, solvents):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. In PowerShell run: $env:GEMINI_API_KEY='your_key_here'")

    client = genai.Client(api_key=api_key)

    tutor_system_prompt = f"""
You are a Socratic Tutor for organic chemistry.

Reaction input:
- Substrate: {substrates}
- Reactants: {reactants}
- Solvents: {solvents}

Rules:
1. Do not reveal the final product immediately.
2. Start by asking one guiding question.
3. Ask only one focused question at a time.
4. Good question types include:
   - Where is the electrophilic center?
   - Where would the nucleophile attack first?
   - Is substitution or elimination more likely?
   - What role does the solvent play?
   - Would stereochemistry matter?
5. If the student is partly correct, affirm the correct part and guide them further.
6. If the student is incorrect, do not simply say wrong. Give a hint and ask a simpler follow-up question.
7. Be encouraging, clear, and concise.
8. Only reveal the final answer if:
   - the student asks for it, or
   - enough guided questions have been completed.
9. When revealing the answer, include:
   - major product
   - reaction name
   - why this product wins
   - stereochemistry notes
   - missing conditions
"""

    contents = tutor_system_prompt + "\n\nConversation:\n"
    for msg in messages:
        contents += f"{msg['role'].upper()}: {msg['content']}\n"

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=contents,
    )

    return response.text

tab1, tab2 = st.tabs(["Prediction Mode", "Tutor Mode"])

with tab1:
    # input 1 or 2
    input_type = st.radio(
        "Choose an option: ", 
        ["1", "2"],
        format_func=lambda x: "1 - Manually input chemical name" if x == "1" else "2 - Attach an image",
        key="prediction_input_type"
    )

    if input_type == "1":
        substrates = st.text_input("Substrate")
        uploaded_file = None

    else:
        uploaded_file = st.file_uploader("Upload a molecule image", type = ["png", "jpg", "pdf", "jpeg"])
        substrates = ""

    reactants = st.text_input("Reactants")
    solvents = st.text_input("Solvents")
    # # back to the input 
    # substrates = st.text_input("Substrate")
    # reactants = st.text_input("Reactants")
    # solvents = st.text_input("Solvents")


    if "step_index" not in st.session_state:
        st.session_state["step_index"] = 0

    if st.button("Predict Reaction"):
        try:
            final_substrate = substrates    
            if input_type == "2":
                if uploaded_file is None:
                    st.error("Upload an image first")
                    st.stop()

                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY is not set. In PowerShell run: $env:GEMINI_API_KEY='your_key_here'")
                client = genai.Client(api_key=api_key)

                suffix = os.path.splitext(uploaded_file.name)[1] or ".png"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    temp_path = tmp.name

                detected_smiles, notes = image_to_smiles(client, temp_path)
                final_substrate = detected_smiles

                st.session_state["detected_smiles"] = detected_smiles
                st.session_state["image_notes"] = notes
                os.remove(temp_path)

            result = predict_reaction(final_substrate, reactants, solvents)
            st.session_state["result"] = result
            st.session_state["step_index"] = 0

        except Exception as e:
            st.error(f"Prediction failed: {e}")

            
    if "result" in st.session_state:
        result = st.session_state["result"]

        if "detected_smiles" in st.session_state:
            st.write(f"Detected substrate SMILES: {st.session_state['detected_smiles']}")

        if "image_notes" in st.session_state:
            st.write(f"Image notes: {st.session_state['image_notes']}")

        # write and add the subheader 
        st.subheader(result.reaction_name)
        st.write(result.mech_summary)
        st.write(f"Predicted product formatted in SMILES:  {result.product_smiles} ")
        st.write(f"Confidence value: {result.confindence} ")

        if hasattr(result, "major_product"):
            st.write(f"Major product: {result.major_product}")

        if hasattr(result, "why_this_product_wins"):
            st.markdown("**Why this product wins**")
            st.write(result.why_this_product_wins)

        if hasattr(result, "stereochem"):
            st.markdown("**Stereochemistry**")
            st.write(result.stereochem)

        if hasattr(result, "missing_conditions") and result.missing_conditions:
            st.markdown("**Missing Conditions**")
            for item in result.missing_conditions:
                st.write(f"- {item}")

        # if block on assumptions 
        if result.assumptions:
            st.markdown("**Assumptions**")
            for a in result.assumptions:
                st.write(f"- {a}")

        steps = result.mechanism_mode_steps
        if steps:
            st.markdown("### Mechanism Visualization")

            # index and slider
            idx = st.slider(
                "Choose mechanism step", 
                min_value = 0,
                max_value = len(steps) - 1,
                value = st.session_state["step_index"]
            )
            st.session_state["step_index"] = idx
            step =  steps[idx]

            st.markdown("### Mechanism Flow")
            flow_html = ""
            for i, s in enumerate(steps):
                if i == idx:
                    flow_html += f"<span style='color:#ff4b4b; font-weight:bold;'>{i+1}. {s.label}</span>"
                else:
                    flow_html += f"<span style='color:#cccccc;'>{i+1}. {s.label}</span>"

                if i < len(steps) - 1:
                    flow_html += " <span style='font-size:22px; color:#ff4b4b; '>→</span> "

            st.markdown(flow_html, unsafe_allow_html=True)

            col1, col2 = st.columns([2, 1])
            
            # col 1
            with col1:
                st.markdown(f"### Step {idx + 1}: {step.label}")
                try:
                    render_molecule_3d(step.smiles, step.label)
                except Exception as e:
                    st.error(f"Could not render 3D structure: {e}")
            
            # col 2
            with col2: 
                st.markdown("### Explanation")
                st.write(step.explanation)
                st.code(step.smiles, language="text")
                prev_col, next_col = st.columns(2)

                # prev and next cols
                with prev_col:
                    if st.button("Previous", disabled=(idx == 0)):
                        st.session_state["step_index"] = idx - 1
                        st.rerun()

                with next_col:
                    if st.button("Next", disabled=(idx == len(steps) - 1)):
                        st.session_state["step_index"] = idx + 1
                        st.rerun()
            
            st.markdown("### Mechanism Process")
            for i, s in enumerate(steps, start=1):
                if i - 1 == idx:
                    st.markdown(f"<div style='padding:10px; border:2px solid #ff4b4b; border-radius:10px; margin-bottom:10px;'><b>Step {i}: {s.label}</b></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='padding:10px; border:1px solid #666; border-radius:10px; margin-bottom:10px;'>Step {i}: {s.label}</div>", unsafe_allow_html=True)

                if i < len(steps):
                    st.markdown("<div style='text-align:center; font-size:26px; color:#ff4b4b;'>↓</div>", unsafe_allow_html=True)
        else:
            st.warning("No mechanism steps were provided, returned, or were available")

with tab2:
    st.markdown("### Socratic Tutor Mode")
    st.write("The tutor will ask guiding questions before revealing the answer.")

    tutor_input_type = st.radio(
        "Choose an option for tutor mode: ",
        ["1", "2"],
        format_func=lambda x: "1 - Manually input chemical name" if x == "1" else "2 - Attach an image",
        key="tutor_input_type"
    )

    if tutor_input_type == "1":
        tutor_substrates = st.text_input("Tutor Substrate", key="tutor_substrate")
        tutor_uploaded_file = None
    else:
        tutor_uploaded_file = st.file_uploader("Upload a tutor molecule image", type=["png", "jpg", "pdf", "jpeg"], key="tutor_upload")
        tutor_substrates = ""

    tutor_reactants = st.text_input("Tutor Reactants", key="tutor_reactants")
    tutor_solvents = st.text_input("Tutor Solvents", key="tutor_solvents")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    if st.button("Start Tutor Mode"):
        try:
            final_tutor_substrate = tutor_substrates

            if tutor_input_type == "2":
                if tutor_uploaded_file is None:
                    st.error("Upload an image first")
                    st.stop()

                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY is not set. In PowerShell run: $env:GEMINI_API_KEY='your_key_here'")
                client = genai.Client(api_key=api_key)

                suffix = os.path.splitext(tutor_uploaded_file.name)[1] or ".png"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(tutor_uploaded_file.getvalue())
                    temp_path = tmp.name

                detected_smiles, notes = image_to_smiles(client, temp_path)
                final_tutor_substrate = detected_smiles
                st.session_state["tutor_detected_smiles"] = detected_smiles
                st.session_state["tutor_image_notes"] = notes
                os.remove(temp_path)

            st.session_state["chat_history"] = []
            st.session_state["tutor_substrate_value"] = final_tutor_substrate

            first_reply = tutor_chat(
                st.session_state["chat_history"],
                final_tutor_substrate,
                tutor_reactants,
                tutor_solvents
            )
            st.session_state["chat_history"].append({"role": "assistant", "content": first_reply})
            st.rerun()

        except Exception as e:
            st.error(f"Tutor mode failed: {e}")

    if "tutor_detected_smiles" in st.session_state:
        st.write(f"Detected tutor substrate SMILES: {st.session_state['tutor_detected_smiles']}")

    if "tutor_image_notes" in st.session_state:
        st.write(f"Tutor image notes: {st.session_state['tutor_image_notes']}")

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_message = st.chat_input("Answer the tutor's question...")
    if user_message:
        st.session_state["chat_history"].append({"role": "user", "content": user_message})

        try:
            tutor_reply = tutor_chat(
                st.session_state["chat_history"],
                st.session_state.get("tutor_substrate_value", ""),
                st.session_state.get("tutor_reactants", ""),
                st.session_state.get("tutor_solvents", "")
            )
            st.session_state["chat_history"].append({"role": "assistant", "content": tutor_reply})
            st.rerun()
        except Exception as e:
            error_text = str(e)
            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                st.error("Gemini quota limit reached. Wait a bit and try again, or switch to a different API key/project/model.")
            else:
                st.error(f"Tutor reply failed: {e}")

# attach this to the terminal
# $env:GEMINI_API_KEY="your_real_api_key_here"
# py -m streamlit run dh_streamlit.py
