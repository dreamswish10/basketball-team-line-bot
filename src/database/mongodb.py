#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure
from src.config import Config
import logging

logger = logging.getLogger(__name__)

# MongoDB client instance (singleton)
_mongo_client = None
_database = None


def get_mongo_client():
    """取得 MongoDB client (singleton pattern)"""
    global _mongo_client

    if _mongo_client is None:
        try:
            logger.info(f"Connecting to MongoDB at {Config.MONGODB_URI}")
            _mongo_client = MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,  # 5秒超時
                connectTimeoutMS=10000,  # 10秒連線超時
                socketTimeoutMS=10000,   # 10秒 socket 超時
            )
            # 測試連線
            _mongo_client.admin.command('ping')
            logger.info("MongoDB connection established successfully")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    return _mongo_client


def get_database():
    """取得 MongoDB database instance"""
    global _database

    if _database is None:
        client = get_mongo_client()
        _database = client[Config.MONGODB_DB_NAME]
        logger.info(f"Using MongoDB database: {Config.MONGODB_DB_NAME}")

    return _database


def create_indexes():
    """建立所有 collection 的 indexes"""
    db = get_database()

    try:
        # Players collection indexes
        logger.info("Creating indexes for 'players' collection...")
        db.players.create_index([("user_id", ASCENDING)], unique=True, name="user_id_unique")
        db.players.create_index([("source_group_id", ASCENDING)], name="source_group_id")
        db.players.create_index([("is_registered", ASCENDING)], name="is_registered")
        db.players.create_index([("created_at", DESCENDING)], name="created_at_desc")
        db.players.create_index(
            [("participation_summary.total_divisions", DESCENDING)],
            name="total_divisions_desc"
        )

        # Groups collection indexes
        logger.info("Creating indexes for 'groups' collection...")
        db.groups.create_index([("group_id", ASCENDING)], unique=True, name="group_id_unique")
        db.groups.create_index([("active", ASCENDING)], name="active")
        db.groups.create_index([("created_at", DESCENDING)], name="created_at_desc")

        # Group members collection indexes
        logger.info("Creating indexes for 'group_members' collection...")
        db.group_members.create_index(
            [("group_id", ASCENDING), ("user_id", ASCENDING)],
            unique=True,
            name="group_user_unique"
        )
        db.group_members.create_index(
            [("group_id", ASCENDING), ("is_active", ASCENDING)],
            name="group_active"
        )
        db.group_members.create_index([("user_id", ASCENDING)], name="user_id")
        db.group_members.create_index([("is_active", ASCENDING)], name="is_active")

        # Divisions collection indexes
        logger.info("Creating indexes for 'divisions' collection...")
        db.divisions.create_index([("created_at", DESCENDING)], name="created_at_desc")
        db.divisions.create_index(
            [("group_id", ASCENDING), ("created_at", DESCENDING)],
            name="group_created"
        )
        db.divisions.create_index(
            [("deleted", ASCENDING), ("created_at", DESCENDING)],
            name="deleted_created"
        )
        db.divisions.create_index(
            [("teams.players.user_id", ASCENDING), ("created_at", DESCENDING)],
            name="player_divisions"
        )
        db.divisions.create_index([("division_name", ASCENDING)], name="division_name")

        logger.info("All indexes created successfully")

    except OperationFailure as e:
        logger.error(f"Failed to create indexes: {e}")
        raise


def init_mongodb():
    """初始化 MongoDB - 建立連線並設定 indexes"""
    try:
        logger.info("Initializing MongoDB...")

        # 建立連線並測試
        db = get_database()

        # 建立 indexes
        create_indexes()

        # 列出所有 collections
        collections = db.list_collection_names()
        logger.info(f"Available collections: {collections}")

        logger.info("MongoDB initialization completed successfully")
        return True

    except Exception as e:
        logger.error(f"MongoDB initialization failed: {e}")
        raise


def close_connection():
    """關閉 MongoDB 連線"""
    global _mongo_client, _database

    if _mongo_client is not None:
        logger.info("Closing MongoDB connection...")
        _mongo_client.close()
        _mongo_client = None
        _database = None
        logger.info("MongoDB connection closed")


# 用於測試
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # 初始化 MongoDB
        init_mongodb()

        # 測試連線
        db = get_database()
        result = db.command("ping")
        print(f"MongoDB ping successful: {result}")

        # 列出 collections
        collections = db.list_collection_names()
        print(f"Collections: {collections}")

        # 測試完成後關閉連線
        close_connection()

    except Exception as e:
        print(f"Error: {e}")
