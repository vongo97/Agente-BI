from dotenv import load_dotenv
load_dotenv()
from src.database import SessionLocal, Simulation, SimulationMessage
db = SessionLocal()
sim = db.query(Simulation).filter(Simulation.id == 11).first()
if sim:
    print(f"Status: {sim.status}")
    print(f"Report: {sim.result_report}")
    messages = db.query(SimulationMessage).filter(SimulationMessage.simulation_id == 11).all()
    print(f"Messages count: {len(messages)}")
else:
    print("Simulation not found")
db.close()
