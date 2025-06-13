import json
import os
from typing import Callable, Any, List, Dict
from mcp.server.fastmcp import FastMCP
from pymongo import AsyncMongoClient

mcp = FastMCP("mongodb mcp")
ip = os.getenv("MONGO_HOST", "localhost")
port = int(os.getenv("MONGO_PORT", 27017))
client = AsyncMongoClient(f"mongodb://{ip}:{port}")
current_db, current_col = None, None

def check_connection():
    if client is None:
        raise ConnectionError("No connection to MongoDB")

@mcp.resource("connection://db_server_info")
def get_db_connection_info() -> str:
    """Get MongoDB connection info"""
    check_connection()
    return json.dumps(client.topology_description.to_dict())

@mcp.resource("connection://dbs")
def list_databases() -> List[str]:
    """List all the databases"""
    check_connection()
    return client.List_database_names()

@mcp.resource("connection://cols/{db_name}")
def list_collections(db_name: str) -> List[str]:
    """List all collections from a database"""
    check_connection()
    current_db = client[db_name]
    if current_db is None:
        raise ValueError(f"Database {db_name} does not exist")
    return current_db.list_collection_names()

@mcp.tool()
def get_currrent_db() -> str:
    """Get the currently selected database"""
    if current_db is None:
        return "No database selected"  
    return f"current database: {current_db.name}" 

@mcp.tool()
def get_current_collection() -> str:
    """Get the currently selected collection"""
    if current_col is None:
        return "No Collection selected"
    return f"current collection: {current_col.name}"

@mcp.tool()
def select_database(db_name: str) -> str:
    """Select or create a database"""
    check_connection()
    current_db = client[db_name]
    return f"database {db_name} selected"

@mcp.tool()
def select_collection(col_name: str) -> str:
    """select or create a collection"""
    if current_db is None:
        return "Please select or create a database first"
    current_col = current_db[col_name]
    return f"collection {col_name} selected"   

@mcp.tool()
async def query_documents(filter: None | Dict[str, Any]) -> List[Any]:
    """query documents in the existing collecton
        if search all the documents, please set doc to None
        if search limited documents containing specific fields
        please set doc to a Dict"""
    results = []
    async_cursor = current_col.find(filter)
    async for res in async_cursor:
        results.append(res)
    return results

@mcp.tool()
async def insert_documents(items: List[Dict[str, Any]]) -> str:
    """Insert documents into MongoDB"""
    """item: a List of documents to insert into MongoDB"""
    await current_col.insert_many(items)
    return "Successfully inserted {} documents".format(len(items))

@mcp.tool()
async def update_documents(filter: Dict[str, Any], 
                    update: Dict[str, Dict[str, Any]],
                    upsert: bool = False) -> str: 
    """Update one or more documents that match the filter
    update: a Dictionary of the update to apply to the filtered documents
    upsert: if True, insert a new document if no documents match the filter
    """
    results = await current_col.update_many(filter, update, upsert)
    return f"Sucesefully updated {results.modofied_count} documents"