import sys
import os
import subprocess
import signal
import time

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.tango_device_setup import (
    register_all_devices,
)

logger = get_logger()


def get_start_script_path():
  
    current_file = os.path.abspath(__file__)
    
    project_root = os.path.abspath(os.path.join(current_file, '..', '..', '..', '..', '..', '..'))
    start_script = os.path.join(project_root, 'scripts', 'start_tango_server.py')
    
    
    return start_script


def main():
    """Tango will be started by subprocesses"""
    logger.info("Starting Soleil Tango Server Manager")
    servers = register_all_devices()

    if not servers:
        sys.exit(1)

   
    start_script = get_start_script_path()
    if not os.path.exists(start_script):
        sys.exit(1)

    python_exe = sys.executable
    processes = []

    

    for server_name, instance_name in servers:
        try:
            logger.info(f"Starting {server_name}/{instance_name}...")
          
            
            process = subprocess.Popen(
                [python_exe, start_script, server_name, instance_name],
                stdout=None,  
                stderr=subprocess.STDOUT,  
            )
            processes.append((server_name, instance_name, process))
            logger.info(f"Started {server_name}/{instance_name} (PID: {process.pid})")
            
            time.sleep(0.5)  
        except Exception as e:
            logger.error(f" Failed to start {server_name}/{instance_name}: {e}")
            

    if not processes:
        
        sys.exit(1)

  
   

    # to exectute the stop script
    def signal_handler(sig, frame):
     
        logger.info(" Stopping all servers...")
        for server_name, instance_name, process in processes:
            try:
              
                process.terminate()
                process.wait(timeout=5)
              
            except subprocess.TimeoutExpired:
                
                process.kill()
                process.wait()
            except Exception as e:
              
                logger.error(f" Error stopping {server_name}/{instance_name}: {e}")
 
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    
    try:
        while True:
        
            for server_name, instance_name, process in processes:
                if process.poll() is not None:
                    return_code = process.returncode
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
