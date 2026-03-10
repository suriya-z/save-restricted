import asyncio
from pyrogram import Client

async def main():
    print("Welcome to the Pyrogram Session Generator.")
    print("You will need your API_ID and API_HASH from https://my.telegram.org/apps")
    print("-" * 50)
    
    api_id_input = input("Enter your API_ID: ").strip()
    api_hash_input = input("Enter your API_HASH: ").strip()
    
    if not api_id_input or not api_hash_input:
        print("API_ID and API_HASH are required!")
        return

    try:
        api_id = int(api_id_input)
    except ValueError:
        print("API_ID must be an integer!")
        return
        
    api_hash = api_hash_input
    
    # Initialize an in-memory client
    app = Client(
        "my_account",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True
    )

    print("\nStarting client...")
    await app.start()
    
    session_string = await app.export_session_string()
    
    print("\n" + "="*50)
    print("SESSION STRING GENERATED SUCCESSFULLY!")
    print("="*50 + "\n")
    print(session_string)
    
    with open("session.txt", "w") as f:
        f.write(session_string)
        
    print("\n" + "="*50)
    print("Saved to session.txt!")
    
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
