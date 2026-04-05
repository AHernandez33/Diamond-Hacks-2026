# design step 1 - this is the full code
# step 1 is the streamlit uploader where it requries the user to input two or more reactants and solvents to predict the material
# and give an expalanation in to which why the reaction happens 
# also prompt gemini to upload a photo and then use to detect image generation 
# any molecule input will be converted to smiles strings

from google import genai
from pydantic import BaseModel, Field
from typing import List
import os
import mimetypes
from google.genai import types
from rdkit import Chem
from rdkit.Chem import AllChem
import py3Dmol


class MechanismStep(BaseModel):
    label: str = Field(description="Name of the reaction step")
    smiles: str = Field(description="Main molecule in this step formatted as a SMILES string")
    explanation: str = Field(description="What happens in this step")


class ReactionResult(BaseModel):
    product_smiles: str = Field(description="Predicted product formatted as a SMILES string")
    reaction_name: str = Field(description="Best guess for the reaction type")
    mech_summary: str = Field(description="Explanation of the reaction")
    assumptions: List[str] = Field(description="Assumptions made due to several factors such as temperature, catalyst, equivalent components, etc.")
    steps: List[str] = Field(description="Steps of reasonings")
    confindence: float = Field(description="Confidence from 0.0 to 1.0")
    mechanism_mode_steps: List[MechanismStep] = Field(description="Step-by-step molecular states for each step")
    major: str = Field(description="Name and description of the major product in the reaction")
    product_win: str = Field(description="Why is this product favored than the rest of the products")
    missing_conditions: List[str] = Field(description="Important missing reaction conditions that could have affected the output of the reaction")
    stereochem: str = Field(description="Notes about stereochemistry and/or stereoselectivity")
class ImageToSMILESresult(BaseModel):
    smiles_string: str = Field(description="SMILES string extracted")
    notes: str = Field(description="Short note about image quality and/or uncertainty")


ReactionResult.model_rebuild()


def image_to_smiles(client, image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/png"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            "Look at this image of a chemical structure and return the molecule as a valid SMILES string. If the structure is unclear, make your best effort and explain the uncertainty simply.",
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config={
            "response_mime_type": "application/json",
            "response_json_schema": ImageToSMILESresult.model_json_schema(),
        },
    )

    result = ImageToSMILESresult.model_validate_json(response.text)
    return result.smiles_string, result.notes


def get_substrate_input(client):
    choice = input(
        "\nChoose substrate input type:\n"
        "1 = type the chemical name\n"
        "2 = attach an image\n"
        "Enter 1 or 2: "
    ).strip()

    if choice == "2":
        image_path = input("Enter the full path to the structure image: ").strip().strip('"')
        substrates, notes = image_to_smiles(client, image_path)
        print("\nDetected substrate SMILES:", substrates)
        print("Notes (if applicable):", notes)
        return substrates

    substrates = input("Enter substrate as a name: ").strip()
    return substrates


def smiles_to_3d(smiles_string, name="molecule"):
    mol = Chem.MolFromSmiles(smiles_string)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: {smiles_string}")

    mol = Chem.AddHs(mol)
    status = AllChem.EmbedMolecule(mol, randomSeed=42)
    if status != 0:
        raise RuntimeError(f"Embedding failed for {smiles_string}")

    if AllChem.UFFHasAllMoleculeParams(mol):
        AllChem.UFFOptimizeMolecule(mol)

    mol.SetProp("_Name", name)
    return mol


def mol_to_block(smiles_string, name="molecule"):
    mol = smiles_to_3d(smiles_string, name)
    return Chem.MolToMolBlock(mol)


def save_mechanism_steps(mechanism_steps):
    for i, step in enumerate(mechanism_steps, start=1):
        mol = smiles_to_3d(step.smiles, step.label)
        writer = Chem.SDWriter(f"mechanism_step_{i}.sdf")
        writer.write(mol)
        writer.close()


def show_3d_step(smiles_string, label="Step"):
    mol_block = mol_to_block(smiles_string, label)
    viewer = py3Dmol.view(width=750, height=450)
    viewer.addModel(mol_block, "mol")
    viewer.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
    viewer.setBackgroundColor("black")
    viewer.zoomTo()
    return viewer

# validate SMILES strings
def validate_smiles(smiles_string):
    mol = Chem.MolFromSmiles(smiles_string)
    return mol is not None

def canonicalize_smiles(smiles_string):
    mol = Chem.MolFromSmiles(smiles_string)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)

