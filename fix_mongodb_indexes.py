#!/usr/bin/env python3
"""
Fix MongoDB index conflicts
This script will drop the conflicting telegramId index and let the application recreate it properly
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def fix_indexes():
    """Fix the telegramId index conflict"""
    try:
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME", "guardx_monitor")
        
        if not mongodb_url:
            print("❌ MONGODB_URL not found in environment")
            return False
        
        print(f"🔗 Connecting to MongoDB: {database_name}")
        client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=5000)
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB")
        
        database = client[database_name]
        users_collection = database.users
        
        # List current indexes
        print("\n📋 Current indexes on 'users' collection:")
        indexes = await users_collection.list_indexes().to_list(length=None)
        for idx in indexes:
            print(f"  - {idx['name']}: {idx.get('key', {})}")
        
        # Check if the problematic index exists
        telegramId_indexes = [idx for idx in indexes if 'telegramId' in str(idx.get('key', {}))]
        
        if telegramId_indexes:
            print(f"\n🔍 Found {len(telegramId_indexes)} telegramId index(es)")
            
            for idx in telegramId_indexes:
                index_name = idx['name']
                print(f"\n🗑️  Dropping index: {index_name}")
                try:
                    await users_collection.drop_index(index_name)
                    print(f"✅ Successfully dropped index: {index_name}")
                except Exception as e:
                    print(f"⚠️  Could not drop index {index_name}: {e}")
        else:
            print("\n✅ No conflicting telegramId indexes found")
        
        # Close connection
        client.close()
        print("\n🎉 Index cleanup completed!")
        print("💡 Now restart your application - it will recreate the indexes properly")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing indexes: {e}")
        return False

async def main():
    print("🔧 MongoDB Index Fixer")
    print("=" * 50)
    
    success = await fix_indexes()
    
    if success:
        print("\n✅ All done! Restart your FastAPI application now.")
    else:
        print("\n❌ Failed to fix indexes. Check your MongoDB connection.")

if __name__ == "__main__":
    asyncio.run(main())