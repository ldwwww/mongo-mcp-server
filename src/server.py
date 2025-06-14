import json
import os
import time
from typing import Any, List, Dict, Optional
from mcp.server.fastmcp import FastMCP
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

mcp = FastMCP("mongodb mcp")
ip = os.getenv("MONGO_HOST", "localhost")
port = int(os.getenv("MONGO_PORT", 27017))
RETRY_ATTEMPTS = 3
DELAY_BETWEEN_RETRIES = 5  # seconds
client = None
current_db, current_col = None, None

async def establish_connection():
    """Establish a connection to MongoDB with retry mechanism."""
    global client
    for attempt in range(RETRY_ATTEMPTS):
        try:
            client = AsyncMongoClient(f"mongodb://{ip}:{port}")
            # Test the connection by getting server info
            await client.admin.command('ping')
            return True
        except ConnectionFailure as e:
            if attempt < RETRY_ATTEMPTS - 1:
                print(f"Connection attempt {attempt + 1} failed, retrying in {DELAY_BETWEEN_RETRIES} seconds...")
                time.sleep(DELAY_BETWEEN_RETRIES)
            else:
                print(f"Failed to connect to MongoDB after {RETRY_ATTEMPTS} attempts")
                raise e

async def check_connection():
    """Check if there is an active connection to MongoDB."""
    global client
    if client is None:
        await establish_connection()
    try:
        # Verify the connection is still active
        await client.admin.command('ping')
    except ConnectionFailure:
        # Try to re-establish the connection
        await establish_connection()

@mcp.resource("connection://db_server_info")
async def get_db_connection_info() -> str:
    """
    Get MongoDB connection info
    Returns JSON string containing connection information
    """
    await check_connection()
    return json.dumps(client.topology_description.to_dict())

@mcp.resource("connection://dbs")
async def list_databases() -> List[str]:
    """
    List all the databases
    Returns list of database names
    """
    await check_connection()
    try:
        return await client.list_database_names()
    except PyMongoError as e:
        print(f"Error listing databases: {e}")
        return []

@mcp.resource("connection://cols/{db_name}")
async def list_collections(db_name: str) -> List[str]:
    """
    List all collections from a database
    
    Args:
        db_name: Name of the database
    Returns:
        List of collection names
    """
    global current_db
    await check_connection()
    try:
        current_db = client[db_name]
        if current_db is None:
            raise ValueError(f"Database {db_name} does not exist")
        return await current_db.list_collection_names()
    except PyMongoError as e:
        print(f"Error listing collections for {db_name}: {e}")
        return []

@mcp.tool()
async def get_current_db() -> str:
    """
    Get the currently selected database
    Returns name of the current database or error message
    """
    if current_db is None:
        return "No database selected"  
    return f"current database: {current_db.name}" 

@mcp.tool()
async def get_current_collection() -> str:
    """
    Get the currently selected collection
    Returns name of the current collection or error message
    """
    if current_col is None:
        return "No Collection selected"
    return f"current collection: {current_col.name}"

@mcp.tool()
async def select_database(db_name: str) -> str:
    """
    Select or create a database
    
    Args:
        db_name: Name of the database
    Returns:
        Success message with selected database name
    """
    global current_db
    await check_connection()
    try:
        current_db = client[db_name]
        return f"Successfully selected database, current database: {current_db.name}"
    except PyMongoError as e:
        return f"Error selecting database: {str(e)}"

@mcp.tool()
async def select_collection(col_name: str) -> str:
    """
    Select or create a collection
    
    Args:
        col_name: Name of the collection
    Returns:
        Success message with selected collection name or error message
    """
    if current_db is None:
        return "Please select or create a database first"
    global current_col
    try:
        current_col = current_db[col_name]
        return f"Successfully selected collection, current database: {current_col.name}"
    except PyMongoError as e:
        return f"Error selecting collection: {str(e)}"

@mcp.tool()
async def query_documents(filter: Optional[Dict[str, Any]] = None) -> List[Any]:
    """
    Query documents in a collection
    
    Args:
        filter: A query document that selects which documents to include in the result set.
                if filter is None, query all documents
                if filter is not None, query documents matching the filter
    Returns:
        List of matching documents
    """
    results = []
    try:
        async_cursor = current_col.find(filter)
        async for res in async_cursor:
            results.append(res)
        return results
    except PyMongoError as e:
        print(f"Error querying documents: {e}")
        return []

@mcp.tool()
async def insert_documents(items: List[Dict[str, Any]]) -> str:
    """
    Insert documents into a MongoDB collection
    
    Args:
        items: a list of documents to insert
    Returns:
        Success message with count of inserted documents
    """
    try:
        result = await current_col.insert_many(items)
        return f"Successfully inserted {len(result.inserted_ids)} documents"
    except PyMongoError as e:
        return f"Error inserting documents: {str(e)}"

@mcp.tool()
async def delete_documents(filter: Dict[str, Any]) -> str:
    """
    Delete documents from a collection

    Args: 
        filter: a query that matches the documents to delete
    Returns:
        Success message with count of deleted documents
    """
    try:
        result = await current_col.delete_many(filter)
        return f"Successfully deleted {result.deleted_count} documents"
    except PyMongoError as e:
        return f"Error deleting documents: {str(e)}"

@mcp.tool()
async def update_documents(filter: Dict[str, Any], 
                    update: Dict[str, Dict[str, Any]],
                    upsert: bool = False) -> str: 
    """
    Update one or more documents that match the filter

    Args:
        filter: a query that matches the documents to update
        update: a Dictionary of the update to apply to the filtered documents. e.g.: {'$set': {'field': 'value'}}
        upsert: if True, insert a new document if no documents match the filter
    Returns:
        Success message with count of modified documents
    """
    try:
        results = await current_col.update_many(filter, update, upsert)
        return f"Successfully updated {results.modified_count} documents"
    except PyMongoError as e:
        return f"Error updating documents: {str(e)}"