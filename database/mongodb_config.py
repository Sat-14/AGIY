"""
MongoDB Configuration and Connection Management
Handles database connections, collections, and schema definitions
"""

import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MongoDBManager:
    """Manages MongoDB connections and operations"""

    def __init__(self, connection_string=None):
        """
        Initialize MongoDB connection

        Args:
            connection_string: MongoDB URI (defaults to env variable MONGODB_URI)
        """
        self.connection_string = connection_string or os.getenv(
            'MONGODB_URI',
            'mongodb://localhost:27017/'
        )
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client['sales_agent_db']
            logger.info("Successfully connected to MongoDB")
            self._create_indexes()
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # User profiles collection
            self.db.user_profiles.create_index([("user_id", ASCENDING)], unique=True)

            # Conversation history collection
            self.db.conversations.create_index([("user_id", ASCENDING)])
            self.db.conversations.create_index([("timestamp", DESCENDING)])
            self.db.conversations.create_index([("session_id", ASCENDING)])

            # Inventory collection
            self.db.inventory.create_index([("product_id", ASCENDING)], unique=True)
            self.db.inventory.create_index([("category", ASCENDING)])

            # Orders collection
            self.db.orders.create_index([("order_id", ASCENDING)], unique=True)
            self.db.orders.create_index([("user_id", ASCENDING)])
            self.db.orders.create_index([("status", ASCENDING)])
            self.db.orders.create_index([("created_at", DESCENDING)])

            # Transactions collection
            self.db.transactions.create_index([("transaction_id", ASCENDING)], unique=True)
            self.db.transactions.create_index([("user_id", ASCENDING)])
            self.db.transactions.create_index([("status", ASCENDING)])
            self.db.transactions.create_index([("created_at", DESCENDING)])

            # Reservations collection
            self.db.reservations.create_index([("reservation_id", ASCENDING)], unique=True)
            self.db.reservations.create_index([("user_id", ASCENDING)])
            self.db.reservations.create_index([("expires_at", ASCENDING)])

            # Product recommendations cache
            self.db.recommendations_cache.create_index([
                ("user_id", ASCENDING),
                ("context", ASCENDING)
            ])
            self.db.recommendations_cache.create_index(
                [("created_at", DESCENDING)],
                expireAfterSeconds=3600  # TTL index: expire after 1 hour
            )

            logger.info("Database indexes created successfully")
        except OperationFailure as e:
            logger.error(f"Error creating indexes: {e}")

    def get_collection(self, collection_name):
        """Get a specific collection"""
        return self.db[collection_name]

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


# Collection schemas (for documentation purposes)
SCHEMAS = {
    "user_profiles": {
        "user_id": "string (unique)",
        "preferences": ["string"],
        "size": "string",
        "purchase_history": ["string"],
        "browsing_history": ["string"],
        "loyalty_tier": "string",
        "loyalty_points": "number",
        "created_at": "datetime",
        "updated_at": "datetime"
    },

    "conversations": {
        "session_id": "string",
        "user_id": "string",
        "messages": [
            {
                "role": "string (human|ai)",
                "content": "string",
                "timestamp": "datetime",
                "metadata": "object"
            }
        ],
        "timestamp": "datetime",
        "active": "boolean"
    },

    "inventory": {
        "product_id": "string (unique)",
        "name": "string",
        "category": "string",
        "price": "number",
        "currency": "string",
        "tags": ["string"],
        "warehouses": [
            {
                "warehouse_id": "string",
                "stock_level": "number",
                "location": "string"
            }
        ],
        "stores": [
            {
                "store_id": "string",
                "stock_level": "number",
                "city": "string",
                "region": "string"
            }
        ],
        "last_updated": "datetime"
    },

    "orders": {
        "order_id": "string (unique)",
        "user_id": "string",
        "items": [
            {
                "product_id": "string",
                "quantity": "number",
                "price": "number"
            }
        ],
        "total_amount": "number",
        "currency": "string",
        "status": "string",
        "tracking_number": "string",
        "estimated_delivery": "datetime",
        "created_at": "datetime",
        "updated_at": "datetime"
    },

    "transactions": {
        "transaction_id": "string (unique)",
        "user_id": "string",
        "cart_id": "string",
        "amount": "number",
        "currency": "string",
        "status": "string (initiated|processing|completed|failed)",
        "payment_method": "string",
        "gateway_response": "object",
        "created_at": "datetime",
        "updated_at": "datetime"
    },

    "reservations": {
        "reservation_id": "string (unique)",
        "user_id": "string",
        "product_id": "string",
        "store_id": "string",
        "status": "string (active|expired|fulfilled|cancelled)",
        "created_at": "datetime",
        "expires_at": "datetime"
    },

    "recommendations_cache": {
        "user_id": "string",
        "context": "string",
        "recommendations": "array",
        "created_at": "datetime"
    }
}


# Singleton instance
_db_manager = None

def get_db_manager():
    """Get or create MongoDB manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = MongoDBManager()
    return _db_manager