def validate_and_canonicalize_prod(smiles_string):
    mol = Chem.MolFromSmiles(smiles_string)
    if mol is None:
        raise ValueError(f"Invalid product predicted from SMILES: {smiles_string}")

    try:
        Chem.SanitizeMol(mol)
    except Exception as e:
        raise ValueError(f"Predicted product SMILES failed santitization: {smiles_stirng}. Error: {e}")
    
    return Chem.MolToSmiles(mol, canonical=True)


def predict_reaction(substrates, reactants, solvents):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. In PowerShell run: $env:GEMINI_API_KEY='your_key_here'")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are helping with organic reaction prediction.

Input:
- Substrate SMILES: {substrates}
- Reactants: {reactants}
- Solvents: {solvents}

Task:
1) Predict the most probable product or products
2) Return the product as a valid SMILES string
3) Name the likely reaction if possible
4) Explain the reasoning in the simplest terms as possible in organic chemistry
5) If key conditions are missing, state the assumption or assumptions
6) If uncertain, say so instead of pretending certainty
7) Return a field called mechanism_mode_steps
8) Include and comment on stereochemistry/stereoselectivity if revelant
9) If more than one product is the output, label the major product and detailed but brief explain why this product is more favored than other plausible products
10) State the missing conditions that could have changed the result

For the mechanism_mode_steps:
1) Include the starting material as the first step
2) Include the final product as the last step
3) Include 1-5 important intermediate molecular states if plausible
4) Each step must contain:
   - label
   - smiles
   - explanation
5) Use valid SMILES strings
6) If intermediates are uncertain, keep the list short


IMPORTANT:
Use only reliable information that is consistent with trusted scientific journals such as:
- PubChem
- NIST Chemistry WebBook
- ACS publications
- Royal Society of Chemistry 
- Organic Chemistry Portal
- ChemLibreTexts

! Do NOT reply on unsupported claims. If the informations is uncertain or not directly supported, say so 

IMPORTANT:
- Prefer chemically plausible outputs
- Do NOT invent impossible valence states
- Focus on the major product only
- Distinguish between the major and competing products
- Mention stereochemical consequences if revelant
"""

    tutor_prompt = f"""
    You are a Socratic Tutor for organic chemistry.

Your job is to teach by asking questions before revealing answers.

Reaction input:
- Substrate: {substrates}
- Reactants: {reactants}
- Solvents: {solvents}

Rules:
1. Do not reveal the final product immediately.
2. Start by asking one guiding question.
3. Questions should help the student reason through the mechanism.
4. Good example questions:
   - Where is the electrophilic center?
   - Where would the nucleophile attack first?
   - Is substitution or elimination more likely here?
   - What role does the solvent play?
   - Would stereochemistry matter in this step?
5. If the student gives a partially correct answer, acknowledge what is correct and guide them further.
6. If the student gives an incorrect answer, do not just say "wrong". Give a hint and ask a simpler follow-up question.
7. Be encouraging, concise, and educational.
8. Only reveal the final answer when:
   - the student asks for it, or
   - enough guided questions have been completed.
9. When you finally reveal the answer, provide:
   - major product
   - reaction name
   - why this product wins
   - stereochemistry notes
   - missing conditions
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": ReactionResult.model_json_schema(),
        },
    )

    result = ReactionResult.model_validate_json(response.text)
    return result


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. In PowerShell run: $env:GEMINI_API_KEY='your_key_here'")

    client = genai.Client(api_key=api_key)

    while True:
        substrates = get_substrate_input(client)
        reactants = input("Enter a reactant(s): ").strip()
        solvents = input("Enter a solvent(s): ").strip()

        result = predict_reaction(substrates, reactants, solvents)
        result_product_smiles = result.product_smiles

        print("\nMechanism Mode:")
        for i, step in enumerate(result.mechanism_mode_steps, start=1):
            print(f"\nStep {i}: {step.label}")
            print("SMILES:", step.smiles)
            print("Explanation:", step.explanation)

        save_mechanism_steps(result.mechanism_mode_steps)

        print("\nPredicted product:", result_product_smiles)
        print("Reaction:", result.reaction_name)
        print("Mechanism:", result.mech_summary)
        print("Steps:")
        for step in result.steps:
            print(" ", step)
        print("Assumptions:")
        for a in result.assumptions:
            print(" ", a)
        print("Confidence:", result.confindence)

        again = input("\nRun another reaction? (y/n): ").strip().lower()
        if again != "y":
            break


if __name__ == "__main__":
    main()

# add the image recongintion as an option for people to post their structures
# convert these to smiles strings (done above)


# now do the 3d visualization during reactions
# will comprise of showing an interactive visualization of how the reaction works depending on what the user's input 

# this is done via streamlit, which is moved to the new file dh_streamlit.py
