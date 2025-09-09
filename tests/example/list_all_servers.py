#!/usr/bin/env python3
"""
List all Tango servers in the database.
"""

import os
from tango import Database

def main():
    if not os.environ.get("TANGO_HOST"):
        print("TANGO_HOST not set")
        return
    
    try:
        db = Database()
        servers = db.get_server_list("*")
        server_list = [str(server) for server in servers if str(server).strip()]
        
        print(f"Total servers: {len(server_list)}")
        for i, server in enumerate(server_list, 1):
            print(f"{i:2d}. {server}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
