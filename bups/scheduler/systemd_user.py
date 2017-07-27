import ConfigParser
import io
import os

base_dir = os.getenv("XDG_CONFIG_DIR", os.path.join(os.path.expanduser("~"), ".config"))
config_dir = os.path.join(base_dir, "systemd/user")

def is_available():
    return any(os.access(os.path.join(path, "systemctl"), os.X_OK) 
                for path in os.getenv("PATH").split(os.pathsep))

def get_timer_path(job_id):
    return os.path.join(config_dir, job_id + ".timer")

def get_service_path(job_id):
    return os.path.join(config_dir, job_id + ".service")

def new_config():
    config = ConfigParser.RawConfigParser()
    config.optionxform = str
    return config

def parse_config(timer_cfg):
    config = new_config()
    config.readfp(io.BytesIO(timer_cfg))
    period = config.get("Timer", "OnCalendar").split('/')[1]
    return { "period": period, "delay": "0" }

def get_job(job_id):
    with open(get_timer_path(job_id), "r") as f:
        cfg = parse_config(f.read())
        cfg["id"] = job_id
        return cfg

def write_config(config, file_path):
    with open(file_path, "w") as f:
        config.write(f)
    
def update_job(job):

    job_id = job["id"]
    period = job["period"]
    command = job["command"]

    # Timer
    config = new_config()
    config.add_section("Unit")
    config.set("Unit", "Description", "Bups backup manager timer")
    config.add_section("Timer")
    config.set("Timer", "OnCalendar", "*-*-1/%d" % period)
    config.set("Timer", "Persistent", "true") 
    config.add_section("Install")
    config.set("Install", "WantedBy", "timers.target")
    write_config(config, get_timer_path(job_id))

    # Create service
    config = new_config()
    config.add_section("Unit")
    config.set("Unit", "Description", "Bups backup manager service")
    config.add_section("Service")
    config.set("Service", "Type", "simple")
    config.set("Service", "ExecStart", command)
    write_config(config, get_service_path(job_id))

    # Notify systemd
    call_systemctl(["daemon-reload"])
    call_systemctl(["enable", get_timer_path(job_id)])
    call_systemctl(["start", job_id])

def remove_job(job_id):
    timer_path = get_timer_path(job_id)
    service_path = get_service_path(job_id)
    timer_basename = os.path.basename(timer_path)
    call_systemctl(["stop", timer_basename])
    call_systemctl(["disable", timer_basename])
    os.remove(timer_path)
    os.remove(service_path)

def call_systemctl(args):
    cmd = "systemctl --user %s" % " ".join(args)
    if os.system(cmd) != 0:
        raise IOError("Failed to run command: %" % cmd)

