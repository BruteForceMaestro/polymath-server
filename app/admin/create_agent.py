import argparse
from sqlmodel import Session, select
from app.db import engine, init_dbs
from app.models.auth import Agent, Role
from app.models.node_work import NodePatch, NodeComment
from app.models.graph import VerificationLevel
from app.services.auth import generate_api_key, hash_api_key

def create_agent(name: str, role_name: str = "admin"):
    init_dbs()
    
    with Session(engine) as session:
        # Check if role exists
        statement = select(Role).where(Role.name == role_name)
        role = session.exec(statement).first()
        
        if not role:
            print(f"Creating role: {role_name}")
            role = Role(name=role_name, highest_verification_allowed=VerificationLevel.VERIFIED)
            session.add(role)
            session.commit()
            session.refresh(role)
        
        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)
        
        new_agent = Agent(name=name, api_key_hash=api_key_hash, role_id=role.id)
        session.add(new_agent)
        session.commit()
        session.refresh(new_agent)
        
        print(f"Agent '{name}' created successfully!")
        print(f"API Key: {api_key}")
        print("IMPORTANT: Save this key, it will not be shown again.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new Polymath agent.")
    parser.add_argument("--name", required=True, help="Name of the agent")
    parser.add_argument("--role", default="admin", help="Role of the agent (default: admin)")
    
    args = parser.parse_args()
    create_agent(args.name, args.role)