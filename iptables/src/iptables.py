import os
import sys
import time
from datetime import datetime

import yaml
from pycti import OpenCTIConnectorHelper, get_config_variable
from stix2 import Bundle

class Iptables:
    def __init__(self):
        # Instantiate the connector helper from config
        config_file_path = os.path.dirname(os.path.abspath(__file__)) + "/config.yml"
        config = (
            yaml.load(open(config_file_path), Loader=yaml.FullLoader)
            if os.path.isfile(config_file_path)
            else {}
        )
        self.helper = OpenCTIConnectorHelper(config)
        self.test_interval = get_config_variable(
            "IPTABLES_INTERVAL", ["iptables", "interval"], config, True
        )
        self.update_existing_data = get_config_variable(
            "CONNECTOR_UPDATE_EXISTING_DATA", ["config", "update_existing_data"], config, True
        )
        self.dir_logs = get_config_variable(
            "IPTABLES_DIR_LOGS", ["iptables", "dir_logs"], config
        )

    def get_interval(self) -> int:
        return int(self.test_interval) * 60 * 60 * 24

    def get_logs(self, dir_log):
        try:
            os.stat(dir_log).st_size
            log = []
            
            log = open(dir_log,'r',encoding='utf-8')
            data = log.read()
            log.close()
            return data
        except OSError:
            self.helper.log_error("Log empty")
            time.sleep(60)
        
    def run(self) -> None:  
        self.helper.log_info("Fetching knowledge...")
        while True:
            try:
                # Anounce upcoming work
                timestamp = int(time.time())
                now = datetime.utcfromtimestamp(timestamp)
                friendly_name = "Template run @ " + now.strftime("%Y-%m-%d %H:%M:%S")
                work_id = self.helper.api.work.initiate_work(
				self.helper.connect_id, friendly_name
		)
                # Get the current timestamp and check
                timestamp = int(time.time())
                current_state = self.helper.get_state()
                if current_state is not None and "last_run" in current_state:
                    last_run = current_state["last_run"]
                    self.helper.log_info(
                        "Connector last run: "
                        + datetime.utcfromtimestamp(last_run).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )
                else:
                    last_run = None
                    self.helper.log_info("Connector has never run")
                # If the last_run is more than interval-1 day
                if last_run is None or (
                    (timestamp - last_run)
                    > ((int(self.test_interval) - 1) * 60 * 60 * 24)
                ):
                    timestamp = int(time.time())
                    now = datetime.utcfromtimestamp(timestamp)
                    friendly_name = "Connector run @ " + now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    self.get_logs(self.dir_logs)
                    
                    # Finish the work
                    self.helper.log_info(
			f"Connector successfully run, storing last_run as {str(timestamp)}"
    )              
                    message = "Last_run stored, next run in: {str(round(self.get_interval() / 60 / 60 / 24, 2))} days"
                    self.helper.api.work.to_processed(work_id, message)

                    # Store the current timestamp as a last run
                    self.helper.log_info(
                        "Connector successfully run, storing last_run as "
                        + str(timestamp)
                    )
                    self.helper.set_state({"last_run": timestamp})
                    message = (
                        "Last_run stored, next run in: "
                        + str(round(self.get_interval() / 60 / 60 / 24, 2))
                        + " days"
                    )
                    self.helper.api.work.to_processed(work_id, message)
                    self.helper.log_info(message)
                    time.sleep(60)
                else:
                    new_interval = self.get_interval() - (timestamp - last_run)
                    self.helper.log_info(
                        "Connector will not run, next run in: "
                        + str(round(new_interval / 60 / 60 / 24, 2))
                        + " days"
                    )
                    time.sleep(60)
            except (KeyboardInterrupt, SystemExit):
                self.helper.log_info("Connector stop")
                exit(0)
            except Exception as e:
                self.helper.log_error(str(e))
                time.sleep(60)

if __name__ == "__main__":
    try:
        iptablesConnector = Iptables()
        iptablesConnector.run()
    except Exception as e:
        print(e)
        time.sleep(10)
        sys.exit(0)
