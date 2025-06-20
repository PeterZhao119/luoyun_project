from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import time
import uuid
import datetime
from contextlib import contextmanager

from conf.config import CONF

class MongoDBLockManager:
    def __init__(self, mongo_uri: str = "mongodb://" + CONF["mongodb"]["mongodb_ip"] + ":" + CONF["mongodb"]["mongodb_port"] + "/", 
                 db_name: str = CONF["mongodb"]["mongodb_name"], lock_collection_name="locks"):
        """Initialize the lock manager with MongoDB connection details."""
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.locks = self.db[lock_collection_name]
        
        # Create unique index on resource_id to ensure we can't have duplicate locks
        self.locks.create_index([("resource_id", 1)], unique=True)
    
    def acquire_lock(self, resource_type, resource_id, owner_id=None, timeout=30, max_wait=60):
        """
        Acquire a lock on a specific resource.
        
        Args:
            resource_type: Type of resource (e.g., 'conversations', 'users')
            resource_id: ID of the specific resource to lock
            owner_id: ID of the entity acquiring the lock (defaults to a generated UUID)
            timeout: How long the lock is valid (in seconds)
            max_wait: Maximum time to wait for the lock (in seconds)
            
        Returns:
            lock_id: The ID of the acquired lock, or None if failed
        """
        if owner_id is None:
            owner_id = str(uuid.uuid4())
            
        # Create a unique identifier for this resource
        resource_key = f"{resource_type}:{resource_id}"
        
        # Set expiration time for the lock
        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=timeout)
        
        # Try to acquire the lock until max_wait is reached
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # First, clean up any expired locks
                self.locks.delete_many({
                    "expires_at": {"$lt": datetime.datetime.utcnow()}
                })
                
                # Try to insert a new lock document
                lock_id = str(uuid.uuid4())
                result = self.locks.insert_one({
                    "resource_id": resource_key,
                    "lock_id": lock_id,
                    "owner_id": owner_id,
                    "created_at": datetime.datetime.utcnow(),
                    "expires_at": expiration_time,
                    "resource_type": resource_type
                })
                
                if result.acknowledged:
                    return lock_id
                    
            except DuplicateKeyError:
                # Lock exists, wait and retry
                time.sleep(0.5)
                continue
                
        # Couldn't acquire the lock within max_wait time
        return None
    
    def release_lock(self, resource_type, resource_id, lock_id=None, owner_id=None):
        """
        Release a lock on a specific resource.
        
        Args:
            resource_type: Type of resource
            resource_id: ID of the specific resource
            lock_id: ID of the lock to release (optional)
            owner_id: ID of the owner to release locks for (optional)
            
        Returns:
            bool: Whether the lock was successfully released
        """
        resource_key = f"{resource_type}:{resource_id}"
        
        # Build the query based on provided parameters
        query = {"resource_id": resource_key}
        
        if lock_id:
            query["lock_id"] = lock_id
        if owner_id:
            query["owner_id"] = owner_id
            
        result = self.locks.delete_one(query)
        return result.deleted_count > 0
    
    def renew_lock(self, resource_type, resource_id, lock_id, timeout=30):
        """Extend the expiration time of an existing lock."""
        resource_key = f"{resource_type}:{resource_id}"
        new_expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=timeout)
        
        result = self.locks.update_one(
            {"resource_id": resource_key, "lock_id": lock_id},
            {"$set": {"expires_at": new_expiration}}
        )
        
        return result.matched_count > 0
    
    def get_lock_info(self, resource_type, resource_id):
        """Get information about the current lock on a resource, if any."""
        resource_key = f"{resource_type}:{resource_id}"
        return self.locks.find_one({"resource_id": resource_key})
    
    @contextmanager
    def lock(self, resource_type, resource_id, owner_id=None, timeout=30, max_wait=60):
        """Context manager for acquiring and releasing a lock."""
        lock_id = self.acquire_lock(
            resource_type, resource_id, owner_id, timeout, max_wait
        )
        
        if not lock_id:
            raise TimeoutError(f"Failed to acquire lock for {resource_type}:{resource_id}")
            
        try:
            yield lock_id
        finally:
            self.release_lock(resource_type, resource_id, lock_id)


# Example usage:

def update_conversation_safely(conversation_id, new_data):
    """Example function that safely updates a conversation with locking."""
    lock_manager = MongoDBLockManager()
    
    try:
        # Acquire a lock with a context manager
        with lock_manager.lock("conversations", conversation_id, timeout=30):
            # Now we have exclusive access to this conversation
            db = lock_manager.db
            conversations = db.conversations
            
            # Update the conversation
            result = conversations.update_one(
                {"_id": conversation_id},
                {"$set": new_data}
            )
            
            return result.modified_count > 0
            
    except TimeoutError:
        print(f"Could not acquire lock for conversation {conversation_id}")
        return False

# # Alternative usage without context manager
# def another_example_usage(resource_id, data):
#     lock_manager = MongoDBLockManager()
#     lock_id = lock_manager.acquire_lock("products", resource_id)
    
#     if not lock_id:
#         print("Could not acquire lock")
#         return False
        
#     try:
#         # Do operations with the locked resource
#         products = lock_manager.db.products
#         products.update_one({"_id": resource_id}, {"$set": data})
#         return True
#     finally:
#         # Always release the lock
#         lock_manager.release_lock("products", resource_id, lock_id)